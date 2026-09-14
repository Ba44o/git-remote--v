#!/usr/bin/env python3
"""
Rhode — orquestrador do RELATÓRIO SEMANAL HEAD (terça 08:00) e do CHECK DE SEXTA (sexta 08:00).

Roda dentro da corrente de jobs (o cron do GitHub é estrangulado — a corrente é o único
agendamento confiável), a cada 15 min. É idempotente:
  · relatório de terça → estado = appProperties `semana` na planilha, na pasta do semanal
  · check de sexta     → estado = arquivo marcador na subpasta "_estado", appProperties `check_sexta`
Se a corrente estiver fora do ar na hora marcada, o próximo ciclo recupera (terça→domingo
para o relatório; sexta→domingo para o check). Segunda nunca gera: a semana ainda não amadureceu.

Uso:  python3 automacao/monitor_semanal.py
      python3 automacao/monitor_semanal.py --forcar-semana 2026-09-07
      python3 automacao/monitor_semanal.py --forcar-check
"""
import os, sys, argparse, subprocess
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "automacao"))
try:
    from dotenv import load_dotenv; load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass
from dados_semana import semana_de, semana_id, BRT

PASTA = os.environ.get("DRIVE_FOLDER_HEAD", "1lT2xshXVJBaS3WlGJIwCEDAMJ06a7fmC")
SA = "rhode-etl-936@creators-rhode.iam.gserviceaccount.com"
HORA = 8


