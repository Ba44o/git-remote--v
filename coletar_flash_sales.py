#!/usr/bin/env python3
"""
Rhode Jeans — Coletor de Flash Sales (Promotion API → Supabase → Hub)
--------------------------------------------------------------------
Puxa as flash sales ATIVAS (status ONGOING) da TikTok Shop e grava na tabela
`flash_sales` pro Hub mostrar pra cada creator a oferta dela.

Targeting (decidido com o time):
  • título com @handle que BATE com creator nossa → só ela vê (scope='creator')
  • título "Geral"/"Chat"/sem @handle              → loja toda vê (scope='loja')
  • título com @handle de creator que NÃO é nossa  → ignora (é de outra)

Read-only do lado das creators: NÃO toca login, extrato nem performance_periods.
Root-level de propósito (não dispara etl_sync.yml). Rodar via cron a cada ~30min.

Uso:
  python3 coletar_flash_sales.py            # coleta + grava
  python3 coletar_flash_sales.py --dry-run  # só imprime o que gravaria
"""
import os, re, sys, json, argparse, requests
from datetime import datetime, timezone

from coletar_dados import chamar
try:
    from agente_rhode.etl_v2 import HANDLE_ALIASES
except Exception:
    HANDLE_ALIASES = {}

SB_URL = os.environ["SUPABASE_URL"]
SB_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json"}

# aliases em lowercase → handle canônico (mesma regra do extrato)
ALIAS = {k.lower(): v.lower() for k, v in HANDLE_ALIASES.items()}
ALIAS.update({"tacianecreator": "tacianetorress", "tacirecomenda": "tacianetorress"})

def canon(h):
    h = (h or "").strip().lstrip("@.").lower()
    return ALIAS.get(h, h)


def money(d):
    """{'amount':'169.9','currency':'BRL'} ou string → float."""
    if isinstance(d, dict):
        return float(d.get("amount") or d.get("tax_exclusive_price") or 0)
    return float(d or 0)


def handle_do_titulo(title):
    m = re.findall(r"@([A-Za-z0-9_.]+)", title or "")
    return canon(m[0]) if m else None


def universo_creators():
    """Set de handles canônicos das nossas creators (fonte: extrato_resumo)."""
    out, off = set(), 0
    while True:
        # order=id obrigatório: sem ORDER BY o offset pula linhas e a creator some do
        # universo → a flash dela não aparece no hub.
        r = requests.get(f"{SB_URL}/rest/v1/extrato_resumo?select=creator&order=id&limit=1000&offset={off}",
                         headers=SBH, timeout=60)
        b = r.json() if r.ok else []
        if not b:
            break
        out.update(canon(x["creator"]) for x in b if x.get("creator"))
        off += 1000
        if len(b) < 1000:
            break
    return out


def catalogo():
    """product_id→título e sku_id→preço original (pro % OFF). Pagina products/search."""
    titulos, precos, cursor, pag = {}, {}, "", 0
    while pag < 50:
        pag += 1
        params = {"page_size": 100}
        if cursor:
            params["page_token"] = cursor
        resp = chamar("POST", "/product/202309/products/search", params=params, body={"status": "ALL"})
        if resp.get("code") != 0:
            break
        data = resp.get("data") or {}
        for p in data.get("products", []) or []:
            titulos[str(p["id"])] = p.get("title", "")
            for s in p.get("skus", []) or []:
                precos[str(s["id"])] = money(s.get("price"))
        cursor = data.get("next_page_token", "")
        if not cursor:
            break
    return titulos, precos


def flash_ongoing():
    """Todas as activities FLASHSALE com status ONGOING."""
    acts, tok = [], None
    while True:
        body = {"page_size": 50, "status": "ONGOING"}
        if tok:
            body["page_token"] = tok
        r = chamar("POST", "/promotion/202309/activities/search", params={}, body=body)
        d = r.get("data") or {}
        acts += d.get("activities") or []
        tok = d.get("next_page_token")
        if not tok:
            break
    return [a for a in acts if a.get("activity_type") == "FLASHSALE"]


def detalhe(activity_id):
    r = chamar("GET", f"/promotion/202309/activities/{activity_id}", params={})
    return (r.get("data") or {}) if r.get("code") == 0 else {}


