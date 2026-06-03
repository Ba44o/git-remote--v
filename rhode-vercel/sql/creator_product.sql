-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Creator × Produto (base de inteligência de creator)
-- ═══════════════════════════════════════════════════════════════════════════
-- Quanto cada creator vendeu de cada produto (affiliate orders × catálogo).
-- Base pra: matriz creator×produto, drill-down de creator, direcionar convites.
--
-- Fonte: affiliate_seller/202410/orders/search × product/202309/products/search.
-- ETL: agente_rhode/etl_creator_product.py → warehouse/raw_creator_product.csv.
-- Sync: agente_rhode/sync_supabase.py::sync_creator_product().

-- Grão = creator × produto × DIA (permite janela global ajustável). Recriada
-- (o grão mudou de creator×produto p/ creator×produto×dia → id novo).
DROP TABLE IF EXISTS affiliate_creator_product;
CREATE TABLE affiliate_creator_product (
  id          TEXT PRIMARY KEY,                       -- creator|product_id|data
  creator     TEXT,
  product_id  TEXT,
  data        DATE,
  produto     TEXT,                                   -- título do produto
  seller_sku  TEXT,
  gmv         NUMERIC(12,2) DEFAULT 0,
  comissao    NUMERIC(12,2) DEFAULT 0,
  pedidos     INT DEFAULT 0,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cp_creator ON affiliate_creator_product(creator);
CREATE INDEX IF NOT EXISTS idx_cp_data    ON affiliate_creator_product(data DESC);
CREATE INDEX IF NOT EXISTS idx_cp_gmv     ON affiliate_creator_product(gmv DESC);

ALTER TABLE affiliate_creator_product DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_cp" ON affiliate_creator_product;
CREATE POLICY "anon_all_cp" ON affiliate_creator_product FOR ALL USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS update_cp_updated_at ON affiliate_creator_product;
CREATE TRIGGER update_cp_updated_at
  BEFORE UPDATE ON affiliate_creator_product
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

SELECT 'affiliate_creator_product' AS info, COUNT(*) AS rows FROM affiliate_creator_product;
