"""
Rhode Jeans — Auditoria de Integridade dos Dados
================================================
Compara o que está no Supabase vs. o que deveria estar (segundo os exports
originais do TikTok Shop), por creator, por KPI, por período.

Detecta:
  - Creators no export mas faltando no Supabase
  - Creators no Supabase mas não no export do período
  - Divergências de valor por campo (GMV, pedidos, comissão, refund, etc)
  - Top N maiores discrepâncias

Uso:
  python audit_data.py
  python audit_data.py --periodo 2026-04
  python audit_data.py --tolerancia 0.05   # tolerância em R$ ou unidades
"""
import os
import sys
import argparse
import requests
from pathlib import Path
from collections import defaultdict

# Reusa o ETL para garantir paridade
sys.path.insert(0, str(Path(__file__).parent / "agente_rhode"))
from etl_v2 import (
    detect_period, load_raw, transform, pick_canonical_per_period,
    COLUMN_ALIASES,
)

# ── Config ────────────────────────────────────────────────────────────────────

SB_URL = "https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1"
SB_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2enB5a3VsdXhjeGVmaHl6ZnNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3Mzc5MzYsImV4cCI6MjA5MTMxMzkzNn0.4_ZShB2t3yCg8ag7-LPWvzHXVrTmj0N4iKWp_tEZb9g"

EXPORTS_DIR = Path("dados/creators/exports")

