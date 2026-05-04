-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Tabelas de Amostras
-- Rodar no Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- ═══════════════════════════════════════════════════════════════════════════

-- 1. Catálogo de produtos (SKUs picáveis no form)
CREATE TABLE IF NOT EXISTS produtos (
  sku            TEXT PRIMARY KEY,
  nome           TEXT NOT NULL,
  preco_venda    NUMERIC(10,2),
  custo_unitario NUMERIC(10,2),                 -- custo da peça (entra no cálculo de gasto em amostras)
  ativo          BOOLEAN DEFAULT TRUE,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Pré-popula com a linha atual (atualize custo_unitario depois quando souber)
INSERT INTO produtos (sku, nome, preco_venda, custo_unitario) VALUES
  ('WIDE-MARM',    'Wide Leg Marmorizada',         99.90, NULL),
  ('WIDE-ROSA',    'Wide Leg Rosa Bebê',           89.90, NULL),
  ('WIDE-AZUL',    'Wide Leg Azul Médio',          89.90, NULL),
  ('WIDE-PRETA',   'Wide Leg Preta',               89.90, NULL),
  ('WIDE-BRANCA',  'Wide Leg Branca',              89.90, NULL),
  ('WIDE-CHOCO',   'Wide Leg Chocolate',           89.90, NULL),
  ('WIDE-AMAMNTG', 'Wide Leg Amarelo Manteiga',    89.90, NULL),
  ('WIDE-STONE',   'Wide Leg Stone Used',          89.90, NULL),
  ('WIDE-SKY',     'Wide Leg Sky Used',            89.90, NULL),
  ('WIDE-PRMARM',  'Wide Leg Preta Marmorizada',   99.90, NULL)
ON CONFLICT (sku) DO NOTHING;


-- 2. Amostras enviadas (1 linha = 1 envio)
CREATE TABLE IF NOT EXISTS amostras_enviadas (
  id                       BIGSERIAL PRIMARY KEY,
  creator_id               TEXT NOT NULL,                          -- normalizado UPPERCASE (bate com affiliates.affiliate_id)
  sku                      TEXT NOT NULL REFERENCES produtos(sku) ON UPDATE CASCADE,
  quantidade               INT NOT NULL DEFAULT 1 CHECK (quantidade > 0),
  custo_unitario_snapshot  NUMERIC(10,2),                          -- congela o custo no momento do envio (se mudar depois, histórico não muda)
  data_envio               DATE NOT NULL DEFAULT CURRENT_DATE,
  data_recebimento         DATE,                                   -- preenchido manualmente quando creator confirma
  origem                   TEXT NOT NULL DEFAULT 'manual'
    CHECK (origem IN ('manual','tiktok_import','evento','solicitacao_creator')),
  tier_no_envio            TEXT,                                   -- snapshot do tier no momento do envio
  obs                      TEXT,
  created_at               TIMESTAMPTZ DEFAULT NOW(),
  updated_at               TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_amostras_creator    ON amostras_enviadas(creator_id);
CREATE INDEX IF NOT EXISTS idx_amostras_data_envio ON amostras_enviadas(data_envio DESC);
CREATE INDEX IF NOT EXISTS idx_amostras_sku        ON amostras_enviadas(sku);
CREATE INDEX IF NOT EXISTS idx_amostras_origem     ON amostras_enviadas(origem);


-- 3. Trigger pra atualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_amostras_updated_at ON amostras_enviadas;
CREATE TRIGGER update_amostras_updated_at
  BEFORE UPDATE ON amostras_enviadas
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- 4. View de ROI por SKU (creators com amostra vs sem amostra)
CREATE OR REPLACE VIEW amostra_roi_por_sku AS
WITH creators_com_amostra AS (
  SELECT DISTINCT a.sku, a.creator_id
  FROM amostras_enviadas a
  WHERE a.data_envio IS NOT NULL
),
gmv_proximo_periodo AS (
  -- Para cada amostra enviada, busca o GMV do creator no período seguinte ao envio
  SELECT
    a.sku,
    a.creator_id,
    a.data_envio,
    pp.gmv_liquido AS gmv_pos_amostra
  FROM amostras_enviadas a
  LEFT JOIN performance_periods pp
    ON pp.affiliate_id = a.creator_id
   AND pp.periodo_inicio > a.data_envio
   AND pp.periodo_inicio <= a.data_envio + INTERVAL '60 days'
)
SELECT
  sku,
  COUNT(DISTINCT creator_id) AS creators_com_amostra,
  ROUND(AVG(COALESCE(gmv_pos_amostra, 0))::numeric, 2) AS gmv_medio_pos_amostra,
  ROUND(SUM(COALESCE(gmv_pos_amostra, 0))::numeric, 2) AS gmv_total_pos_amostra
FROM gmv_proximo_periodo
GROUP BY sku
ORDER BY gmv_total_pos_amostra DESC NULLS LAST;
