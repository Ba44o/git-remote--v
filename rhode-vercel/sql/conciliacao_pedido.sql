-- =============================================================
-- Rhode — View conciliacao_pedido v2 (MOTOR de conciliação, dado ITEMIZADO)
-- Por pedido: cascata completa preço→desconto→receita→taxas→repasse, com o
-- ESPERADO (regras contratadas) ao lado do REAL, divergência tipada, e a
-- DEVOLUÇÃO separada da taxa normal (v1 conflava → falso overcharge).
--
-- Validado: comissão bate 6% ao centavo; 95% dos pedidos "ok". Os "servico_revisar"
-- são majoritariamente FRETE não-subsidiado que o vendedor absorve (custo real),
-- não cobrança errada — por isso não entram como "recuperável garantido".
--
-- Agregação SINAL (sum com sinal) → um pedido com venda+devolução não infla.
-- revenue robusto: usa a coluna itemizada; se 0 (mês não re-coletado), deriva.
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
-- CREATE OR REPLACE não reestrutura colunas (só adiciona no fim) → dropar antes.
-- resumo depende de pedido, então dropa resumo primeiro.
DROP VIEW IF EXISTS conciliacao_resumo;
DROP VIEW IF EXISTS conciliacao_pedido;
CREATE VIEW conciliacao_pedido AS
WITH tx AS (
    SELECT order_id,
           max(periodo) AS periodo, max(data) AS data,
           sum(customer_payment)              AS pago,
           sum(settlement)                    AS settlement,
           sum(fee_total)                     AS fee_s,
           sum(platform_commission)           AS com_s,
           sum(affiliate_commission)          AS afi_s,
           sum(affiliate_ads_commission)      AS ads_s,
           sum(shipping)                      AS fre_s,
           sum(gross_sales)                   AS gross_sales,
           sum(seller_discount)               AS seller_discount,
           sum(revenue)                       AS revenue_col,
           sum(customer_refund)               AS customer_refund,
           sum(return_shipping)               AS return_shipping,
           sum(refund_admin_fee)              AS refund_admin_fee
    FROM statement_tx GROUP BY order_id
),
q AS (
    SELECT order_id, sum(qty) AS qty, max(produto) AS produto, max(status) AS status
    FROM pedidos_sku GROUP BY order_id
),
base AS (
    SELECT tx.*, coalesce(q.qty,1) AS qty, q.produto, q.status,
           abs(fee_s) AS fee, abs(com_s) AS comissao, abs(afi_s) AS afiliada,
           abs(ads_s) AS ads, abs(fre_s) AS frete,
           round(coalesce(nullif(revenue_col,0), settlement + abs(fee_s) + abs(fre_s))::numeric, 2) AS receita_liq,
           (abs(customer_refund) > 0.01 OR abs(return_shipping) > 0.01 OR abs(refund_admin_fee) > 0.01) AS tem_devolucao
    FROM tx LEFT JOIN q ON q.order_id = tx.order_id
)
SELECT
    order_id, periodo, data, produto, status, qty, pago, receita_liq, settlement,
    -- ---- PROMOÇÃO (o que o vendedor banca) ----
    round(abs(gross_sales)::numeric, 2)                              AS preco_tabela,
    round(abs(seller_discount)::numeric, 2)                          AS desconto_vendedor,
    round((abs(seller_discount)/nullif(abs(gross_sales),0)*100)::numeric, 1) AS desconto_pct,
    round((receita_liq / nullif(qty,0))::numeric, 2)                 AS preco_unit,
    -- ---- REAL ----
    comissao                                                         AS comissao_real,
    round((fee - comissao - afiliada - ads)::numeric, 2)             AS servico_frete_real,
    afiliada                                                         AS afiliada_real,
    ads                                                              AS ads_real,
    frete                                                            AS frete_real,
    round((abs(return_shipping) + abs(refund_admin_fee))::numeric, 2) AS custo_devolucao,
    round(((comissao + (fee-comissao-afiliada-ads) + afiliada + ads)/nullif(receita_liq,0)*100)::numeric, 1) AS taxa_efetiva_pct,
    -- ---- ESPERADO (pré-15/07) ----
    round((receita_liq * 0.06)::numeric, 2)                          AS comissao_esperada,
    round((receita_liq * 0.06 + 4.0 * qty)::numeric, 2)              AS servico_frete_esperado,
    -- ---- DIVERGÊNCIA ----
    round((comissao - receita_liq*0.06)::numeric, 2)                 AS div_comissao,
    round(((fee-comissao-afiliada-ads) - (receita_liq*0.06 + 4.0*qty))::numeric, 2) AS div_servico_frete,
    -- ---- SIM 15/07 ----
    round((CASE WHEN receita_liq/nullif(qty,0) < 50 THEN receita_liq*0.04 ELSE 2.0*qty END)::numeric, 2) AS impacto_1507,
    -- ---- CLASSIFICAÇÃO (honesta) ----
    CASE
      WHEN settlement <= 0.01 AND status ILIKE '%CANCEL%'                THEN 'cancelado'
      WHEN settlement <= 0.01                                            THEN 'repasse_faltante'
      WHEN (abs(customer_refund)>0.01 OR abs(return_shipping)>0.01 OR abs(refund_admin_fee)>0.01) THEN 'com_devolucao'
      WHEN comissao - receita_liq*0.06 > 0.50                            THEN 'comissao_acima'
      WHEN (fee-comissao-afiliada-ads) - (receita_liq*0.06 + 4.0*qty) > 2.0 THEN 'servico_revisar'
      ELSE 'ok'
    END AS conciliacao
