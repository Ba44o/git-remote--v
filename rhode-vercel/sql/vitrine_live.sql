-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Vitrine /live (QR físico → TikTok live)
-- Arquivo: rhode-vercel/sql/vitrine_live.sql
-- Rodar uma única vez no Supabase SQL Editor.
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 0. hub_eventos extensions (ip_hash usado pelo /api/track) ────────────
ALTER TABLE hub_eventos ADD COLUMN IF NOT EXISTS ip_hash TEXT;

-- ── 1. live_schedule ────────────────────────────────────────────────────────
-- Agenda de lives por creator. Determina o estado de /live/:creator.
-- status: 'scheduled' (futura), 'live' (rolando agora), 'ended' (encerrada), 'cancelled'
-- actual_start: preenchido quando creator confirma entrada (substitui scheduled_start na decisão)
-- tiktok_room_url: link específico da sala (override de affiliate_link na redirect URL)
-- replay_url: preenchido após o live terminar, habilita link de replay no estado BETWEEN

CREATE TABLE IF NOT EXISTS live_schedule (
  id               BIGSERIAL PRIMARY KEY,
  creator_handle   TEXT NOT NULL,                  -- UPPERCASE, sem @ (ex: 'TACIANE')
  scheduled_start  TIMESTAMPTZ NOT NULL,
  scheduled_end    TIMESTAMPTZ NOT NULL,
  actual_start     TIMESTAMPTZ,                     -- override real quando admin/cron marca status='live'
  status           TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled','live','ended','cancelled')),
  tiktok_room_url  TEXT,                            -- link da sala TikTok (preenchido pelo admin ao iniciar)
  replay_url       TEXT,                            -- preenchido após ended
  replay_status    TEXT DEFAULT 'unknown' CHECK (replay_status IN ('unknown','valid','broken')),
  titulo           TEXT,
  notes            TEXT,
  created_at       TIMESTAMPTZ DEFAULT NOW(),
  updated_at       TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT scheduled_end_after_start CHECK (scheduled_end > scheduled_start)
);

CREATE INDEX IF NOT EXISTS idx_live_schedule_creator      ON live_schedule(creator_handle);
CREATE INDEX IF NOT EXISTS idx_live_schedule_window       ON live_schedule(creator_handle, scheduled_start, scheduled_end);
CREATE INDEX IF NOT EXISTS idx_live_schedule_status       ON live_schedule(status);
CREATE INDEX IF NOT EXISTS idx_live_schedule_active       ON live_schedule(creator_handle, status) WHERE status IN ('scheduled','live');

