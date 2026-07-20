#!/usr/bin/env python3
"""
Rhode — Coletor de PERFORMANCE POR VÍDEO × CREATOR → tabela `video_perf`.
Fonte: Shop Partner API GET /analytics/202409/shop_videos/performance (HMAC via coletar_dados.chamar).
Métricas são LIFETIME por vídeo; a janela (start_date_ge/end_date_lt) filtra QUAIS vídeos voltam
(por atividade, não por data de post) → UMA janela só + dedup por id. Fatiar por mês DUPLICARIA vídeos.

Por que existe: hoje o pipeline só rastreia creator que VENDE (extrato/affiliate_creator_product).
Quem posta e ainda não converteu é invisível. Este coletor abastece o "Radar de creators de potencial"
(alcance sem conversão + esforço consistente + frequência) no admin.html. NÃO é financeiro (≠ conciliacao).

Uso:  python3 coletar_shop_videos.py --dias 120
      python3 coletar_shop_videos.py --inicio 2026-04-01 --fim 2026-07-18
      python3 coletar_shop_videos.py --dias 120 --dry     # não grava; imprime radar + dump JSON
"""
import os, sys, json, argparse, urllib.request, urllib.error, re, time
from decimal import Decimal as D
from collections import defaultdict
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE); load_dotenv(os.path.join(BASE, ".env"))
from coletar_dados import chamar

SB = os.environ.get("SUPABASE_URL"); SK = os.environ.get("SUPABASE_SERVICE_KEY")
SBH = {"apikey": SK, "Authorization": f"Bearer {SK}", "Content-Type": "application/json"} if SK else {}
SCR = "/private/tmp/claude-501/-Users-user-Documents-VS-Claude-Teste/8ca2de48-2449-4f41-aa50-1f0f3434200f/scratchpad"

def f(v):
    try: return float(D(str(v))) if v not in (None, "") else 0.0
    except Exception: return 0.0
def i(v):
    try: return int(float(v)) if v not in (None, "") else 0
    except Exception: return 0

