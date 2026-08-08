#!/usr/bin/env python3
"""
Rhode — Gera os benchmarks da extensão DashLive a partir da FONTE ÚNICA (tabela `lives`).

Porquê: o build de referência trazia os números de abril/26 chumbados no content.js
(ctr 28,4 · co 8,9 · convView 2,52 · ticket 67 · viewers 9519). Três estavam com o
enquadramento errado (ver docs/DECISOES-E-PREMISSAS.md R10/R11) e nenhum era
rastreável. Aqui eles saem calculados do dado, com janela e n declarados.

O QUE MUDA POR PERFIL (crítico — R11): a coluna `lives.ctr` tem DOIS denominadores
diferentes conforme o schema do export:
  • perfil "views"       (v1, v2)   → ctr = product_clicks ÷ views            (~21-28%)
  • perfil "impressoes"  (v2-api)   → ctr = product_clicks ÷ product_impressions (~5-6%)
São métricas distintas na mesma coluna. Cada perfil ganha seu próprio conjunto de
benchmarks; a extensão detecta em qual deles a tela do Seller Center está e usa o
correspondente. Misturar os dois marcaria a live inteira de vermelho.

CO (R10): `lives.ctor` É a taxa de compra após clique. Não é derivado, não é provisório.
TICKET: bench = GMV ÷ PEDIDOS (o mesmo quociente que o painel calcula ao vivo).
  `avg_price` do export é preço médio por ITEM — outro denominador, vai junto só como referência.

ROOT de propósito (fora de agente_rhode/ → NÃO dispara etl_sync.yml).
Uso:  python3 gerar_benchmarks_live.py [--meses 3] [--out dashlive-ext/benchmarks.js]
"""
import os, re, json, argparse, statistics as st, urllib.request
from datetime import datetime, timezone
from collections import defaultdict
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))
SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": SK, "Authorization": f"Bearer {SK}"}

# schema_version → perfil de denominador do CTR. v3-api não entra: não traz funil.
PERFIS = {"views": ("v1", "v2"), "impressoes": ("v2-api",)}
MIN_LIVES = 3          # mês com menos que isso não entra na janela
TOL = 0.05             # tolerância (p.p.) pra considerar que a identidade fecha


def fetch_lives():
    """Puxa a tabela inteira. order=id (PK única) obriga paginação estável — R7/RUNBOOK #17."""
    out, off = [], 0
    while True:
        q = f"{SB}/rest/v1/lives?select=*&order=id&limit=1000&offset={off}"
        page = json.load(urllib.request.urlopen(urllib.request.Request(q, headers=H)))
        if not page: break
        out += page
        if len(page) < 1000: break
        off += 1000
    return out


def agg(rows, f, zero_e_ausente=False):
    """zero_e_ausente: em views/peak_viewers o importador grava 0 quando o export não
    trouxe a coluna (FUNIL_NULL em atualizar_painel_lives.py). Somar esses zeros afunda
    a média e inventa um benchmark que nenhuma live atingiria."""
    v = [r[f] for r in rows if r.get(f) is not None and not (zero_e_ausente and r[f] == 0)]
    return (round(sum(v) / len(v), 4), round(st.median(v), 4), len(v)) if v else (None, None, 0)


def ticket_por_live(rows):
    """GMV ÷ pedidos por live — o MESMO quociente que o painel calcula ao vivo."""
    v = [r["gmv_bruto"] / r["orders"] for r in rows
         if r.get("orders") and r.get("gmv_bruto") is not None]
    return (round(sum(v) / len(v), 2), round(st.median(v), 2), len(v)) if v else (None, None, 0)


def checa_identidade(rows, perfil):
    """Confirma que o dado ainda obedece à identidade do perfil antes de virar benchmark."""
    ok = n = 0
    for r in rows:
        c, ctr = r.get("product_clicks"), r.get("ctr")
        den = r.get("views") if perfil == "views" else r.get("product_impressions")
        if not (c and ctr and den): continue
        n += 1
        if abs(100 * c / den - ctr) < TOL: ok += 1
    return ok, n


