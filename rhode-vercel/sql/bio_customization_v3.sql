-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode Bio — V3: Hero dinâmico + seções + WhatsApp pré-preenchido
-- Depende de: bio_customization_v2.sql
-- Roda uma vez no Supabase SQL Editor.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. Hero (card grande de topo, com toggle live) ─────────────────────────
CREATE TABLE IF NOT EXISTS rhode_bio_hero (
  id           INT PRIMARY KEY DEFAULT 1,
  ativo        BOOLEAN NOT NULL DEFAULT true,
  kicker       TEXT DEFAULT 'Agora na Rhode',
  titulo       TEXT DEFAULT 'Wide Leg Marmorizada de volta',
  descricao    TEXT DEFAULT 'A queridinha voltou pro estoque — e vai rápido.',
  cta          TEXT DEFAULT 'Ver na lojinha →',
  url          TEXT,
  bg           TEXT DEFAULT '#3C444C',            -- slate por default (paleta warm)
  color        TEXT DEFAULT '#F6F0EA',            -- cream
  live_mode    BOOLEAN NOT NULL DEFAULT false,
  live_kicker  TEXT DEFAULT 'AO VIVO AGORA',
  live_titulo  TEXT DEFAULT 'A live tá rolando!',
  live_desc    TEXT DEFAULT 'Cupom e condição especial só pra quem tá dentro.',
  live_cta     TEXT DEFAULT 'Entrar na live →',
  live_url     TEXT DEFAULT 'https://www.tiktok.com/@rhodejeans/live',
  updated_at   TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT single_hero CHECK (id = 1)
);

INSERT INTO rhode_bio_hero (id) VALUES (1) ON CONFLICT DO NOTHING;

ALTER TABLE rhode_bio_hero ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_hero" ON rhode_bio_hero;
CREATE POLICY "anon_read_hero" ON rhode_bio_hero
  FOR SELECT TO anon USING (ativo = true);

DROP TRIGGER IF EXISTS trg_rhode_bio_hero_updated ON rhode_bio_hero;
CREATE TRIGGER trg_rhode_bio_hero_updated
  BEFORE UPDATE ON rhode_bio_hero
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- ── 2. Novos campos no rhode_links ─────────────────────────────────────────
ALTER TABLE rhode_links
  ADD COLUMN IF NOT EXISTS secao   TEXT,       -- label do divisor de seção (ex: "Comprar", "Pra você que cria")
  ADD COLUMN IF NOT EXISTS wa_msg  TEXT;       -- mensagem pré-preenchida (se URL é wa.me)


-- ── 3. Recria view efetivos incluindo secao + wa_msg ───────────────────────
DROP VIEW IF EXISTS rhode_links_efetivos;
CREATE VIEW rhode_links_efetivos AS
SELECT
  id, ordem, titulo, subtitulo, url, icone, destaque, meta,
  secao, wa_msg,
  starts_at, ends_at
FROM rhode_links
WHERE ativo = true
  AND (starts_at IS NULL OR starts_at <= NOW())
  AND (ends_at   IS NULL OR ends_at   >= NOW())
ORDER BY destaque DESC, ordem ASC, id ASC;


-- ── 4. Confirmação ─────────────────────────────────────────────────────────
SELECT
  (SELECT COUNT(*) FROM rhode_bio_hero)                              AS hero_rows,
  (SELECT column_name FROM information_schema.columns
    WHERE table_name='rhode_links' AND column_name='secao'  LIMIT 1) AS col_secao,
  (SELECT column_name FROM information_schema.columns
    WHERE table_name='rhode_links' AND column_name='wa_msg' LIMIT 1) AS col_wa_msg;
