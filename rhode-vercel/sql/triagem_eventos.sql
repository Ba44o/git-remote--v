-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Eventos da Triagem (instrumentação de funil do bem-vinda.html)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- 1 linha por "passo visto" durante uma visita ao bem-vinda.html.
-- Gravado client-side via anon key (fetch keepalive). Best-effort — se a tabela
-- não existir, o track() falha em silêncio e nada quebra.
--
-- step:
--   passo1        → tela "Qual é a sua relação com a Rhode hoje?" (= começou a triagem)
--   passo2        → faixa de GMV (implica: escolheu "já sou afiliada")
--   passo3        → "O que você quer fazer agora?"
--   mais_modelos  → tela "Como funciona a análise" (interstitial do "aplicar pra mais modelos")
--   form          → tela do formulário (nome/@/WhatsApp) aberta
--   submit        → formulário enviado com sucesso (= conversão) · meta tem relacao/gmv/pedido/tem_peca/diagnostico
--   flash         → clicou "solicitar flash sale" e saiu pro WhatsApp (não preenche form)
--   result        → card de resultado renderizado (inclui o caminho de token, que pula a triagem)
--
-- Funil = nº de session_id distintos em cada step. Conversão = sessions(submit) / sessions(passo1).

CREATE TABLE IF NOT EXISTS triagem_eventos (
  id          BIGSERIAL PRIMARY KEY,
  session_id  TEXT NOT NULL,        -- uuid gerado no client por visita
  step        TEXT NOT NULL,
  meta        JSONB,                -- dados extras do passo
  referrer    TEXT,
  user_agent  TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_triagem_eventos_session ON triagem_eventos(session_id);
CREATE INDEX IF NOT EXISTS idx_triagem_eventos_step    ON triagem_eventos(step);
CREATE INDEX IF NOT EXISTS idx_triagem_eventos_created ON triagem_eventos(created_at DESC);

ALTER TABLE triagem_eventos DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_triagem_eventos" ON triagem_eventos;
CREATE POLICY "anon_all_triagem_eventos" ON triagem_eventos FOR ALL USING (true) WITH CHECK (true);

-- View de conveniência: funil dos últimos 30 dias (sessões distintas por step)
CREATE OR REPLACE VIEW triagem_funil AS
SELECT step, COUNT(DISTINCT session_id) AS sessoes, COUNT(*) AS eventos
FROM triagem_eventos
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY step;

-- ── Confirmação ──
SELECT
  COUNT(*)                                                   AS total_eventos,
  COUNT(DISTINCT session_id)                                 AS sessoes_distintas,
  COUNT(DISTINCT session_id) FILTER (WHERE step='submit')    AS submissoes
FROM triagem_eventos
WHERE created_at >= NOW() - INTERVAL '30 days';
