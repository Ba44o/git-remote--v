-- =============================================================
-- Rhode — Colunas de REEMBOLSO (crédito +) em statement_tx.
-- Nas statement_transactions, `type != 'ORDER'` são lançamentos de ajuste que vêm
-- com order_id NULL (pedido no adjustment_order_id) e valor duplicado em
-- settlement_amount E adjustment_amount. Dois deles aparecem nos dados da Rhode,
-- ambos crédito que a TikTok devolve ao vendedor:
--   • LOGISTICS_REIMBURSEMENT → problema logístico (extravio/atraso na devolução)
--   • PLATFORM_REIMBURSEMENT  → política "refund without return" (plataforma absorve e credita)
-- O coletor antigo (`if not oid: continue`) DESCARTAVA essas linhas → statement_tx
-- ficava menor que finance_statements pelo total de reembolsos (jun/26: gap R$ 3.096
-- só com LOGISTICS; +R$ 67 de PLATFORM). Agora o coletar_statement_tx.py religa por
-- adjustment_order_id, soma em `settlement` (fecha o gap) e isola cada crédito na sua
-- coluna, mantendo-os FORA do `adjustment` genérico.
-- Não-destrutivo (ADD COLUMN IF NOT EXISTS). Rodar no Supabase → SQL Editor → Run.
-- Depois: backfill → python3 coletar_statement_tx.py --inicio 2026-01-01 --fim 2026-06-30
-- =============================================================
ALTER TABLE statement_tx
  ADD COLUMN IF NOT EXISTS logistics_reimbursement numeric(12,2) DEFAULT 0,  -- crédito (+) por problema logístico
  ADD COLUMN IF NOT EXISTS platform_reimbursement  numeric(12,2) DEFAULT 0;  -- crédito (+) "refund without return"
