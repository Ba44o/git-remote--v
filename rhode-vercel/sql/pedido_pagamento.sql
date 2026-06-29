-- =============================================================
-- Rhode — Tabela pedido_pagamento (GMV OFICIAL · order-level, da Orders API)
-- O que o cliente PAGOU por pedido (total_amount = produto + frete), sem atraso
-- de settlement. Σ total_amount onde paid_time>0 = GMV do Seller Center (validado
-- Maio: R$521,7k vs SC R$522,1k = -0,1%). Resolve o mês corrente (Orders API não
-- tem lag, ao contrário do statement_tx que depende de liquidação).
-- Granularidade: 1 linha por pedido. Coletor: coletar_pedidos_sku.py (mesma chamada).
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE TABLE IF NOT EXISTS pedido_pagamento (
  id                text PRIMARY KEY,        -- = order_id
  order_id          text NOT NULL,
  status            text,
  paid              boolean DEFAULT false,    -- paid_time > 0
  paid_time         bigint,
  order_time        bigint,
  data              date,
  periodo           text,                     -- YYYY-MM (por data do pedido)
  total_amount      numeric DEFAULT 0,        -- o que o cliente pagou (produto + frete) = GMV oficial
  sub_total         numeric DEFAULT 0,        -- produto (após desconto vendedor)
  shipping_fee      numeric DEFAULT 0,        -- frete pago pelo cliente
  seller_discount   numeric DEFAULT 0,
  platform_discount numeric DEFAULT 0,
  updated_at        timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pedpag_periodo ON pedido_pagamento(periodo);
CREATE INDEX IF NOT EXISTS idx_pedpag_paid    ON pedido_pagamento(paid);

-- deny-anon (consistente com as outras tabelas; o console lê via proxy service_role)
ALTER TABLE pedido_pagamento ENABLE ROW LEVEL SECURITY;

-- =============================================================
-- View gmv_oficial_resumo — a PONTE por período:
--   GMV oficial (= Seller Center) → −frete → produto → −pagos-cancelados → produto válido
-- =============================================================
CREATE OR REPLACE VIEW gmv_oficial_resumo AS
SELECT
  periodo,
  count(*) FILTER (WHERE paid)                                                          AS pedidos_pagos,
  round(sum(total_amount) FILTER (WHERE paid)::numeric, 2)                              AS gmv_oficial,
  round(sum(sub_total)    FILTER (WHERE paid)::numeric, 2)                              AS produto,
  round(sum(shipping_fee) FILTER (WHERE paid)::numeric, 2)                              AS frete,
  round(sum(total_amount) FILTER (WHERE paid AND status ILIKE '%CANCEL%')::numeric, 2)  AS pago_cancelado,
  round(sum(sub_total)    FILTER (WHERE paid AND status ILIKE '%CANCEL%')::numeric, 2)  AS produto_cancelado,
  count(*) FILTER (WHERE paid AND status ILIKE '%CANCEL%')                              AS n_pago_cancelado,
  -- produto válido (base de margem) = produto pago − produto pago-e-cancelado
  round((sum(sub_total) FILTER (WHERE paid)
         - sum(sub_total) FILTER (WHERE paid AND status ILIKE '%CANCEL%'))::numeric, 2) AS produto_valido
FROM pedido_pagamento
WHERE periodo IS NOT NULL
GROUP BY periodo
ORDER BY periodo;

SELECT * FROM gmv_oficial_resumo;
