-- =============================================================
-- Rhode — Liquidação REAL por Corte × Cor (lavagem) × Canal.
-- Aba "Liquidação SKU" do console de conciliação (creators.rhodejeans.com.br/conciliacao.html).
-- A cor/lavagem mora no SKU (seller_sku REF, ex: REF516 = Marmorizada = hero), NÃO no nome do anúncio.
-- Liquidação = settlement REAL por pedido (conciliacao_pedido), rateado por linha (gmv share).
-- Guarda SOMAS (não médias) p/ agregação multi-mês correta no cliente.
-- Populado por liquidacao_cor_canal.py (ROOT, cron). RLS deny-anon (só service_role/proxy admin lê).
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE TABLE IF NOT EXISTS liquidacao_cor_canal (
  id              text PRIMARY KEY,        -- "{periodo}:{corte}:{cor}:{canal}"
  periodo         text,                    -- 'YYYY-MM'
  corte           text,                    -- Wide Leg | Mom | Baggy
  cor             text,                    -- lavagem/cor (do sku_name), ex: Marmorizada
  canal           text,                    -- video_afil | live_afil | loja | TOTAL
  pecas           integer DEFAULT 0,       -- peças no período (todas, p/ mix e preço)
  pecas_liq       integer DEFAULT 0,       -- peças de pedidos JÁ liquidados (base do settlement real)
  settlement_real numeric  DEFAULT 0,      -- soma do settlement real rateado (só liquidados)
  gmv             numeric  DEFAULT 0,      -- soma do GMV bruto (todas as peças)
  cpv_total       numeric  DEFAULT 0,      -- soma do CPV (todas as peças)
  is_hero         boolean  DEFAULT false,  -- REF516 Marmorizada Wide Leg
  updated_at      timestamptz DEFAULT now()
  -- derivados no cliente: preco=gmv/pecas · liq_pc=settlement_real/pecas_liq
  --                       cov=pecas_liq/pecas · margem_pc=liq_pc - cpv_total/pecas
);
CREATE INDEX IF NOT EXISTS idx_liq_cor_canal_periodo ON liquidacao_cor_canal(periodo);
ALTER TABLE liquidacao_cor_canal ENABLE ROW LEVEL SECURITY;  -- deny-anon; service_role bypassa
SELECT 'liquidacao_cor_canal criada' AS ok;
