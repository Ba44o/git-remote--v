-- =============================================================
-- Rhode — Conciliação TikTok (admin/CFO) · Fase 0: fundação de dados
-- Tabelas NOVAS, admin-only. NÃO encostam no que roda pras creators
-- (hub.html / get-hub creator-facing não leem estas tabelas).
-- RLS deny-anon (igual rls_hardening): só service_role (ETL + proxy admin) acessa.
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================

-- ========== 1. PEDIDOS POR SKU (lado LOJA — GMV por produto) ==========
-- Fonte: TikTok Shop API /order/202309/orders/search → line_items.
-- Hoje o etl_diario só salva o agregado diário (performance_diario); aqui
-- persistimos o detalhe por (order_id, sku) pra conciliação por produto.
-- Diferente do extrato_pedidos (que é o lado AFILIADO/comissão, subconjunto).
CREATE TABLE IF NOT EXISTS pedidos_sku (
    id            text PRIMARY KEY,            -- "{order_id}:{sku}" (idempotência do upsert)
    order_id      text NOT NULL,
    sku           text,                        -- sku_name do TikTok
    seller_sku    text,                        -- seller_sku (costuma carregar o REF do Bling)
    produto       text,
    cor           text,                        -- extraída do nome quando possível
    qty           integer       DEFAULT 0,
    gmv           numeric(12,2) DEFAULT 0,     -- valor de venda bruto da linha (preço × qty)
    status        text,                        -- status do pedido (COMPLETED / CANCELLED / ...)
    order_time    bigint,                      -- epoch (segundos)
    data          date,
    periodo       text,                        -- 'YYYY-MM' (facilita agregação por mês)
    updated_at    timestamptz   DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_pedidos_sku_periodo ON pedidos_sku(periodo);
CREATE INDEX IF NOT EXISTS idx_pedidos_sku_sku     ON pedidos_sku(sku);
CREATE INDEX IF NOT EXISTS idx_pedidos_sku_order   ON pedidos_sku(order_id);

-- ========== 2. CPV POR SKU (custo de produto vendido) ==========
-- Cadastro/importação da planilha de custos (a do Lucas, quando chegar).
-- Chave flexível: REF do Bling quando existir, senão 'produto|cor'.
-- O lookup na conciliação desce em cascata: REF → produto+cor → produto.
CREATE TABLE IF NOT EXISTS custos_sku (
    id            text PRIMARY KEY,            -- chave normalizada (ref OU 'produto|cor')
    ref           text,                        -- REF do Bling (se houver)
    produto       text,
    cor           text,
    tam           text,
    cpv           numeric(10,2) NOT NULL DEFAULT 0,
    fonte         text          DEFAULT 'import',  -- import | manual
    updated_at    timestamptz   DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_custos_sku_ref ON custos_sku(ref);

-- ========== RLS: deny-anon (só service_role acessa, igual ao resto do projeto) ==========
ALTER TABLE pedidos_sku ENABLE ROW LEVEL SECURITY;
ALTER TABLE custos_sku  ENABLE ROW LEVEL SECURITY;
-- Sem policy permissiva → anon/authenticated NÃO leem. ETL e proxy admin
-- usam a service_role key (BYPASSRLS). Mantém o padrão do rls_hardening.sql.

-- ========== Sanity check ==========
SELECT 'pedidos_sku' AS tabela, COUNT(*) AS linhas FROM pedidos_sku
UNION ALL
SELECT 'custos_sku'  AS tabela, COUNT(*) AS linhas FROM custos_sku;