-- live_schedule: leitura anon OK (sem PII). RLS habilitada por boa prática.
ALTER TABLE live_schedule ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_read_live_schedule" ON live_schedule;
CREATE POLICY "anon_read_live_schedule" ON live_schedule FOR SELECT USING (true);
-- INSERT/UPDATE/DELETE só service_role (admin via /api/*)

-- VIEW pra admin debugar em BRT (resolve confusão de timezone)
CREATE OR REPLACE VIEW live_schedule_brt AS
SELECT
  id,
  creator_handle,
  scheduled_start AT TIME ZONE 'America/Sao_Paulo' AS start_brt,
  scheduled_end   AT TIME ZONE 'America/Sao_Paulo' AS end_brt,
  actual_start    AT TIME ZONE 'America/Sao_Paulo' AS actual_start_brt,
  status, tiktok_room_url, replay_url, titulo
FROM live_schedule
ORDER BY scheduled_start DESC;


-- ── 2. vitrine_optins ──────────────────────────────────────────────────────
-- Captura WhatsApp opt-in no estado BETWEEN_LIVES.
-- Idempotente por (creator_handle, phone) via UPSERT.
-- RLS HABILITADA com policies granulares: anon só INSERT (LGPD/PII).

CREATE TABLE IF NOT EXISTS vitrine_optins (
  id                      BIGSERIAL PRIMARY KEY,
  creator_handle          TEXT NOT NULL,
  phone                   TEXT NOT NULL,           -- normalizado 55XXXXXXXXXXX
  phone_hash              TEXT GENERATED ALWAYS AS (substring(encode(digest(phone, 'sha256'), 'hex') from 1 for 16)) STORED,
  session_id              TEXT,
  next_live_id            BIGINT REFERENCES live_schedule(id) ON DELETE SET NULL,
  coupon                  TEXT DEFAULT 'VITRINE10',
  consent_text_version    TEXT DEFAULT 'v1-2026-06',
  last_confirmation_at    TIMESTAMPTZ,             -- antifloodig de mensagem Z-API
  opted_out_at            TIMESTAMPTZ,             -- LGPD: timestamp do opt-out (PARAR)
  meta                    JSONB,
  created_at              TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (creator_handle, phone)
);

-- Extension pra digest()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE INDEX IF NOT EXISTS idx_vitrine_optins_creator ON vitrine_optins(creator_handle);
CREATE INDEX IF NOT EXISTS idx_vitrine_optins_created ON vitrine_optins(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vitrine_optins_phone   ON vitrine_optins(phone);

-- RLS HABILITADA: anon só INSERT, leitura via service_role
ALTER TABLE vitrine_optins ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_insert_vitrine_optins" ON vitrine_optins;
CREATE POLICY "anon_insert_vitrine_optins" ON vitrine_optins
  FOR INSERT TO anon
  WITH CHECK (
    phone ~ '^55[0-9]{10,11}$'           -- valida formato BR
    AND length(creator_handle) BETWEEN 2 AND 40
    AND creator_handle ~ '^[A-Z0-9_.-]+$'
  );
-- SELECT/UPDATE/DELETE: APENAS service_role (negação implícita pra anon)

-- Authenticated role (futuro: admin via Supabase Auth) pode ler
DROP POLICY IF EXISTS "auth_read_vitrine_optins" ON vitrine_optins;
CREATE POLICY "auth_read_vitrine_optins" ON vitrine_optins FOR SELECT TO authenticated USING (true);


-- ── 3. (REUSO) hub_eventos para tracking ─────────────────────────────────────
-- Convenção:
--   aba = 'vitrine'
--   evento IN ('qr_scanned','tiktok_redirected','optin_shown','optin_submitted','action')
--   meta = { coupon, handle, state, utm_source, utm_campaign, url?, tipo?, phone_hash?, next_start?, scan_source, is_likely_bot? }
-- NÃO modificar RLS de hub_eventos aqui — assumir já configurado no projeto.


-- ── 4. Views de agregação para o admin ─────────────────────────────────────

-- Scans por dia × creator (últimos 30d) — exclui bots
CREATE OR REPLACE VIEW vitrine_scans_diario AS
SELECT
  DATE(created_at AT TIME ZONE 'America/Sao_Paulo')  AS dia,
  affiliate_id                                        AS creator,
  COUNT(*)                                            AS scans,
  COUNT(DISTINCT session_id)                          AS sessoes_unicas,
  COUNT(*) FILTER (WHERE meta->>'state' = 'live_now')       AS scans_live_now,
  COUNT(*) FILTER (WHERE meta->>'state' = 'between_lives')  AS scans_between,
  COUNT(*) FILTER (WHERE meta->>'state' = 'no_schedule')    AS scans_no_sched,
  COUNT(*) FILTER (WHERE meta->>'scan_source' = 'qr')       AS scans_qr_fisico
FROM hub_eventos
WHERE aba = 'vitrine'
  AND evento = 'qr_scanned'
  AND (meta->>'is_likely_bot' IS NULL OR meta->>'is_likely_bot' = 'false')
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY 1, 2
ORDER BY 1 DESC, 3 DESC;

-- Funil: scan_live_now → tiktok_redirected (proxy de conversão p/ live)
-- NOTA: denominador conta APENAS scans onde meta.state='live_now' (humanos, scan_source=qr).
-- Limitação: sendBeacon perdido em iOS muito antigo (~3%) pode subestimar redirects.
CREATE OR REPLACE VIEW vitrine_conversao_creator AS
WITH scans AS (
  SELECT affiliate_id AS creator, COUNT(*) AS n
  FROM hub_eventos
  WHERE aba = 'vitrine' AND evento = 'qr_scanned'
    AND meta->>'state' = 'live_now'
    AND (meta->>'is_likely_bot' IS NULL OR meta->>'is_likely_bot' = 'false')
    AND created_at >= NOW() - INTERVAL '30 days'
  GROUP BY 1
),
redirs AS (
  SELECT affiliate_id AS creator, COUNT(*) AS n
  FROM hub_eventos
  WHERE aba = 'vitrine' AND evento = 'tiktok_redirected'
    AND (meta->>'is_likely_bot' IS NULL OR meta->>'is_likely_bot' = 'false')
    AND created_at >= NOW() - INTERVAL '30 days'
  GROUP BY 1
)
SELECT
  COALESCE(s.creator, r.creator)              AS creator,
  COALESCE(s.n, 0)                             AS scans_live_now,
  COALESCE(r.n, 0)                             AS tiktok_redirects,
  CASE WHEN COALESCE(s.n,0) > 0
       THEN ROUND(100.0 * COALESCE(r.n,0) / s.n, 1)
       ELSE NULL END                           AS taxa_redirect_pct
FROM scans s FULL OUTER JOIN redirs r ON r.creator = s.creator
ORDER BY scans_live_now DESC NULLS LAST;

-- Opt-ins recentes (admin via service_role)
CREATE OR REPLACE VIEW vitrine_optins_recentes AS
SELECT
  o.created_at,
  o.creator_handle,
  o.phone,
  o.phone_hash,
  o.coupon,
  o.consent_text_version,
  ls.scheduled_start                           AS next_live_em,
  o.last_confirmation_at,
  o.opted_out_at
FROM vitrine_optins o
LEFT JOIN live_schedule ls ON ls.id = o.next_live_id
WHERE o.created_at >= NOW() - INTERVAL '60 days'
ORDER BY o.created_at DESC;


-- ── 5. Job de retenção LGPD (rodar via cron 1x/semana) ──────────────────────
-- Apaga opt-ins inativos há mais de 6 meses (LGPD: retenção mínima necessária)
-- Executar manualmente: SELECT vitrine_purge_old_optins();
CREATE OR REPLACE FUNCTION vitrine_purge_old_optins() RETURNS INT AS $$
DECLARE deleted INT;
BEGIN
  WITH del AS (
    DELETE FROM vitrine_optins
    WHERE created_at < NOW() - INTERVAL '6 months'
      AND (last_confirmation_at IS NULL OR last_confirmation_at < NOW() - INTERVAL '6 months')
    RETURNING id
  )
  SELECT COUNT(*) INTO deleted FROM del;
  RETURN deleted;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;


-- ── 6. Confirmação ──────────────────────────────────────────────────────────
SELECT
  (SELECT COUNT(*) FROM live_schedule)                                AS lives_agendadas,
  (SELECT COUNT(*) FROM vitrine_optins)                                AS optins_total,
  (SELECT COUNT(*) FROM hub_eventos WHERE aba='vitrine')               AS eventos_vitrine,
  (SELECT relrowsecurity FROM pg_class WHERE relname='vitrine_optins') AS optins_rls_enabled;