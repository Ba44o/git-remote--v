#!/usr/bin/env python3
"""
Rhode — autorização OAuth do Google, UMA VEZ SÓ.

POR QUE PRECISA: a service account (rhode-etl-936@...) tem quota ZERO de Drive —
testado em 11/09, erro "The user's Drive storage quota has been exceeded". Ela consegue
ESCREVER em planilha que já exista, mas não consegue CRIAR nenhuma. Para a automação criar
os relatórios sozinha, ela precisa agir como o DONO da conta.

PASSO 1 (no navegador, uma vez):
  1. Abra  https://console.cloud.google.com/apis/credentials?project=creators-rhode
  2. "+ CRIAR CREDENCIAIS" → "ID do cliente OAuth"
  3. Tipo de aplicativo: "App para computador" (Desktop app). Nome: "Rhode Relatorios"
  4. CRIAR → baixe o JSON → salve como  client_secret.json  na raiz do projeto
     (se pedir para configurar a tela de consentimento: tipo "Externo", preencha só o
      obrigatório, e em "Usuários de teste" adicione seu próprio e-mail)

PASSO 2 (aqui):
  python3 automacao/oauth_setup.py

  Ele abre o navegador, você autoriza, e ele grava token_google.json.
  No fim imprime o conteúdo para você colar como secret GOOGLE_OAUTH_TOKEN no GitHub.

⚠️  token_google.json e client_secret.json NÃO vão para o git (já no .gitignore).
"""
import os, sys, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"]
CS = os.path.join(ROOT, "client_secret.json")
TK = os.path.join(ROOT, "token_google.json")


def main():
    if not os.path.exists(CS):
        print(__doc__)
        print(f"\n❌ Não achei {CS} — faça o PASSO 1 primeiro.")
        raise SystemExit(1)
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("❌ falta a lib. Rode:  pip3 install google-auth-oauthlib")
        raise SystemExit(1)

    flow = InstalledAppFlow.from_client_secrets_file(CS, SCOPES)
    print("Abrindo o navegador para autorizar…")
    print("(se não abrir, copie a URL que aparecer abaixo)\n")
    cred = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not cred.refresh_token:
        print("❌ não veio refresh_token. Revogue o acesso em "
              "https://myaccount.google.com/permissions e rode de novo.")
        raise SystemExit(1)

    dados = {"token": cred.token, "refresh_token": cred.refresh_token,
             "token_uri": cred.token_uri, "client_id": cred.client_id,
             "client_secret": cred.client_secret, "scopes": list(cred.scopes)}
    with open(TK, "w") as f:
        json.dump(dados, f)
    os.chmod(TK, 0o600)
    print(f"\n✅ gravado em {TK}")

    # valida de verdade: cria e apaga um arquivo na pasta de relatórios
    from googleapiclient.discovery import build
    drive = build("drive", "v3", credentials=cred)
    me = drive.about().get(fields="user(emailAddress)").execute()
    print(f"   autorizado como: {me['user']['emailAddress']}")
    pasta = os.environ.get("DRIVE_FOLDER_ID")
    if pasta:
        f = drive.files().create(body={"name": "__teste_oauth__",
            "mimeType": "application/vnd.google-apps.spreadsheet",
            "parents": [pasta]}, fields="id").execute()
        drive.files().delete(fileId=f["id"]).execute()
        print("   ✓ consegue criar planilha na pasta de relatórios")

    print("\n" + "=" * 70)
    print("AGORA COLE ISTO COMO SECRET NO GITHUB")
    print("  Settings → Secrets and variables → Actions → New repository secret")
    print("  Nome:  GOOGLE_OAUTH_TOKEN")
    print("  Valor: (a linha abaixo inteira)")
    print("=" * 70)
    print(json.dumps(dados))
    print("=" * 70)
    print("\nOu, se preferir, rode:")
    print(f"  gh secret set GOOGLE_OAUTH_TOKEN < {TK}")


if __name__ == "__main__":
    main()
