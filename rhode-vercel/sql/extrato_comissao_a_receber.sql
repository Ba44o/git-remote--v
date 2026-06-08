-- Rhode — Extrato: coluna comissão a receber (comissão dos pedidos que VÃO pagar,
-- i.e. status "a liquidar"). Separada da comissão estimada total (que inclui
-- inelegíveis/reembolsados que não pagam) → número limpo pra creator.
-- Aditivo. Rodar no Supabase → SQL Editor → Run.

ALTER TABLE extrato_resumo
  ADD COLUMN IF NOT EXISTS comissao_a_receber NUMERIC DEFAULT 0;

SELECT 'extrato_resumo.comissao_a_receber' AS coluna, COUNT(*) AS linhas FROM extrato_resumo;
