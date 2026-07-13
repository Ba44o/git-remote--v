#!/usr/bin/env python3
"""
Coletor do Extrato de Comissões (creator-facing) — LOCAL/untracked.

Puxa affiliate orders da TikTok Shop API, agrega por creator e popula 2 tabelas
no Supabase: extrato_resumo (creator × mês) e extrato_pedidos (por pedido).

PORQUÊ LOCAL: precisa do token TikTok (.env) que o GitHub Action não tem; e
manter fora de agente_rhode/ evita disparar o etl_sync.yml (que reprocessa a
performance_periods). Escreve direto no Supabase via service key.

ADITIVO: não toca performance_periods nem tier. Roda no daily (launchd).

Uso:
  python3 coletar_extrato.py --dias 21           # janela recente (daily)
  python3 coletar_extrato.py --inicio 2026-01-01 --fim 2026-06-30   # range
  python3 coletar_extrato.py --backfill          # 2026-01-01 → hoje (chunks 3m)
"""
import os, sys, json, argparse, urllib.request
from datetime import datetime, timezone, timedelta, date

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import coletar_dados as C
import calendar
try:
    from agente_rhode.etl_v2 import HANDLE_ALIASES, calc_tier
except Exception:
    HANDLE_ALIASES = {"NATMARQUESSS": "NATMARQUESVI"}
    def calc_tier(g):
        for t,l in [(500000,"Black"),(150000,"Diamond"),(80000,"Gold"),(50000,"Silver"),(20000,"Bronze")]:
            if g>=t: return (l,0)
        return ("Iniciante",0)

# Forward-only: Jan-Mai vêm do EXPORT (congelados). Jun+ vêm da API.
# build_performance_forward NUNCA escreve período < FORWARD_FROM (protege o passado).
FORWARD_FROM = "2026-06"

SB_URL = os.environ["SUPABASE_URL"]
SB_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json"}

# aliases aplicados em lowercase (a tabela guarda handle lowercase canônico)
ALIAS_LC = {k.lower(): v.lower() for k, v in HANDLE_ALIASES.items()}
# Taci: 3 handles = 1 pessoa. Canônico = tacianetorress (o que o login/preview resolve).
# Seguro AQUI (agregação soma em Python) — diferente do etl_v2 que colidia no UPSERT.
ALIAS_LC.update({"tacianecreator": "tacianetorress", "tacirecomenda": "tacianetorress"})

def money(f): return float(f.get("amount") or 0) if isinstance(f, dict) else float(f or 0)
def norm(h):  return (h or "").strip().lstrip("@.").lower()
def canon(h): h = norm(h); return ALIAS_LC.get(h, h)
def mes(epoch): return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m")
def dia(epoch): return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%d")

STATUS_MAP = {"SETTLED": "liquidado", "TO-SETTLE": "a_liquidar", "INELIGIBLE": "inelegivel"}

def status_of(s):
    return STATUS_MAP.get((s or "").upper(), "a_liquidar")

