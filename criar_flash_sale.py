#!/usr/bin/env python3
"""
Rhode Jeans — Criar Flash Sale por API (Promotion API 202309)
--------------------------------------------------------------
Cria a flash dedicada de uma creator direto na TikTok Shop, no MESMO formato que
o time sobe na mão hoje ("Flash Sale- @handle", product_level=VARIATION, preço
por SKU). O `coletar_flash_sales.py` (cron 30min) publica no Hub sozinho depois.

Por que existe — os dois erros que já custaram dinheiro medido (P21, docs/DECISOES-E-PREMISSAS.md):
  • ESCOPO: a promoção de 04/09 vazou p/ 5 famílias não promovidas — −R$351 contra
    +R$110 de ganho (3,2x). Aqui o escopo é lista explícita de REF e o nível é
    VARIATION: entra só o SKU pedido, nunca o anúncio inteiro.
  • PREÇO: preço fixo não é desconto igual ("R$69,90 pras duas" = 11% num REF e
    22% no outro), e a mesma etiqueta rende R$4,37/peça no CPV 45 e R$0,50 no CPV
    49. O padrão aqui é contribuição-alvo por peça, resolvida por faixa de CPV.

Régua (P21 — base é o preço de LISTA; o cupom da plataforma é subsídio do TikTok):
    contrib/peça = preço_lista × 0,7066 − CPV
    piso (contrib = 0) = CPV ÷ 0,7066     → CPV 45 = R$ 63,69 · CPV 49 = R$ 69,35

Uso:
  # dry-run (PADRÃO): mostra preço e contribuição por SKU, não cria nada
  python3 criar_flash_sale.py --handle @lobarrosss --refs REF516,REF551 \
      --contrib-alvo 6 --inicio +5m --duracao 3h

  # cria de verdade
  ...mesmo comando... --confirmar

  # encerra antes da hora
  python3 criar_flash_sale.py --encerrar 7683247273749890834 --confirmar

ROOT-level de propósito (não dispara etl_sync.yml).
"""
import os, re, sys, json, time, hmac, math, hashlib, argparse, requests
from datetime import datetime, timedelta, timezone

from coletar_dados import chamar, APP_KEY, APP_SECRET, ACCESS_TOKEN, SHOP_CIPHER, BASE_URL, assinar

TAXA      = 0.7066          # settlement ÷ revenue (agosto/26, n=2.143 — P21)
BRT       = timezone(timedelta(hours=-3))
SB_URL    = os.environ["SUPABASE_URL"]
SB_KEY    = os.environ["SUPABASE_SERVICE_KEY"]
SBH       = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json"}
LOG       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "flash_sales_criadas.jsonl")


# ── API (o chamar() do coletor não faz PUT) ─────────────────────────────
def api(method, path, params=None, body=None):
    if method in ("GET", "POST"):
        return chamar(method, path, params=params, body=body)
    p = dict(params or {})
    p.update({"app_key": APP_KEY, "timestamp": int(time.time()),
              "sign_method": "HmacSHA256", "shop_cipher": SHOP_CIPHER})
    bs = json.dumps(body, separators=(",", ":")) if body is not None else ""
    p["sign"] = assinar(path, p, bs)
    r = requests.request(method, BASE_URL + path, params=p, data=bs or None,
                         headers={"Content-Type": "application/json",
                                  "x-tts-access-token": ACCESS_TOKEN}, timeout=60)
    try:
        return r.json()
    except Exception:
        return {"code": -1, "message": f"HTTP {r.status_code}: resposta não-JSON"}


def morrer(msg):
    print(f"\n  ✖ ABORTADO — {msg}")
    sys.exit(1)


# ── FONTES ──────────────────────────────────────────────────────────────
def ref_de(seller_sku):
    m = re.match(r"(REF\d{3})", (seller_sku or "").upper())
    return m.group(1) if m else None


def catalogo():
    """product_id → {title, skus:[{id, seller_sku, ref, preco, estoque}]}. Só produtos ativos."""
    out, cursor, pag = {}, "", 0
    while pag < 50:
        pag += 1
        params = {"page_size": 100}
        if cursor:
            params["page_token"] = cursor
        r = chamar("POST", "/product/202309/products/search", params=params, body={"status": "ACTIVATE"})
        if r.get("code") != 0:
            morrer(f"products/search: {r.get('message')}")
        d = r.get("data") or {}
        for p in d.get("products", []) or []:
            skus = []
            for s in p.get("skus", []) or []:
                ssku = s.get("seller_sku") or ""
                skus.append({
                    "id": str(s["id"]), "seller_sku": ssku, "ref": ref_de(ssku),
                    "preco": float((s.get("price") or {}).get("tax_exclusive_price") or 0),
                    "estoque": sum(i.get("quantity", 0) for i in (s.get("inventory") or [])),
                })
            out[str(p["id"])] = {"title": p.get("title", ""), "skus": skus}
        cursor = d.get("next_page_token", "")
        if not cursor:
            break
    return out


