-- =============================================================
-- Rhode — View statement_tx_resumo (conciliação de repasse, por período)
-- Agrega statement_tx por PEDIDO (across statements) → classifica liquidado /
-- a receber (pendente) / devolvido → soma por período. Base da camada koncili.
-- O console consulta a view (≈10 linhas) em vez de 60k linhas brutas.
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE OR REPLACE VIEW statement_tx_resumo AS
WITH por_pedido AS (
    SELECT order_id,
           max(periodo)                  AS periodo,
           sum(customer_payment)         AS pago,
           sum(settlement)               AS settle,
           sum(platform_commission)      AS plat,
           sum(affiliate_commission)     AS afi,
           sum(affiliate_ads_commission) AS ads,
           sum(shipping)                 AS ship
    FROM statement_tx
    GROUP BY order_id
)
SELECT periodo,
       count(*)                                                          AS pedidos,
       count(*) FILTER (WHERE settle >  0.01)                            AS liquidados,
       count(*) FILTER (WHERE abs(settle) <= 0.01)                       AS pendentes,
       count(*) FILTER (WHERE settle < -0.01)                            AS devolvidos,
       round(sum(pago)::numeric, 2)                                      AS pago_total,
       round(sum(settle) FILTER (WHERE settle > 0.01)::numeric, 2)       AS settle_liq,
       round(sum(pago)   FILTER (WHERE settle > 0.01)::numeric, 2)       AS pago_liq,
       round(sum(pago)   FILTER (WHERE abs(settle) <= 0.01)::numeric, 2) AS a_receber,
       round(sum(settle) FILTER (WHERE settle < -0.01)::numeric, 2)      AS devolucao,
       round(abs(sum(plat))::numeric, 2)                                 AS comissao_plataforma,
       round(abs(sum(afi))::numeric, 2)                                  AS comissao_afiliada,
       round(abs(sum(ads))::numeric, 2)                                  AS comissao_ads_afil,
       round(abs(sum(ship))::numeric, 2)                                 AS frete
FROM por_pedido
WHERE periodo IS NOT NULL
GROUP BY periodo
ORDER BY periodo;

SELECT * FROM statement_tx_resumo;