def agregar(orders, prod_nomes=None):
    """orders → (resumo_rows, pedido_rows)."""
    prod_nomes = prod_nomes or {}
    resumo = {}           # (creator, periodo) -> dict
    ped_resumo = {}       # (creator, periodo) -> set(order_id) p/ contar pedidos
    reemb_orders = {}     # (creator, periodo) -> set(order_id) reembolsados
    content = {}          # (creator, periodo) -> {'VIDEO':set(content_id),'LIVE':set(content_id)}
    pedidos = {}          # id(order|sku) -> row
    for o in orders:
        oid = o.get("id"); ct = o.get("create_time")
        if not ct: continue
        per = mes(ct); dt = dia(ct)
        for s in (o.get("skus") or []):
            c = canon(s.get("creator_username"))
            if not c: continue
            st = status_of(s.get("settlement_status"))
            ret = (s.get("fully_return") == "Yes")
            est = money(s.get("estimated_commission_base"))
            act = money(s.get("actual_commission_base"))
            # Comissão da CREATOR = orgânica + ADS (shop ads) + bônus cofinanciado.
            # Vendas via Spark Ads têm a orgânica zerada e pagam pelo shop_ads —
            # somar só a orgânica subcontava ~metade (bug pego jun/26). Partner =
            # comissão da agência/TAP, NÃO entra.
            com_est = (money(s.get("estimated_paid_commission"))
                       + money(s.get("estimated_paid_shop_ads_commission"))
                       + money(s.get("estimated_cofunded_creator_bonus_amount")))
            com_pago = (money(s.get("actual_paid_commission"))
                        + money(s.get("actual_paid_shop_ads_commission"))
                        + money(s.get("actual_cofunded_creator_bonus_amount")))

            r = resumo.setdefault((c, per), dict(
                gmv_estimado=0.0, gmv_liquidado=0.0, gmv_a_liquidar=0.0, gmv_inelegivel=0.0,
                comissao_estimada=0.0, comissao_paga=0.0, comissao_a_receber=0.0, reembolsos_valor=0.0))
            r["gmv_estimado"] += est
            r["comissao_estimada"] += com_est
            if st == "liquidado":
                r["gmv_liquidado"] += act; r["comissao_paga"] += com_pago
            elif st == "a_liquidar":
                r["gmv_a_liquidar"] += est; r["comissao_a_receber"] += com_est  # comissão que VAI pagar
            else:
                r["gmv_inelegivel"] += est
            if ret:
                r["reembolsos_valor"] += est
                reemb_orders.setdefault((c, per), set()).add(oid)
            ped_resumo.setdefault((c, per), set()).add(oid)
            # vídeos/lives: conta content_id distinto por tipo (≈ conteúdo que gerou venda)
            cid = s.get("content_id"); ctype = (s.get("content_type") or "").upper()
            if cid and ctype in ("VIDEO", "LIVE"):
                content.setdefault((c, per), {"VIDEO": set(), "LIVE": set()})[ctype].add(cid)

            sku_id = s.get("sku_id") or s.get("product_id") or ""
            pid = s.get("product_id") or ""
            pedidos[f"{oid}|{sku_id}"] = dict(
                id=f"{oid}|{sku_id}", creator=c, periodo=per, data=dt, order_id=str(oid),
                product_id=str(pid), produto=prod_nomes.get(str(pid), ""),
                content_type=s.get("content_type") or "", gmv=round(est, 2),
                status=st, reembolso=ret,
                comissao_estimada=round(com_est, 2), comissao_paga=round(com_pago, 2))

    resumo_rows = []
    for (c, per), r in resumo.items():
        resumo_rows.append(dict(
            id=f"{c}|{per}", creator=c, periodo=per,
            pedidos=len(ped_resumo.get((c, per), set())),
            gmv_estimado=round(r["gmv_estimado"], 2),
            gmv_liquidado=round(r["gmv_liquidado"], 2),
            gmv_a_liquidar=round(r["gmv_a_liquidar"], 2),
            gmv_inelegivel=round(r["gmv_inelegivel"], 2),
            comissao_estimada=round(r["comissao_estimada"], 2),
            comissao_paga=round(r["comissao_paga"], 2),
            comissao_a_receber=round(r["comissao_a_receber"], 2),
            reembolsos_n=len(reemb_orders.get((c, per), set())),
            reembolsos_valor=round(r["reembolsos_valor"], 2),
            videos=len(content.get((c, per), {}).get("VIDEO", set())),
            lives=len(content.get((c, per), {}).get("LIVE", set()))))
    return resumo_rows, list(pedidos.values())

