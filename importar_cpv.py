#!/usr/bin/env python3
"""
Rhode — Importador de CPV → tabela custos_sku (admin/CFO).

Lê a planilha de custos (REF · Produto · Cor · Tamanho · CPV) e faz upsert em
custos_sku. Chave = REF (que casa exato com pedidos_sku.seller_sku). Idempotente.

Uso:  python3 importar_cpv.py ~/Downloads/cpv-rhode-2026-06-10.xlsx
"""
import os, sys, json, urllib.request, urllib.error
import pandas as pd

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

SB_URL = os.environ["SUPABASE_URL"]
SB_KEY = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}", "Content-Type": "application/json"}


def parse_cpv(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip().replace("R$", "").replace(" ", "")
    if "," in s:  # formato BR
        s = s.replace(".", "").replace(",", ".")
    try:
        n = float(s)
        return round(n, 2) if n > 0 else None
    except ValueError:
        return None


def s(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    t = str(v).strip()
    return t or None


def upsert(table, rows, chunk=500, on_conflict="id"):
    if not rows:
        return
    url = f"{SB_URL}/rest/v1/{table}?on_conflict={on_conflict}"
    for i in range(0, len(rows), chunk):
        body = json.dumps(rows[i:i + chunk]).encode()
        req = urllib.request.Request(url, data=body,
            headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
        try:
            urllib.request.urlopen(req, timeout=120)
        except urllib.error.HTTPError as e:
            print(f"  [ERRO upsert {table}] {e.code}: {e.read()[:300]}"); raise
    print(f"  ✓ {table}: {len(rows)} linhas upsertadas")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Downloads/cpv-rhode-2026-06-10.xlsx")
    print(f"═════ Importar CPV — {path} ═════")
    df = pd.read_excel(path, sheet_name="CPV", header=0)
    # normaliza nomes de coluna (tolerante a variações)
    cols = {str(c).strip().lower(): c for c in df.columns}
    def col(*names):
        for n in names:
            if n in cols:
                return cols[n]
        return None
    c_ref = col("ref")
    c_prod = col("produto", "product")
    c_cor = col("cor", "color")
    c_tam = col("tamanho", "tam", "size")
    c_cpv = col("cpv (r$)", "cpv", "custo")
    if not c_ref or not c_cpv:
        print(f"  [ERRO] planilha precisa de colunas REF e CPV. Achei: {list(df.columns)}"); sys.exit(1)

    rows, sem_cpv, sem_ref = [], 0, 0
    for _, r in df.iterrows():
        ref = s(r.get(c_ref))
        cpv = parse_cpv(r.get(c_cpv))
        if not ref:
            sem_ref += 1; continue
        if cpv is None:
            sem_cpv += 1; continue
        rows.append({
            "id": ref.upper(),
            "ref": ref.upper(),
            "produto": s(r.get(c_prod)) if c_prod else None,
            "cor": s(r.get(c_cor)) if c_cor else None,
            "tam": s(r.get(c_tam)) if c_tam else None,
            "cpv": cpv,
            "fonte": "import",
        })
    print(f"  → {len(df)} linhas na planilha · {len(rows)} com REF+CPV · {sem_cpv} sem CPV · {sem_ref} sem REF")
    # Dedup por id (REF). Mesmo REF aparece p/ cor/tam — colapsa em 1 CPV (granularidade da loja é REF).
    dedup, conflitos = {}, 0
    for x in rows:
        prev = dedup.get(x["id"])
        if prev is not None and abs(prev["cpv"] - x["cpv"]) > 0.001:
            conflitos += 1
        dedup[x["id"]] = x  # last-wins
    final = list(dedup.values())
    print(f"  → {len(final)} REFs únicos (após dedup){f' · ⚠ {conflitos} com CPV divergente no mesmo REF (mantido o último)' if conflitos else ''}")
    if final:
        cpvs = [x["cpv"] for x in final]
        print(f"  → CPV: min R$ {min(cpvs):.2f} · max R$ {max(cpvs):.2f} · médio R$ {sum(cpvs)/len(cpvs):.2f}")
    upsert("custos_sku", final, on_conflict="id")
    print("  ✓ concluído.")


if __name__ == "__main__":
    main()
