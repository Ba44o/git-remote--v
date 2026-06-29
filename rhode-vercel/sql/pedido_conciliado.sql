-- =============================================================
-- Rhode — View pedido_conciliado (drill-down pedido-a-pedido · aba Pedidos)
-- Junta statement_tx (settlement + cascata) com pedidos_sku (produto/status/qty)
-- → 1 linha por pedido com tudo pra conciliar. Base da aba "Pedidos".
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE OR REPLACE VIEW pedido_conciliado AS
WITH tx AS (
    SELECT order_id,
           max(periodo) AS periodo,
           max(data)    AS data,
           sum(customer_payment)         AS pago,
           sum(settlement)               AS settle,
           sum(fee_total)                AS fee,
           sum(platform_commission)      AS plat,
           sum(affiliate_commission)     AS afi,
           sum(affiliate_ads_commission) AS ads,
           sum(shipping)                 AS ship
    FROM statement_tx GROUP BY order_id
),
ps AS (
    SELECT order_id, max(status) AS status, max(produto) AS produto, sum(qty) AS qty
    FROM pedidos_sku GROUP BY order_id
)
SELECT tx.order_id,
       tx.periodo,
       tx.data,
       ps.produto,
       ps.status,
       coalesce(ps.qty,0)                AS qty,
       round(tx.pago::numeric, 2)        AS pago,
       round(tx.settle::numeric, 2)      AS settlement,
       round(abs(tx.fee)::numeric, 2)    AS fee,
       round(abs(tx.plat)::numeric, 2)   AS comissao_plataforma,
       round(abs(tx.afi)::numeric, 2)    AS comissao_afiliada,
       round(abs(tx.ads)::numeric, 2)    AS comissao_ads,
       round(abs(tx.ship)::numeric, 2)   AS frete,
       CASE WHEN tx.pago > 0 AND tx.settle > 0.01
            THEN round((1 - tx.settle / tx.pago) * 100, 1) END AS taxa_pct,
       CASE WHEN tx.settle >  0.01 THEN 'liquidado'
            WHEN tx.settle < -0.01 THEN 'devolvido'
            ELSE 'a_receber' END         AS situacao
FROM tx LEFT JOIN ps ON ps.order_id = tx.order_id;
