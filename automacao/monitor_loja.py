#!/usr/bin/env python3
"""
Rhode — orquestrador do Relatório Diário da Loja.

Roda junto com o monitor de lives (mesma corrente de jobs, que é a única forma confiável
de agendamento — o cron do GitHub é estrangulado). A cada ciclo pergunta: já existe
relatório da loja para o dia D-1? Se não, atualiza as fontes, gera, publica e avisa.

Uso:  python3 automacao/monitor_loja.py
      python3 automacao/monitor_loja.py --data 2026-09-13    # força um dia
      python3 automacao/monitor_loja.py --dry-run

ESTADO: a própria pasta do Drive — cada planilha leva a data em appProperties.
Apagou o relatório da pasta? Ele se regenera no próximo ciclo.
"""
import os, sys, json, argparse, subprocess
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "automacao"))
try:
    from dotenv import load_dotenv; load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

BRT = timezone(timedelta(hours=-3))
PASTA = os.environ.get("DRIVE_FOLDER_LOJA", "1ubpK3GZLdLUbzfnJrafyW63p9NdadR4a")
SA = "rhode-etl-936@creators-rhode.iam.gserviceaccount.com"


def _drive():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pubdrive", os.path.join(ROOT, "relatorios", "_publicar_drive.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    from googleapiclient.discovery import build
    cred = mod.obter_credenciais()
    return build("drive", "v3", credentials=cred), cred


def ja_feitos():
    try:
        drive, _ = _drive()
    except Exception as e:
        print(f"  ⚠ sem acesso ao Drive ({str(e)[:80]})")
        return {}
    out = {}; tok = None
    while True:
        resp = drive.files().list(q=f"'{PASTA}' in parents and trashed=false",
            fields="nextPageToken, files(id,name,appProperties,webViewLink)",
            pageSize=200, pageToken=tok).execute()
        for f in resp.get("files", []):
            d = (f.get("appProperties") or {}).get("data")
            if d: out[d] = f
        tok = resp.get("nextPageToken")
        if not tok: break
    return out


def coletar(dia):
    """Atualiza as fontes ANTES de medir. Levanta se qualquer uma falhar — relatório
    com dado velho é pior que relatório nenhum (lição de 11/09 e 14/09)."""
    prox = (datetime.strptime(dia, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    for cmd in (["python3", "coletar_pedidos_sku.py", "--inicio", dia, "--fim", prox],   # data é UTC
                ["python3", "coletar_gmvmax_api.py", "--inicio", dia, "--fim", dia],
                ["python3", "coletar_lives_attr_api.py", "--inicio", dia, "--fim", dia]):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1200)
        if r.returncode != 0:
            raise RuntimeError(f"{cmd[1]} falhou:\n{(r.stderr or '')[-400:]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    dia = a.data or (datetime.now(BRT) - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"═══ relatório da loja · dia {dia} ═══")

    feitos = ja_feitos()
    if dia in feitos and not a.data:
        print(f"  já publicado: {feitos[dia].get('webViewLink')}")
        return
    if a.dry_run:
        print("  [dry-run] coletaria, geraria e publicaria")
        return

    print("  · atualizando fontes…")
    try:
        coletar(dia)
    except RuntimeError as e:
        print(f"  ✗ {e}")
        return

    print("  · gerando…")
    xlsx = f"/tmp/loja_{dia}.xlsx"
    r = subprocess.run(["python3", os.path.join(ROOT, "automacao", "gerar_relatorio_loja.py"),
                        "--data", dia, "--saida", xlsx],
                       cwd=ROOT, capture_output=True, text=True, timeout=1200)
    print("   ", "\n    ".join(l for l in r.stdout.strip().splitlines() if l.strip()))
    if r.returncode != 0 or not os.path.exists(xlsx):
        print(f"  ✗ falhou: {(r.stderr or '')[-400:]}")
        return
    md = xlsx.replace(".xlsx", ".md")

    nome = f"Relatorio Diario da Loja_{dia}"
    print(f"  · criando planilha: {nome}")
    drive, cred = _drive()
    if not getattr(cred, "refresh_token", None):
        print("  ✗ sem OAuth — a service account tem quota zero e não cria arquivo")
        return
    f = drive.files().create(body={"name": nome,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [PASTA], "appProperties": {"data": dia}},
        fields="id,webViewLink").execute()
    sid = f["id"]; url = f.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{sid}/edit")
    try:
        drive.permissions().create(fileId=sid, body={"type": "user", "role": "writer",
            "emailAddress": SA}, sendNotificationEmail=False).execute()
    except Exception:
        pass

    args = [sys.executable, os.path.join(ROOT, "relatorios", "_publicar_drive.py"), xlsx, sid]
    if os.path.exists(md): args.append(md)
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=1200)
    print("   ", "\n    ".join(l for l in r.stdout.strip().splitlines() if l.strip()))
    if r.returncode != 0:
        print(f"  ✗ publicação falhou: {(r.stderr or '')[-400:]}")
        return
    print(f"  ✅ {url}")

    if not os.environ.get("SEM_EMAIL"):
        try:
            from dados_loja import montar
            from avisar import avisar_loja
            avisar_loja(montar(dia), url)
        except Exception as e:
            print(f"  ⚠ aviso não saiu (relatório está publicado): {str(e)[:150]}")


if __name__ == "__main__":
    main()
