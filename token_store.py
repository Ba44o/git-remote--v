"""
Token store da API TikTok Shop (Partner/Seller) no Supabase.

PORQUÊ: hoje o access_token vive no .env (só no Mac). Pra rodar a coleta fora da
máquina (GitHub Actions etc.), o token renovado precisa persistir num lugar que
sobreviva entre execuções stateless → tabela `api_tokens` no Supabase.

⚠️ ISTO NÃO É O LOGIN DAS CREATORS. O login delas fica em
   affiliates.access_token / eventos_creators.access_token — NUNCA tocado aqui.
   Esta tabela guarda só o token de servidor que chama a API da TikTok.

Fallback gracioso: se o Supabase não responder ou a tabela estiver vazia, cai
pro .env — então o local continua funcionando igual.
"""
import os, json, urllib.request
from datetime import datetime, timezone

TOKEN_ID = "tiktok_partner"

def _sb():
    u = os.getenv("SUPABASE_URL"); k = os.getenv("SUPABASE_SERVICE_KEY")
    return (u, k) if (u and k) else (None, None)

def load():
    """Linha do token no Supabase, ou None (se sem creds/tabela/erro)."""
    u, k = _sb()
    if not u:
        return None
    try:
        req = urllib.request.Request(
            f"{u}/rest/v1/api_tokens?id=eq.{TOKEN_ID}&limit=1",
            headers={"apikey": k, "Authorization": f"Bearer {k}"})
        rows = json.loads(urllib.request.urlopen(req, timeout=20).read())
        return rows[0] if rows else None
    except Exception:
        return None

def get_access_token():
    """access_token: tabela primeiro (fonte de verdade na nuvem), senão .env."""
    r = load()
    return (r and r.get("access_token")) or os.getenv("TIKTOK_ACCESS_TOKEN")

def get_refresh_token():
    r = load()
    return (r and r.get("refresh_token")) or os.getenv("TIKTOK_REFRESH_TOKEN")

def save(data):
    """Grava o token (data = .data da resposta do TikTok) na tabela api_tokens.
    Campos *_expire_in vêm como epoch ABSOLUTO. Retorna True/False (best-effort)."""
    u, k = _sb()
    if not u:
        return False
    def iso(epoch):
        try:
            return datetime.fromtimestamp(int(epoch), tz=timezone.utc).isoformat() if epoch else None
        except Exception:
            return None
    row = {
        "id": TOKEN_ID,
        "access_token":     data.get("access_token"),
        "refresh_token":    data.get("refresh_token"),
        "shop_id":          data.get("open_id"),
        "access_expire_at": iso(data.get("access_token_expire_in")),
        "refresh_expire_at": iso(data.get("refresh_token_expire_in")),
        "updated_at":       datetime.now(tz=timezone.utc).isoformat(),
    }
    try:
        req = urllib.request.Request(
            f"{u}/rest/v1/api_tokens?on_conflict=id",
            data=json.dumps(row).encode(),
            headers={"apikey": k, "Authorization": f"Bearer {k}",
                     "Content-Type": "application/json",
                     "Prefer": "resolution=merge-duplicates,return=minimal"},
            method="POST")
        urllib.request.urlopen(req, timeout=20)
        return True
    except Exception as e:
        print(f"  [token_store] falha ao gravar no Supabase: {e}")
        return False