def _drive():
    import importlib.util
    spec = importlib.util.spec_from_file_location("pubdrive", os.path.join(ROOT, "relatorios", "_publicar_drive.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    from googleapiclient.discovery import build
    cred = mod.obter_credenciais()
    return build("drive", "v3", credentials=cred), cred


def _listar(drive, pasta, extra=""):
    out = []; tok = None
    while True:
        r = drive.files().list(q=f"'{pasta}' in parents and trashed=false{extra}",
                               fields="nextPageToken, files(id,name,appProperties,webViewLink,mimeType)",
                               pageSize=200, pageToken=tok).execute()
        out += r.get("files", []); tok = r.get("nextPageToken")
        if not tok: return out


def _pasta_estado(drive):
    for f in _listar(drive, PASTA, " and mimeType='application/vnd.google-apps.folder'"):
        if f["name"] == "_estado":
            return f["id"]
    return drive.files().create(body={"name": "_estado", "parents": [PASTA],
                                      "mimeType": "application/vnd.google-apps.folder"}, fields="id").execute()["id"]


def coletar(seg, dom, pesado=False):
    """Fontes da semana. As críticas abortam; as não-críticas só avisam."""
    d = lambda x: x.strftime("%Y-%m-%d")
    criticas = [
        ["python3", "coletar_pedidos_sku.py", "--inicio", d(seg), "--fim", d(dom + timedelta(days=1))],  # data é UTC
        ["python3", "coletar_gmvmax_api.py", "--inicio", d(seg), "--fim", d(dom)],
        ["python3", "coletar_lives_attr_api.py", "--inicio", d(seg), "--fim", d(dom)],
    ]
    for cmd in criticas:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            raise RuntimeError(f"{cmd[1]} falhou — não fecho a semana com dado velho:\n{(r.stderr or '')[-400:]}")
    # extrato: sem ele, pedido de afiliada vira "loja própria" (visto 14/09: 476 → 88 peças).
    # Não-crítico para não travar o fechamento se o coletor falhar na nuvem — a aba Saúde do
    # dado e o aviso no Veredito denunciam o atraso. --no-forward: NÃO tocar performance_periods.
    nao_criticas = [["python3", "coletar_extrato.py", "--inicio", d(seg - timedelta(days=1)),
                     "--fim", d(dom + timedelta(days=1)), "--no-forward"],
                    ["python3", "agente_rhode/etl_devolucoes.py", "--dias", "14"],
                    ["python3", "agente_rhode/sync_supabase.py", "--only", "devolucoes"]]
    if pesado:
        nao_criticas.append(["python3", "coletar_statement_tx.py", "--dias", "45"])
    for cmd in nao_criticas:
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=2400)
        if r.returncode != 0:
            print(f"  ⚠ {cmd[1]} falhou (não-crítico, segue): {(r.stderr or '')[-160:]}")


def relatorio_semanal(seg, forcar=False):
    dom = seg + timedelta(days=6); sid = semana_id(seg)
    drive, cred = _drive()
    feitos = {(f.get("appProperties") or {}).get("semana"): f for f in _listar(drive, PASTA)}
    if sid in feitos and not forcar:
        return feitos[sid].get("webViewLink")
    print(f"═══ relatório semanal head · {sid} ({seg} → {dom}) ═══")
    print("  · coletando fontes da semana…")
    try:
        coletar(seg, dom, pesado=True)
    except RuntimeError as e:
        print(f"  ✗ {e}"); return None
    xlsx = f"/tmp/head_{sid}.xlsx"
    r = subprocess.run(["python3", os.path.join(ROOT, "automacao", "gerar_relatorio_head.py"),
                        "--seg", seg.strftime("%Y-%m-%d"), "--saida", xlsx],
                       cwd=ROOT, capture_output=True, text=True, timeout=3600)
    print("   ", "\n    ".join(l for l in r.stdout.strip().splitlines() if l.strip() and not l.startswith("  ·")))
    if r.returncode != 0 or not os.path.exists(xlsx):
        print(f"  ✗ geração falhou: {(r.stderr or '')[-400:]}"); return None
    if not getattr(cred, "refresh_token", None):
        print("  ✗ sem OAuth — a service account não cria arquivo"); return None
    hoje = datetime.now(BRT).strftime("%Y-%m-%d")
    nome = f"Relatorio Semanal Head {sid} ({seg.strftime('%d-%m')} a {dom.strftime('%d-%m')})_{hoje}"
    f = drive.files().create(body={"name": nome, "mimeType": "application/vnd.google-apps.spreadsheet",
                                   "parents": [PASTA], "appProperties": {"semana": sid}},
                             fields="id,webViewLink").execute()
    try:
        drive.permissions().create(fileId=f["id"], body={"type": "user", "role": "writer", "emailAddress": SA},
                                   sendNotificationEmail=False).execute()
    except Exception:
        pass
    md = xlsx.replace(".xlsx", ".md")
    args = [sys.executable, os.path.join(ROOT, "relatorios", "_publicar_drive.py"), xlsx, f["id"]]
    if os.path.exists(md): args.append(md)
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        print(f"  ✗ publicação falhou: {(r.stderr or '')[-300:]}"); return None
    url = f.get("webViewLink")
    print(f"  ✅ {url}")
    # a PRÉVIA da mesma semana (appProperties previa) sai de cena quando o oficial é publicado —
    # a prévia nunca conta como "feito", então não bloqueia o fechamento de terça
    for pf in _listar(drive, PASTA):
        if (pf.get("appProperties") or {}).get("previa") == sid:
            drive.files().update(fileId=pf["id"], body={"trashed": True}).execute()
            print(f"  · prévia substituída pelo oficial: {pf['name']}")
    if not os.environ.get("SEM_EMAIL"):
        try:
            import pickle
            from dados_semana import montar_semana
            from recomendacoes import medir, decisoes_da_semana
            from avisar import avisar_head
            R = pickle.load(open("/tmp/semana_head.pkl", "rb")) if os.path.exists("/tmp/semana_head.pkl") else None
            if not R or R["id"] != sid:
                R = montar_semana(seg)
            med, _ = medir(R)
            avisar_head(R, med, decisoes_da_semana(R, med), url)
        except Exception as e:
            print(f"  ⚠ aviso não saiu (relatório publicado): {str(e)[:160]}")
    return url


def check_sexta(forcar=False):
    hoje = datetime.now(BRT).date()
    seg = hoje - timedelta(days=hoje.weekday()); sid = semana_id(seg)
    drive, cred = _drive()
    est = _pasta_estado(drive)
    marcados = {(f.get("appProperties") or {}).get("check_sexta") for f in _listar(drive, est)}
    if sid in marcados and not forcar:
        return
    print(f"═══ check de sexta · {sid} ═══")
    from check_sexta import executar
    R = executar(hoje)
    # link do relatório de terça desta semana (que fechou a semana ANTERIOR)
    ant = semana_id(seg - timedelta(days=7))
    url_terca = next((f.get("webViewLink") for f in _listar(drive, PASTA)
                      if (f.get("appProperties") or {}).get("semana") == ant), None)
    enviado = True
    if not os.environ.get("SEM_EMAIL"):
        from avisar import avisar_check
        enviado = avisar_check(R, url_terca)
    if enviado:
        drive.files().create(body={"name": f"check_sexta_{sid}", "parents": [est],
                                   "mimeType": "text/plain", "appProperties": {"check_sexta": sid}},
                             fields="id").execute()
        print(f"  ✅ check registrado: {len(R['vermelhos'])} vermelho(s), {len(R['alarmes'])} alarme(s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forcar-semana", help="segunda-feira AAAA-MM-DD para (re)gerar")
    ap.add_argument("--forcar-check", action="store_true")
    a = ap.parse_args()
    if a.forcar_semana:
        relatorio_semanal(datetime.strptime(a.forcar_semana, "%Y-%m-%d").date(), forcar=True); return
    if a.forcar_check:
        check_sexta(forcar=True); return
    agora = datetime.now(BRT); wd = agora.weekday()          # 0=seg … 6=dom
    # terça 08:00 em diante (com recuperação até domingo). Segunda nunca: semana não amadureceu.
    if wd >= 1 and (wd > 1 or agora.hour >= HORA):
        seg, _ = semana_de(agora.date())
        relatorio_semanal(seg)
    if wd >= 4 and (wd > 4 or agora.hour >= HORA):
        check_sexta()


if __name__ == "__main__":
    main()
