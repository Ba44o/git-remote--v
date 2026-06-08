-- ═══════════════════════════════════════════════════════════════════════════
--  Rhode — api_tokens: token da API TikTok Shop (Partner/Seller) p/ rodar a
--  coleta FORA do Mac (GitHub Actions etc.).
-- ═══════════════════════════════════════════════════════════════════════════
--  ⚠️ NÃO é o login das creators. O login delas fica em affiliates.access_token /
--     eventos_creators.access_token — esta tabela NÃO os toca. Aqui é só o token
--     de servidor que chama a API da TikTok (renovado via refresh_token).
--
--  deny-anon (segredo): só o service_role (coletores) lê/escreve. RLS ligado e
--  SEM policy permissiva → anon não acessa.
--
--  Rodar no Supabase → SQL Editor → Run.
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS api_tokens (
  id                 TEXT PRIMARY KEY,          -- 'tiktok_partner'
  access_token       TEXT,
  refresh_token      TEXT,
  shop_id            TEXT,
  access_expire_at   TIMESTAMPTZ,
  refresh_expire_at  TIMESTAMPTZ,
  updated_at         TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE api_tokens ENABLE ROW LEVEL SECURITY;
-- (sem policy permissiva → anon não lê; service_role bypassa RLS)

-- Verificação:
SELECT 'api_tokens' AS tabela, COUNT(*) AS linhas FROM api_tokens;