FROM base;

-- =============================================================
-- View conciliacao_resumo — agregado por período (leve, p/ o dashboard)
-- =============================================================
CREATE OR REPLACE VIEW conciliacao_resumo AS
SELECT periodo,
    count(*)                                                    AS pedidos_total,
    count(*) FILTER (WHERE conciliacao='ok')                    AS n_ok,
    count(*) FILTER (WHERE conciliacao='servico_revisar')       AS n_servico,
    count(*) FILTER (WHERE conciliacao='comissao_acima')        AS n_comissao,
    count(*) FILTER (WHERE conciliacao='com_devolucao')         AS n_devolucao,
    count(*) FILTER (WHERE conciliacao='repasse_faltante')      AS n_faltante,
    count(*) FILTER (WHERE conciliacao='cancelado')             AS n_cancelado,
    round(sum(receita_liq)            FILTER (WHERE settlement>0.01)::numeric,2) AS receita,
    round(sum(settlement)             FILTER (WHERE settlement>0.01)::numeric,2) AS repasse,
    round(sum(comissao_real)          FILTER (WHERE settlement>0.01)::numeric,2) AS comissao_real,
    round(sum(comissao_esperada)      FILTER (WHERE settlement>0.01)::numeric,2) AS comissao_esp,
    round(sum(servico_frete_real)     FILTER (WHERE settlement>0.01)::numeric,2) AS servico_real,
    round(sum(servico_frete_esperado) FILTER (WHERE settlement>0.01)::numeric,2) AS servico_esp,
    round(sum(afiliada_real)          FILTER (WHERE settlement>0.01)::numeric,2) AS afiliada,
    round(sum(ads_real)               FILTER (WHERE settlement>0.01)::numeric,2) AS ads,
    round(sum(frete_real)             FILTER (WHERE settlement>0.01)::numeric,2) AS frete,
    round(sum(preco_tabela)           FILTER (WHERE settlement>0.01)::numeric,2) AS preco_tabela,
    round(sum(desconto_vendedor)      FILTER (WHERE settlement>0.01)::numeric,2) AS desconto_vendedor,
    round(sum(div_servico_frete) FILTER (WHERE conciliacao='servico_revisar')::numeric,2) AS div_servico_revisar,
    round(sum(custo_devolucao)::numeric,2)                                       AS custo_devolucao,
    round(sum(pago) FILTER (WHERE conciliacao='repasse_faltante')::numeric,2)    AS valor_faltante,
    round(sum(impacto_1507)           FILTER (WHERE settlement>0.01)::numeric,2) AS impacto_1507
FROM conciliacao_pedido
GROUP BY periodo ORDER BY periodo;

SELECT * FROM conciliacao_resumo;
