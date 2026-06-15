-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Sample Applications (free sample REAL do TikTok Shop)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Fonte de verdade das PEÇAS de seeding (quem pediu qual SKU e em que status).
--   POST /affiliate_seller/202409/sample_applications/search
--   (data do convite = create_time do pedido, via GET /order/202309/orders)
-- ETL:  agente_rhode/etl_sample_applications.py → warehouse/raw_sample_applications.csv
-- Sync: agente_rhode/sync_supabase.py::sync_sample_applications()
--
-- Peça ENVIADA = status COMPLETED / SHIPPED / CONTENT_PENDING.
-- NÃO enviada  = *_CANCELLED ou AWAITING_SHIPMENT.
-- ADMIN-ONLY: lido pelo painel "ROI Seeding" via proxy (custo/margem não vão pra creator).

-- Grão: 1 linha por creator × SKU pedido.
DROP TABLE IF EXISTS sample_applications;
CREATE TABLE sample_applications (
  id              TEXT PRIMARY KEY,    -- id do pedido de amostra (API)
  creator         TEXT,                -- @handle (username)
  nickname        TEXT,
  product_id      TEXT,
  sku_id          TEXT,
  sku_name        TEXT,
  title           TEXT,
  status          TEXT,                -- COMPLETED/SHIPPED/CONTENT_PENDING/*_CANCELLED/AWAITING_SHIPMENT
  order_id        TEXT,
  commission_rate NUMERIC,             -- fração (0.08, 0.12, ...)
  convite_data    DATE,                -- create_time do pedido de amostra
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sample_apps_creator ON sample_applications(creator);
CREATE INDEX IF NOT EXISTS idx_sample_apps_status  ON sample_applications(status);

ALTER TABLE sample_applications DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_sample_apps" ON sample_applications;
CREATE POLICY "anon_all_sample_apps" ON sample_applications FOR ALL USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS update_sample_apps_updated_at ON sample_applications;
CREATE TRIGGER update_sample_apps_updated_at
  BEFORE UPDATE ON sample_applications
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

SELECT 'sample_applications' AS info, COUNT(*) AS rows FROM sample_applications;
