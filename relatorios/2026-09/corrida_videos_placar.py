#!/usr/bin/env python3
"""
Rhode — PLACAR da Corrida de Vídeos Rhode Jeans (#CorridaRhode).
Regras oficiais V3 (playbook 07/09/2026):
  · Janela 07/09 → 13/09 23h59.  Pontua: vídeo com #CorridaRhode + LINK no carrinho.
    (video_perf só traz vídeo que marcou produto = já garante o "link no carrinho".)
  · Live NÃO pontua (video_perf é vídeo, não live — ok por construção).
  · VENCEDOR = Top 5 GMV; DESEMPATE = mais views.
  · Metas coletivas (gatilhos): grupo bate 150 vídeos → destrava R$1.500 Pix Top 5 GMV;
    bate 500 → Top 5 de VOLUME leva R$100 cada.
  · Qualificação individual: 5 vídeos → cupom RHODE10; >5 vídeos → 1 peça Rhode.
  · Prêmio Top 5 GMV: 1º 600 · 2º 400 · 3º 250 · 4º 125 · 5º 125 (= R$1.500).

⚠️ TRAVA (honesta): GMV é lifetime por vídeo e só atualiza quando coletar_shop_videos.py roda;
   vídeo novo aparece com GMV≈0 e matura em dias. Apuração de DINHEIRO justa só ~D+2 do fim
   (≥15/09). Cedo, o Top 5 GMV é na prática ranking por VIEWS (o desempate manda).

Uso:
  python3 corrida_videos_placar.py                       # print do placar (padrão)
  python3 corrida_videos_placar.py --xlsx caminho.xlsx   # gera planilha expert
  python3 corrida_videos_placar.py --inscritas @a,@b     # ∪ lista de inscritas
  python3 corrida_videos_placar.py --merge b=a,d=c       # funde handles (b vira a)
"""
import os, sys, json, argparse, urllib.request, urllib.parse
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
load_dotenv(os.path.join(BASE, "..", "..", ".env"))
SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
H = {"apikey": SK, "Authorization": f"Bearer {SK}"}

HASHTAG = "corridarhode"
JAN_INI = "2026-09-07"; JAN_FIM = "2026-09-14"   # exclusivo (pega até 13/09 23h59)
GATE_150 = 150; GATE_500 = 500
META_QUALIF = 5                                   # ≥5 vídeos → cupom
PREMIO_GMV = {1: 600, 2: 400, 3: 250, 4: 125, 5: 125}
BONUS_VOL = 100
CUPOM = "RHODE10"

TAG_JSON = os.path.join(BASE, "corrida_tag_total.json")

def load_tag():
    """Retorna a contagem da tag no TikTok mais recente já informada (manual)."""
    try:
        d = json.load(open(TAG_JSON))
        if d:
            last = sorted(d.keys())[-1]
            return {"value": int(d[last]), "date": last}
    except Exception:
        pass
    return None

def save_tag(n):
    d = {}
    try: d = json.load(open(TAG_JSON))
    except Exception: pass
    hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d")
    d[hoje] = int(n)
    json.dump(d, open(TAG_JSON, "w"), ensure_ascii=False, indent=2)
    return {"value": int(n), "date": hoje}

def q(path):
    r = urllib.request.Request(f"{SB}/rest/v1/{path}", headers=H)
    return json.load(urllib.request.urlopen(r, timeout=90))

def puxar(ini, fim, inscritas):
    """Coorte = (#CorridaRhode na legenda) ∪ (inscritas), dentro da janela."""
    cols = "id,username,post_time,gmv,views,ctr,sku_orders,units_sold,title,produtos"
    vids = {}
    for v in q(f"video_perf?select={cols}&title=ilike.*{HASHTAG}*&post_time=gte.{ini}&post_time=lt.{fim}"):
        vids[v["id"]] = {**v, "via_tag": True, "via_inscrita": False}
    for u in inscritas:
        for v in q(f"video_perf?select={cols}&username=eq.{urllib.parse.quote(u)}&post_time=gte.{ini}&post_time=lt.{fim}"):
            if v["id"] in vids:
                vids[v["id"]]["via_inscrita"] = True
            else:
                vids[v["id"]] = {**v, "via_tag": False, "via_inscrita": True}
    return list(vids.values())

def agregar(vids, merge):
    cre = defaultdict(lambda: {"n": 0, "views": 0, "gmv": 0.0, "ord": 0, "un": 0,
                               "cliques": 0.0, "tag": False, "insc": False})
    for v in vids:
        u = merge.get(v["username"], v["username"])
        c = cre[u]
        c["n"] += 1; c["views"] += v.get("views") or 0
        c["gmv"] += float(v.get("gmv") or 0)
        c["ord"] += v.get("sku_orders") or 0; c["un"] += v.get("units_sold") or 0
        if v.get("ctr") and v.get("views"):
            c["cliques"] += (v["ctr"] / 100.0) * v["views"]
        c["tag"] = c["tag"] or v.get("via_tag", False)
        c["insc"] = c["insc"] or v.get("via_inscrita", False)
    out = []
    for u, c in cre.items():
        out.append({
            "creator": u, "videos": c["n"], "views": c["views"],
            "gmv": round(c["gmv"], 2), "pedidos": c["ord"], "unidades": c["un"],
            "gmv_video": round(c["gmv"] / c["n"], 2) if c["n"] else 0.0,
            "ctr": round(c["cliques"] / c["views"] * 100, 2) if c["views"] else 0.0,
            "conv": round(c["ord"] / c["views"] * 100, 3) if c["views"] else 0.0,
            "meta1": c["n"] >= META_QUALIF, "meta2": c["n"] > META_QUALIF,
            "origem": ("tag+insc" if c["tag"] and c["insc"] else "tag" if c["tag"] else "só inscrita (s/ #)"),
        })
    return out

