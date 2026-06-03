-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Performance de Afiliadas (creator × dia × conteúdo)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Granularidade: 1 linha por creator × data × content_type (SHOP/VIDEO/LIVE).
-- GMV = base de comissão (valor de venda atribuído). Comissão = ganho da creator.
--
-- Fonte: TikTok Shop API POST /affiliate_seller/202410/orders/search.
-- ETL: agente_rhode/etl_affiliate.py → warehouse/raw_affiliate.csv.
-- Sync: agente_rhode/sync_supabase.py::sync_affiliate_perf().
--
-- ⚠️ Performance por creator (sensível). RLS segue o padrão anon do projeto pra
--    não quebrar o admin; fechar no item 8 (hardening).

CREATE TABLE IF NOT EXISTS affiliate_perf (
  id            TEXT PRIMARY KEY,                  -- creator|data|content_type
  creator       TEXT,
  data          DATE,
  content_type  TEXT,                              -- SHOP / VIDEO / LIVE
  gmv           NUMERIC(12,2) DEFAULT 0,
  comissao      NUMERIC(12,2) DEFAULT 0,
  pedidos       INT DEFAULT 0,
  itens         INT DEFAULT 0,
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_affperf_data    ON affiliate_perf(data DESC);
CREATE INDEX IF NOT EXISTS idx_affperf_creator ON affiliate_perf(creator);

ALTER TABLE affiliate_perf DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_affperf" ON affiliate_perf;
CREATE POLICY "anon_all_affperf" ON affiliate_perf FOR ALL USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS update_affperf_updated_at ON affiliate_perf;
CREATE TRIGGER update_affperf_updated_at
  BEFORE UPDATE ON affiliate_perf
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

SELECT 'affiliate_perf' AS info, COUNT(*) AS rows FROM affiliate_perf;
