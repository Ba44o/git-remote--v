-- =============================================================
-- Rhode — Conciliação koncili-style · tabela statement_tx (admin/CFO)
-- Fonte: TikTok Shop Finance API, order-level:
--   /finance/202309/statements/{statement_id}/statement_transactions
-- Cada linha = 1 pedido num statement, com a CASCATA COMPLETA de taxas.
-- Substitui a estimativa "GMV × eficiência" por settlement EXATO por pedido.
-- (Nome 'lancamentos' já é do Catálogo de Lançamentos do hub — por isso statement_tx.)
-- Admin-only, RLS deny-anon. Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE TABLE IF NOT EXISTS statement_tx (
    id                  text PRIMARY KEY,        -- "{statement_id}:{order_id}"
    statement_id        text,
    order_id            text,
    order_create_time   bigint,                  -- epoch (atribuição ao período da VENDA)
    data                date,
    periodo             text,                     -- 'YYYY-MM' (pela data da venda)
    customer_payment    numeric(12,2) DEFAULT 0, -- o que o cliente pagou
    settlement          numeric(12,2) DEFAULT 0, -- repasse final (o que a loja recebe) — EXATO
    fee_total           numeric(12,2) DEFAULT 0, -- dedução total TikTok (negativo)
    platform_commission numeric(12,2) DEFAULT 0, -- comissão de plataforma
    affiliate_commission        numeric(12,2) DEFAULT 0, -- comissão de creator/afiliada
    affiliate_ads_commission    numeric(12,2) DEFAULT 0, -- comissão de shop ads (GMV Max)
    shipping            numeric(12,2) DEFAULT 0,
    adjustment          numeric(12,2) DEFAULT 0,
    moeda               text          DEFAULT 'BRL',
    updated_at          timestamptz   DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_stmttx_periodo ON statement_tx(periodo);
CREATE INDEX IF NOT EXISTS idx_stmttx_order   ON statement_tx(order_id);
CREATE INDEX IF NOT EXISTS idx_stmttx_stmt    ON statement_tx(statement_id);

ALTER TABLE statement_tx ENABLE ROW LEVEL SECURITY;  -- deny-anon; só service_role acessa

SELECT 'statement_tx' AS tabela, COUNT(*) AS linhas FROM statement_tx;