def cpv_por_ref():
    """REF → CPV (tabela custos_sku, mesma fonte do console de conciliação)."""
    r = requests.get(f"{SB_URL}/rest/v1/custos_sku?select=ref,cpv&order=ref&limit=1000",
                     headers=SBH, timeout=60)
    r.raise_for_status()
    cpv = {}
    for x in r.json():
        ref = ref_de(x.get("ref")) or (x.get("ref") or "").upper()
        c = float(x.get("cpv") or 0)
        if ref and c > 0:
            cpv.setdefault(ref, c)
    return cpv


def skus_ocupados():
    """SKUs já presos em activity ONGOING/NOT_START.
    A API recusa (17029022) SKU em duas promoções ao mesmo tempo — sem essa checagem
    a criação falha no meio, com a activity já criada e vazia."""
    ocupados = {}
    for st in ("ONGOING", "NOT_START"):
        tok = None
        while True:
            body = {"page_size": 50, "status": st}
            if tok:
                body["page_token"] = tok
            r = chamar("POST", "/promotion/202309/activities/search", params={}, body=body)
            d = r.get("data") or {}
            for a in d.get("activities", []) or []:
                det = chamar("GET", f"/promotion/202309/activities/{a['id']}", params={})
                for p in ((det.get("data") or {}).get("products") or []):
                    for s in (p.get("skus") or []):
                        ocupados[str(s.get("id"))] = a.get("title") or a.get("id")
            tok = d.get("next_page_token")
            if not tok:
                break
    return ocupados


# ── PREÇO ───────────────────────────────────────────────────────────────
def piso(cpv):
    return round(cpv / TAXA, 2)


def contrib(preco, cpv):
    return round(preco * TAXA - cpv, 2)


def termina_em_90(v):
    """Sobe pro próximo X,90 (nunca desce — arredondar pra baixo come contribuição)."""
    base = math.floor(v)
    return round(base + 0.90 if base + 0.90 >= v - 1e-9 else base + 1.90, 2)


def precificar(sku, cpv, a):
    if a.contrib_alvo is not None:
        bruto = (cpv + a.contrib_alvo) / TAXA
        p = bruto if a.sem_terminacao else termina_em_90(bruto)
    elif a.off is not None:
        p = round(sku["preco"] * (1 - a.off / 100.0), 2)
    else:
        p = round(a.preco, 2)
    return round(p, 2)


# ── TEMPO ───────────────────────────────────────────────────────────────
def parse_inicio(s):
    if s.startswith("+"):
        n, u = int(re.match(r"\+(\d+)", s).group(1)), s[-1].lower()
        return datetime.now(BRT) + timedelta(minutes=n if u == "m" else n * 60)
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=BRT)


def parse_dur(s):
    m = re.match(r"^(\d+(?:[.,]\d+)?)([hm])$", s.strip().lower())
    if not m:
        morrer(f"--duracao inválida: {s!r} (use 90m ou 3h)")
    v = float(m.group(1).replace(",", "."))
    return timedelta(minutes=v if m.group(2) == "m" else v * 60)


