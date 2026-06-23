#!/usr/bin/env python3
"""
Rhode — Troca o auth_code do TikTok Marketing API por access_token (+ advertiser_id)
e guarda em api_tokens (id='tiktok_ads'). Token de anunciante é longo (não expira),
então é troca única — sem refresh diário.

Pré-requisitos no .env:  TIKTOK_ADS_APP_ID, TIKTOK_ADS_SECRET, SUPABASE_URL, SUPABASE_SERVICE_KEY

Uso:  python3 obter_token_ads.py <auth_code>
"""
import os, sys, json, urllib.request, urllib.error
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

APP_ID = os.environ.get("TIKTOK_ADS_APP_ID", "")
SECRET = os.environ.get("TIKTOK_ADS_SECRET", "")
SB_URL = os.environ["SUPABASE_URL"]
SB_KEY = os.environ["SUPABASE_SERVICE_KEY"]
BASE = "https://business-api.tiktok.com"

def main():
    if len(sys.argv) < 2:
        print("uso: python3 obter_token_ads.py <auth_code>"); sys.exit(1)
    if not APP_ID or not SECRET:
        print("[ERRO] defina TIKTOK_ADS_APP_ID e TIKTOK_ADS_SECRET no .env"); sys.exit(1)
    auth_code = sys.argv[1].strip()

    # 1) troca auth_code → access_token
    body = json.dumps({"app_id": APP_ID, "secret": SECRET, "auth_code": auth_code}).encode()
    req = urllib.request.Request(f"{BASE}/open_api/v1.3/oauth2/access_token/",
        data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        resp = json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        print(f"[ERRO HTTP] {e.code}: {e.read()[:400]}"); sys.exit(1)

    if resp.get("code") != 0:
        print(f"[ERRO API] code={resp.get('code')} msg={resp.get('message')!r}"); sys.exit(1)

    d = resp.get("data", {})
    token = d.get("access_token", "")
    advs = d.get("advertiser_ids", []) or []
    scope = d.get("scope", [])
    print(f"  ✓ access_token obtido (scope={scope})")
    print(f"  ✓ advertiser_ids: {advs}")
    if not token or not advs:
        print("[ERRO] resposta sem access_token/advertiser_ids"); sys.exit(1)

    # 2) guarda no api_tokens (reusa shop_id p/ advertiser_id; token de ads não expira)
    row = [{
        "id": "tiktok_ads",
        "access_token": token,
        "shop_id": str(advs[0]),       # advertiser_id principal
        "refresh_token": json.dumps(advs),  # lista completa de advertisers, p/ referência
    }]
    url = f"{SB_URL}/rest/v1/api_tokens?on_conflict=id"
    req2 = urllib.request.Request(url, data=json.dumps(row).encode(),
        headers={"apikey": SB_KEY, "Authorization": f"Bearer {SB_KEY}",
                 "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal"},
        method="POST")
    try:
        urllib.request.urlopen(req2, timeout=60)
        print(f"  ✓ guardado em api_tokens (id='tiktok_ads', advertiser={advs[0]})")
    except urllib.error.HTTPError as e:
        print(f"[ERRO Supabase] {e.code}: {e.read()[:300]}"); sys.exit(1)
    print("  ✓ pronto — agora dá pra rodar o coletor do GMV Max.")


if __name__ == "__main__":
    main()
