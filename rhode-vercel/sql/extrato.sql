-- ═══════════════════════════════════════════════════════════════════════════
--  Rhode — Central de Comissões / "Meu Extrato" (creator-facing)
-- ═══════════════════════════════════════════════════════════════════════════
--  Fonte: TikTok Shop Affiliate Orders API (/affiliate_seller/202410/orders/search).
--  Mostra pra creator o que o painel da TikTok não mostra bem: pipeline de
--  liquidação (liquidado / a liquidar / inelegível), reembolsos e comissão.
--
--  ADITIVO: tabelas NOVAS. NÃO toca performance_periods nem tier. O Hub continua
--  tirando GMV/tier do export; o extrato é uma camada extra via API.
--
--  RLS: deny-anon. Lidas SÓ via /api/get-hub (service key), com escopo por token
--  (cada creator vê só o dela). Rodar no Supabase → SQL Editor → Run.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── Resumo por creator × mês ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS extrato_resumo (
  id                TEXT PRIMARY KEY,        -- creator|periodo  (lowercase|YYYY-MM)
  creator           TEXT NOT NULL,           -- handle (lowercase, canônico p/ aliases)
  periodo           TEXT NOT NULL,           -- YYYY-MM
  pedidos           INT     DEFAULT 0,       -- nº de pedidos distintos atribuídos
  gmv_estimado      NUMERIC DEFAULT 0,       -- base de comissão estimada (bruto)
  gmv_liquidado     NUMERIC DEFAULT 0,       -- SETTLED (actual_commission_base)
  gmv_a_liquidar    NUMERIC DEFAULT 0,       -- To-SETTLE (estimated)
  gmv_inelegivel    NUMERIC DEFAULT 0,       -- INELIGIBLE (não paga — refund/cancel)
  comissao_estimada NUMERIC DEFAULT 0,
  comissao_paga     NUMERIC DEFAULT 0,       -- actual_paid_commission (SETTLED)
  reembolsos_n      INT     DEFAULT 0,       -- pedidos com fully_return = Yes
  reembolsos_valor  NUMERIC DEFAULT 0,
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_extrato_resumo_creator ON extrato_resumo(creator);
CREATE INDEX IF NOT EXISTS idx_extrato_resumo_periodo ON extrato_resumo(periodo);

-- ── Detalhe por pedido (drill-down "ver pedidos") ───────────────────────────
CREATE TABLE IF NOT EXISTS extrato_pedidos (
  id                TEXT PRIMARY KEY,        -- order_id|sku_id
  creator           TEXT NOT NULL,
  periodo           TEXT NOT NULL,           -- YYYY-MM (da data do pedido)
  data              DATE,                    -- create_time do pedido
  order_id          TEXT,
  product_id        TEXT,
  produto           TEXT,                    -- nome (join via produtos, quando houver)
  content_type      TEXT,                    -- VIDEO / LIVE / SHOP
  gmv               NUMERIC DEFAULT 0,       -- estimated_commission_base da linha
  status            TEXT,                    -- liquidado / a_liquidar / inelegivel
  reembolso         BOOLEAN DEFAULT FALSE,   -- fully_return = Yes
  comissao_estimada NUMERIC DEFAULT 0,
  comissao_paga     NUMERIC DEFAULT 0,
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_extrato_pedidos_creator ON extrato_pedidos(creator);
CREATE INDEX IF NOT EXISTS idx_extrato_pedidos_cp ON extrato_pedidos(creator, periodo);

-- ── RLS: deny-anon nas duas (só o proxy/service_role lê) ─────────────────────
ALTER TABLE extrato_resumo  ENABLE ROW LEVEL SECURITY;
ALTER TABLE extrato_pedidos ENABLE ROW LEVEL SECURITY;
-- (sem policy permissiva → anon não lê; service_role do proxy bypassa RLS)

-- Verificação:
SELECT 'extrato_resumo'  AS tabela, COUNT(*) FROM extrato_resumo
UNION ALL
SELECT 'extrato_pedidos' AS tabela, COUNT(*) FROM extrato_pedidos;
