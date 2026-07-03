-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Bio Link Oficial (bio.rhodejeans.com.br)
-- Arquivo: rhode-vercel/sql/bio_rhode.sql
-- Rodar uma única vez no Supabase SQL Editor.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. rhode_links ─────────────────────────────────────────────────────────
-- Blocos da bio da marca Rhode. Editado só pelo admin da Rhode.
-- Página pública lê via anon (RLS permite SELECT quando ativo=true).
-- starts_at/ends_at controlam janela temporal (campanhas com auto-hide).
-- destaque=true puxa o bloco pro topo em Rhode Red (bloco fixado/campanha ativa).

CREATE TABLE IF NOT EXISTS rhode_links (
  id            BIGSERIAL PRIMARY KEY,
  ordem         INT NOT NULL DEFAULT 100,
  titulo        TEXT NOT NULL,
  subtitulo     TEXT,
  url           TEXT NOT NULL,
  icone         TEXT,                              -- emoji (ex: '🛍') ou nome de svg (ex: 'shop')
  ativo         BOOLEAN NOT NULL DEFAULT true,
  destaque      BOOLEAN NOT NULL DEFAULT false,    -- se true, aparece no topo em Rhode Red
  starts_at     TIMESTAMPTZ,                        -- NULL = sempre visível a partir de agora
  ends_at       TIMESTAMPTZ,                        -- NULL = sem expiração
  meta          JSONB,                              -- pra extensões futuras (utm, badge, cor custom)
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT ends_after_starts CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at > starts_at),
  CONSTRAINT url_http CHECK (url ~ '^https?://')
);

CREATE INDEX IF NOT EXISTS idx_rhode_links_ativo_ordem ON rhode_links(ativo, destaque DESC, ordem ASC);
CREATE INDEX IF NOT EXISTS idx_rhode_links_window     ON rhode_links(starts_at, ends_at) WHERE ativo = true;

-- updated_at trigger (reusa função update_updated_at_column se já existe no projeto)
DROP TRIGGER IF EXISTS trg_rhode_links_updated ON rhode_links;
CREATE TRIGGER trg_rhode_links_updated
  BEFORE UPDATE ON rhode_links
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS: anon SELECT-only nos ativos; INSERT/UPDATE/DELETE só service_role
ALTER TABLE rhode_links ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_active_rhode_links" ON rhode_links;
CREATE POLICY "anon_read_active_rhode_links" ON rhode_links
  FOR SELECT TO anon
  USING (ativo = true);
-- SELECT/INSERT/UPDATE/DELETE completo pra service_role (default sem RLS block)
DROP POLICY IF EXISTS "auth_all_rhode_links" ON rhode_links;
CREATE POLICY "auth_all_rhode_links" ON rhode_links FOR ALL TO authenticated USING (true) WITH CHECK (true);


-- ── 2. View pública "efetiva" ──────────────────────────────────────────────
-- Filtra ativo=true + janela temporal + ordena. A página consome direto.
CREATE OR REPLACE VIEW rhode_links_efetivos AS
SELECT
  id, ordem, titulo, subtitulo, url, icone, destaque, starts_at, ends_at
FROM rhode_links
WHERE ativo = true
  AND (starts_at IS NULL OR starts_at <= NOW())
  AND (ends_at   IS NULL OR ends_at   >= NOW())
ORDER BY destaque DESC, ordem ASC, id ASC;


-- ── 3. Analytics view (clicks por link, 30 dias) ───────────────────────────
CREATE OR REPLACE VIEW rhode_links_stats AS
SELECT
  (meta->>'link_id')::BIGINT                          AS link_id,
  meta->>'titulo'                                     AS titulo_no_clique,
  COUNT(*)                                            AS clicks,
  COUNT(DISTINCT session_id)                          AS clicks_unicos,
  MAX(created_at)                                     AS ultimo_clique,
  MIN(created_at)                                     AS primeiro_clique
FROM hub_eventos
WHERE aba = 'bio_rhode'
  AND evento = 'link_click'
  AND created_at >= NOW() - INTERVAL '30 days'
  AND (meta->>'is_likely_bot' IS NULL OR meta->>'is_likely_bot' = 'false')
GROUP BY 1, 2
ORDER BY clicks DESC;

-- View "views" da página (bio_view) — quantas pessoas viram
CREATE OR REPLACE VIEW rhode_bio_views_diario AS
SELECT
  DATE(created_at AT TIME ZONE 'America/Sao_Paulo')   AS dia,
  COUNT(*)                                            AS views,
  COUNT(DISTINCT session_id)                          AS sessoes_unicas,
  COUNT(*) FILTER (WHERE meta->>'referrer_host' = 'instagram.com')  AS from_ig,
  COUNT(*) FILTER (WHERE meta->>'referrer_host' = 'tiktok.com')     AS from_tt
FROM hub_eventos
WHERE aba = 'bio_rhode'
  AND evento = 'page_view'
  AND created_at >= NOW() - INTERVAL '30 days'
  AND (meta->>'is_likely_bot' IS NULL OR meta->>'is_likely_bot' = 'false')
GROUP BY 1
ORDER BY 1 DESC;


-- ── 4. Seed inicial (bloco mínimo pra página não nascer vazia) ─────────────
INSERT INTO rhode_links (ordem, titulo, subtitulo, url, icone, destaque, ativo)
VALUES
  (10, 'Loja oficial no TikTok Shop', 'Wide Leg, Baggy, Mom · frete pro Brasil todo', 'https://www.tiktok.com/shop/store/rhodejeans', '🛍', false, true),
  (20, 'Vem ser afiliada Rhode', 'Comissão de 8-12% + benefícios por tier', 'https://creators.rhodejeans.com.br/parceria', '💛', false, true),
  (30, 'Instagram @rhodejeans', 'Ver últimos posts', 'https://instagram.com/rhodejeans', '📸', false, true),
  (40, 'Fale conosco no WhatsApp', 'Tire dúvidas de pedido, tamanho, troca', 'https://wa.me/5511999999999', '💬', false, true)
ON CONFLICT DO NOTHING;


-- ── 5. Confirmação ─────────────────────────────────────────────────────────
SELECT
  (SELECT COUNT(*) FROM rhode_links)                     AS links_total,
  (SELECT COUNT(*) FROM rhode_links WHERE ativo = true)  AS links_ativos,
  (SELECT COUNT(*) FROM rhode_links_efetivos)            AS visiveis_agora,
  (SELECT relrowsecurity FROM pg_class WHERE relname='rhode_links') AS rls_enabled;
