-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Status de Pagamento de Comissão
-- Adiciona campos em performance_periods pra rastrear pagamentos
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE performance_periods
  ADD COLUMN IF NOT EXISTS pagamento_status TEXT
    DEFAULT 'pendente'
    CHECK (pagamento_status IN ('pendente','pago','disputado','ajustado'));

ALTER TABLE performance_periods
  ADD COLUMN IF NOT EXISTS pago_em DATE;

ALTER TABLE performance_periods
  ADD COLUMN IF NOT EXISTS comissao_paga NUMERIC(10,2);

ALTER TABLE performance_periods
  ADD COLUMN IF NOT EXISTS pago_obs TEXT;

CREATE INDEX IF NOT EXISTS idx_pp_pgto_status
  ON performance_periods(pagamento_status, periodo);

SELECT pagamento_status, COUNT(*) AS rows
FROM performance_periods
GROUP BY pagamento_status
ORDER BY pagamento_status NULLS FIRST;
