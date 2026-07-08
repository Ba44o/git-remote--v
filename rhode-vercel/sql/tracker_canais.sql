-- =============================================================
-- Rhode — Tracker da meta de 10 mil peças/mês por canal (painel interno dash-live).
-- Modelo origem × conteúdo, dedup por cascata (cada peça 1 dono). Populado por
-- tracker_canais.py. Lido pelo painel via proxy dashlive which=tracker.
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE TABLE IF NOT EXISTS tracker_canais (
  id          text PRIMARY KEY,   -- "{mes}:{canal}"  (canal='net' = loja total)
  mes         text,
  canal       text,               -- live_propria | live_afiliada | video_afiliada | organico | net
  pecas       integer DEFAULT 0,  -- realizado (peças)
  meta_pecas  integer DEFAULT 0,
  semanas     jsonb,              -- {"1":n,"2":n,...} peças por semana do mês
  updated_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tracker_canais_mes ON tracker_canais(mes);
ALTER TABLE tracker_canais ENABLE ROW LEVEL SECURITY;
SELECT 'tracker_canais criada' AS ok;
