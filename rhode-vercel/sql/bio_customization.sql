-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode Bio — Customização (aparência da página + styles per-block)
-- Delta migration. Roda uma vez no Supabase SQL Editor.
-- Depende de: bio_rhode.sql (já rodado)
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. rhode_bio_config: config singleton da página ────────────────────────
CREATE TABLE IF NOT EXISTS rhode_bio_config (
  id             INT PRIMARY KEY DEFAULT 1,
  page_bg        TEXT DEFAULT '#0A0A0A',           -- cor primária de fundo
  page_bg_type   TEXT DEFAULT 'solid',              -- 'solid' | 'gradient'
  page_bg_2      TEXT,                              -- segundo stop pra gradient
  page_bg_angle  INT DEFAULT 180,                   -- ângulo do gradient
  accent_color   TEXT DEFAULT '#F2D413',            -- Rhode Amarelo por default
  text_color     TEXT DEFAULT '#FFFFFF',
  tagline        TEXT DEFAULT 'Denim brasileiro · Fábrica própria',
  card_bg        TEXT,                              -- cor default dos blocos (null=translucent)
  card_border    TEXT,                              -- cor da borda default dos blocos
  logo_style     TEXT DEFAULT 'default',            -- pra expansão futura
  meta           JSONB,                              -- pra extensões futuras
  updated_at     TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT single_row CHECK (id = 1),
  CONSTRAINT bg_type_valid CHECK (page_bg_type IN ('solid','gradient'))
);

INSERT INTO rhode_bio_config (id) VALUES (1) ON CONFLICT DO NOTHING;

-- RLS: anon SELECT, service_role escreve
ALTER TABLE rhode_bio_config ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_config" ON rhode_bio_config;
CREATE POLICY "anon_read_config" ON rhode_bio_config
  FOR SELECT TO anon USING (true);

-- updated_at trigger
DROP TRIGGER IF EXISTS trg_rhode_bio_config_updated ON rhode_bio_config;
CREATE TRIGGER trg_rhode_bio_config_updated
  BEFORE UPDATE ON rhode_bio_config
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ── 2. Recriar view efetivos incluindo meta ────────────────────────────────
-- (CREATE OR REPLACE não muda estrutura de colunas — precisa DROP + CREATE)
DROP VIEW IF EXISTS rhode_links_efetivos;
CREATE VIEW rhode_links_efetivos AS
SELECT
  id, ordem, titulo, subtitulo, url, icone, destaque, meta,
  starts_at, ends_at
FROM rhode_links
WHERE ativo = true
  AND (starts_at IS NULL OR starts_at <= NOW())
  AND (ends_at   IS NULL OR ends_at   >= NOW())
ORDER BY destaque DESC, ordem ASC, id ASC;


-- ── 3. Confirmação ─────────────────────────────────────────────────────────
SELECT
  (SELECT COUNT(*) FROM rhode_bio_config)                AS config_rows,
  (SELECT page_bg FROM rhode_bio_config WHERE id=1)      AS bg_atual,
  (SELECT accent_color FROM rhode_bio_config WHERE id=1) AS accent_atual,
  (SELECT COUNT(*) FROM rhode_links_efetivos)            AS blocks_visiveis;
