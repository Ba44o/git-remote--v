"""
Rhode Jeans — Sync do Relatório MENSAL de Seeding para o Google Sheets (entrega na nuvem)
=========================================================================================
O .xlsx rico continua sendo o artefato local; ESTE script é a entrega COMPARTILHADA:
espelha os dados do relatório num Google Sheet NATIVO (o `relatorios/` é gitignored, então
commitar de volta não serve). Reusa o modelo já computado pelo pipeline
(`seeding_report.compute_seeding`) — não recalcula do zero.

Auth: service account (credentials.json) via gspread + oauth2client — mesmo padrão do
agente_rhode/sync_v2.py (escopo Sheets + Drive). Sheet NATIVO (client.create) não esbarra
na cota de storage da SA (o problema de storageQuotaExceeded é só p/ upload de binário).

Uso:
  python sync_seeding_to_sheets.py [--mes AAAA-MM]     # vazio/ausente = mês anterior a hoje

Abas por mês: "AAAA-MM · Resumo", "· Detalhe", "· Itens", "· Segmentos"
+ aba rolling "KPIs (histórico)" (1 linha/mês, upsert).
"""
from __future__ import annotations
import argparse
import sys
from datetime import date
from pathlib import Path

import gspread
from oauth2client.service_account import ServiceAccountCredentials

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from seeding_report import (compute_seeding, fmt_val, taxa_env, taxa_canc,
                            TIER_ORDER, TIER_FILL, GMV_AFIL_NOTA, mes_label)

CREDENTIALS_FILE = str(BASE / "credentials.json")
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_TITLE = "Rhode — Relatórios de Seeding"
SHARE_EMAIL = "humbertobasso9@gmail.com"
# Reusa o Sheet do projeto (mesmo do sync_v2.py/etl_sync). O SA já tem acesso de escrita;
# ele NÃO tem cota de Drive p/ criar um Sheet novo, então escrevemos neste que já existe.
# O script só cria abas com prefixo do mês + "KPIs (histórico)" — nunca mexe nas abas do ETL.
SPREADSHEET_ID = "1hiyu1y9G7NeiBKnwV6FNlYRjVqTCRP3jY--I0Lv0Mh0"

# paleta
NAVY = "1F2937"; ACCENT = "4F46E5"; GREEN = "ECFDF5"; RED = "FEF2F2"; GREY = "F3F4F6"


# ── helpers de cor/format ───────────────────────────────────────────────────
def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


def _hdr_fmt():
    return {"backgroundColor": _rgb(NAVY),
            "textFormat": {"bold": True, "foregroundColor": _rgb("FFFFFF"), "fontSize": 10},
            "horizontalAlignment": "CENTER", "verticalAlignment": "MIDDLE", "wrapStrategy": "WRAP"}


def mes_anterior(hoje: date) -> str:
    y, m = hoje.year, hoje.month
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


# ── auth / spreadsheet ──────────────────────────────────────────────────────
def auth() -> gspread.Client:
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)
    return gspread.authorize(creds)


def get_or_create(client: gspread.Client):
    global SPREADSHEET_ID
    if SPREADSHEET_ID:
        return client.open_by_key(SPREADSHEET_ID), False
    try:
        ss = client.open(SPREADSHEET_TITLE)
        return ss, False
    except gspread.SpreadsheetNotFound:
        ss = client.create(SPREADSHEET_TITLE)
        print(f"  [+] Spreadsheet criado. FIXE no script: SPREADSHEET_ID = \"{ss.id}\"")
        return ss, True


def ws_reset(ss, title, rows, cols):
    try:
        ws = ss.worksheet(title)
        ws.clear()
        try:
            ws.clear_basic_filter()
        except Exception:
            pass
    except gspread.WorksheetNotFound:
        ws = ss.add_worksheet(title=title, rows=max(rows, 20), cols=max(cols, 8))
    ws.resize(rows=max(rows, 20), cols=max(cols, 8))
    return ws


