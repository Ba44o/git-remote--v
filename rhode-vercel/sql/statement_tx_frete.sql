-- =============================================================
-- Rhode — Colunas de FRETE DETALHADO em statement_tx.
-- Campos de alta frequência do 202309 statement_transactions que o coletor não
-- separava (ficavam invisíveis, agregados só no fee/settlement). Permitem apurar
-- o CUSTO DE FRETE LÍQUIDO por pedido/período (frete real − subsídio da plataforma).
--   • actual_shipping_fee_amount        (~91%) → frete REAL pago à transportadora (−)
--   • fbm_shipping_cost_amount          (~90%) → frete que a LOJA banca (merchant-fulfilled, −)
--   • platform_shipping_fee_discount_amount (~84%) → subsídio de frete da plataforma (crédito +)
-- Não-destrutivo (ADD COLUMN IF NOT EXISTS). Rodar no Supabase → SQL Editor → Run.
-- Depois: backfill → python3 coletar_statement_tx.py --inicio 2026-01-01 --fim 2026-06-30
-- =============================================================
ALTER TABLE statement_tx
  ADD COLUMN IF NOT EXISTS actual_shipping_fee       numeric(12,2) DEFAULT 0,  -- frete real (−)
  ADD COLUMN IF NOT EXISTS fbm_shipping_cost         numeric(12,2) DEFAULT 0,  -- frete que a loja banca (−)
  ADD COLUMN IF NOT EXISTS platform_shipping_subsidy numeric(12,2) DEFAULT 0;  -- subsídio de frete da plataforma (+)
