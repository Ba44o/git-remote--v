-- =============================================================
-- Rhode — LIVE (atribuição do Seller Center, por SESSÃO/sala)
-- Fonte: export "Livestream / Creator-Live-Performance" (aba performance_detail)
--   coluna "Attributed GMV" = GMV atribuído à sala de live (orgânico + ads).
--   É a FONTE DA VERDADE que o Humberto usa no fechamento (bate ao centavo:
--   junho/26 = R$ 205.591,75 nas 54 salas).
-- Difere do GMV Max (live_sessao): aquele é atribuição de ADS (gross_revenue).
-- Importador: importar_live_performance.py. Rodar no Supabase → SQL Editor → Run.
-- =============================================================

CREATE TABLE IF NOT EXISTS live_attr (
  id          text PRIMARY KEY,      -- room_id
  room_id     text,
  titulo      text,                  -- nome da LIVE (Room Title)
  inicio      timestamptz,           -- Start Time
  fim         timestamptz,           -- End Time
  duracao     text,                  -- "3h06m"
  data        date,                  -- date(inicio)
  periodo     text,                  -- YYYY-MM
  origem      text DEFAULT 'propria',-- shop = live própria da Rhode
  gmv         numeric DEFAULT 0,     -- Attributed GMV  ← headline
  pedidos     integer DEFAULT 0,     -- Attributed orders
  itens       integer DEFAULT 0,     -- Attributed items sold
  sku_orders  integer DEFAULT 0,     -- Attributed SKU orders
  customers   integer DEFAULT 0,     -- Customers
  aov         numeric DEFAULT 0,     -- AOV
  views       integer DEFAULT 0,     -- Views
  impressions bigint  DEFAULT 0,     -- Impressions
  updated_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_live_attr_periodo ON live_attr(periodo);
CREATE INDEX IF NOT EXISTS idx_live_attr_data ON live_attr(data);
ALTER TABLE live_attr ENABLE ROW LEVEL SECURITY;

-- Totais por período (conferência rápida)
CREATE OR REPLACE VIEW live_attr_resumo AS
SELECT periodo,
       count(*)                 AS sessoes,
       round(sum(gmv),2)        AS gmv,
       sum(pedidos)             AS pedidos,
       sum(views)               AS views,
       sum(customers)           AS customers,
       round(sum(gmv)/NULLIF(sum(pedidos),0),2) AS ticket
FROM live_attr
GROUP BY periodo
ORDER BY periodo;

SELECT 'live_attr criada' AS ok;