def _put(ws, values, rng="A1"):
    ws.update(values, rng, value_input_option="RAW")


# ═══════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════
def tab_resumo(ss, M):
    mes = M["mes"]; title = f"{mes} · Resumo"
    rows = []
    rows.append([f"Relatório de Seeding — {M['MES_LBL']}"])
    rows.append([f"Comparação vs. {M['PREV_LBL']} · gerado {M['exec_date']} · fonte: API TikTok Shop"])
    rows.append([])
    rows.append(["Recortes temporais", ""])
    rows.append(["Janela", "Mensal (mês fechado)"])
    rows.append(["Mês analisado", M["MES_LBL"]])
    rows.append(["Mês de comparação", f"{M['PREV_LBL']} (período imediatamente anterior)"])
    rows.append([f"Data de/até ({M['MESN']})", f"{M['TMIN']} a {M['TMAX']}"])
    rows.append(["Janela de atribuição (conversão)", f"1º convite do mês por creator → {M['ATTR_FIM']}"])
    rows.append([])
    rows.append(["Resumo executivo", ""])
    for line in M["resumo"]:
        rows.append([f"• {line}"])
    rows.append([])
    kpi_hdr_row = len(rows) + 1
    rows.append(["KPI", M["MES_LBL"], M["PREV_LBL"], "Δ abs.", "Δ %"])
    for lbl, vj, vm, kind, dt in M["KPIS"]:
        if dt == "pp":
            da = f"{vj - vm:+.1f} p.p."; dp = "—"
        else:
            d = vj - vm
            da = (f"R$ {d:+,.2f}" if kind == "money" else f"{d:+,.1f}" if kind == "num1" else f"{d:+.0f}")
            dpv = ((vj - vm) / vm * 100) if vm else None
            dp = f"{dpv:+.1f}%" if dpv is not None else "sem dado"
        rows.append([lbl, fmt_val(vj, kind), fmt_val(vm, kind), da, dp])
    rows.append([])
    conv = M["conv"]; tem = M["TEM_VENDAS"] and conv["atingidas"]
    sd = None if tem else "sem dado"
    conv_hdr_row = len(rows) + 1
    rows.append([f"Conversão / ROI do seeding ({M['MESN']})", ""])
    conv_rows = [
        ("Creators atingidas (receberam amostra)", str(conv["atingidas"])),
        ("Já venderam pós-amostra (Sim)", sd or str(conv["venderam"])),
        ("Ainda não venderam (Não)", sd or str(conv["nao_venderam"])),
        ("Taxa de conversão do seeding", sd or f"{conv['taxa']:.1f}%"),
        ("Peças vendidas atribuídas (un.)", sd or str(conv["unid"])),
        ("GMV gerado atribuído (R$)", sd or f"R$ {conv['gmv_gerado']:,.2f}"),
        ("GMV gerado por peça enviada (R$)", sd or f"R$ {conv['gmv_por_peca']:,.2f}"),
        ("ROI (lucro ÷ custo)", "sem dado — falta COGS/frete real"),
    ]
    for a, b in conv_rows:
        rows.append([a, b])

    ws = ws_reset(ss, title, len(rows) + 4, 5)
    _put(ws, rows)
    sid = ws.id
    try:
        ws.merge_cells("A1:E1"); ws.merge_cells("A2:E2")
        ws.format("A1", {"textFormat": {"bold": True, "fontSize": 15, "foregroundColor": _rgb(NAVY)}})
        ws.format("A2", {"textFormat": {"italic": True, "foregroundColor": _rgb("6B7280")}})
        for lbl_row in (4, 11, conv_hdr_row):
            ws.format(f"A{lbl_row}", {"textFormat": {"bold": True, "foregroundColor": _rgb(ACCENT)}})
        ws.format(f"A{kpi_hdr_row}:E{kpi_hdr_row}", _hdr_fmt())
        ws.freeze(rows=2)
        ws.columns_auto_resize(0, 4)
    except Exception as e:
        print(f"  [aviso] formatação Resumo: {e}")
    return sid


