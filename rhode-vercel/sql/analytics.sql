-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Analytics de Comportamento no Hub das Creators
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Item: sistema de análise de comportamento de usuária no hub.
-- Captura no client (hub.html) via navigator.sendBeacon → tabela hub_eventos.
--
-- Tipos de evento (coluna `evento`):
--   'session_start'  → abriu o hub (1 por sessão)
--   'session_end'    → fechou/saiu (1 por sessão; duracao_ms = sessão inteira)
--   'tab_view'       → saiu de uma aba (aba = qual; duracao_ms = tempo naquela aba)
--   'action'         → ação relevante (meta.tipo: 'copy_gerada','amostra_solicitada',
--                       'flash_modal_aberto','script_marcado_venda', etc)
--
-- session_id é um UUID gerado no client por sessão (sessionStorage).

CREATE TABLE IF NOT EXISTS hub_eventos (
  id            BIGSERIAL PRIMARY KEY,
  affiliate_id  TEXT,                       -- handle UPPERCASE da creator (null se anônimo)
  session_id    TEXT NOT NULL,              -- uuid da sessão (client)
  evento        TEXT NOT NULL,              -- session_start | session_end | tab_view | action
  aba           TEXT,                       -- perf | perfdetail | novidades | copy | entregaveis | hist
  duracao_ms    BIGINT,                     -- tempo (tab_view: na aba; session_end: sessão toda)
  meta          JSONB,                      -- dados extras por evento
  referrer      TEXT,                       -- document.referrer (ex: vindo do WhatsApp)
  user_agent    TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hub_eventos_created   ON hub_eventos(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_hub_eventos_affiliate ON hub_eventos(affiliate_id);
CREATE INDEX IF NOT EXISTS idx_hub_eventos_session   ON hub_eventos(session_id);
CREATE INDEX IF NOT EXISTS idx_hub_eventos_evento    ON hub_eventos(evento);
CREATE INDEX IF NOT EXISTS idx_hub_eventos_aba       ON hub_eventos(aba) WHERE aba IS NOT NULL;

-- anon pode INSERT (tracking) e SELECT (admin lê). Sem RLS — projeto interno.
ALTER TABLE hub_eventos DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_hub_eventos" ON hub_eventos;
CREATE POLICY "anon_all_hub_eventos" ON hub_eventos FOR ALL USING (true) WITH CHECK (true);


-- ── Views de agregação (o admin pode usar direto ou calcular client-side) ──

-- Tempo médio por aba (últimos 30 dias)
CREATE OR REPLACE VIEW hub_tempo_por_aba AS
SELECT
  aba,
  COUNT(*)                                           AS views,
  ROUND(AVG(duracao_ms)/1000.0, 1)                   AS seg_medio,
  ROUND(SUM(duracao_ms)/60000.0, 1)                  AS min_total,
  COUNT(DISTINCT affiliate_id)                        AS creators_unicas
FROM hub_eventos
WHERE evento = 'tab_view'
  AND aba IS NOT NULL
  AND duracao_ms BETWEEN 500 AND 1800000              -- ignora ruído (<0.5s) e outliers (>30min)
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY aba
ORDER BY views DESC;

-- Resumo de sessões (últimos 30 dias)
CREATE OR REPLACE VIEW hub_sessoes_resumo AS
SELECT
  s.session_id,
  s.affiliate_id,
  s.created_at                                        AS inicio,
  e.duracao_ms                                        AS duracao_ms,
  (SELECT COUNT(DISTINCT t.aba) FROM hub_eventos t
     WHERE t.session_id = s.session_id AND t.evento = 'tab_view') AS abas_visitadas,
  (SELECT COUNT(*) FROM hub_eventos a
     WHERE a.session_id = s.session_id AND a.evento = 'action')   AS acoes
FROM hub_eventos s
LEFT JOIN hub_eventos e ON e.session_id = s.session_id AND e.evento = 'session_end'
WHERE s.evento = 'session_start'
  AND s.created_at >= NOW() - INTERVAL '30 days'
ORDER BY s.created_at DESC;


-- ── Confirmação ──
SELECT
  COUNT(*)                                            AS total_eventos,
  COUNT(*) FILTER (WHERE evento = 'session_start')    AS sessoes,
  COUNT(DISTINCT affiliate_id)                         AS creators_distintas
FROM hub_eventos;
