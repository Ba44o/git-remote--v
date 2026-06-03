-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Seeding REAL (Target Collaborations × vendas por produto)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Fonte: TikTok Shop Affiliate Seller API — convites de target collaboration
--   POST /affiliate_seller/202409/target_collaborations/search (+ /{id} detalhe)
-- Atribuição CORRETA: gmv_seedado = vendas (affiliate orders) só dos PRODUTOS do
--   convite, feitas pela CREATOR convidada (join creator_username × product_id).
-- ETL: agente_rhode/etl_seeding.py → warehouse/raw_seeding.csv.
-- Sync: agente_rhode/sync_supabase.py::sync_seeding().
--
-- Substitui o painel v2a (que usava amostras_enviadas manual + GMV total da creator).

-- Grão: 1 linha por CREATOR (produtos deduplicados entre os convites dela).
CREATE TABLE IF NOT EXISTS seeding (
  id                TEXT PRIMARY KEY,                 -- creator (handle lowercased)
  creator           TEXT,
  creator_nick      TEXT,
  convites          INT DEFAULT 0,                    -- nº de target collaborations
  n_produtos        INT DEFAULT 0,                    -- produtos únicos convidados
  has_free_sample   BOOLEAN DEFAULT FALSE,
  status            TEXT,                             -- VALID·COMPLETED·...
  commission_pct    NUMERIC(5,1) DEFAULT 0,
  gmv_seedado       NUMERIC(12,2) DEFAULT 0,          -- GMV nos produtos convidados (dedup, por essa creator)
  comissao_seedada  NUMERIC(12,2) DEFAULT 0,
  pedidos_seedados  INT DEFAULT 0,
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_seeding_gmv ON seeding(gmv_seedado DESC);

ALTER TABLE seeding DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_seeding" ON seeding;
CREATE POLICY "anon_all_seeding" ON seeding FOR ALL USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS update_seeding_updated_at ON seeding;
CREATE TRIGGER update_seeding_updated_at
  BEFORE UPDATE ON seeding
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

SELECT 'seeding' AS info, COUNT(*) AS rows FROM seeding;
