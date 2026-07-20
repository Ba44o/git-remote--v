-- =============================================================
-- Rhode — Radar de conteúdo por VÍDEO × CREATOR (performance, admin.html).
-- Fonte: Shop Partner API GET /analytics/202409/shop_videos/performance (métricas LIFETIME por vídeo).
-- Populado por coletar_shop_videos.py (ROOT, cron). NÃO é dado financeiro → não entra no conciliacao.html.
-- Objetivo: enxergar creator que POSTA e ainda NÃO vende (hoje o sistema só rastreia quem vende).
--   Radar de POTENCIAL = alcance sem conversão + esforço consistente + frequência de vídeos.
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE TABLE IF NOT EXISTS video_perf (
  id          text PRIMARY KEY,                 -- video id (TikTok)
  username    text NOT NULL,                     -- creator handle (minúsculo)
  title       text,
  post_time   timestamptz,                       -- video_post_time (quando foi postado)
  views       bigint  NOT NULL DEFAULT 0,        -- lifetime
  ctr         numeric(7,4),                      -- click_through_rate (0..1)
  gmv         numeric(12,2) NOT NULL DEFAULT 0,  -- lifetime, BRL
  sku_orders  int NOT NULL DEFAULT 0,            -- pedidos atribuídos ao vídeo
  units_sold  int NOT NULL DEFAULT 0,
  produtos    text,                              -- nomes de produto (csv, informativo)
  updated_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_vperf_user ON video_perf(username);
CREATE INDEX IF NOT EXISTS idx_vperf_time ON video_perf(post_time);
CREATE INDEX IF NOT EXISTS idx_vperf_ord  ON video_perf(sku_orders);
ALTER TABLE video_perf ENABLE ROW LEVEL SECURITY;   -- deny-anon; só service_role / proxy admin

-- ---- agregado por creator: as 3 réguas do dono viram colunas ----
--   alcance = views_total · sem conversão = orders_total/gmv_total · consistência = semanas_ativas
--   frequência = videos_por_semana (TAXA, não volume). dias_desde_ultimo = frescor (ainda posta?).
CREATE OR REPLACE VIEW creator_radar AS
SELECT
  username                                          AS creator,
  count(*)                                          AS n_videos,
  count(DISTINCT date_trunc('week', post_time))     AS semanas_ativas,
  min(post_time)::date                              AS primeiro_video,
  max(post_time)::date                              AS ultimo_video,
  (current_date - max(post_time)::date)             AS dias_desde_ultimo,
  sum(views)                                        AS views_total,
  round(avg(views))                                 AS views_por_video,
  round(sum(gmv)::numeric, 2)                        AS gmv_total,
  sum(sku_orders)                                   AS orders_total,
  round(sum(sku_orders)::numeric / nullif(sum(views),0) * 100, 4) AS conv_pct,
  round(count(*)::numeric
        / nullif(count(DISTINCT date_trunc('week', post_time)),0), 2) AS videos_por_semana
FROM video_perf
GROUP BY username;

-- score de POTENCIAL (transparente, tunável): cadência sustentada > pico > alcance.
--   semanas_ativas domina (esforço consistente); frequência entra como TAXA limitada a 5/sem
--   (rajada não fura a fila); alcance soma linear. Burst 48-vids/2-sem NÃO ranqueia alto.
--     score = semanas_ativas*12 + LEAST(videos_por_semana, 5)*4 + views_total/1000
CREATE OR REPLACE VIEW creator_radar_scored AS
SELECT r.*,
  round(semanas_ativas*12 + LEAST(videos_por_semana, 5)*4 + views_total/1000.0)::int AS score
FROM creator_radar r;

-- LISTA 1 — POTENCIAL ATIVO: alcance sem conversão, consistente E ainda postando (≤30d). Prospectar.
CREATE OR REPLACE VIEW creator_potencial_ativo AS
SELECT * FROM creator_radar_scored
WHERE orders_total = 0 AND views_total >= 500 AND dias_desde_ultimo <= 30
ORDER BY score DESC;

-- LISTA 2 — ESFRIARAM: foram consistentes (3+ semanas), tinham alcance, e pararam (>30d). Reativar.
CREATE OR REPLACE VIEW creator_esfriou AS
SELECT * FROM creator_radar_scored
WHERE orders_total = 0 AND views_total >= 500 AND dias_desde_ultimo > 30 AND semanas_ativas >= 3
ORDER BY score DESC;

SELECT 'video_perf + creator_radar + creator_potencial_ativo + creator_esfriou criadas' AS ok;
