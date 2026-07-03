-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode Bio — Customização V2
-- - Imagem de fundo + overlay + tipografia (config global)
-- - Storage bucket 'bio-assets' pra uploads via admin
-- Depende de: bio_customization.sql (rodado)
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. Novas colunas ───────────────────────────────────────────────────────
ALTER TABLE rhode_bio_config
  ADD COLUMN IF NOT EXISTS page_bg_image   TEXT,
  ADD COLUMN IF NOT EXISTS page_bg_overlay TEXT DEFAULT 'rgba(10,10,10,0.55)',
  ADD COLUMN IF NOT EXISTS font_heading    TEXT DEFAULT 'Montserrat',
  ADD COLUMN IF NOT EXISTS font_body       TEXT DEFAULT 'DM Sans';

-- Estende constraint pra aceitar 'image'
ALTER TABLE rhode_bio_config DROP CONSTRAINT IF EXISTS bg_type_valid;
ALTER TABLE rhode_bio_config
  ADD CONSTRAINT bg_type_valid CHECK (page_bg_type IN ('solid','gradient','image'));


-- ── 2. Storage bucket 'bio-assets' (público pra leitura) ───────────────────
INSERT INTO storage.buckets (id, name, public)
  VALUES ('bio-assets', 'bio-assets', true)
  ON CONFLICT (id) DO UPDATE SET public = EXCLUDED.public;

-- Policies: anon lê (bucket é public de qualquer jeito, mas explicito), service_role escreve
DROP POLICY IF EXISTS "bio_assets_public_read" ON storage.objects;
CREATE POLICY "bio_assets_public_read" ON storage.objects
  FOR SELECT TO anon USING (bucket_id = 'bio-assets');


-- ── 3. Confirmação ─────────────────────────────────────────────────────────
SELECT
  (SELECT column_name FROM information_schema.columns
    WHERE table_name='rhode_bio_config' AND column_name='page_bg_image' LIMIT 1)  AS col_image,
  (SELECT column_name FROM information_schema.columns
    WHERE table_name='rhode_bio_config' AND column_name='font_heading' LIMIT 1)   AS col_font,
  (SELECT id FROM storage.buckets WHERE id='bio-assets')                          AS bucket_id,
  (SELECT public FROM storage.buckets WHERE id='bio-assets')                      AS bucket_pub;