def upsert(table, rows, chunk=500, on_conflict=None):
    if not rows: return
    url = f"{SB_URL}/rest/v1/{table}"
    if on_conflict:
        url += f"?on_conflict={on_conflict}"
    for i in range(0, len(rows), chunk):
        body = json.dumps(rows[i:i+chunk]).encode()
        req = urllib.request.Request(url, data=body,
            headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as e:
            print(f"  [ERRO upsert {table}] {e.code}: {e.read()[:300]}"); raise
    print(f"  ✓ {table}: {len(rows)} linhas upsertadas")

EXTRATO_COLS = ("id","creator","periodo","pedidos","gmv_estimado","gmv_liquidado",
                "gmv_a_liquidar","gmv_inelegivel","comissao_estimada","comissao_paga",
                "comissao_a_receber","reembolsos_n","reembolsos_valor")

def build_performance_forward(resumo_rows, forward_from=FORWARD_FROM, window_start=None):
    """performance_periods rows pra meses >= forward_from (FORWARD-ONLY).

    Jan-Mai vêm do EXPORT e NUNCA são tocados (guarda `per < forward_from`).
    gmv_liquido = liquidado + a_liquidar (vendas atribuídas que vão pagar; exclui
    reembolso/inelegível). Mesma base dos meses passados e não encolhe conforme
    liquida. affiliate_id em UPPERCASE (convenção do performance_periods).

    window_start = 1º dia coletado. GUARDA DE COBERTURA: só escreve um mês que foi
    coletado INTEIRO (janela começa <= dia 1 do mês). Senão o daily `--dias 21`
    reagregaria o mês passado só parcialmente e ENCOLHERIA o hub no upsert. Mês
    parcial (ex.: junho numa janela que começa 22/06) é PULADO — quem corrige o
    passado é um backfill full-window (`--inicio <1º-do-mês>`)."""
    out = []
    for r in resumo_rows:
        per = r["periodo"]
        if per < forward_from:          # GUARDA: nunca escreve o passado do export
            continue
        if window_start is not None and date.fromisoformat(f"{per}-01") < window_start:
            continue                     # GUARDA: não sobrescreve mês coletado parcial
        gmv_liq = round(r["gmv_liquidado"] + r["gmv_a_liquidar"], 2)
        reemb = round(r["reembolsos_valor"], 2)
        gmv_bruto = round(gmv_liq + reemb, 2)
        ped = int(r["pedidos"])
        tier, _ = calc_tier(gmv_liq)
        y, m = per.split("-"); last = calendar.monthrange(int(y), int(m))[1]
        out.append({
            "affiliate_id": r["creator"].upper(), "periodo": per,
            "periodo_inicio": f"{per}-01", "periodo_fim": f"{per}-{last:02d}",
            "gmv_bruto": gmv_bruto, "gmv_liquido": gmv_liq, "reembolso": reemb,
            "refund_pct": round(100*reemb/gmv_bruto, 2) if gmv_bruto > 0 else 0.0,
            "pedidos": ped, "aov": round(gmv_bruto/ped, 2) if ped > 0 else 0.0,
            "videos": int(r.get("videos", 0)), "lives": int(r.get("lives", 0)),
            "comissao": round(r["comissao_estimada"], 2), "tier": tier,
        })
    return out

def affiliate_ids_existentes():
    """Set de affiliate_id já na tabela affiliates (UPPERCASE). performance_periods
    tem FK pra affiliates → só dá pra escrever creators que já existem lá."""
    ids = set(); off = 0
    while True:
        url = f"{SB_URL}/rest/v1/affiliates?select=affiliate_id&limit=1000&offset={off}"
        rows = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=SBH), timeout=60).read())
        if not rows: break
        for r in rows:
            if r.get("affiliate_id"): ids.add(str(r["affiliate_id"]).upper())
        off += 1000
        if len(rows) < 1000: break
    return ids

