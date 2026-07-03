-- =============================================================
-- Rhode — Tabela ads_custo (CUSTO REAL do GMV Max, do painel de ads)
-- Fonte: export "Campaign overview data" (Ads Manager) — coluna "Custo do GMV
-- máximo" = gasto real por dia, TODAS as campanhas (inclui Vendas Líquidas que
-- o export "creative data" mostra como 0). Este é o custo de mídia que NÃO está
-- no settlement do seller (pago na conta de ads) e precisa entrar no lucro.
-- Coletor: importar_ads_overview.py. Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE TABLE IF NOT EXISTS ads_custo (
  id         text PRIMARY KEY,      -- data YYYY-MM-DD
  data       date,
  periodo    text,                  -- YYYY-MM
  custo      numeric DEFAULT 0,     -- Custo do GMV máximo (gasto real)
  receita    numeric DEFAULT 0,     -- Receita bruta atribuída (loja atual)
  pedidos    integer DEFAULT 0,
  roi        numeric DEFAULT 0,
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ads_custo_periodo ON ads_custo(periodo);
ALTER TABLE ads_custo ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE VIEW ads_custo_resumo AS
SELECT periodo,
       round(sum(custo)::numeric, 2)   AS custo,
       round(sum(receita)::numeric, 2) AS receita,
       sum(pedidos)                     AS pedidos,
       CASE WHEN sum(custo) > 0 THEN round((sum(receita)/sum(custo))::numeric, 2) ELSE 0 END AS roi
FROM ads_custo
WHERE periodo IS NOT NULL
GROUP BY periodo ORDER BY periodo;

SELECT * FROM ads_custo_resumo;
