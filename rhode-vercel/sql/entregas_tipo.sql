-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Estende amostras_enviadas com tipos de entrega
-- ═══════════════════════════════════════════════════════════════════════════

ALTER TABLE amostras_enviadas
  ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'amostra'
    CHECK (tipo IN ('amostra','placa_tier','spark_ads','kit_surpresa','premio_evento','outro'));

CREATE INDEX IF NOT EXISTS idx_entregas_tipo ON amostras_enviadas(tipo);

-- Para entregas que não são produto (placa, spark ads, prêmio), o sku pode ser null
ALTER TABLE amostras_enviadas
  ALTER COLUMN sku DROP NOT NULL;

-- Confirmação
SELECT tipo, COUNT(*) AS rows FROM amostras_enviadas GROUP BY tipo ORDER BY rows DESC;
