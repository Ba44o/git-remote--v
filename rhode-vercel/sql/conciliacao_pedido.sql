-- =============================================================
-- Rhode — View conciliacao_pedido (MOTOR de conciliação esperado × real)
-- Por pedido: decompõe o repasse real e compara com o ESPERADO (regras
-- contratadas do TikTok Shop BR), sinalizando divergência por componente.
--
-- Identidade validada em 480 pedidos (resíduo 0,00):
--   settlement = receita_liquida − fee_total − frete
--   fee_total  = comissão(6%) + [frete_grátis 6% + taxa fixa R$4/item] + afiliada + ads
--   receita_liquida (revenue/net_sales) = settlement + |fee_total| + |frete|
--
-- Fonte: statement_tx (real, itemizado) + pedidos_sku (qtd/produto/status).
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE OR REPLACE VIEW conciliacao_pedido AS
WITH tx AS (
    SELECT order_id,
           max(periodo)                      AS periodo,
           max(data)                         AS data,
           sum(customer_payment)             AS pago,
           sum(settlement)                   AS settlement,
           sum(abs(fee_total))               AS fee,
           sum(abs(platform_commission))     AS comissao,
           sum(abs(affiliate_commission))    AS afiliada,
           sum(abs(affiliate_ads_commission))AS ads,
           sum(abs(shipping))                AS frete
    FROM statement_tx
    GROUP BY order_id
),
q AS (
    SELECT order_id, sum(qty) AS qty, max(produto) AS produto, max(status) AS status
    FROM pedidos_sku GROUP BY order_id
),
base AS (
    SELECT tx.*,
           coalesce(q.qty,1)                        AS qty,
           q.produto, q.status,
           round((tx.settlement + tx.fee + tx.frete)::numeric, 2) AS receita_liq,
           -- taxa de serviço + frete grátis (real) = fee menos as comissões nomeadas
           round((tx.fee - tx.comissao - tx.afiliada - tx.ads)::numeric, 2) AS servico_frete
    FROM tx LEFT JOIN q ON q.order_id = tx.order_id
)
SELECT
    order_id, periodo, data, produto, status, qty,
    pago, receita_liq, settlement,
    -- preço unitário líquido (define a faixa da tarifa 15/07)
    round((receita_liq / nullif(qty,0))::numeric, 2)               AS preco_unit,
    -- ---- REAL (o que o TikTok cobrou) ----
    comissao        AS comissao_real,
    servico_frete   AS servico_frete_real,
    afiliada        AS afiliada_real,
    ads             AS ads_real,
    frete           AS frete_real,
    round(((comissao+servico_frete+afiliada+ads)/nullif(receita_liq,0)*100)::numeric,1) AS taxa_efetiva_pct,
    -- ---- ESPERADO (regras contratadas, pré-15/07) ----
    round((receita_liq * 0.06)::numeric, 2)                        AS comissao_esperada,   -- 6%
    round((receita_liq * 0.06 + 4.0 * qty)::numeric, 2)            AS servico_frete_esperado, -- frete 6% + R$4/item
    -- ---- DIVERGÊNCIA (real − esperado; >0 = cobraram a mais) ----
    round((comissao      - receita_liq * 0.06)::numeric, 2)        AS div_comissao,
    round((servico_frete - (receita_liq * 0.06 + 4.0 * qty))::numeric, 2) AS div_servico_frete,
    -- ---- SIMULAÇÃO TARIFA 15/07/2026 (por preço unitário líquido) ----
    -- <R$50: comissão 6%→10% (+4% da receita). ≥R$50: taxa fixa R$4→R$6 (+R$2/item).
    round((CASE WHEN receita_liq/nullif(qty,0) < 50 THEN receita_liq * 0.04
                ELSE 2.0 * qty END)::numeric, 2)                   AS impacto_1507,
    -- ---- CLASSIFICAÇÃO ----
    CASE
      WHEN settlement <= 0.01 AND status ILIKE '%CANCEL%'          THEN 'cancelado'
      WHEN settlement <= 0.01                                      THEN 'repasse_faltante'
      WHEN comissao - receita_liq*0.06 > 0.50                      THEN 'comissao_acima'
      WHEN servico_frete - (receita_liq*0.06 + 4.0*qty) > 0.50     THEN 'servico_acima'
      WHEN abs(comissao - receita_liq*0.06) <= 0.50
       AND abs(servico_frete - (receita_liq*0.06 + 4.0*qty)) <= 0.50 THEN 'ok'
      ELSE 'revisar'
    END AS conciliacao
FROM base;