def chunks_3m(ini, fim):
    """Quebra [ini,fim] em janelas <=3 meses (limite da API)."""
    out = []; cur = ini
    while cur <= fim:
        end = min(fim, cur + timedelta(days=89))
        out.append((cur.isoformat(), end.isoformat())); cur = end + timedelta(days=1)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int)
    ap.add_argument("--inicio"); ap.add_argument("--fim")
    ap.add_argument("--backfill", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="não escreve nada; mostra o que faria")
    ap.add_argument("--no-forward", action="store_true", help="não escreve performance_periods (só extrato)")
    a = ap.parse_args()
    hoje = datetime.now(tz=timezone.utc).date()
    if a.backfill:
        ini, fim = date(2026, 1, 1), hoje
    elif a.inicio and a.fim:
        ini, fim = date.fromisoformat(a.inicio), date.fromisoformat(a.fim)
    else:
        d = a.dias or 21
        ini, fim = hoje - timedelta(days=d), hoje

    print(f"Extrato: coletando {ini} → {fim}")
    # nomes de produto (best-effort)
    prod_nomes = {}
    try:
        cat = C.buscar_produtos() or {}          # {product_id: {title,status,seller_sku}}
        for pid, info in cat.items():
            prod_nomes[str(pid)] = (info.get("title") or "") if isinstance(info, dict) else ""
        print(f"  catálogo: {len(prod_nomes)} produtos p/ nome")
    except Exception as e:
        print(f"  (sem nomes de produto: {str(e)[:60]})")

    all_orders = []
    for (ci, cf) in chunks_3m(ini, fim):
        all_orders += C.buscar_affiliate_orders(ci, cf)
    print(f"  total pedidos: {len(all_orders)}")
    resumo_rows, pedido_rows = agregar(all_orders, prod_nomes)
    print(f"  agregado: {len(resumo_rows)} linhas resumo · {len(pedido_rows)} linhas pedido")
    # extrato_resumo não tem colunas videos/lives → projeta só as colunas da tabela
    extrato_rows = [{k: r[k] for k in EXTRATO_COLS if k in r} for r in resumo_rows]

    # FORWARD-ONLY: performance_periods só pra meses >= FORWARD_FROM (Jan-Mai = export)
    perf_fwd = [] if a.no_forward else build_performance_forward(resumo_rows, window_start=ini)
    perf_fwd = [r for r in perf_fwd if r["affiliate_id"]]   # descarta handle vazio (FK)
    novas_aff = []
    if perf_fwd:
        # FK: performance_periods.affiliate_id → affiliates. Creators que VENDEM mas ainda
        # não têm identidade em `affiliates` (100%-novas, sem export — ex.: @suzane.ganga)
        # são AUTO-CADASTRADAS aqui em vez de sumirem do hub. Insere só a identidade mínima
        # (affiliate_id + tiktok_handle real); os números vêm do perf logo abaixo, e o
        # primeiro acesso (PIN/WhatsApp) elas mesmas completam. merge-duplicates só cria a
        # linha que falta — tier/pin/token/phone de quem já existe ficam INTACTOS.
        existentes = affiliate_ids_existentes()
        handle_por_id = {r["creator"].upper(): r["creator"] for r in resumo_rows}
        faltantes = sorted({r["affiliate_id"] for r in perf_fwd} - existentes)
        if faltantes:
            novas_aff = [{"affiliate_id": aid, "tiktok_handle": handle_por_id.get(aid, aid.lower())}
                         for aid in faltantes]
            print(f"  forward: auto-cadastrando {len(novas_aff)} creators novas em affiliates "
                  f"(vendem mas não tinham identidade): {', '.join(faltantes)[:240]}")

    if a.dry_run:
        print(f"  [DRY-RUN] extrato_resumo={len(extrato_rows)} · extrato_pedidos={len(pedido_rows)} · "
              f"affiliates_novas={len(novas_aff)} · performance_periods(forward >= {FORWARD_FROM})={len(perf_fwd)} — NADA escrito")
        if perf_fwd:
            tot = sum(x["gmv_liquido"] for x in perf_fwd)
            pers = sorted({x["periodo"] for x in perf_fwd})
            print(f"  [DRY-RUN] forward períodos={pers} · creators={len(perf_fwd)} · GMV líq total R${tot:,.2f}")
            for x in sorted(perf_fwd, key=lambda r:-r["gmv_liquido"])[:5]:
                print(f"      {x['affiliate_id']:<20} {x['periodo']} gmv_liq R${x['gmv_liquido']:,.0f} ped {x['pedidos']} tier {x['tier']}")
        return
    # FK: cria as identidades novas ANTES do performance_periods (senão o upsert do perf falha)
    if novas_aff:
        upsert("affiliates", novas_aff, on_conflict="affiliate_id")
    upsert("extrato_resumo", extrato_rows)
    upsert("extrato_pedidos", pedido_rows)
    if perf_fwd:
        upsert("performance_periods", perf_fwd, on_conflict="affiliate_id,periodo")
    print("✓ extrato atualizado"
          + (f" + {len(novas_aff)} affiliates novas" if novas_aff else "")
          + (f" + performance_periods forward ({len(perf_fwd)})" if perf_fwd else ""))

if __name__ == "__main__":
    main()
