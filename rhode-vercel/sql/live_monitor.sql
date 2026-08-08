-- =============================================================
-- Rhode — DashLive Monitor: o lado OPERACIONAL da live (o "durante").
--
-- As tabelas de live que já existiam só guardam o desfecho, e todas vêm de fora:
--   live_attr    → GMV atribuído por sala (export do Seller Center)  ← headline
--   live_sessao  → custo/receita de GMV Max por sala (Business API)
--   lives        → funil consolidado que alimenta o dash-live
-- Nenhuma delas sabe o que ACONTECEU durante a transmissão: em que minuto o funil
-- caiu, qual framework o operador acionou, se houve violação de compliance.
-- É isso que a extensão captura e o que estas duas tabelas passam a guardar.
--
-- Escrita: extensão Chrome → /api/get-hub (action=live_monitor) → service_role.
-- A extensão NUNCA fala com o PostgREST direto (mesmo contrato do resto do projeto).
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================

-- ── Uma linha por live monitorada ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS live_monitor_sessao (
  id            text PRIMARY KEY,       -- "mon:{inicio ISO}" — determinístico: reenviar atualiza, não duplica
  room_id       text,                   -- preenchido depois, pra casar com live_attr.room_id
  titulo        text,
  inicio        timestamptz,
  fim           timestamptz,
  data          date,
  periodo       text,                   -- YYYY-MM
  duracao_h     numeric,
  meta          numeric,                -- meta de GMV definida no popup
  gmv_final     numeric DEFAULT 0,      -- último GMV lido na tela
  pct_meta      numeric,
  pedidos       integer DEFAULT 0,
  ticket_medio  numeric,
  err_medio     numeric,
  ctr_medio     numeric,
  co_medio      numeric,                -- compra após clique (medido, = lives.ctor)
  conv_visualizacao_media numeric,      -- DERIVADO ctr×co — nunca lido direto
  views_pico    integer,
  ctr_perfil    text,                   -- 'views' | 'impressoes': qual régua de CTR valeu (R11)
  bench_janela  text,                   -- janela dos benchmarks usados no julgamento
  bench_gerado_em timestamptz,
  frameworks    jsonb DEFAULT '[]'::jsonb,
  violacoes     jsonb DEFAULT '[]'::jsonb,
  snapshots_n   integer DEFAULT 0,
  origem        text DEFAULT 'dashlive-ext',
  versao        text,
  updated_at    timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_lms_periodo ON live_monitor_sessao(periodo);
CREATE INDEX IF NOT EXISTS idx_lms_data    ON live_monitor_sessao(data);
CREATE INDEX IF NOT EXISTS idx_lms_room    ON live_monitor_sessao(room_id);
ALTER TABLE live_monitor_sessao ENABLE ROW LEVEL SECURITY;

-- ── Série temporal dentro da live (1 a cada 15min + manuais) ───────────────
CREATE TABLE IF NOT EXISTS live_monitor_snapshot (
  id          text PRIMARY KEY,         -- "{sessao_id}:{epoch_ms}"
  sessao_id   text REFERENCES live_monitor_sessao(id) ON DELETE CASCADE,
  t           timestamptz,
  minuto      integer,                  -- minutos desde o início (curva sem depender de fuso)
  err         numeric,
  impressions bigint,
  clicks      integer,
  views       integer,
  ctr         numeric,
  co          numeric,
  gmv         numeric,
  orders      integer,
  comments    integer,
  ctr_perfil  text
);
CREATE INDEX IF NOT EXISTS idx_lmsnap_sessao ON live_monitor_snapshot(sessao_id, t);
ALTER TABLE live_monitor_snapshot ENABLE ROW LEVEL SECURITY;

-- ── Conferência: o que a extensão leu na tela × o que o Seller Center atribuiu ──
-- É o teste permanente do parser. Divergência grande = leitura errada (calibração
-- apontando pro número errado) ou live casada com a sala errada — não "o dado mudou".
CREATE OR REPLACE VIEW live_monitor_vs_oficial AS
SELECT m.id, m.data, m.periodo, m.titulo,
       m.gmv_final           AS gmv_lido,
       a.gmv                 AS gmv_oficial,
       round(m.gmv_final - COALESCE(a.gmv,0), 2)                              AS dif_abs,
       round(100 * (m.gmv_final - a.gmv) / NULLIF(a.gmv,0), 2)                AS dif_pct,
       m.pedidos             AS pedidos_lidos,
       a.pedidos             AS pedidos_oficiais,
       m.ctr_perfil, m.snapshots_n
FROM live_monitor_sessao m
LEFT JOIN live_attr a
  ON (m.room_id IS NOT NULL AND a.room_id = m.room_id)
  -- sem room_id, casa pela sala do mesmo dia cujo início é o mais próximo do da monitoria
  OR (m.room_id IS NULL AND a.data = m.data
      AND a.inicio = (SELECT a2.inicio FROM live_attr a2 WHERE a2.data = m.data
                      ORDER BY abs(extract(epoch FROM a2.inicio - m.inicio)) LIMIT 1))
ORDER BY m.data DESC;

SELECT 'live_monitor_sessao + live_monitor_snapshot + view de conferência criadas' AS ok;