def bench_do_perfil(rows, perfil, meses):
    porm = defaultdict(list)
    for r in rows: porm[r["month"]].append(r)
    janela = [m for m in sorted(porm) if len(porm[m]) >= MIN_LIVES][-meses:]
    if not janela: return None
    sel = [r for m in janela for r in porm[m]]

    ctr_a, ctr_m, ctr_n = agg(sel, "ctr")
    co_a,  co_m,  co_n  = agg(sel, "ctor")
    tk_a,  tk_m,  tk_n  = ticket_por_live(sel)
    gmv_a, gmv_m, gmv_n = agg(sel, "gmv_bruto")
    vw_a,  vw_m,  vw_n  = agg(sel, "views", zero_e_ausente=True)
    pk_a,  pk_m,  pk_n  = agg(sel, "peak_viewers", zero_e_ausente=True)
    ap_a,  _,     _     = agg(sel, "avg_price")
    ok, tot = checa_identidade(sel, perfil)

    return {
        "janela": {"de": janela[0], "ate": janela[-1], "meses": janela, "lives": len(sel)},
        "identidade": {
            "formula": "product_clicks ÷ views" if perfil == "views" else "product_clicks ÷ product_impressions",
            "confere_em": ok, "testadas": tot,
        },
        # bench principal = média (mesma leitura do dash-live.html). Mediana vai junto:
        # GMV/live e views têm cauda longa, e é ela que o painel mostra como referência robusta.
        "ctr":        {"v": ctr_a, "mediana": ctr_m, "n": ctr_n, "unid": "%",  "origem": "lives.ctr"},
        "co":         {"v": co_a,  "mediana": co_m,  "n": co_n,  "unid": "%",  "origem": "lives.ctor (taxa de compra após clique — medido, R10)"},
        "ticket":     {"v": tk_a,  "mediana": tk_m,  "n": tk_n,  "unid": "R$", "origem": "gmv_bruto ÷ orders por live"},
        "gmvPerLive": {"v": gmv_a, "mediana": gmv_m, "n": gmv_n, "unid": "R$", "origem": "lives.gmv_bruto"},
        "views":      {"v": vw_a,  "mediana": vw_m,  "n": vw_n,  "unid": "views", "origem": "lives.views"},
        "peakViewers": ({"v": pk_a, "mediana": pk_m, "n": pk_n, "unid": "viewers", "origem": "lives.peak_viewers"}
                        if pk_n else None),
        # derivado, nunca calibrado: é o produto das duas etapas do funil.
        "convView":   {"v": round(ctr_a * co_a / 100, 4) if (ctr_a and co_a) else None,
                       "unid": "%", "origem": "DERIVADO = ctr × co"},
        "avgPriceItem": {"v": ap_a, "unid": "R$", "origem": "lives.avg_price (preço por ITEM — referência, não é o ticket)"},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meses", type=int, default=3, help="janela rolante de meses por perfil")
    ap.add_argument("--out", default=os.path.join(BASE, "dashlive-ext", "benchmarks.js"))
    a = ap.parse_args()

    rows = fetch_lives()
    porsv = defaultdict(list)
    for r in rows: porsv[r.get("schema_version")].append(r)

    perfis = {}
    for perfil, svs in PERFIS.items():
        sel = [r for sv in svs for r in porsv.get(sv, [])]
        b = bench_do_perfil(sel, perfil, a.meses)
        if b: perfis[perfil] = b

    if not perfis:
        raise SystemExit("nenhum perfil com dado suficiente — benchmarks NÃO regravados")

    payload = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fonte": "Supabase · tabela lives (mesma fonte do dash-live.html)",
        "gerador": "gerar_benchmarks_live.py",
        "total_lives_na_base": len(rows),
        "perfis": perfis,
    }

    js = ("/* GERADO por gerar_benchmarks_live.py — NÃO editar à mão.\n"
          "   Fonte única: tabela `lives` no Supabase (a mesma do dash-live.html).\n"
          "   Regerar:  python3 gerar_benchmarks_live.py\n"
          "   Dois perfis porque `lives.ctr` troca de denominador conforme o schema (R11).\n"
          "   Carregado como content_script ANTES de lib.js/content.js — sem fetch, sem remote code.\n"
          "   Alvo global: `self` no Chrome, `globalThis` sob Node (usado por tests/). */\n"
          '"use strict";\n'
          '(typeof self !== "undefined" ? self : globalThis).DASHLIVE_BENCHMARKS = ' + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n")
    with open(a.out, "w", encoding="utf-8") as f: f.write(js)

    print(f"✓ {a.out}  ({len(rows)} lives na base)")
    for p, b in perfis.items():
        idt = b["identidade"]
        print(f"\n  perfil {p!r} — {idt['formula']}  (identidade confere em {idt['confere_em']}/{idt['testadas']})")
        print(f"    janela {b['janela']['de']}→{b['janela']['ate']} · {b['janela']['lives']} lives")
        for k in ("ctr", "co", "convView", "ticket", "gmvPerLive", "views", "peakViewers"):
            m = b.get(k)
            if not m: continue
            med = f" · mediana {m['mediana']}" if m.get("mediana") is not None else ""
            print(f"    {k:12} = {m['v']} {m['unid']}{med}  (n={m.get('n','—')})")


if __name__ == "__main__":
    main()