def produtos_da_flash(det, titulos, precos):
    """Lista enxuta de produtos da flash: nome, preço promo, original, % off."""
    out = []
    for p in det.get("products", []) or []:
        pid = str(p.get("id") or "")
        skus = p.get("skus", []) or []
        # menor preço promo entre as variações (o gancho da oferta)
        promos = [money(s.get("activity_price")) for s in skus if money(s.get("activity_price")) > 0]
        if not promos:
            continue
        promo = min(promos)
        # preço original da SKU correspondente (a de menor promo) p/ o % off
        sku_min = min((s for s in skus if money(s.get("activity_price")) > 0),
                      key=lambda s: money(s.get("activity_price")))
        orig = precos.get(str(sku_min.get("id")), 0.0)
        pct = round((orig - promo) / orig * 100) if orig > promo > 0 else 0
        out.append({
            "product_id": pid,
            "nome": titulos.get(pid, ""),
            "preco_promo": round(promo, 2),
            "preco_original": round(orig, 2) if orig else None,
            "pct_off": pct,
            "moeda": (skus[0].get("activity_price") or {}).get("currency", "BRL"),
        })
    # mais barato primeiro (oferta mais forte no topo do card)
    out.sort(key=lambda x: x["preco_promo"])
    return out


def upsert(rows):
    if not rows:
        return
    r = requests.post(f"{SB_URL}/rest/v1/flash_sales?on_conflict=id",
                     headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"},
                     data=json.dumps(rows), timeout=60)
    r.raise_for_status()


def reconcile(now_ts, ids_atuais):
    """Tabela espelha exatamente as flashes dedicadas ATIVAS desta coleta.
    Apaga expiradas sempre; e tudo que não veio nesta coleta (loja/Geral antigas,
    canceladas, de-targetadas) — só quando há coleta, p/ não zerar por hiccup."""
    H = {**SBH, "Prefer": "return=minimal"}
    requests.delete(f"{SB_URL}/rest/v1/flash_sales?end_ts=lt.{now_ts}", headers=H, timeout=60)
    if ids_atuais:
        lst = ",".join(f'"{i}"' for i in ids_atuais)
        requests.delete(f"{SB_URL}/rest/v1/flash_sales?id=not.in.({lst})", headers=H, timeout=60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    print(f"Flash sales — coleta {datetime.now(tz=timezone.utc):%Y-%m-%d %H:%M} UTC")

    nossas = universo_creators()
    print(f"  creators no universo: {len(nossas)}")
    titulos, precos = catalogo()
    print(f"  catálogo: {len(titulos)} produtos · {len(precos)} skus c/ preço")

    flash = flash_ongoing()
    print(f"  FLASHSALE ongoing: {len(flash)}")

    # Regra firme: cada creator vê SÓ a flash dedicada do @handle dela.
    # Flashes sem @handle nosso (Geral/loja/de outra creator) → não entram.
    rows, n_skip = [], 0
    for a_ in flash:
        title = a_.get("title") or ""
        h = handle_do_titulo(title)
        if not (h and h in nossas):
            n_skip += 1; continue

        det = detalhe(a_.get("id"))
        prods = produtos_da_flash(det, titulos, precos)
        if not prods:
            continue
        rows.append({
            "id": str(a_.get("id")),
            "title": title,
            "activity_type": a_.get("activity_type"),
            "scope": "creator",
            "creator": h,
            "begin_ts": int(a_.get("begin_time") or 0),
            "end_ts": int(a_.get("end_time") or 0),
            "status": a_.get("status"),
            "products": prods,
            "updated_at": datetime.now(tz=timezone.utc).isoformat(),
        })

    print(f"  → dedicadas por creator: {len(rows)} · ignoradas (sem @handle nosso): {n_skip}")

    if a.dry_run:
        for r in rows[:8]:
            top = r["products"][0]
            print(f"    [@{r['creator']}] {r['title'][:42]} · {top['nome'][:28]} "
                  f"R$ {top['preco_promo']} ({top['pct_off']}% off) · {len(r['products'])} prod")
        print("  [DRY-RUN] nada gravado.")
        return

    upsert(rows)
    reconcile(now_ts, [r["id"] for r in rows])
    print(f"  ✓ gravado em flash_sales · tabela reconciliada (só dedicadas ativas)")


if __name__ == "__main__":
    main()