# Campos numéricos a auditar (nome local → nome Supabase)
NUMERIC_FIELDS = {
    "gmv_bruto":   ("gmv_bruto",   0.50),    # tolerância: R$ 0,50
    "gmv_liquido": ("gmv_liquido", 0.50),
    "reembolso":   ("reembolso",   0.50),
    "pedidos":     ("pedidos",     0),       # tolerância: 0 (inteiro)
    "videos":      ("videos",      0),
    "lives":       ("lives",       0),
    "aov":         ("aov",         0.10),    # tolerância: R$ 0,10 (rounding)
    "refund_pct":  ("refund_pct",  0.10),    # tolerância: 0,1 ponto percentual
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def fetch_supabase_period(periodo):
    """Busca todas as linhas de um período (paginado)."""
    rows, offset = [], 0
    while True:
        r = requests.get(
            f"{SB_URL}/performance_periods",
            headers={"apikey": SB_KEY},
            params={
                "select": "affiliate_id,gmv_bruto,gmv_liquido,reembolso,refund_pct,pedidos,aov,videos,lives,comissao,tier",
                "periodo": f"eq.{periodo}",
                # order=id obrigatório: sem ORDER BY o offset pula/duplica linhas e a
                # auditoria compara um recorte incompleto (falso alarme / falso "ok").
                "order": "id",
                "limit": 1000,
                "offset": offset,
            },
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return rows


def normalize_id(s):
    return str(s or "").strip().upper().lstrip("@.").lstrip(".")


def fmt(v):
    """Formata número pra display."""
    if isinstance(v, float):
        return f"{v:,.2f}"
    return str(v)


# ── Audit ─────────────────────────────────────────────────────────────────────

def audit_period(canonical_file: Path, periodo: str, tolerancia_extra: float = 0.0):
    """Compara o canonical export com o que está no Supabase para um período."""
    print(f"\n{'═' * 70}")
    print(f"  AUDITORIA · {periodo}")
    print(f"  Export canônico: {canonical_file.name}")
    print(f"{'═' * 70}\n")

    # 1. Carrega e processa o export como o ETL faria
    ym, ini, fim = detect_period(canonical_file)
    raw = load_raw(canonical_file)
    df = transform(raw, ym, ini, fim)

    expected = {}
    for _, row in df.iterrows():
        cid = normalize_id(row["creator_id"])
        if not cid or cid in ("NAN", "NONE"):
            continue
        expected[cid] = {f: row.get(f) for f in NUMERIC_FIELDS}

    print(f"▶ Export:   {len(expected):>5} creators")

    # 2. Busca do Supabase
    sb_rows = fetch_supabase_period(periodo)
    actual = {}
    for r in sb_rows:
        cid = normalize_id(r["affiliate_id"])
        actual[cid] = r
    print(f"▶ Supabase: {len(actual):>5} creators")

    # 3. Detecta sumidos/extras
    no_supabase = sorted(set(expected) - set(actual))
    no_export   = sorted(set(actual) - set(expected))

    if no_supabase:
        print(f"\n⚠️  {len(no_supabase)} creators no export MAS NÃO no Supabase:")
        for cid in no_supabase[:10]:
            e = expected[cid]
            print(f"   {cid:<35} GMV={fmt(e['gmv_liquido'])} ped={fmt(e['pedidos'])}")
        if len(no_supabase) > 10:
            print(f"   ... +{len(no_supabase) - 10} outros")

    if no_export:
        print(f"\n⚠️  {len(no_export)} creators no Supabase MAS NÃO no export:")
        for cid in no_export[:10]:
            a = actual[cid]
            print(f"   {cid:<35} GMV={fmt(a['gmv_liquido'])} ped={fmt(a['pedidos'])}")
        if len(no_export) > 10:
            print(f"   ... +{len(no_export) - 10} outros")

    # 4. Compara campos para creators que estão em ambos
    common = sorted(set(expected) & set(actual))
    print(f"\n▶ Comparando {len(common)} creators presentes em ambos...\n")

    divergencias_por_campo = defaultdict(list)  # campo → [(cid, esperado, atual, diff)]

    for cid in common:
        exp = expected[cid]
        act = actual[cid]
        for local_field, (sb_field, tol) in NUMERIC_FIELDS.items():
            try:
                e_val = float(exp.get(local_field) or 0)
                a_val = float(act.get(sb_field) or 0)
            except (TypeError, ValueError):
                continue
            diff = abs(a_val - e_val)
            tolerance = max(tol, tolerancia_extra)
            if diff > tolerance:
                divergencias_por_campo[local_field].append((cid, e_val, a_val, diff))

    # 5. Reporta por campo
    if not any(divergencias_por_campo.values()):
        print("✅ NENHUMA DIVERGÊNCIA detectada nos campos numéricos.\n")
    else:
        for campo, lista in divergencias_por_campo.items():
            if not lista:
                continue
            lista.sort(key=lambda x: x[3], reverse=True)
            print(f"❌ {campo}: {len(lista)} creators com divergência")
            print(f"   {'creator_id':<35} {'export':>14} {'supabase':>14} {'diff':>12}")
            for cid, e, a, d in lista[:10]:
                arrow = "→" if a > e else "←"
                print(f"   {cid:<35} {fmt(e):>14} {fmt(a):>14} {arrow}{fmt(d):>11}")
            if len(lista) > 10:
                print(f"   ... +{len(lista) - 10} outros")
            print()

    # 6. Sumário
    return {
        "periodo": periodo,
        "export_count": len(expected),
        "supabase_count": len(actual),
        "common": len(common),
        "no_supabase": len(no_supabase),
        "no_export": len(no_export),
        "divergencias": {k: len(v) for k, v in divergencias_por_campo.items() if v},
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--periodo", help="Auditar só um período (ex: 2026-04)")
    parser.add_argument("--tolerancia", type=float, default=0.0, help="Tolerância extra em R$/unidades")
    args = parser.parse_args()

    files = sorted(EXPORTS_DIR.glob("*.xlsx"))
    if not files:
        print(f"[ERRO] Nenhum .xlsx em {EXPORTS_DIR}", file=sys.stderr)
        sys.exit(1)

    canonical = pick_canonical_per_period(files)

    results = []
    for f in canonical:
        ym, _, _ = detect_period(f)
        if args.periodo and ym != args.periodo:
            continue
        try:
            r = audit_period(f, ym, args.tolerancia)
            results.append(r)
        except Exception as e:
            print(f"\n[ERRO em {ym}] {e}\n")

    # Sumário final
    print(f"\n{'═' * 70}")
    print(f"  SUMÁRIO")
    print(f"{'═' * 70}")
    print(f"  {'Período':<10} {'Export':>8} {'Supabase':>10} {'Comum':>8} {'Faltando':>10} {'Extra':>8} {'Divergentes':>12}")
    for r in results:
        total_div = sum(r["divergencias"].values())
        print(f"  {r['periodo']:<10} {r['export_count']:>8} {r['supabase_count']:>10} {r['common']:>8} {r['no_supabase']:>10} {r['no_export']:>8} {total_div:>12}")
    print()


if __name__ == "__main__":
    main()
