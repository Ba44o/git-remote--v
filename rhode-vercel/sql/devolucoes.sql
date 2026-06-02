-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Devoluções / Reembolsos (TikTok Shop)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Granularidade: 1 linha por ITEM devolvido (return_line_item). Permite análise
-- de reembolso por produto. refund_return (denormalizado) = refund do return
-- inteiro → somar deduplicando por return_id pro total real.
--
-- Fonte: TikTok Shop API POST /return_refund/202309/returns/search.
-- ETL: agente_rhode/etl_devolucoes.py → warehouse/raw_devolucoes.csv.
-- Sync: agente_rhode/sync_supabase.py::sync_devolucoes().

CREATE TABLE IF NOT EXISTS devolucoes (
  id              TEXT PRIMARY KEY,                   -- return_line_item_id
  return_id       TEXT,
  order_id        TEXT,
  data            DATE,
  product_name    TEXT,
  seller_sku      TEXT,
  sku_name        TEXT,                               -- variante: cor + tamanho
  refund_item     NUMERIC(12,2) DEFAULT 0,            -- reembolso do item
  refund_return   NUMERIC(12,2) DEFAULT 0,            -- reembolso do return inteiro
  return_reason   TEXT,
  return_status   TEXT,
  return_type     TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_devolucoes_data_desc ON devolucoes(data DESC);
CREATE INDEX IF NOT EXISTS idx_devolucoes_return    ON devolucoes(return_id);

ALTER TABLE devolucoes DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_devolucoes" ON devolucoes;
CREATE POLICY "anon_all_devolucoes" ON devolucoes FOR ALL USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS update_devolucoes_updated_at ON devolucoes;
CREATE TRIGGER update_devolucoes_updated_at
  BEFORE UPDATE ON devolucoes
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

SELECT 'devolucoes' AS info, COUNT(*) AS rows FROM devolucoes;
