-- =============================================================
-- Rhode — Tabela ads_campanha (detalhe POR CAMPANHA do GMV Max, via Business API)
-- Fonte: /gmv_max/report/get/ (dimensions stat_time_day + campaign_id). Base do
-- relatório de mídia (investimento, receita, ROAS, CPA, ticket, por campanha).
-- modelo: net_cost=0 & cost>0 = 'vendas_liquidas' (pay-with-GMV); senão 'tradicional'.
-- Coletor: coletar_gmvmax_api.py. Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE TABLE IF NOT EXISTS ads_campanha (
  id          text PRIMARY KEY,       -- "{data}:{campaign_id}"
  data        date,
  periodo     text,                   -- YYYY-MM
  campaign_id text,
  campanha    text,
  modelo      text,                   -- 'tradicional' | 'vendas_liquidas'
  cost        numeric DEFAULT 0,      -- "Custo do GMV máximo" (investimento real)
  net_cost    numeric DEFAULT 0,      -- custo líquido pós-proteção de ROI (0 nas VL)
  receita     numeric DEFAULT 0,      -- gross_revenue (GMV atribuído)
  pedidos     integer DEFAULT 0,
  updated_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ads_campanha_periodo ON ads_campanha(periodo);
CREATE INDEX IF NOT EXISTS idx_ads_campanha_data    ON ads_campanha(data);
ALTER TABLE ads_campanha ENABLE ROW LEVEL SECURITY;

SELECT 'ads_campanha criada' AS ok;
