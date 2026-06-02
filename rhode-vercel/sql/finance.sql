-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Financeiro (statements / settlements da TikTok Shop)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Granularidade: 1 linha por statement (settlement). O painel agrega por dia/período.
-- Mostra o caminho do dinheiro: receita − taxa TikTok − frete + ajuste = settlement.
--
-- Fonte: TikTok Shop API GET /finance/202309/statements (escopo seller.finance.info).
-- ETL: agente_rhode/etl_finance.py → warehouse/raw_finance.csv.
-- Sync: agente_rhode/sync_supabase.py::sync_finance().
--
-- ⚠️ DADO SENSÍVEL (receita/settlement). RLS segue o padrão atual (anon) só pra não
--    quebrar o admin que lê via anon key — será fechado junto no item 8 (hardening).

CREATE TABLE IF NOT EXISTS finance_statements (
  id              TEXT PRIMARY KEY,                   -- statement id
  data            DATE,                               -- dia do statement_time
  statement_time  BIGINT,
  revenue_amount  NUMERIC(12,2) DEFAULT 0,            -- receita bruta
  fee_amount      NUMERIC(12,2) DEFAULT 0,            -- taxa TikTok (negativo)
  shipping_cost   NUMERIC(12,2) DEFAULT 0,            -- frete (negativo)
  adjustment      NUMERIC(12,2) DEFAULT 0,
  net_sales       NUMERIC(12,2) DEFAULT 0,
  settlement      NUMERIC(12,2) DEFAULT 0,            -- o que a loja recebe de fato
  payment_status  TEXT,
  currency        TEXT DEFAULT 'BRL',
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_finance_data_desc ON finance_statements(data DESC);

ALTER TABLE finance_statements DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_finance" ON finance_statements;
CREATE POLICY "anon_all_finance" ON finance_statements FOR ALL USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS update_finance_updated_at ON finance_statements;
CREATE TRIGGER update_finance_updated_at
  BEFORE UPDATE ON finance_statements
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

SELECT 'finance_statements' AS info, COUNT(*) AS rows FROM finance_statements;
