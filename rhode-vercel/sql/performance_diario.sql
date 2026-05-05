-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Performance Diária da Loja (TikTok Shop)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Granularidade: 1 linha por dia (loja toda agregada). NÃO é por creator.
-- Para granularidade creator × dia, precisaríamos de outro coletor (Order
-- List API). Esta tabela cobre o KPI shop-wide diário (GMV, pedidos, ticket,
-- cancelados) usado no gráfico de tendência diária do admin.
--
-- Fonte: aba "Diario" dos exports Overview_*.xlsx (gerados por
-- coletar_dados.py via TikTok Shop API com report_granularity=DAY).
-- ETL: agente_rhode/etl_diario.py → warehouse/raw_diario.csv.
-- Sync: agente_rhode/sync_supabase.py::sync_performance_diario().

CREATE TABLE IF NOT EXISTS performance_diario (
  data            DATE PRIMARY KEY,
  gmv_bruto       NUMERIC(12,2) DEFAULT 0,            -- todos os pedidos (GMV)
  gmv_liquido     NUMERIC(12,2) DEFAULT 0,            -- só confirmados (GMV_CF)
  pedidos         INT DEFAULT 0,                      -- confirmados
  cancelados      INT DEFAULT 0,
  itens           INT DEFAULT 0,
  clientes        INT DEFAULT 0,                      -- distintos no dia
  ticket          NUMERIC(10,2) DEFAULT 0,            -- gmv_liquido / pedidos
  taxa_cancel_pct NUMERIC(5,2) DEFAULT 0,             -- %
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_perf_diario_data_desc ON performance_diario(data DESC);

ALTER TABLE performance_diario DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_perf_diario" ON performance_diario;
CREATE POLICY "anon_all_perf_diario" ON performance_diario FOR ALL USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS update_perf_diario_updated_at ON performance_diario;
CREATE TRIGGER update_perf_diario_updated_at
  BEFORE UPDATE ON performance_diario
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- Confirmação
SELECT 'performance_diario' AS info, COUNT(*) AS rows FROM performance_diario;
