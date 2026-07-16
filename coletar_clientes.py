#!/usr/bin/env python3
"""
Rhode — Coletor do módulo CLIENTES (CRM) → tabela `cliente`.
Identidade por CPF **HASHEADO** (sha256[:16]); CPF cru NUNCA é gravado (LGPD).
Fonte: Orders API (única que tem cliente) + extrato_pedidos (creator do 1º pedido).

Recompute COMPLETO da janela (não incremental): o total de um cliente exige TODOS os
pedidos dele, então recalcula e faz upsert idempotente. Rodar semanal (é pesado).

Uso:  python3 coletar_clientes.py --dias 180
      python3 coletar_clientes.py --inicio 2026-04-01 --fim 2026-07-01
"""
import os, sys, json, argparse, hashlib, urllib.request, urllib.error, re
from decimal import Decimal as D
from collections import defaultdict
from datetime import datetime, timezone, date, timedelta
from dotenv import load_dotenv
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE); load_dotenv(os.path.join(BASE, ".env"))
from coletar_dados import chamar

SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
SBH = {"apikey": SK, "Authorization": f"Bearer {SK}", "Content-Type": "application/json"}

def ep(s): return int(datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
def h16(x): return hashlib.sha256(str(x).encode()).hexdigest()[:16]
def f(v):
    try: return float(D(str(v))) if v not in (None, "") else 0.0
    except Exception: return 0.0

def pageall(b):
    out = []; off = 0
    while True:
        r = json.load(urllib.request.urlopen(urllib.request.Request(f"{SB}/rest/v1/{b}&limit=1000&offset={off}", headers=SBH)))
        out += r
        if len(r) < 1000: break
        off += 1000
    return out

def upsert(table, rows, chunk=500, on_conflict="id"):
    """Self-healing: se a tabela não tem uma coluna (migração pendente), dropa e reenvia
    em vez de crashar e perder a coleta inteira (lição do statement_tx / RUNBOOK #13)."""
    if not rows: print(f"  [SKIP] {table} sem linhas"); return
    url = f"{SB}/rest/v1/{table}?on_conflict={on_conflict}"; dropped = set()
    for i in range(0, len(rows), chunk):
        while True:
            batch = [{k: v for k, v in r.items() if k not in dropped} for r in rows[i:i+chunk]]
            req = urllib.request.Request(url, data=json.dumps(batch).encode(),
                headers={**SBH, "Prefer": "resolution=merge-duplicates,return=minimal"}, method="POST")
            try:
                urllib.request.urlopen(req, timeout=120); break
            except urllib.error.HTTPError as e:
                msg = e.read()[:400].decode(errors="replace")
                m = re.search(r"Could not find the '([^']+)' column", msg)
                if e.code == 400 and m and m.group(1) not in dropped:
                    dropped.add(m.group(1)); print(f"  [SCHEMA-DRIFT] '{m.group(1)}' não existe — dropando. RODAR cliente.sql"); continue
                print(f"  [ERRO upsert {table}] {e.code}: {msg}"); raise
    print(f"  ✓ {table}: {len(rows)} linhas upsertadas" + (f" (ignoradas: {sorted(dropped)})" if dropped else ""))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=180)
    ap.add_argument("--inicio"); ap.add_argument("--fim")
    a = ap.parse_args()
    fim = a.fim or (date.today() + timedelta(days=1)).isoformat()
    ini = a.inicio or (date.today() - timedelta(days=a.dias)).isoformat()
    print(f"═════ clientes — pedidos {ini} → {fim} ═════")
    GE, LT = ep(ini), ep(fim)

    cust = defaultdict(lambda: {"n":0,"gmv":0.0,"first":"9999-99-99","last":"0000-00-00","uf":None,"cid":None,"o1":None})
    tok = None; page = 0; n = 0
    while True:
        p = {"page_size":100,"sort_field":"create_time","sort_order":"ASC"}
        if tok: p["page_token"] = tok
        r = chamar("POST", "/order/202309/orders/search", params=p, body={"create_time_ge":GE,"create_time_lt":LT})
        if r.get("code") != 0:
            print(f"  [API {r.get('code')}] {str(r.get('message'))[:70]}"); break
        d = r.get("data", {}); orders = d.get("orders", [])
        for o in orders:
            if "CANCEL" in (o.get("status") or "").upper(): continue
            cpf = o.get("cpf")
            if not cpf: continue
            c = cust[h16(cpf)]; n += 1
            c["n"] += 1; c["gmv"] += f((o.get("payment") or {}).get("total_amount"))
            dt = datetime.fromtimestamp(int(o.get("create_time") or 0), timezone.utc).strftime("%Y-%m-%d")
            if dt < c["first"]: c["first"] = dt; c["o1"] = str(o.get("id"))
            if dt > c["last"]: c["last"] = dt
            ra = o.get("recipient_address") or {}; di = ra.get("district_info") or []
            if not c["uf"]:
                c["uf"] = next((x.get("address_name") for x in di if x.get("address_level")=="L1"), None)
                c["cid"] = next((x.get("address_name") for x in di if x.get("address_level")=="L2"), None)
        tok = d.get("next_page_token"); page += 1
        if page % 25 == 0: print(f"  …{page}p · {n} pedidos · {len(cust)} clientes", flush=True)
        if not tok or not orders: break

    # creator de origem (1º pedido) via extrato de afiliada
    pers = sorted({ini[:7], fim[:7]} | {d[:7] for c in cust.values() for d in (c["first"], c["last"]) if d[0] == "2"})
    ext = pageall(f"extrato_pedidos?periodo=in.({','.join(pers)})&select=order_id,creator")
    o2c = {}
    for r in ext:
        oid = str(r.get("order_id") or "")
        if oid and oid not in o2c: o2c[oid] = r.get("creator") or ""

    rows = [{"id": k, "n_pedidos": c["n"], "gmv_total": round(c["gmv"], 2),
             "primeiro_pedido": c["first"] if c["first"][0] == "2" else None,
             "ultimo_pedido": c["last"] if c["last"][0] == "2" else None,
             "uf": c["uf"], "cidade": c["cid"], "creator_origem": o2c.get(c["o1"] or "", "")}
            for k, c in cust.items()]
    upsert("cliente", rows)
    seg = defaultdict(int); hoje = date.today()
    for c in cust.values():
        if c["n"] >= 3: seg["vip"] += 1
        elif c["n"] == 2: seg["recorrente"] += 1
        elif c["last"][0] == "2" and (hoje - date.fromisoformat(c["last"])).days <= 60: seg["unico_recente"] += 1
        else: seg["unico_frio"] += 1
    print(f"\n  {n:,} pedidos · {len(cust):,} clientes · GMV R$ {sum(c['gmv'] for c in cust.values()):,.0f}")
    for s in ["vip","recorrente","unico_recente","unico_frio"]:
        print(f"    {s:<14} {seg[s]:>6} ({seg[s]/len(cust)*100:>4.1f}%)")
    print("  ✓ concluído. Views: cliente_resumo · cliente_uf · cliente_creator")

if __name__ == "__main__":
    main()