def upsert(table, rows, chunk=500, on_conflict="id"):
    """Self-healing: se falta coluna (migração pendente), dropa e reenvia em vez de perder tudo
    (lição do statement_tx / RUNBOOK #13)."""
    if not rows: print(f"  [SKIP] {table} sem linhas"); return
    url = f"{SB}/rest/v1/{table}?on_conflict={on_conflict}"; dropped = set()
    for k in range(0, len(rows), chunk):
        while True:
            batch = [{c: v for c, v in r.items() if c not in dropped} for r in rows[k:k+chunk]]
            req = urllib.request.Request(url, data=json.dumps(batch).encode(),
                headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
            try:
                urllib.request.urlopen(req, timeout=120); break
            except urllib.error.HTTPError as e:
                msg = e.read()[:400].decode(errors="replace")
                m = re.search(r"Could not find the '([^']+)' column", msg)
                if e.code == 400 and m and m.group(1) not in dropped:
                    dropped.add(m.group(1)); print(f"  [SCHEMA-DRIFT] '{m.group(1)}' não existe — dropando. RODAR video_perf.sql"); continue
                print(f"  [ERRO upsert {table}] {e.code}: {msg}"); raise
    print(f"  ✓ {table}: {len(rows)} linhas upsertadas" + (f" (ignoradas: {sorted(dropped)})" if dropped else ""))

def coletar(ge, lt):
    """UMA janela, token-loop robusto. Termina SÓ quando next_page_token vazio (fim natural).
    Página vazia COM token = assinatura da truncagem silenciosa (bug 16/07) → retenta o mesmo token."""
    vids = {}; tok = None; page = 0; total = None; empty_retry = 0
    while True:
        p = {"start_date_ge": ge, "end_date_lt": lt, "granularity": "ALL", "page_size": 100}
        if tok: p["page_token"] = tok
        r = chamar("GET", "/analytics/202409/shop_videos/performance", params=p)
        if r.get("code") != 0:
            raise RuntimeError(f"API code={r.get('code')}: {str(r.get('message'))[:80]}")
        d = r.get("data", {}) or {}
        if total is None: total = i(d.get("total_count"))
        got = d.get("videos") or []
        ntok = d.get("next_page_token") or ""
        if not got and ntok:                      # vazio mas há token → possível truncagem
            empty_retry += 1
            if empty_retry <= 5:
                time.sleep(1.5); continue         # NÃO avança o token — retenta a mesma página
            raise RuntimeError(f"página vazia com token vivo após 5 tentativas (pg {page}) — API instável, abortando")
        empty_retry = 0
        for v in got:
            vid = str(v.get("id") or "")
            if vid: vids[vid] = v                 # dedup por id
        page += 1; tok = ntok
        if page % 20 == 0: print(f"  …{page}p · {len(vids)} vídeos", flush=True)
        if not tok: break
    # GUARDA DE COMPLETUDE: bateu com o total_count que a própria API declara?
    if total and len(vids) < total * 0.98:
        raise SystemExit(f"\n🛑 ABORTADO: coletei {len(vids)} de {total} vídeos (total_count da API). "
                         f"Coleta truncou — NADA gravado. Rode de novo.")
    print(f"  ✓ {len(vids)} vídeos únicos (total_count API: {total}) · {page} páginas")
    return list(vids.values())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=120)
    ap.add_argument("--inicio"); ap.add_argument("--fim")
    ap.add_argument("--dry", action="store_true", help="não grava no Supabase; imprime radar + dump JSON")
    a = ap.parse_args()
    fim = a.fim or (date.today() + timedelta(days=1)).isoformat()
    ini = a.inicio or (date.today() - timedelta(days=a.dias)).isoformat()
    print(f"═════ shop_videos — janela {ini} → {fim} ═════")

    raw = coletar(ini, fim)

    rows = []
    for v in raw:
        prods = ", ".join(sorted({(p.get("name") or "")[:40] for p in (v.get("products") or []) if p.get("name")}))
        rows.append({
            "id": str(v.get("id")), "username": (v.get("username") or "").lower(),
            "title": (v.get("title") or "")[:300] or None,
            "post_time": (v.get("video_post_time") or None),
            "views": i(v.get("views")), "ctr": f(v.get("click_through_rate")) or None,
            "gmv": round(f((v.get("gmv") or {}).get("amount")), 2),
            "sku_orders": i(v.get("sku_orders")), "units_sold": i(v.get("units_sold")),
            "produtos": prods or None,
        })

    # ── radar por creator (as 3 réguas: alcance · consistência sustentada · frequência-taxa) ──
    hoje = date.today()
    cre = defaultdict(lambda: {"n": 0, "views": 0, "gmv": 0.0, "ord": 0, "semanas": set(),
                               "first": "9999", "last": "0000"})
    for r in rows:
        c = cre[r["username"]]; c["n"] += 1; c["views"] += r["views"]; c["gmv"] += r["gmv"]; c["ord"] += r["sku_orders"]
        pt = (r["post_time"] or "")[:10]
        if pt and pt[0] == "2":
            try:
                iso = date.fromisoformat(pt).isocalendar(); c["semanas"].add((iso[0], iso[1]))
            except Exception: pass
            if pt < c["first"]: c["first"] = pt
            if pt > c["last"]: c["last"] = pt
    radar = []
    for u, c in cre.items():
        sem = len(c["semanas"]); vsem = c["n"]/sem if sem else c["n"]
        try: dias = (hoje - date.fromisoformat(c["last"])).days if c["last"][0] == "2" else 999
        except Exception: dias = 999
        radar.append({"creator": u, "n_videos": c["n"], "semanas_ativas": sem,
                      "views_total": c["views"], "views_por_video": round(c["views"]/c["n"]),
                      "gmv_total": round(c["gmv"], 2), "orders_total": c["ord"],
                      "conv_pct": round(c["ord"]/c["views"]*100, 4) if c["views"] else 0.0,
                      "videos_por_semana": round(vsem, 2), "dias_desde_ultimo": dias,
                      "score": round(sem*12 + min(vsem, 5)*4 + c["views"]/1000),
                      "primeiro": c["first"], "ultimo": c["last"]})
    base = [x for x in radar if x["orders_total"] == 0 and x["views_total"] >= 500]
    ativo = sorted([x for x in base if x["dias_desde_ultimo"] <= 30], key=lambda x: -x["score"])
    esfriou = sorted([x for x in base if x["dias_desde_ultimo"] > 30 and x["semanas_ativas"] >= 3],
                     key=lambda x: -x["score"])

    print(f"\n  {len(rows):,} vídeos · {len(radar):,} creators · {sum(r['sku_orders'] for r in rows):,} pedidos atribuídos")
    def tabela(titulo, lst):
        print(f"\n── {titulo}: {len(lst)} creators")
        print(f"  {'creator':<26}{'score':>6}{'vids':>6}{'sem':>5}{'views':>10}{'v/sem':>7}{'últ.':>6}")
        for x in lst[:15]:
            print(f"  {x['creator'][:25]:<26}{x['score']:>6}{x['n_videos']:>6}{x['semanas_ativas']:>5}"
                  f"{x['views_total']:>10,}{x['videos_por_semana']:>7}{x['dias_desde_ultimo']:>5}d")
    tabela("POTENCIAL ATIVO — alcance s/ conversão, consistente e ainda postando (≤30d) → PROSPECTAR", ativo)
    tabela("ESFRIARAM — foram consistentes (3+ sem) e pararam (>30d) → REATIVAR", esfriou)

    if a.dry:
        os.makedirs(SCR, exist_ok=True)
        json.dump({"radar": radar, "potencial_ativo": ativo, "esfriou": esfriou},
                  open(f"{SCR}/creator_radar.json", "w"), ensure_ascii=False)
        print(f"\n  [DRY] nada gravado no Supabase. Dump → {SCR}/creator_radar.json")
        return
    upsert("video_perf", rows)
    print("  ✓ concluído. Views: creator_radar · creator_potencial")

if __name__ == "__main__":
    main()
