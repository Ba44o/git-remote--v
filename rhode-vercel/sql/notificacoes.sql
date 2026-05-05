-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Inbox de Notificações no hub
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Item 6 do ROADMAP. Centraliza comms operacionais (amostra aprovada, tier
-- novo, flash sale, lançamento, alerta de refund) num só lugar dentro do
-- hub, reduzindo dependência de WhatsApp.
--
-- Granularidade: 1 row = 1 notificação para 1 creator. Lida/não-lida via
-- coluna `lida` (BOOLEAN). Não armazena push tokens — drawer é polled
-- on tab focus + setInterval no hub.

CREATE TABLE IF NOT EXISTS notificacoes (
  id          BIGSERIAL PRIMARY KEY,
  creator_id  TEXT NOT NULL,                          -- UPPERCASE (bate com affiliates.affiliate_id)
  tipo        TEXT NOT NULL,                          -- 'amostra_aprovada','amostra_recusada','tier_up','flash_sale','lancamento','alerta_refund','sistema'
  titulo      TEXT NOT NULL,
  corpo       TEXT,
  link        TEXT,                                   -- destino interno opcional (ex: 'novidades' pra goTab)
  lida        BOOLEAN NOT NULL DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  read_at     TIMESTAMPTZ
);

-- Index principal: query "minhas não-lidas mais recentes" do hub
CREATE INDEX IF NOT EXISTS idx_notif_inbox
  ON notificacoes(creator_id, lida, created_at DESC);

-- Index para limpeza periódica (opcional)
CREATE INDEX IF NOT EXISTS idx_notif_created
  ON notificacoes(created_at DESC);

ALTER TABLE notificacoes DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_notif" ON notificacoes;
CREATE POLICY "anon_all_notif" ON notificacoes
  FOR ALL USING (true) WITH CHECK (true);


-- Confirmação
SELECT
  COUNT(*)                                  AS total,
  COUNT(*) FILTER (WHERE lida = FALSE)      AS nao_lidas,
  COUNT(DISTINCT creator_id)                AS creators_com_notif
FROM notificacoes;
