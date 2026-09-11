#!/usr/bin/env python3
"""
Rhode Jeans — OPERADOR de Flash Sale (reconciliador idempotente)
-----------------------------------------------------------------
Opera o dia sozinho, em dois trilhos:

  1. CREATORS — cada handle da config tem que ter uma flash ativa. Se falta (ou
     está pra vencer), o operador DUPLICA a flash padrão da loja com o título
     "Flash Sale- @handle" (mesmos produtos, mesmos preços — decisão do dono).
  2. LIVE PRÓPRIA — nos dias/horário da regra, confirma que a live existe de
     verdade e cria a ESCADA de rajadas do dia (blocos curtos de preço no hero).

É RECONCILIADOR, não fila: a verdade é o estado das activities na TikTok Shop,
lido a cada tick. Rodar 10x ou 1x no mesmo dia dá o mesmo resultado — ele só cria
o que está faltando. Não guarda estado local pra dar errado.

Régua de preço da rajada (P21, docs/DECISOES-E-PREMISSAS.md):
  contrib/peça = lista × 0,7066 − CPV · piso = CPV ÷ 0,7066 (CPV 45 → R$ 63,69)
  R$ 69,90 de lista no hero tem folga 2,1× — é o ponto medido, não chute.

Uso:
  python3 operador_flash.py                 # dry-run: diz o que faria
  python3 operador_flash.py --executar      # opera (é o que o cron roda)
  python3 operador_flash.py --executar --forcar-live   # ignora a checagem de live
"""
import os, re, sys, time, json, argparse
from datetime import datetime, timedelta, timezone

import requests
import criar_flash_sale as F          # api(), catalogo(), cpv_por_ref(), piso(), contrib()

BRT      = F.BRT
BASE     = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.environ.get("OPERADOR_FLASH_CONFIG") or os.path.join(BASE, "config", "operador_flash.json")
OUT_DIR  = os.path.join(BASE, "flash")
MAX_SKU_POR_CALL = 250               # a API corta em 300 SKUs por chamada


def agora():
    return datetime.now(BRT)


def cfg():
    with open(CFG_PATH) as f:
        return json.load(f)



API_LOG = os.path.join(BASE, "logs", "flash_api.jsonl")


PAUSA_ESCRITA = 2.5          # s entre escritas — a Promotion API corta rajada (36009002)
_ultima_escrita = [0.0]