DET_COLS = ["#", "Creator", "@ TikTok", "Tier (estim.)", "GMV afiliação (R$)", "Peças pedidas",
            "Enviadas", "Canceladas", "Líquidas", "SKUs distintos", "Produtos distintos",
            "1º convite", "Último convite", "Status envio", "Vendeu pós-amostra?",
            "Peças vendidas (un.)", "GMV gerado (R$)", "GMV gerado / peça env. (R$)", "ROI amostra"]


def tab_detalhe(ss, M):
    mes = M["mes"]; title = f"{mes} · Detalhe"
    tgt, ROI = M["tgt"], M["ROI"]
    data = [DET_COLS]
    tier_bg = []       # (row_index_0based, tier)
    for i, c in enumerate(tgt):
        roi = ROI.get(c["canon"], {})
        status = "Enviado" if c["enviadas"] > 0 else "Nada enviado"
        if c["enviadas"] == 0:
            vd, pv, gg, gp, ro = "n/a (não recebida)", "n/a", "n/a", "n/a", "n/a"
        elif not roi.get("ok"):
            vd, pv, gg, gp, ro = ("sem dado",) * 5
        else:
            vd = "Sim" if roi["vendeu"] else "Não"
            pv = roi["unid"]; gg = roi["gmv"]; gp = round(roi["gmv"] / c["enviadas"], 2) if c["enviadas"] else 0
            ro = "sem dado (falta COGS/frete)"
        data.append([i + 1, c["nick"], "@" + c["handle"], c["tier"], c["gmv"], c["pedidas"],
                     c["enviadas"], c["canceladas"], c["liquidas"], c["skus"], c["produtos"],
                     c["d_ini"] or "sem dado", c["d_fim"] or "sem dado", status, vd, pv, gg, gp, ro])
        tier_bg.append((i + 1, c["tier"]))
    # TOTAL
    n = len(tgt); tr = 1 + n
    total = ["", f"TOTAL ({M['AT']['creators_tot']} creators)", "", "", "", M["AT"]["pedidas"],
             M["AT"]["enviadas"], M["AT"]["canceladas"], M["AT"]["liquidas"], "", "", "", "", "",
             "", M["conv"]["unid"], M["conv"]["gmv_gerado"], M["conv"]["gmv_por_peca"], ""]
    data.append(total)

    ws = ws_reset(ss, title, len(data) + 4, len(DET_COLS))
    _put(ws, data)
    sid = ws.id
    last = 1 + n
    try:
        ws.format(f"A1:{_col(len(DET_COLS))}1", _hdr_fmt())
        ws.freeze(rows=1, cols=3)
        # formatos numéricos
        ws.format(f"E2:E{last}", _numfmt('"R$" #,##0.00'))
        ws.format(f"Q2:R{last + 1}", _numfmt('"R$" #,##0.00'))
        ws.format(f"A2:A{last}", {"horizontalAlignment": "CENTER"})
        ws.format(f"F2:K{last}", {"horizontalAlignment": "CENTER"})
        # nota na coluna GMV afiliação (E1)
        _note(ss, sid, 0, 4, GMV_AFIL_NOTA)
        # fills de tier (coluna D = idx 3)
        _tier_fills(ss, sid, tier_bg, col_idx=3)
        # linha TOTAL destacada
        ws.format(f"A{last + 1}:{_col(len(DET_COLS))}{last + 1}",
                  {"backgroundColor": _rgb("EEF2FF"), "textFormat": {"bold": True}})
        # cond. formatting na conversão: Vendeu (col O = idx14) Sim/Não
        _cond_text(ss, sid, 14, 1, last, "Sim", GREEN)
        _cond_text(ss, sid, 14, 1, last, "Não", "FEF3C7")
        # basic filter no cabeçalho de dados
        ws.set_basic_filter(f"A1:{_col(len(DET_COLS))}{last}")
    except Exception as e:
        print(f"  [aviso] formatação Detalhe: {e}")
    return sid


