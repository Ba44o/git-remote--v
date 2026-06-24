-- =============================================================
-- Rhode — View repasse_divergencias (motor de divergências koncili · Fase B-2)
-- Classifica pedidos PAGOS mas SEM settlement (a receber) em:
--   • repasse_faltante = antigo (>30d) + não cancelado → RECUPERÁVEL (abrir chamado)
--   • cancelado        = pedido cancelado → esperado, não recuperável
--   • pendente         = recente, settlement ainda vai cair
-- Cruza statement_tx (settlement por pedido) com pedidos_sku (status do pedido).
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE OR REPLACE VIEW repasse_divergencias AS
WITH ped AS (   -- statement_tx agregado por pedido
    SELECT order_id,
           max(periodo) AS periodo,
           max(data)    AS data,
           sum(customer_payment) AS pago,
           sum(settlement)       AS settle
    FROM statement_tx
    GROUP BY order_id
),
st AS (         -- status do pedido (lado loja)
    SELECT order_id, max(status) AS status, max(produto) AS produto
    FROM pedidos_sku
    GROUP BY order_id
)
SELECT p.order_id,
       p.periodo,
       p.data,
       round(p.pago::numeric, 2) AS pago,
       st.status,
       st.produto,
       CASE
         WHEN st.status ILIKE '%CANCEL%'        THEN 'cancelado'
         WHEN p.data < (current_date - 30)      THEN 'repasse_faltante'
         ELSE 'pendente'
       END AS classe
FROM ped p
LEFT JOIN st ON st.order_id = p.order_id
WHERE abs(p.settle) <= 0.01 AND p.pago > 0;

SELECT classe, count(*) AS pedidos, round(sum(pago)::numeric,2) AS valor
FROM repasse_divergencias GROUP BY classe ORDER BY valor DESC;
