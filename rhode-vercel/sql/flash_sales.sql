-- ═══════════════════════════════════════════════════════════════════════════
--  Rhode — Flash Sales ao vivo (creator-facing) · FONTE = TikTok Promotion API
-- ═══════════════════════════════════════════════════════════════════════════
--  Substitui o esquema manual antigo (curado à mão, FK produtos, view _ativas)
--  pela versão alimentada automaticamente por coletar_flash_sales.py (cron ~30min).
--
--  Targeting (gravado pelo coletor a partir do @handle no título da activity):
--    scope='creator' + creator=<handle canônico> → só aquela creator vê
--    scope='loja'    + creator=NULL              → todas veem (flash "Geral")
--
--  ADITIVO/SUBSTITUTIVO: só mexe na flash_sales. NÃO toca extrato, performance_periods,
--  login nem a tabela produtos. RLS deny-anon (lida só via /api/get-hub, service key).
--  Rodar no Supabase → SQL Editor → Run.
-- ═══════════════════════════════════════════════════════════════════════════

-- 1) Remove o esquema manual antigo (estava vestigial: skus/preços null, tudo expirado)
DROP VIEW  IF EXISTS flash_sales_ativas;
DROP TABLE IF EXISTS flash_sales CASCADE;

-- 2) Tabela nova — uma linha por activity (flash sale), com produtos em JSONB
CREATE TABLE flash_sales (
  id             TEXT PRIMARY KEY,        -- activity_id da Promotion API
  title          TEXT,                    -- título da activity (pode conter @handle)
  activity_type  TEXT,                    -- FLASHSALE
  scope          TEXT NOT NULL,           -- 'creator' | 'loja'
  creator        TEXT,                    -- handle canônico (NULL quando scope='loja')
  begin_ts       BIGINT DEFAULT 0,        -- início (epoch segundos)
  end_ts         BIGINT DEFAULT 0,        -- fim    (epoch segundos) — filtro "ativa agora"
  status         TEXT,                    -- ONGOING
  products       JSONB  DEFAULT '[]',     -- [{product_id,nome,preco_promo,preco_original,pct_off,moeda}]
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_flash_creator ON flash_sales(creator);
CREATE INDEX idx_flash_scope   ON flash_sales(scope);
CREATE INDEX idx_flash_end     ON flash_sales(end_ts);

-- 3) RLS deny-anon (sem policy permissiva → anon não lê; service_role do proxy bypassa)
ALTER TABLE flash_sales ENABLE ROW LEVEL SECURITY;

-- Verificação:
SELECT 'flash_sales' AS tabela, COUNT(*) AS linhas FROM flash_sales;