ITENS_COLS = ["#", "Data convite", "Creator", "@ TikTok", "Tier (estim.)", "Produto (título)",
              "SKU / variação", "Status", "Enviada?", "Comissão %", "Order ID"]


def tab_itens(ss, M):
    from seeding_report import SENT, _ck, _tier
    mes = M["mes"]; title = f"{mes} · Itens"
    items = sorted(M["tgt_rows"], key=lambda r: (r["status"] not in SENT, _ck(r["creator"]), r["convite_data"]))
    data = [ITENS_COLS]
    tier_bg = []
    for i, r in enumerate(items):
        env = r["status"] in SENT
        try:
            rate = f"{float(r['commission_rate']) * 100:.0f}%"
        except (ValueError, TypeError):
            rate = "sem dado"
        t = _tier(float(r["creator_gmv"] or 0))
        data.append([i + 1, r["convite_data"] or "sem dado", r["nickname"] or r["creator"],
                     "@" + r["creator"], t, r["title"], r["sku_name"], r["status"],
                     "Sim" if env else "Não", rate,
                     r["order_id"] if r["order_id"] not in ("0", "") else "sem dado"])
        tier_bg.append((i + 1, t))
    ws = ws_reset(ss, title, len(data) + 4, len(ITENS_COLS))
    _put(ws, data)
    sid = ws.id; last = len(items)
    try:
        ws.format(f"A1:{_col(len(ITENS_COLS))}1", _hdr_fmt())
        ws.freeze(rows=1, cols=3)
        _tier_fills(ss, sid, tier_bg, col_idx=4)
        _cond_text(ss, sid, 8, 1, last, "Sim", GREEN)
        _cond_text(ss, sid, 8, 1, last, "Não", RED)
        ws.set_basic_filter(f"A1:{_col(len(ITENS_COLS))}{last}")
    except Exception as e:
        print(f"  [aviso] formatação Itens: {e}")
    return sid


def tab_segmentos(ss, M):
    mes = M["mes"]; title = f"{mes} · Segmentos"
    TJ, TM, cbt, conv = M["TJ"], M["TM"], M["cbt"], M["conv"]
    prod_rows, prod_title, prod_creators = M["prod_rows"], M["prod_title"], M["prod_creators"]
    totj = sum(TJ.values()) or 1
    rows = []
    rows.append([f"Segmentações — {M['MES_LBL']} (peças enviadas)"])
    rows.append([])
    t1 = len(rows) + 1
    rows.append(["Tier", M["MESN"], M["PREVN"], "Δ abs.", "% do total"])
    for t in TIER_ORDER:
        vj, vm = TJ.get(t, 0), TM.get(t, 0)
        rows.append([t, vj, vm, f"{vj - vm:+d}", vj / totj])
    rows.append(["TOTAL", sum(TJ.values()), sum(TM.values()), "", 1.0])
    rows.append([])
    p1 = len(rows) + 1
    rows.append(["#", "Produto", "Peças enviadas", "Creators distintas"])
    for i, (pid, nn) in enumerate(prod_rows):
        rows.append([i + 1, prod_title[pid], nn, len(prod_creators[pid])])
    rows.append([])
    c1 = len(rows) + 1
    rows.append(["Tier", "Atingidas", "Venderam", "Conversão", "Peças env.", "GMV gerado (R$)", "GMV / peça env."])
    for t in TIER_ORDER:
        d = cbt[t]
        if d["ating"] == 0:
            continue
        rows.append([t, d["ating"], d["vend"], (d["vend"] / d["ating"]) if d["ating"] else 0,
                     d["env"], round(d["gmv"], 2), round(d["gmv"] / d["env"], 2) if d["env"] else 0])
    rows.append(["TOTAL", conv["atingidas"], conv["venderam"], (conv["taxa"] / 100),
                 conv["enviadas"], conv["gmv_gerado"], conv["gmv_por_peca"]])

    ncols = 7
    ws = ws_reset(ss, title, len(rows) + 4, ncols)
    _put(ws, rows)
    sid = ws.id
    try:
        ws.format("A1", {"textFormat": {"bold": True, "fontSize": 14, "foregroundColor": _rgb(NAVY)}})
        for hr, wide in ((t1, 5), (p1, 4), (c1, 7)):
            ws.format(f"A{hr}:{_col(wide)}{hr}", _hdr_fmt())
        # % col do bloco tier (col E) e conversão (col E do bloco c1) e produto GMV
        ws.format(f"E{t1 + 1}:E{t1 + len(TIER_ORDER) + 1}", _numfmt("0.0%"))
        ws.format(f"E{c1 + 1}:E{c1 + 8}", _numfmt("0.0%"))
        ws.format(f"F{c1 + 1}:G{c1 + 9}", _numfmt('"R$" #,##0.00'))
        # fills de tier nas duas tabelas de tier
        _tier_fills(ss, sid, [(t1 - 1 + 1 + k, t) for k, t in enumerate(TIER_ORDER)], col_idx=0)
        ws.freeze(rows=1)
        ws.columns_auto_resize(0, ncols - 1)
    except Exception as e:
        print(f"  [aviso] formatação Segmentos: {e}")
    return sid


