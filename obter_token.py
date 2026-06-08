"""
Rhode Jeans — Obter / Renovar Access Token TikTok Shop
------------------------------------------------------
Autorizar o app no browser (primeira vez ou após ligar novo escopo):
  https://auth.tiktok-shops.com/oauth/authorize?app_key=6jebftqsep751&state=rhode123

Uso:
  python3 obter_token.py SEU_AUTH_CODE   # troca auth_code por access+refresh token
  python3 obter_token.py --refresh       # renova usando o refresh_token salvo (sem browser)
"""

import sys, re, time, requests
from dotenv import load_dotenv
import os

load_dotenv()
try:
    import token_store
except Exception:
    token_store = None

APP_KEY     = os.getenv("TIKTOK_APP_KEY")
APP_SECRET  = os.getenv("TIKTOK_APP_SECRET")
ENV_PATH    = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
TOKEN_URL   = "https://auth.tiktok-shops.com/api/v2/token/get"
REFRESH_URL = "https://auth.tiktok-shops.com/api/v2/token/refresh"

def set_env(env_text, key, value):
    """Substitui a linha key=... se existir; senão acrescenta no fim.
    Usa replacement por função pra não interpretar backslash/grupos no valor."""
    pat = rf"^{re.escape(key)}=.*$"
    if re.search(pat, env_text, flags=re.M):
        return re.sub(pat, lambda _m: f"{key}={value}", env_text, flags=re.M)
    sep = "" if env_text == "" or env_text.endswith("\n") else "\n"
    return env_text + f"{sep}{key}={value}\n"

def salvar(data):
    """Persiste access_token, refresh_token e shop_id no .env."""
    with open(ENV_PATH) as f:
        env = f.read()
    env = set_env(env, "TIKTOK_ACCESS_TOKEN",  data["access_token"])
    env = set_env(env, "TIKTOK_REFRESH_TOKEN", data["refresh_token"])
    if data.get("open_id"):
        env = set_env(env, "TIKTOK_SHOP_ID", data["open_id"])
    with open(ENV_PATH, "w") as f:
        f.write(env)

    # Dual-write: também grava no Supabase (api_tokens) pra rodar fora do Mac.
    # Best-effort — se falhar, o .env já foi salvo e o local segue funcionando.
    if token_store:
        if token_store.save(data):
            print("   ↳ também salvo no Supabase (api_tokens) ✓")

    # expire_in vem como timestamp ABSOLUTO (epoch), não duração → subtrai agora
    now = int(time.time())
    acc_h = max(0, data.get("access_token_expire_in", 0)  - now) // 3600
    ref_d = max(0, data.get("refresh_token_expire_in", 0) - now) // 86400
    print("\n✅ Tokens salvos no .env")
    print(f"   Access token  expira em ~{acc_h}h")
    print(f"   Refresh token expira em ~{ref_d}d (renove antes com --refresh)")

def get_token(auth_code):
    params = {
        "app_key":    APP_KEY,
        "app_secret": APP_SECRET,
        "auth_code":  auth_code,
        "grant_type": "authorized_code",
    }
    data = requests.get(TOKEN_URL, params=params).json()
    if data.get("code") == 0:
        salvar(data["data"])
        print("\nPróximo passo: python3 coletar_dados.py")
    else:
        print(f"\n❌ Erro: {data.get('message')} (code {data.get('code')})")

def refresh():
    # refresh_token: Supabase primeiro (fonte de verdade na nuvem), senão .env
    refresh_token = (token_store.get_refresh_token() if token_store else None) or os.getenv("TIKTOK_REFRESH_TOKEN")
    if not refresh_token:
        print("❌ Sem refresh_token (Supabase nem .env) — rode o fluxo de auth_code no browser primeiro.")
        sys.exit(1)
    params = {
        "app_key":       APP_KEY,
        "app_secret":    APP_SECRET,
        "refresh_token": refresh_token,
        "grant_type":    "refresh_token",
    }
    data = requests.get(REFRESH_URL, params=params).json()
    if data.get("code") == 0:
        salvar(data["data"])
        print("\n♻️  Token renovado sem browser.")
    else:
        print(f"\n❌ Erro ao renovar: {data.get('message')} (code {data.get('code')})")
        print("   Se o refresh expirou, refaça o fluxo de auth_code no browser.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    if sys.argv[1] == "--refresh":
        refresh()
    else:
        get_token(sys.argv[1])