def placar(vids, creators, tag_info=None):
    verificados = len(vids)                       # tag + link, em video_perf (base do GMV)
    # Gate dos 150/500 usa a CONTAGEM DA TAG no TikTok (o que o grupo vê); se não informada,
    # cai no verificado. Ver reference_hashtag_via_video_perf_title.
    tag_total = (tag_info or {}).get("value")
    gate = tag_total if tag_total is not None else verificados
    b150 = gate >= GATE_150; b500 = gate >= GATE_500
    top_gmv = sorted(creators, key=lambda x: (-x["gmv"], -x["views"]))[:5]
    top_vol = sorted(creators, key=lambda x: (-x["videos"], -x["gmv"]))[:5]
    premios = {}
    if b150:
        for i, c in enumerate(top_gmv, 1):
            premios[c["creator"]] = f"R$ {PREMIO_GMV[i]}" + (" + Ads" if i == 1 else " + Comissão turbo" if i in (2, 3) else "") + " + Peça"
    return {
        "verificados": verificados, "tag_total": tag_total,
        "tag_date": (tag_info or {}).get("date"), "gate": gate,
        "bateu_150": b150, "bateu_500": b500,
        "faltam_150": max(0, GATE_150 - gate), "faltam_500": max(0, GATE_500 - gate),
        "gmv_total": round(sum(c["gmv"] for c in creators), 2),
        "views_total": sum(c["views"] for c in creators),
        "pedidos_total": sum(c["pedidos"] for c in creators),
        "n_creators": len(creators),
        "n_meta1": sum(1 for c in creators if c["meta1"]),
        "n_meta2": sum(1 for c in creators if c["meta2"]),
        "top_gmv": top_gmv, "top_vol": top_vol, "premios": premios,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ini", default=JAN_INI); ap.add_argument("--fim", default=JAN_FIM)
    ap.add_argument("--inscritas", default=""); ap.add_argument("--merge", default="")
    ap.add_argument("--tag_total", type=int, default=None,
                    help="contagem de publicações na #CorridaRhode lida no TikTok (manual, persiste)")
    ap.add_argument("--xlsx", default="")
    a = ap.parse_args()
    inscritas = [x.strip().lstrip("@").lower() for x in a.inscritas.split(",") if x.strip()]
    merge = {}
    for par in a.merge.split(","):
        if "=" in par:
            k, v = par.split("=", 1); merge[k.strip().lstrip("@").lower()] = v.strip().lstrip("@").lower()

    tag_info = save_tag(a.tag_total) if a.tag_total is not None else load_tag()
    vids = puxar(a.ini, a.fim, inscritas)
    creators = agregar(vids, merge)
    p = placar(vids, creators, tag_info)
    agora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M")
    tagd = (p["tag_date"][8:10] + "/" + p["tag_date"][5:7]) if p["tag_date"] else None

    print(f"═════ 🏁 CORRIDA DE VÍDEOS RHODE · #{HASHTAG} · {a.ini}→13/09 · {agora} ═════")
    imaturos = sum(1 for v in vids if float(v.get('gmv') or 0) == 0)
    tagtxt = f"{p['tag_total']} publicações na tag (TikTok, informado {tagd})" if p["tag_total"] is not None else f"{p['verificados']} (sem contagem da tag informada)"
    print(f"  TERMÔMETRO: {p['gate']}/150  →  {tagtxt}")
    print(f"  Verificados com link (base do prêmio GMV): {p['verificados']}  ·  faltam {p['faltam_150']} p/ R$1.500"
          f"{'  ✅ 150 BATIDA' if p['bateu_150'] else ''}{'  🚀 500 BATIDA' if p['bateu_500'] else ''}")
    print(f"  {p['n_creators']} creators · {p['views_total']:,} views · R$ {p['gmv_total']:,.0f} GMV · "
          f"{p['pedidos_total']} pedidos · {imaturos}/{len(vids)} verificados com GMV=0 (imaturos)")
    print(f"  Qualificação: {p['n_meta1']} creators com ≥5 vídeos (cupom) · {p['n_meta2']} com >5 (peça)")

    print(f"\n  🏆 TOP 5 GMV (desempate por views){'  — provisório: GMV imaturo, manda o alcance' if p['gmv_total']==0 else ''}")
    print(f"    {'#':>2} {'creator':<24}{'gmv':>8}{'views':>9}{'víd':>5}{'ped':>5}  prêmio (se bater 150)")
    for i, c in enumerate(p["top_gmv"], 1):
        print(f"    {i:>2} {c['creator'][:23]:<24}{c['gmv']:>8,.0f}{c['views']:>9,}{c['videos']:>5}{c['pedidos']:>5}  "
              f"{p['premios'].get(c['creator'], '—')}")

    print(f"\n  📹 TOP 5 VOLUME (bônus R$100 se grupo bater 500)")
    print(f"    {'#':>2} {'creator':<24}{'víd':>5}{'views':>9}{'gmv':>8}")
    for i, c in enumerate(p["top_vol"], 1):
        print(f"    {i:>2} {c['creator'][:23]:<24}{c['videos']:>5}{c['views']:>9,}{c['gmv']:>8,.0f}")

    if merge:
        print(f"\n  🔗 handles fundidos: {merge}")
    print()

    if a.xlsx:
        from corrida_xlsx import build_xlsx
        build_xlsx(a.xlsx, p, creators, vids, agora, a.ini, "13/09/2026 23h59", tagd)
        print(f"  ✓ xlsx → {a.xlsx}")

if __name__ == "__main__":
    main()