HIST_COLS = ["Mês", "Peças enviadas", "Canceladas", "Creators atingidas",
             "Conversão", "GMV gerado (R$)", "GMV gerado / peça env. (R$)"]


def tab_historico(ss, M):
    """Rolling: 1 linha por mês (upsert por mês, mantém ordenado)."""
    title = "KPIs (histórico)"
    conv = M["conv"]
    linha = [M["mes"], M["AT"]["enviadas"], M["AT"]["canceladas"], conv["atingidas"],
             round(conv["taxa"] / 100, 4), conv["gmv_gerado"], conv["gmv_por_peca"]]
    # lê existente
    existentes = {}
    try:
        ws = ss.worksheet(title)
        vals = ws.get_all_values()
        for r in vals[1:]:
            if r and r[0] and r[0] != "Mês":
                existentes[r[0]] = r
    except gspread.WorksheetNotFound:
        pass
    existentes[M["mes"]] = linha
    ordenado = [existentes[k] for k in sorted(existentes)]
    data = [HIST_COLS] + ordenado
    ws = ws_reset(ss, title, len(data) + 6, len(HIST_COLS))
    _put(ws, data)
    sid = ws.id; last = len(ordenado) + 1
    try:
        ws.format(f"A1:{_col(len(HIST_COLS))}1", _hdr_fmt())
        ws.freeze(rows=1)
        ws.format(f"E2:E{last}", _numfmt("0.0%"))
        ws.format(f"F2:G{last}", _numfmt('"R$" #,##0.00'))
        ws.format(f"B2:D{last}", {"horizontalAlignment": "CENTER"})
        # color scale na conversão
        _cond_scale(ss, sid, 4, 1, last)
        ws.columns_auto_resize(0, len(HIST_COLS) - 1)
    except Exception as e:
        print(f"  [aviso] formatação Histórico: {e}")
    return sid


# ── formatação via batch_update (notes, fills, conditional) ─────────────────
def _col(n):  # idx 1-based → letra
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _numfmt(pattern):
    return {"numberFormat": {"type": "NUMBER", "pattern": pattern}}


def _note(ss, sid, row0, col0, text):
    ss.batch_update({"requests": [{"updateCells": {
        "range": {"sheetId": sid, "startRowIndex": row0, "endRowIndex": row0 + 1,
                  "startColumnIndex": col0, "endColumnIndex": col0 + 1},
        "rows": [{"values": [{"note": text}]}], "fields": "note"}}]})


