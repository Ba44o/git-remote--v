-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Upgrade Amostras v2: catálogo expandido + campanhas + lote multi-SKU
-- Rodar no Supabase SQL Editor
-- ═══════════════════════════════════════════════════════════════════════════

-- 1. Expandir catálogo de produtos
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS categoria  TEXT;
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS colecao    TEXT;
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS foto_url   TEXT;
ALTER TABLE produtos ADD COLUMN IF NOT EXISTS descricao  TEXT;

-- Categoriza Wide Legs existentes
UPDATE produtos SET categoria = 'wide_leg', colecao = 'core'
WHERE sku LIKE 'WIDE-%' AND categoria IS NULL;


-- 2. Campanhas (agrupador estratégico)
CREATE TABLE IF NOT EXISTS campanhas (
  id                BIGSERIAL PRIMARY KEY,
  nome              TEXT NOT NULL,
  briefing_creator  TEXT,                                       -- aparece no hub das creators
  meta              TEXT,                                       -- ex: "lançamento Mom Jeans · Dia das Mães"
  data_inicio       DATE DEFAULT CURRENT_DATE,
  data_fim_envio    DATE,
  prazo_video       DATE,
  status            TEXT DEFAULT 'ativa' CHECK (status IN ('ativa','concluida','cancelada')),
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

DROP TRIGGER IF EXISTS update_campanhas_updated_at ON campanhas;
CREATE TRIGGER update_campanhas_updated_at
  BEFORE UPDATE ON campanhas
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- 3. Expandir amostras_enviadas — vira "item de um lote"
ALTER TABLE amostras_enviadas ADD COLUMN IF NOT EXISTS lote_id            UUID;
ALTER TABLE amostras_enviadas ADD COLUMN IF NOT EXISTS campanha_id        BIGINT REFERENCES campanhas(id) ON DELETE SET NULL;
ALTER TABLE amostras_enviadas ADD COLUMN IF NOT EXISTS briefing_creator   TEXT;
ALTER TABLE amostras_enviadas ADD COLUMN IF NOT EXISTS prazo_video        DATE;
ALTER TABLE amostras_enviadas ADD COLUMN IF NOT EXISTS confirmada_em      TIMESTAMPTZ;  -- creator clicou "✓ Recebi"
ALTER TABLE amostras_enviadas ADD COLUMN IF NOT EXISTS video_url          TEXT;          -- creator anexou link
ALTER TABLE amostras_enviadas ADD COLUMN IF NOT EXISTS video_postado_em   TIMESTAMPTZ;
ALTER TABLE amostras_enviadas ADD COLUMN IF NOT EXISTS dispensada         BOOLEAN DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_amostras_lote        ON amostras_enviadas(lote_id);
CREATE INDEX IF NOT EXISTS idx_amostras_campanha    ON amostras_enviadas(campanha_id);
CREATE INDEX IF NOT EXISTS idx_amostras_confirmada  ON amostras_enviadas(confirmada_em) WHERE confirmada_em IS NULL;


-- 4. RLS para campanhas (mesmo padrão das outras)
ALTER TABLE campanhas DISABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "anon_all_campanhas" ON campanhas;
CREATE POLICY "anon_all_campanhas" ON campanhas
  FOR ALL USING (true) WITH CHECK (true);


-- 5. View consolidada — "lote" como unidade lógica (1 row = 1 envio físico)
CREATE OR REPLACE VIEW amostras_lotes AS
SELECT
  COALESCE(lote_id::text, 'avulso-' || id::text) AS lote_key,
  lote_id,
  creator_id,
  campanha_id,
  MIN(data_envio) AS data_envio,
  MIN(briefing_creator) AS briefing_creator,
  MIN(prazo_video) AS prazo_video,
  MIN(tier_no_envio) AS tier_no_envio,
  MAX(confirmada_em) AS confirmada_em,
  MAX(video_url) AS video_url,
  MAX(video_postado_em) AS video_postado_em,
  COUNT(*) AS total_itens,
  SUM(quantidade) AS total_pecas,
  ARRAY_AGG(json_build_object('sku', sku, 'qtd', quantidade) ORDER BY id) AS itens
FROM amostras_enviadas
WHERE COALESCE(dispensada, false) = false
GROUP BY lote_id, creator_id, campanha_id, id
ORDER BY data_envio DESC;


-- 6. Confirmação visual
SELECT
  'produtos com categoria' AS info,
  COUNT(*) AS qtd
FROM produtos WHERE categoria IS NOT NULL
UNION ALL
SELECT 'campanhas', COUNT(*) FROM campanhas
UNION ALL
SELECT 'amostras_enviadas (atual)', COUNT(*) FROM amostras_enviadas
UNION ALL
SELECT 'colunas novas em amostras', (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_name='amostras_enviadas'
    AND column_name IN ('lote_id','campanha_id','briefing_creator','prazo_video','confirmada_em','video_url','video_postado_em','dispensada')
);