def escrever(method, path, body, tentativas=4):
    """Chamada de ESCRITA com pacing, backoff e registro em disco (req + resp crus).

    A Promotion API derruba escrita em rajada com 36009002. Duas rodadas do canário
    morreram assim: o retry de título disparou no mesmo segundo do create anterior.
    Aqui todo write respeita um intervalo mínimo e recua quando leva rate limit.
    """
    r = None
    for n in range(tentativas):
        espera = PAUSA_ESCRITA - (time.time() - _ultima_escrita[0])
        if espera > 0:
            time.sleep(espera)
        r = F.api(method, path, params={}, body=body)
        _ultima_escrita[0] = time.time()
        if r.get("code") != 36009002:
            break
        recuo = 15 * (n + 1)
        print(f"  ⏳ rate limit — aguardando {recuo}s ({n+1}/{tentativas-1})")
        time.sleep(recuo)
    try:
        os.makedirs(os.path.dirname(API_LOG), exist_ok=True)
        with open(API_LOG, "a") as f:
            f.write(json.dumps({
                "ts": agora().isoformat(), "method": method, "path": path,
                "body_amostra": {
                    "activity_id": (body or {}).get("activity_id"),
                    "n_produtos": len((body or {}).get("products") or []),
                    "n_skus": sum(len(p.get("skus") or []) for p in ((body or {}).get("products") or [])),
                    "primeiro_produto": ((body or {}).get("products") or [{}])[0],
                } if "products" in (body or {}) else body,
                "resposta": r,
            }, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"  (aviso: nao consegui gravar {API_LOG}: {e})")
    return r


# ── ESTADO REAL (a TikTok Shop é a fonte de verdade) ────────────────────
def activities(status=("ONGOING", "NOT_START")):
    out = []
    for st in status:
        tok = None
        while True:
            body = {"page_size": 50, "status": st}
            if tok:
                body["page_token"] = tok
            r = F.chamar("POST", "/promotion/202309/activities/search", params={}, body=body)
            d = r.get("data") or {}
            for a in d.get("activities", []) or []:
                out.append({"id": str(a["id"]), "title": a.get("title") or "", "status": st,
                            "tipo": a.get("activity_type"),
                            "begin": int(a.get("begin_time") or 0), "end": int(a.get("end_time") or 0)})
            tok = d.get("next_page_token")
            if not tok:
                break
    return out


def detalhe(aid):
    r = F.chamar("GET", f"/promotion/202309/activities/{aid}", params={})
    return (r.get("data") or {}) if r.get("code") == 0 else {}


def produtos_do_template(det):
    """Copia produtos+preços do template no formato do Update Activity Product."""
    saida = []
    for p in det.get("products", []) or []:
        skus = []
        for s in p.get("skus", []) or []:
            amt = (s.get("activity_price") or {}).get("amount")
            if not amt:
                continue
            skus.append({"id": str(s["id"]), "activity_price_amount": str(amt),
                         "quantity_limit": -1, "quantity_per_user": -1})
        if skus:
            saida.append({"id": str(p["id"]), "quantity_limit": -1,
                          "quantity_per_user": -1, "skus": skus})
    return saida


# ── ESCRITA ─────────────────────────────────────────────────────────────
def criar(titulo, ini, fim, produtos, log):
    """Cria a activity e anexa os produtos em lotes. Rollback se o anexo falhar."""
    base_titulo, r = titulo, None
    for tentativa in range(6):
        r = escrever("POST", "/promotion/202309/activities", {
            "title": titulo, "activity_type": "FLASHSALE", "product_level": "VARIATION",
            "duration_type": "NORMAL", "begin_time": int(ini.timestamp()), "end_time": int(fim.timestamp()),
            "participation_limit": [{"type": "BUYER_NO_LIMIT"}]})
        if r.get("code") != 17029004:
            break
        # nome ja usado por uma activity DEACTIVATED/EXPIRED (a busca de idempotencia
        # so enxerga ONGOING/NOT_START). Varia o nome ate achar um livre.
        titulo = f"{base_titulo} {chr(98 + tentativa)}"[:50]
        log(f"  nome ocupado — tentando '{titulo}'")
    if r.get("code") != 0:
        log(f"✖ create '{titulo}': {json.dumps(r, ensure_ascii=False)}")
        return None
    aid = str((r.get("data") or {}).get("activity_id"))

    # lotes de ≤250 SKUs (a API recusa acima de 300 por chamada)
    lote, n_sku, enviados = [], 0, 0
    def flush():
        nonlocal lote, enviados
        if not lote:
            return True
        r2 = escrever("PUT", f"/promotion/202309/activities/{aid}/products",
                      {"activity_id": aid, "products": lote})
        if r2.get("code") != 0:
            log(f"✖ anexar em '{titulo}' (lote {len(lote)} anúncios / {n_sku} SKU): "
                f"{json.dumps(r2, ensure_ascii=False)}")
            p0 = dict(lote[0]); p0["skus"] = p0["skus"][:1]
            rp = escrever("PUT", f"/promotion/202309/activities/{aid}/products",
                          {"activity_id": aid, "products": [p0]})
            log(f"  sonda 1 SKU ({p0['skus'][0].get('id')} a R$ "
                f"{p0['skus'][0].get('activity_price_amount')}): "
                f"code={rp.get('code')} msg={rp.get('message')!r}")
            return False
        enviados += (r2.get("data") or {}).get("total_count") or 0
        lote = []
        return True

    for p in produtos:
        if n_sku + len(p["skus"]) > MAX_SKU_POR_CALL and lote:
            if not flush():
                escrever("POST", f"/promotion/202309/activities/{aid}/deactivate", {})
                log(f"  ↳ activity {aid} DESATIVADA (rollback)")
                return None
            n_sku = 0
        lote.append(p); n_sku += len(p["skus"])
    if not flush():
        escrever("POST", f"/promotion/202309/activities/{aid}/deactivate", {})
        log(f"  ↳ activity {aid} DESATIVADA (rollback)")
        return None

    log(f"✓ criada '{titulo}' · id {aid} · {enviados} SKU · {ini:%d/%m %H:%M}→{fim:%d/%m %H:%M}")
    return {"activity_id": aid, "titulo": titulo, "skus": enviados,
            "begin": int(ini.timestamp()), "end": int(fim.timestamp())}


def desativar(aid, log, motivo=""):
    r = escrever("POST", f"/promotion/202309/activities/{aid}/deactivate", {})
    ok = r.get("code") == 0
    log(f"{'✓' if ok else '✖'} encerrada {aid} {motivo}" if ok else
        f"✖ encerrar {aid}: {r.get('code')} {r.get('message')}")
    return ok


# ── TRILHO 1 · CREATORS ─────────────────────────────────────────────────
def handle_no_titulo(t):
    m = re.findall(r"@([A-Za-z0-9_.]+)", t or "")
    return "@" + m[0].lower() if m else None


def trilho_creators(c, ativas, executar, log):
    if not c.get("ativo"):
        log("creators: desligado na config"); return []

    tid = c.get("template_activity_id")
    det = None
    if not tid:
        # A flash padrão é LONGA (14d). As rajadas da live também são FLASHSALE e têm
        # MAIS SKUs, mas com preço de rajada — clonar uma delas num flash de 14 dias
        # jogaria o preço de rajada no catálogo inteiro por duas semanas. Por isso o
        # filtro de duração vem ANTES do critério de tamanho.
        minimo = timedelta(days=max(2, c.get("duracao_dias", 14) // 2))
        cands = [a for a in ativas if a["tipo"] == "FLASHSALE" and a["status"] == "ONGOING"
                 and (a["end"] - a["begin"]) >= minimo.total_seconds()]
        melhor, d_melhor, n_melhor = None, None, 0
        for a in cands:
            d = detalhe(a["id"])
            n = sum(len(p.get("skus") or []) for p in (d.get("products") or []))
            if n > n_melhor:
                melhor, d_melhor, n_melhor = a, d, n
        if not melhor:
            log(f"✖ creators: nenhuma flash com ≥{minimo.days}d pra servir de template"); return []
        tid, det = melhor["id"], d_melhor
        dur = (melhor["end"] - melhor["begin"]) / 86400
        log(f"template: '{melhor['title']}' (id {tid}, {n_melhor} SKU, {dur:.0f}d)")
    produtos = produtos_do_template(det if det is not None else detalhe(tid))
    if not produtos:
        log(f"✖ creators: template {tid} sem produtos"); return []
    precos = [float(s["activity_price_amount"]) for p in produtos for s in p["skus"]]
    log(f"  preços do template: R$ {min(precos):.2f}–{max(precos):.2f} "
        f"({sum(len(p['skus']) for p in produtos)} SKU)")

    limite = agora() + timedelta(hours=c.get("renovar_faltando_horas", 48))
    tem = {}
    for a in ativas:
        h = handle_no_titulo(a["title"])
        if h and a["tipo"] == "FLASHSALE":
            tem[h] = max(tem.get(h, 0), a["end"])

    feitos, pendentes = [], []
    for h in [x.lower() for x in c.get("handles", [])]:
        fim_atual = tem.get(h)
        if fim_atual and datetime.fromtimestamp(fim_atual, BRT) > limite:
            continue
        pendentes.append(h)

    if not pendentes:
        log(f"creators: {len(c.get('handles', []))} handles, todos com flash válida ✓")
        return []

    # RODÍZIO. Duas promoções catálogo-inteiro não coexistem pela API (17029022) —
    # não importa a duração. Então é UMA creator por vez, servindo primeiro quem está
    # há mais tempo sem flash. Encurtar a duração é o que faz a fila girar.
    pendentes.sort(key=lambda h: tem.get(h, 0))
    horas = c.get("duracao_horas") or c.get("duracao_dias", 14) * 24
    log(f"creators: {len(pendentes)} sem flash válida · rodízio de {horas}h → "
        f"{len(pendentes) * horas / 24:.1f}d pra fila inteira girar")

    for h in pendentes[:c.get("max_por_tick", 1)]:
        ini = agora() + timedelta(minutes=5)
        fim = ini + timedelta(hours=horas)
        titulo = f"FLASH-{h}-{ini:%d%m}"[:50]           # taxonomia interna (regra do dono)
        presos = conflitos(produtos, ativas, ini, fim)
        if presos:
            log(f"✖ {h}: catálogo preso por {len(presos)} promoção(ões) na janela — "
                f"{', '.join(t[:26] for t in presos[:3])}")
            log("  ↳ rode --liberar antes; criar agora só gastaria chamada e rollback")
            break
        if not executar:
            log(f"[dry] duplicaria template p/ {h} → '{titulo}' "
                f"({len(produtos)} anúncios · {ini:%d/%m %H:%M}→{fim:%d/%m %H:%M})")
            continue
        r = criar(titulo, ini, fim, produtos, log)
        if r:
            r.update({"trilho": "creator", "handle": h, "template": tid})
            feitos.append(r)
    return feitos


# ── TRILHO 2 · LIVE PRÓPRIA ─────────────────────────────────────────────
def live_ativa_hoje():
    """Sinal de live: room da loja com movimento hoje (live_sessao, via GMV Max).
    Tem latência do report de ads — por isso é CONFIRMAÇÃO, não gatilho."""
    hoje = agora().strftime("%Y-%m-%d")
    try:
        r = requests.get(f"{F.SB_URL}/rest/v1/live_sessao"
                         f"?select=room_id,receita,pedidos,views,updated_at,origem"
                         f"&data=eq.{hoje}&origem=eq.propria&order=id&limit=100",
                         headers=F.SBH, timeout=60)
        rows = r.json() if r.ok else []
    except Exception:
        rows = []
    vivos = [x for x in rows if (x.get("views") or 0) > 0 or (x.get("pedidos") or 0) > 0]
    return (len(vivos) > 0), vivos


def blocos_do_dia(lp, base):
    e = lp["escada"]
    out = []
    for i in range(e["blocos"]):
        ini = base + timedelta(minutes=e["atraso_inicial_min"] + i * e["intervalo_min"])
        out.append((i + 1, ini, ini + timedelta(minutes=e["duracao_min"])))
    return out


def trilho_live(lp, ativas, executar, forcar, log):
    if not lp.get("ativo"):
        log("live: desligado na config"); return []
    ag = agora()
    if ag.weekday() not in lp.get("dias_semana", []):
        log(f"live: hoje ({ag:%a}) não é dia de live na regra"); return []

    hh, mm = [int(x) for x in lp["hora_inicio"].split(":")]
    base = ag.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if ag < base:
        log(f"live: ainda antes do horário ({lp['hora_inicio']} BRT) — nada a fazer"); return []
    if ag > base + timedelta(minutes=lp.get("janela_confirmacao_min", 60)):
        log("live: passou da janela de confirmação do dia"); return []

    viva, rooms = live_ativa_hoje()
    if not viva and not forcar:
        log(f"live: sem sinal de room ativo hoje ainda — não cria (use --forcar-live se estiver no ar)")
        return []
    log(f"live: confirmada ({len(rooms)} room ativo)" if viva else "live: FORÇADA pelo operador")

    # preço da rajada: valida piso por CPV antes de qualquer escrita
    cpvs = F.cpv_por_ref()
    cat = F.catalogo()
    preco = float(lp["preco_lista"])
    produtos, linhas = [], []
    for pid, p in cat.items():
        skus = []
        for s in p["skus"]:
            if s["ref"] not in lp["refs"] or s["estoque"] <= 0:
                continue
            cpv = cpvs.get(s["ref"])
            if not cpv:
                log(f"✖ rajada: {s['ref']} sem CPV em custos_sku — abortando o trilho"); return []
            c = F.contrib(preco, cpv)
            if c < lp.get("contrib_min", 0.0):
                log(f"✖ rajada: R$ {preco:.2f} dá contrib R$ {c:.2f} no {s['ref']} "
                    f"(CPV {cpv:.0f}, piso R$ {F.piso(cpv):.2f}) — abortando"); return []
            if preco >= s["preco"]:
                continue
            skus.append({"id": s["id"], "activity_price_amount": f"{preco:.2f}",
                         "quantity_limit": -1, "quantity_per_user": -1})
            linhas.append((s["ref"], s["preco"], preco, cpv, c))
        if skus:
            produtos.append({"id": pid, "quantity_limit": -1, "quantity_per_user": -1, "skus": skus})
    if not produtos:
        log(f"✖ rajada: nenhum SKU de {','.join(lp['refs'])} elegível (estoque/preço)"); return []
    cs = [l[4] for l in linhas]
    log(f"rajada: {sum(len(p['skus']) for p in produtos)} SKU a R$ {preco:.2f} · "
        f"contrib/peça R$ {min(cs):.2f}–{max(cs):.2f}")

    titulos = {a["title"] for a in ativas}
    feitos = []
    for idx, ini, fim in blocos_do_dia(lp, base):
        titulo = f"Rajada {ini:%d/%m} B{idx} {ini:%H%M}"[:50]
        if titulo in titulos:
            log(f"  B{idx} já existe ✓"); continue
        if fim <= ag:
            log(f"  B{idx} já passou — pulando"); continue
        if ini <= ag:
            ini = ag + timedelta(minutes=2)   # begin_time tem que ser futuro (17029005)
        if not executar:
            log(f"[dry] criaria '{titulo}' {ini:%H:%M}→{fim:%H:%M}"); continue
        r = criar(titulo, ini, fim, produtos, log)
        if r:
            r.update({"trilho": "rajada", "bloco": idx, "preco": preco})
            feitos.append(r)
    return feitos



# ── TRILHO 3 · DUPLICAR TEMPLATE EM ESCADA (live própria) ───────────────
def trilho_duplicar(template_id, de, ate, cada, ativas, executar, log):
    """Escada de blocos consecutivos duplicando um template.

    Flash de live própria expira e precisa ser RESUBIDA — por isso blocos curtos
    encostados um no outro cobrindo a live inteira, e não uma promoção longa.

    Cria um bloco por vez e PARA no primeiro erro, com a resposta crua da API.
    Queimar 16 tentativas repetindo o mesmo erro não ensina nada e suja a loja.
    """
    det = detalhe(template_id)
    if not det:
        log(f"✖ template {template_id} não encontrado"); return []
    produtos = produtos_do_template(det)
    if not produtos:
        log(f"✖ template {template_id} sem produtos"); return []
    n_sku = sum(len(p["skus"]) for p in produtos)
    precos = [float(s["activity_price_amount"]) for p in produtos for s in p["skus"]]
    log(f"template '{det.get('title')}' · {len(produtos)} anúncios · {n_sku} SKU · "
        f"R$ {min(precos):.2f}–{max(precos):.2f}")

    ag = agora()
    def hoje_as(hhmm):
        h, m = [int(x) for x in hhmm.split(":")]
        return ag.replace(hour=h, minute=m, second=0, microsecond=0)
    ini_live, fim_live = hoje_as(de), hoje_as(ate)
    if fim_live <= ini_live:
        log("✖ --ate tem que ser depois de --de"); return []

    blocos, t = [], ini_live
    while t < fim_live:
        blocos.append((t, min(t + timedelta(minutes=cada), fim_live)))
        t += timedelta(minutes=cada)
    log(f"escada: {len(blocos)} blocos de {cada}min · {ini_live:%H:%M}→{fim_live:%H:%M} BRT")

    titulos = {a["title"] for a in ativas}
    feitos = []
    for b_ini, b_fim in blocos:
        titulo = f"LIVE-{b_ini:%d%m}-{b_ini:%H%M}"      # taxonomia interna (regra do dono)
        if titulo in titulos:
            log(f"  {titulo} já existe ✓"); continue
        if b_fim <= ag:
            log(f"  {titulo} já passou — pulando"); continue
        if b_ini <= ag:
            b_ini = ag + timedelta(minutes=2)      # begin_time tem que ser futuro (17029005)
            if b_ini >= b_fim:
                log(f"  {titulo} curto demais agora — pulando"); continue
        if not executar:
            log(f"  [dry] criaria '{titulo}' {b_ini:%H:%M}→{b_fim:%H:%M} ({n_sku} SKU)"); continue
        r = criar(titulo, b_ini, b_fim, produtos, log)
        if not r:
            log(f"  ⛔ PAREI no bloco {titulo} — {len(feitos)} criado(s) antes dele")
            break
        r.update({"trilho": "duplicar", "template": str(template_id)})
        feitos.append(r)
    return feitos


# ── CONFLITO DE SKU · a regra que manda na operação ─────────────────────
def conflitos(produtos, ativas, ini, fim):
    """Títulos das activities que prendem SKUs destes produtos na janela ini→fim.

    A API recusa promoção nova que toque num SKU já preso (17029022). A UI da TikTok
    NÃO passa por essa regra — foi por isso que a loja acumulou 14 promoções
    catálogo-inteiro sobrepostas, e é por isso que nada entra por API enquanto elas
    existirem. Checar antes evita criar activity que vai morrer no rollback.
    """
    alvo = {str(s["id"]) for p in produtos for s in p["skus"]}
    fora = []
    for a in ativas:
        if not (a["begin"] < fim.timestamp() and a["end"] > ini.timestamp()):
            continue                                    # não encosta na janela
        d = detalhe(a["id"])
        ids = {str(x["id"]) for q in (d.get("products") or []) for x in (q.get("skus") or [])}
        if alvo & ids:
            fora.append(a["title"])
    return fora


# ── LIBERAR · desativa o que prende os SKUs de uma janela ───────────────
def trilho_liberar(template_id, de, ate, ativas, executar, log, tudo=False):
    """Lista (e desativa) as activities que seguram SKUs do template numa janela.

    DESTRUTIVO: dry-run é o padrão e a lista inteira sai antes de qualquer escrita.
    """
    det = detalhe(template_id)
    produtos = produtos_do_template(det)
    alvo = {str(s["id"]) for p in produtos for s in p["skus"]}
    if not alvo:
        log(f"✖ template {template_id} sem SKUs"); return []

    ag = agora()
    def hoje_as(hhmm):
        h, m = [int(x) for x in hhmm.split(":")]
        return ag.replace(hour=h, minute=m, second=0, microsecond=0)
    ini, fim = hoje_as(de), hoje_as(ate)
    log(f"template '{det.get('title')}' · {len(alvo)} SKU · janela {ini:%d/%m %H:%M}→{fim:%H:%M}")

    bloqueiam, presos = [], set()
    for a in ativas:
        if not (a["begin"] < fim.timestamp() and a["end"] > ini.timestamp()):
            continue
        d = detalhe(a["id"])
        ids = alvo & {str(x["id"]) for q in (d.get("products") or []) for x in (q.get("skus") or [])}
        if ids:
            bloqueiam.append((len(ids), a)); presos |= ids
    if not bloqueiam:
        log("nada bloqueia essa janela ✓"); return []

    # FLASHSALE = promoção temporária (os clones). DIRECT_DISCOUNT / FIXED_PRICE são
    # política de preço da loja (ex: 'Desconto Produto', 'Desconto Card Video') e NÃO
    # entram no alvo por padrão — desativar isso seria mexer em precificação, não em flash.
    alvos = [(n, a) for n, a in bloqueiam if a["tipo"] == "FLASHSALE"] if not tudo else bloqueiam
    poupados = [(n, a) for n, a in bloqueiam if (n, a) not in alvos]

    bloqueiam.sort(key=lambda x: -x[0]); alvos.sort(key=lambda x: -x[0])
    log(f"{len(bloqueiam)} activity(ies) segurando SKUs do template:")
    for n, a in bloqueiam:
        f_ = datetime.fromtimestamp(a["end"], BRT)
        marca = "→" if (n, a) in alvos else " "
        log(f"  {marca} {n:>3} SKU · {a['tipo']:<15} · até {f_:%d/%m %H:%M} · "
            f"{a['title'][:36]:<36} · {a['id']}")
    log(f"→ {len(presos)}/{len(alvo)} SKUs presos · {len(alvo) - len(presos)} livres agora")

    # quanto sobra preso DEPOIS de desativar só os alvos
    resta = set()
    for n, a in poupados:
        d = detalhe(a["id"])
        resta |= alvo & {str(x["id"]) for q in (d.get("products") or []) for x in (q.get("skus") or [])}
    log(f"alvo: {len(alvos)} FLASHSALE · poupados: {len(poupados)} (política de preço)")
    log(f"depois de liberar → {len(alvo) - len(resta)}/{len(alvo)} SKUs livres "
        f"({len(resta)} seguem presos pelos poupados)")

    if not executar:
        log("[dry] nada desativado. Confira a lista e repita com --executar.")
        return []
    feitos = []
    for n, a in alvos:
        if desativar(a["id"], log, f"({n} SKU · {a['title'][:30]})"):
            feitos.append({"trilho": "liberar", "activity_id": a["id"], "titulo": a["title"],
                           "skus": n, "begin": a["begin"], "end": a["end"]})
    return feitos


# ── MAIN ────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Operador de flash sale da Rhode.")
    ap.add_argument("--executar", action="store_true", help="escreve de verdade (sem isso é dry-run)")
    ap.add_argument("--forcar-live", action="store_true", help="cria a escada mesmo sem sinal de room ativo")
    ap.add_argument("--so", choices=["creators", "live"], help="roda só um trilho")
    ap.add_argument("--duplicar", help="activity_id do template a duplicar em escada")
    ap.add_argument("--liberar", help="activity_id do template: desativa quem prende os SKUs dele")
    ap.add_argument("--tudo", action="store_true",
                    help="--liberar: inclui DIRECT_DISCOUNT/FIXED_PRICE (política de preço). Cuidado.")
    ap.add_argument("--de", default="11:00", help="início da live, HH:MM BRT")
    ap.add_argument("--ate", default="15:00", help="fim da live, HH:MM BRT")
    ap.add_argument("--cada", type=int, default=15, help="minutos por bloco")
    a = ap.parse_args()

    linhas = []
    def log(m):
        print("  " + m); linhas.append(m)

    ag = agora()
    print(f"\n═══ Operador de Flash · {ag:%d/%m/%Y %H:%M} BRT "
          f"{'(DRY-RUN)' if not a.executar else ''} ═══")
    c = cfg()
    ativas = activities()
    log(f"estado: {len(ativas)} activities ONGOING/NOT_START na loja")

    feitos = []
    if a.liberar:                       # destrave: DESTRUTIVO, dry-run por padrão
        print("\n── liberar SKUs ──")
        feitos += trilho_liberar(a.liberar, a.de, a.ate, ativas, a.executar, log, a.tudo)
        _fechar(ag, linhas, feitos, a.executar)
        return
    if a.duplicar:                      # modo escada: ignora os trilhos recorrentes
        print("\n── escada (duplicar template) ──")
        feitos += trilho_duplicar(a.duplicar, a.de, a.ate, a.cada, ativas, a.executar, log)
        _fechar(ag, linhas, feitos, a.executar)
        return
    if a.so != "live":
        print("\n── creators ──")
        feitos += trilho_creators(c["creators"], ativas, a.executar, log)
    if a.so != "creators":
        print("\n── live própria ──")
        feitos += trilho_live(c["live_propria"], ativas, a.executar, a.forcar_live, log)

    _fechar(ag, linhas, feitos, a.executar)


def _fechar(ag, linhas, feitos, executar):
    # relatório: o Actions commita, a rotina cloud lê e posta no Notion (padrão do pace)
    os.makedirs(OUT_DIR, exist_ok=True)
    md = [f"# Operador de Flash — {ag:%d/%m/%Y %H:%M} BRT", ""]
    md += [f"- {l}" for l in linhas]
    if feitos:
        md += ["", "## Criado neste tick", "",
               "| trilho | título | id | SKUs | janela |", "|---|---|---|---:|---|"]
        for f_ in feitos:
            b = datetime.fromtimestamp(f_["begin"], BRT); e = datetime.fromtimestamp(f_["end"], BRT)
            md.append(f"| {f_['trilho']} | {f_['titulo']} | {f_['activity_id']} | {f_['skus']} | "
                      f"{b:%d/%m %H:%M}→{e:%d/%m %H:%M} |")
    else:
        md += ["", "**Nada criado neste tick.**"]
    with open(os.path.join(OUT_DIR, "OPERADOR_ATUAL.md"), "w") as f:
        f.write("\n".join(md) + "\n")
    if executar and feitos:        # so loga tick que MEXEU (o cron commita por este arquivo)
        with open(os.path.join(OUT_DIR, "operador_log.jsonl"), "a") as f:
            f.write(json.dumps({"ts": ag.isoformat(), "linhas": linhas, "feitos": feitos},
                               ensure_ascii=False) + "\n")
    print(f"\n  → flash/OPERADOR_ATUAL.md ({len(feitos)} criada(s))\n")


if __name__ == "__main__":
    main()
