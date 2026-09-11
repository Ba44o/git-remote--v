#!/usr/bin/env python3
"""
Rhode — MONITOR DE LIVES. Roda de tempos em tempos; quando uma live termina e passam
45 minutos, gera o relatório no template travado e publica numa pasta do Drive.

Uso:
  python3 automacao/monitor_lives.py                 # ciclo normal
  python3 automacao/monitor_lives.py --dry-run       # mostra o que faria, não publica
  python3 automacao/monitor_lives.py --room <id>     # força uma sala específica
  python3 automacao/monitor_lives.py --espera 45     # muda a espera (default 45 min)

POR QUE ESPERAR 45 MIN: pedidos continuam entrando e mudando de status depois que a live
acaba, e a atribuição de mídia do GMV Max leva alguns minutos para assentar. Medido em
10/09: a coleta feita 2h após a live já pegava o essencial, mas o status de pagamento
ainda se moveu depois. 45 min é o piso — por isso o relatório declara o horário da medição
e traz o alerta de remedir os não pagos em 48h.

ESTADO: a própria pasta do Drive. Cada planilha criada leva o room_id em appProperties,
então listar a pasta já diz o que foi feito. Sem tabela nova, sem DDL, sem arquivo de
controle no git — e se você apagar um relatório da pasta, ele se regenera no próximo ciclo.
"""
import os, sys, json, argparse, subprocess, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
try:
    from dotenv import load_dotenv; load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass

SB = os.environ["SUPABASE_URL"]; SK = os.environ["SUPABASE_SERVICE_KEY"]
HD = {"apikey": SK, "Authorization": "Bearer " + SK, "Content-Type": "application/json"}
BRT = timezone(timedelta(hours=-3))
PASTA = os.environ.get("DRIVE_FOLDER_ID", "1tWpDpY6gpOijpEkw_EpWmylohL8BpRix")
ESPERA_PADRAO = 45
DUR_MIN = 0.25          # < 15 min = reinício técnico, não é live (premissa P22)


def q(path):
    return json.load(urllib.request.urlopen(
        urllib.request.Request(f"{SB}/rest/v1/{path}", headers=HD), timeout=60))


def _drive():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pubdrive", os.path.join(ROOT, "relatorios", "_publicar_drive.py"))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    from googleapiclient.discovery import build
    cred = mod.obter_credenciais()
    return build("drive", "v3", credentials=cred), cred


def ja_publicadas():
    """Lê o estado da pasta do Drive: cada relatório carrega seu room_id em appProperties."""
    try:
        drive, _ = _drive()
    except Exception as e:
        print(f"  ⚠ sem acesso ao Drive ({str(e)[:80]}) — seguindo sem estado")
        return {}
    feitas = {}; tok = None
    while True:
        resp = drive.files().list(
            q=f"'{PASTA}' in parents and trashed=false",
            fields="nextPageToken, files(id,name,appProperties,webViewLink)",
            pageSize=200, pageToken=tok).execute()
        for f in resp.get("files", []):
            rid = (f.get("appProperties") or {}).get("room_id")
            if rid:
                feitas[rid] = {"sheet_id": f["id"], "url": f.get("webViewLink"), "nome": f["name"]}
        tok = resp.get("nextPageToken")
        if not tok: break
    return feitas


def coletar(dia):
    """Atualiza as fontes do dia antes de medir."""
    for cmd in (["python3", "coletar_lives_attr_api.py", "--inicio", dia, "--fim", dia],
                ["python3", "coletar_gmvmax_api.py", "--inicio", dia, "--fim", dia],
                ["python3", "coletar_pedidos_sku.py", "--inicio", dia, "--fim", dia]):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            print(f"  ⚠ {cmd[1]} falhou: {(r.stderr or '')[-300:]}")


def criar_planilha(nome, room):
    """Cria a planilha na pasta, como o DONO (OAuth). A service account não consegue —
    quota zero de Drive, testado em 11/09. O room_id vai em appProperties e é o ESTADO."""
    drive, cred = _drive()
    if not getattr(cred, "refresh_token", None):
        raise RuntimeError("sem OAuth: a service account não cria arquivo (quota zero). "
                           "Rode automacao/oauth_setup.py e configure GOOGLE_OAUTH_TOKEN.")
    f = drive.files().create(body={"name": nome,
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "parents": [PASTA], "appProperties": {"room_id": str(room)}},
        fields="id,webViewLink").execute()
    # a service account também escreve nela, para o publicador funcionar de qualquer lado
    try:
        drive.permissions().create(fileId=f["id"], body={"type": "user", "role": "writer",
            "emailAddress": "rhode-etl-936@creators-rhode.iam.gserviceaccount.com"},
            sendNotificationEmail=False).execute()
    except Exception:
        pass
    return f["id"], f.get("webViewLink", f"https://docs.google.com/spreadsheets/d/{f['id']}/edit")


