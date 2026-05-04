-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Flash Sales
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS flash_sales (
  id                  BIGSERIAL PRIMARY KEY,
  sku                 TEXT NOT NULL REFERENCES produtos(sku) ON UPDATE CASCADE,
  desconto_pct        NUMERIC(5,2),                                  -- 25.00 = 25% off
  preco_de            NUMERIC(10,2),                                  -- snapshot do preço normal
  preco_por           NUMERIC(10,2),                                  -- preço promocional final
  inicio_at           TIMESTAMPTZ NOT NULL,
  fim_at              TIMESTAMPTZ NOT NULL,
  tier_minimo         TEXT DEFAULT 'Bronze' CHECK (tier_minimo IN ('Iniciante','Bronze','Silver','Gold','Diamond','Black')),
  creators_convidadas TEXT[],                                          -- null/[] = todas que atendem tier_minimo
  briefing            TEXT,
  ativo               BOOLEAN DEFAULT TRUE,                           -- pode desativar manualmente sem apagar
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  updated_at          TIMESTAMPTZ DEFAULT NOW(),
  CHECK (fim_at > inicio_at)
);

CREATE INDEX IF NOT EXISTS idx_flash_window ON flash_sales(inicio_at, fim_at) WHERE ativo = true;
CREATE INDEX IF NOT EXISTS idx_flash_sku    ON flash_sales(sku);

DROP TRIGGER IF EXISTS update_flash_updated_at ON flash_sales;
CREATE TRIGGER update_flash_updated_at
  BEFORE UPDATE ON flash_sales
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS off (admin é gated por senha, hub usa anon mas filtra por flash ativa)
ALTER TABLE flash_sales DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_flash" ON flash_sales;
CREATE POLICY "anon_all_flash" ON flash_sales FOR ALL USING (true) WITH CHECK (true);

-- View prática: flashes ATIVAS agora (com produto join)
CREATE OR REPLACE VIEW flash_sales_ativas AS
SELECT
  f.*,
  p.nome     AS produto_nome,
  p.foto_url AS produto_foto,
  p.categoria,
  EXTRACT(EPOCH FROM (f.fim_at - NOW()))::int AS segundos_restantes,
  EXTRACT(EPOCH FROM (NOW() - f.inicio_at))::int AS segundos_decorridos
FROM flash_sales f
JOIN produtos p ON p.sku = f.sku
WHERE f.ativo = TRUE
  AND NOW() BETWEEN f.inicio_at AND f.fim_at;

-- Confirmação
SELECT
  'flash_sales criada'  AS info,
  (SELECT COUNT(*) FROM flash_sales) AS rows;
