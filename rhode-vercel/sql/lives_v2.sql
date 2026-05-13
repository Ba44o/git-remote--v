-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Lives v2 — colunas novas vindas do schema atualizado do TikTok Shop
-- ═══════════════════════════════════════════════════════════════════════════
--
-- O schema do export "Creator-Live-Performance" mudou em abr-mai/2026.
-- Adiciona métricas novas que antes não existiam.
-- Mantém colunas antigas (gmv_bruto, gmv_direct, viewers, peak_viewers, etc).
-- Para lives no schema novo, as colunas que sumiram (Viewers/Peak viewers)
-- ficam NULL até o usuário baixar export com elas (se TikTok permitir).
--
-- Aplicar 1× no Supabase SQL Editor.
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE lives
  ADD COLUMN IF NOT EXISTS live_impressions       BIGINT,
  ADD COLUMN IF NOT EXISTS impressions_per_hour   BIGINT,
  ADD COLUMN IF NOT EXISTS gmv_per_hour           NUMERIC(12,2),
  ADD COLUMN IF NOT EXISTS show_gpm               NUMERIC(12,2),
  ADD COLUMN IF NOT EXISTS watch_gpm              NUMERIC(12,2),
  ADD COLUMN IF NOT EXISTS ads_roas               NUMERIC(10,4),
  ADD COLUMN IF NOT EXISTS ads_cost               NUMERIC(12,2),
  ADD COLUMN IF NOT EXISTS ads_gmv                NUMERIC(12,2),
  ADD COLUMN IF NOT EXISTS follow_rate            NUMERIC(10,6),
  ADD COLUMN IF NOT EXISTS comment_rate           NUMERIC(10,6),
  ADD COLUMN IF NOT EXISTS share_rate             NUMERIC(10,6),
  ADD COLUMN IF NOT EXISTS like_rate              NUMERIC(10,6),
  ADD COLUMN IF NOT EXISTS tap_through_rate       NUMERIC(10,6),
  ADD COLUMN IF NOT EXISTS sku_order_rate         NUMERIC(10,6),
  ADD COLUMN IF NOT EXISTS live_ctr               NUMERIC(10,6),
  ADD COLUMN IF NOT EXISTS attributed_sku_orders  INT,
  ADD COLUMN IF NOT EXISTS schema_version         TEXT;  -- 'v1' (até abr) ou 'v2' (mai+)

-- Índice pra filtrar por schema_version quando precisar isolar análises
CREATE INDEX IF NOT EXISTS idx_lives_schema_version ON lives(schema_version);

-- ── Confirmação ──
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'lives'
ORDER BY ordinal_position;