def processar(room, L, dry=False):
    ini = datetime.fromisoformat(L["inicio"]).astimezone(BRT)
    dia = ini.strftime("%Y-%m-%d")
    print(f"\n▶ sala {room} — {ini.strftime('%d/%m %H:%M')} · {(L['titulo'] or '(sem título)')[:40]}")
    if dry:
        print("  [dry-run] coletaria, geraria e publicaria")
        return None
    print("  · atualizando fontes…")
    coletar(dia)
    print("  · gerando relatório…")
    xlsx = os.path.join("/tmp", f"live_{room}.xlsx")
    r = subprocess.run(["python3", os.path.join(ROOT, "automacao", "gerar_relatorio_live.py"),
                        "--room", str(room), "--saida", xlsx],
                       cwd=ROOT, capture_output=True, text=True, timeout=900)
    print("   ", "\n    ".join(l for l in r.stdout.strip().splitlines() if l.strip()))
    if r.returncode != 0 or not os.path.exists(xlsx):
        print(f"  ✗ falhou: {(r.stderr or '')[-400:]}")
        return None
    nome = f"Relatorio Live {ini.strftime('%d-%m')} {ini.strftime('%Hh%M')}_{dia}"
    print(f"  · criando planilha no Drive: {nome}")
    sid, url = criar_planilha(nome, room)
    r = subprocess.run(["python3", os.path.join(ROOT, "relatorios", "_publicar_drive.py"), xlsx, sid],
                       cwd=ROOT, capture_output=True, text=True, timeout=900)
    print("   ", "\n    ".join(l for l in r.stdout.strip().splitlines() if l.strip()))
    if r.returncode != 0:
        print(f"  ✗ publicação falhou: {(r.stderr or '')[-400:]}")
        return None
    print(f"  ✅ {url}")
    return url


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--room")
    ap.add_argument("--espera", type=int, default=ESPERA_PADRAO)
    ap.add_argument("--max", type=int, default=4, help="teto de relatórios por ciclo")
    a = ap.parse_args()
    agora = datetime.now(timezone.utc)
    print(f"═══ monitor de lives · {agora.astimezone(BRT).strftime('%d/%m/%Y %H:%M')} BRT ═══")

    if a.room:
        L = q(f"live_attr?select=room_id,titulo,inicio,fim&room_id=eq.{a.room}")
        if not L: raise SystemExit(f"sala {a.room} não encontrada")
        processar(a.room, L[0], a.dry_run); return

    # olha os últimos 3 dias para não perder nada se o job ficar fora do ar
    desde = (agora - timedelta(days=3)).strftime("%Y-%m-%d")
    salas = q(f"live_attr?select=room_id,titulo,inicio,fim,data&data=gte.{desde}&order=inicio")
    feitas = ja_publicadas()
    pend = []
    for L in salas:
        rid = str(L["room_id"])
        if rid in feitas or not L["fim"]:
            continue
        fim = datetime.fromisoformat(L["fim"])
        ini = datetime.fromisoformat(L["inicio"])
        dur = (fim - ini).total_seconds() / 3600
        if dur < DUR_MIN:
            continue                         # reinício técnico
        mins = (agora - fim).total_seconds() / 60
        if mins < a.espera:
            print(f"  ⏳ sala {rid} terminou há {mins:.0f} min — espera {a.espera}")
            continue
        pend.append((L, mins))
    if not pend:
        print("  nada pendente.")
        return
    print(f"  {len(pend)} live(s) para reportar")
    if len(pend) > a.max:
        print(f"  (processando as {a.max} mais recentes neste ciclo; o resto no próximo)")
        pend = pend[-a.max:]
    for L, mins in pend:
        try:
            processar(str(L["room_id"]), L, a.dry_run)
        except Exception as e:
            print(f"  ✗ sala {L['room_id']}: {str(e)[:200]}")


if __name__ == "__main__":
    main()
