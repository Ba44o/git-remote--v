-- =============================================================
-- Rhode — Enriquecer statement_tx com o breakdown ITEMIZADO do settlement.
-- Separar taxa NORMAL (comissão/frete/serviço) de custo de DEVOLUÇÃO e da
-- PROMOÇÃO — sem isso a conciliação mistura custo de reversão com "cobrança
-- errada" (ex.: pedido de R$110 com fee de R$88 = frete reverso, não overcharge).
-- Não-destrutivo (ADD COLUMN IF NOT EXISTS). Rodar no Supabase → SQL Editor.
-- Depois: rodar o coletor enriquecido (backfill) p/ preencher as colunas novas.
-- =============================================================
ALTER TABLE statement_tx
  -- comissões extras
  ADD COLUMN IF NOT EXISTS affiliate_partner   numeric DEFAULT 0,
  ADD COLUMN IF NOT EXISTS referral_fee        numeric DEFAULT 0,
  ADD COLUMN IF NOT EXISTS transaction_fee     numeric DEFAULT 0,
  -- receita / promoção
  ADD COLUMN IF NOT EXISTS gross_sales         numeric DEFAULT 0,   -- preço de tabela
  ADD COLUMN IF NOT EXISTS seller_discount     numeric DEFAULT 0,   -- promo que o VENDEDOR banca
  ADD COLUMN IF NOT EXISTS platform_discount   numeric DEFAULT 0,   -- cupom da plataforma (reembolsado)
  ADD COLUMN IF NOT EXISTS revenue             numeric DEFAULT 0,   -- receita líquida (net_sales)
  -- custos de DEVOLUÇÃO (separar da taxa normal!)
  ADD COLUMN IF NOT EXISTS customer_refund     numeric DEFAULT 0,
  ADD COLUMN IF NOT EXISTS return_shipping     numeric DEFAULT 0,
  ADD COLUMN IF NOT EXISTS refund_admin_fee    numeric DEFAULT 0;
