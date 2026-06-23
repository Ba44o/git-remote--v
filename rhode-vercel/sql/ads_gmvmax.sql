-- =============================================================
-- Rhode — GMV Max (Shop ads) · tabela ads_gmvmax (admin/CFO)
-- Fonte: export "creative data for product campaigns" do Seller Center.
-- Agregado por (período, campanha, produto). Admin-only, RLS deny-anon.
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE TABLE IF NOT EXISTS ads_gmvmax (
    id             text PRIMARY KEY,          -- "{periodo_ini}|{campaign_id}|{product_id}"
    periodo        text,                       -- 'YYYY-MM' (do nome do arquivo)
    periodo_ini    date,
    periodo_fim    date,
    campanha       text,
    campaign_id    text,
    product_id     text,
    is_gmvmax      boolean       DEFAULT true, -- nome começa com [GMV-MAX]
    custo          numeric(12,2) DEFAULT 0,    -- gasto de ads
    pedidos        integer       DEFAULT 0,    -- pedidos de SKU atribuídos
    receita_bruta  numeric(12,2) DEFAULT 0,    -- GMV gerado pelo anúncio
    roi            numeric(10,2) DEFAULT 0,    -- receita / custo (ROAS)
    impressoes     bigint        DEFAULT 0,
    cliques        bigint        DEFAULT 0,
    moeda          text          DEFAULT 'BRL',
    updated_at     timestamptz   DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ads_gmvmax_periodo ON ads_gmvmax(periodo);
CREATE INDEX IF NOT EXISTS idx_ads_gmvmax_produto ON ads_gmvmax(product_id);

ALTER TABLE ads_gmvmax ENABLE ROW LEVEL SECURITY;  -- deny-anon; só service_role acessa

SELECT 'ads_gmvmax' AS tabela, COUNT(*) AS linhas FROM ads_gmvmax;