# ── MAIN ────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="Cria a flash sale dedicada de uma creator na TikTok Shop.")
    ap.add_argument("--handle", help="@handle da creator (vai no título → é o que roteia no Hub)")
    ap.add_argument("--refs", help="escopo EXPLÍCITO, ex: REF516,REF551")
    ap.add_argument("--contrib-alvo", type=float, help="contribuição-alvo R$/peça (recomendado)")
    ap.add_argument("--off", type=float, help="alternativa: %% off sobre o preço de lista")
    ap.add_argument("--preco", type=float, help="alternativa: preço fixo (cuidado: base difere por REF)")
    ap.add_argument("--contrib-min", type=float, default=0.0, help="contribuição mínima aceita (default 0 = piso)")
    ap.add_argument("--inicio", default="+5m", help='"+5m" | "+2h" | "2026-09-10 20:00" (BRT)')
    ap.add_argument("--duracao", default="3h", help="90m | 3h")
    ap.add_argument("--fim", help='alternativa a --duracao: "2026-09-10 23:00" (BRT)')
    ap.add_argument("--titulo", help="sobrescreve o título (default: Flash Sale- @handle DDMM-HHMM)")
    ap.add_argument("--limite-por-cliente", type=int, default=-1, help="peças por comprador (-1 = sem limite)")
    ap.add_argument("--sem-terminacao", action="store_true", help="não arredondar o preço pra X,90")
    ap.add_argument("--incluir-sem-estoque", action="store_true")
    ap.add_argument("--strict-conflito", action="store_true",
                    help="aborta se algum SKU já estiver em outra promoção ativa (default: só avisa)")
    ap.add_argument("--encerrar", help="activity_id para desativar (encerra a flash antes da hora)")
    ap.add_argument("--confirmar", action="store_true", help="EXECUTA. Sem isso é dry-run.")
    a = ap.parse_args()

    # ── encerrar ──
    if a.encerrar:
        if not a.confirmar:
            print(f"[DRY-RUN] desativaria a activity {a.encerrar}. Repita com --confirmar."); return
        r = api("POST", f"/promotion/202309/activities/{a.encerrar}/deactivate", params={}, body={})
        print("  ✓ desativada" if r.get("code") == 0 else f"  ✖ falhou: {r.get('code')} {r.get('message')}")
        return

    if not (a.handle and a.refs):
        morrer("--handle e --refs são obrigatórios (escopo explícito é a regra da casa)")
    modos = [x is not None for x in (a.contrib_alvo, a.off, a.preco)]
    if sum(modos) != 1:
        morrer("escolha UM modo de preço: --contrib-alvo (recomendado), --off ou --preco")

    handle = "@" + a.handle.strip().lstrip("@").lower()
    refs = [r.strip().upper() for r in a.refs.split(",") if r.strip()]
    ini = parse_inicio(a.inicio)
    fim = datetime.strptime(a.fim, "%Y-%m-%d %H:%M").replace(tzinfo=BRT) if a.fim else ini + parse_dur(a.duracao)
    if ini <= datetime.now(BRT):
        morrer("--inicio precisa ser no futuro (a API recusa: 17029005)")
    if fim <= ini:
        morrer("--fim precisa ser depois do --inicio")
    titulo = a.titulo or f"Flash Sale- {handle} {ini:%d%m-%H%M}"
    if len(titulo) > 50:
        morrer(f"título tem {len(titulo)} chars (máx 50): {titulo!r}")

    print(f"\n═══ Flash Sale · {handle} ═══")
    print(f"  janela: {ini:%d/%m %H:%M} → {fim:%d/%m %H:%M} BRT ({(fim-ini).total_seconds()/3600:.1f}h)")
    print(f"  título: {titulo}")
    print(f"  escopo: {', '.join(refs)}\n")

    cat = catalogo()
    cpvs = cpv_por_ref()
    ocupados = skus_ocupados()

    # ── monta o escopo: SÓ os SKUs dos REFs pedidos (nível VARIATION) ──
    produtos, avisos, sem_cpv, presos, sem_estoque = [], [], set(), [], []
    linhas = []
    for pid, p in cat.items():
        escolhidos = []
        for s in p["skus"]:
            if s["ref"] not in refs:
                continue
            cpv = cpvs.get(s["ref"])
            if not cpv:
                sem_cpv.add(s["ref"]); continue
            if s["estoque"] <= 0 and not a.incluir_sem_estoque:
                sem_estoque.append(s["seller_sku"]); continue
            if s["id"] in ocupados:
                presos.append((s["seller_sku"], ocupados[s["id"]]))
            preco = precificar(s, cpv, a)
            c = contrib(preco, cpv)
            if preco >= s["preco"]:
                morrer(f"{s['seller_sku']}: promo R$ {preco:.2f} não é menor que a lista R$ {s['preco']:.2f}")
            if c < a.contrib_min:
                morrer(f"{s['seller_sku']} (CPV {cpv:.2f}): contrib R$ {c:.2f} < mínimo R$ {a.contrib_min:.2f} "
                       f"· piso desse CPV é R$ {piso(cpv):.2f}")
            escolhidos.append({"id": s["id"], "activity_price_amount": f"{preco:.2f}",
                               "quantity_limit": -1, "quantity_per_user": a.limite_por_cliente})
            linhas.append((s["ref"], s["seller_sku"], f'{p["title"][:20]} …{pid[-5:]}', s["preco"], preco,
                           round((s["preco"] - preco) / s["preco"] * 100, 1), cpv, c, s["estoque"]))
        if escolhidos:
            produtos.append({"id": pid, "quantity_limit": -1,
                             "quantity_per_user": a.limite_por_cliente, "skus": escolhidos})

    if sem_cpv:
        morrer(f"sem CPV em custos_sku para {', '.join(sorted(sem_cpv))} — sem CPV não dá pra precificar "
               f"(regra da casa: sem dado, não inventa)")
    if presos:
        # A doc diz que a API recusa SKU em 2 activities (17029022), mas a loja opera HOJE com
        # 12+ flashes ONGOING carregando os mesmos 390 SKUs — medido em 09/09. Então é AVISO:
        # com sobreposição, quem vale é o menor preço vigente, não necessariamente esta flash.
        conflitos = sorted({t for _, t in presos})
        print(f"  ⚠ {len({ss for ss, _ in presos})} SKU(s) do escopo já estão em {len(conflitos)} "
              f"promoção(ões) ativa(s) — o preço que vale é o MENOR entre elas:")
        for t in conflitos[:6]:
            print(f"      · {t}")
        if a.strict_conflito:
            morrer("--strict-conflito: encerre a outra promoção (--encerrar <id>) ou reduza o escopo")
        print()
    if not produtos:
        morrer(f"nenhum SKU ativo bateu com {', '.join(refs)}")
    if sem_estoque:
        print(f"  ⚠ {len(sem_estoque)} SKU(s) fora por estoque zero: {', '.join(sem_estoque[:8])}"
              f"{' …' if len(sem_estoque) > 8 else ''}\n")

    # ── tabela ──
    print(f"  {'REF':<7} {'SKU':<12} {'anúncio':<26} {'lista':>7} {'promo':>7} {'off':>6} "
          f"{'CPV':>6} {'contrib':>8} {'est':>5}")
    print("  " + "─" * 92)
    for ref, ssku, tit, lista, promo, off, cpv, c, est in sorted(linhas):
        flag = " ⚠" if c < 1 else ("!" if off > 50 else "")
        print(f"  {ref:<7} {ssku:<12} {tit:<26} {lista:>7.2f} {promo:>7.2f} {off:>5.1f}% "
              f"{cpv:>6.2f} {c:>8.2f}{flag} {est:>4}")
    n_sku = sum(len(p["skus"]) for p in produtos)
    cs = [l[7] for l in linhas]
    print("  " + "─" * 92)
    print(f"  {len(produtos)} anúncio(s) · {n_sku} SKU(s) · contrib/peça R$ {min(cs):.2f} a R$ {max(cs):.2f}")
    if any(l[5] > 50 for l in linhas):
        print("  ! desconto acima de 50% em alguns SKUs — a API tem teto por produto/região "
              "(17029020/21). Se recusar, suba o preço ou reduza o escopo.")
    print(f"  pisos por CPV no escopo: " +
          " · ".join(f"CPV {c:.0f} → R$ {piso(c):.2f}" for c in sorted({l[6] for l in linhas})))

    if not a.confirmar:
        print("\n  [DRY-RUN] nada foi criado. Confira escopo e preço e repita com --confirmar.\n")
        return

    # ── cria ──
    print("\n  criando activity...")
    r = api("POST", "/promotion/202309/activities", params={}, body={
        "title": titulo, "activity_type": "FLASHSALE", "product_level": "VARIATION",
        "duration_type": "NORMAL", "begin_time": int(ini.timestamp()), "end_time": int(fim.timestamp()),
        "participation_limit": [{"type": "BUYER_NO_LIMIT"}],
    })
    if r.get("code") != 0:
        morrer(f"create activity: {r.get('code')} {r.get('message')}")
    aid = (r.get("data") or {}).get("activity_id")
    print(f"  ✓ activity {aid} criada (status {(r.get('data') or {}).get('status')})")

    print("  anexando produtos...")
    r2 = api("PUT", f"/promotion/202309/activities/{aid}/products", params={},
             body={"activity_id": str(aid), "products": produtos})
    if r2.get("code") != 0:
        # rollback: activity vazia no ar é pior que erro — desativa e falha alto.
        api("POST", f"/promotion/202309/activities/{aid}/deactivate", params={}, body={})
        morrer(f"update products: {r2.get('code')} {r2.get('message')} · activity {aid} DESATIVADA (rollback)")
    print(f"  ✓ {(r2.get('data') or {}).get('total_count')} SKU(s) anexados · status {(r2.get('data') or {}).get('status')}")

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps({"ts": datetime.now(BRT).isoformat(), "activity_id": aid, "titulo": titulo,
                            "handle": handle, "refs": refs, "begin": int(ini.timestamp()),
                            "end": int(fim.timestamp()), "skus": n_sku,
                            "modo": ("contrib" if a.contrib_alvo is not None else "off" if a.off is not None else "preco"),
                            "linhas": [list(l) for l in linhas]}, ensure_ascii=False) + "\n")
    print(f"\n  ✓ registrado em {os.path.relpath(LOG)}")
    print(f"  → o Hub mostra pra {handle} no próximo ciclo do coletar_flash_sales (≤30min)\n")


if __name__ == "__main__":
    main()