def _tier_fills(ss, sid, tier_bg, col_idx):
    reqs = []
    for row0, tier in tier_bg:
        reqs.append({"repeatCell": {
            "range": {"sheetId": sid, "startRowIndex": row0, "endRowIndex": row0 + 1,
                      "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
            "cell": {"userEnteredFormat": {
                "backgroundColor": _rgb(TIER_FILL.get(tier, "9CA3AF")),
                "textFormat": {"bold": True, "foregroundColor": _rgb("FFFFFF")},
                "horizontalAlignment": "CENTER"}},
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"}})
    if reqs:
        ss.batch_update({"requests": reqs})


def _cond_text(ss, sid, col0, start_row0, end_row1, text, hexcolor):
    ss.batch_update({"requests": [{"addConditionalFormatRule": {"rule": {
        "ranges": [{"sheetId": sid, "startRowIndex": start_row0, "endRowIndex": end_row1,
                    "startColumnIndex": col0, "endColumnIndex": col0 + 1}],
        "booleanRule": {"condition": {"type": "TEXT_EQ",
                                      "values": [{"userEnteredValue": text}]},
                        "format": {"backgroundColor": _rgb(hexcolor)}}}, "index": 0}}]})


def _cond_scale(ss, sid, col0, start_row0, end_row1):
    ss.batch_update({"requests": [{"addConditionalFormatRule": {"rule": {
        "ranges": [{"sheetId": sid, "startRowIndex": start_row0, "endRowIndex": end_row1,
                    "startColumnIndex": col0, "endColumnIndex": col0 + 1}],
        "gradientRule": {"minpoint": {"color": _rgb("FEF2F2"), "type": "MIN"},
                         "maxpoint": {"color": _rgb("D1FAE5"), "type": "MAX"}}}, "index": 0}}]})


# ═══════════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", default=None, help="mês-alvo AAAA-MM; vazio/ausente = mês anterior a hoje")
    args = ap.parse_args()
    hoje = date.today()
    mes = args.mes.strip() if (args.mes and args.mes.strip()) else mes_anterior(hoje)
    try:
        assert len(mes) == 7 and mes[4] == "-" and 1 <= int(mes[5:7]) <= 12
    except (ValueError, AssertionError):
        print(f"[ERRO] --mes inválido: {args.mes!r}", file=sys.stderr); sys.exit(2)

    print(f"Sync Seeding → Google Sheets · mês-alvo: {mes}")
    M = compute_seeding(mes, exec_date=hoje.strftime("%Y-%m-%d"), base=BASE)

    client = auth()
    ss, criado = get_or_create(client)
    # só (re)compartilha se NÓS criamos o Sheet; num Sheet reusado o usuário já tem acesso
    # e o SA pode nem ter permissão de gerenciar collaborators.
    if criado:
        try:
            ss.share(SHARE_EMAIL, perm_type="user", role="writer", notify=False)
            print(f"  [✓] compartilhado (writer) com {SHARE_EMAIL}")
        except Exception as e:
            print(f"  [aviso] share falhou: {e}")

    print("  → Resumo");     tab_resumo(ss, M)
    print("  → Detalhe");    tab_detalhe(ss, M)
    print("  → Itens");      tab_itens(ss, M)
    print("  → Segmentos");  tab_segmentos(ss, M)
    print("  → KPIs (histórico)"); tab_historico(ss, M)

    # só limpa a aba default se NÓS criamos o spreadsheet — nunca apaga aba de um Sheet reusado
    if criado:
        for junk in ("Sheet1", "Página1", "Planilha1"):
            try:
                ss.del_worksheet(ss.worksheet(junk))
            except Exception:
                pass

    url = f"https://docs.google.com/spreadsheets/d/{ss.id}"
    print(f"\n=== OK ===\nSpreadsheet ID: {ss.id}\nURL: {url}")
    if criado or not SPREADSHEET_ID:
        print(f"IMPORTANTE: fixe no script → SPREADSHEET_ID = \"{ss.id}\"")


if __name__ == "__main__":
    main()
