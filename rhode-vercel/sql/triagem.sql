-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Triagem de Creators (formulário do bem-vinda.html → fila de análise)
-- ═══════════════════════════════════════════════════════════════════════════
--
-- 1 linha por submissão do formulário de triagem (screenIdentity em bem-vinda.html).
-- O INSERT é feito client-side via anon key (mesmo padrão de eventos_creators / hub_eventos).
-- Consumido pela aba "Triagem" do admin (admin.html).
--
-- Campos:
--   pedido       → o que a creator quer:
--                  ver_lugar         (afiliada c/ peça → ver grupo/hub/benefícios)
--                  amostra_gratis    (afiliada sem peça → pediu amostra → análise)
--                  mais_modelos      (afiliada → aplicou pra receber mais modelos → análise)
--                  quero_ser_creator (não-afiliada → quer entrar no programa → fila/análise)
--                  (a opção "flash sale" do Passo 3 redireciona pro WhatsApp e NÃO grava aqui)
--   diagnostico  → card que a creator viu: analise | ativar | fechado | parceira_track | onboarding
--   status       → o time atualiza no admin: novo | em_analise | aprovada | recusada

CREATE TABLE IF NOT EXISTS triagem (
  id            BIGSERIAL PRIMARY KEY,
  nome          TEXT,
  handle        TEXT,                       -- @ do TikTok (sem o @)
  whatsapp      TEXT,
  relacao       TEXT,                       -- afiliada_ativa | quero_ser_creator
  gmv_faixa     TEXT,                       -- 0 | ate5k | 5a20k | 20a80k (declarado; vazio se não-afiliada)
  pedido        TEXT,                       -- ver_lugar | amostra_gratis | mais_modelos | quero_ser_creator
  tem_peca      TEXT,                       -- sim | nao | quer_mais (vazio se não passou pelo Passo 3)
  diagnostico   TEXT,                       -- analise | ativar | fechado | parceira_track | onboarding
  origem        TEXT,                       -- cold | token
  status        TEXT DEFAULT 'novo',        -- novo | em_analise | aprovada | recusada
  referrer      TEXT,
  user_agent    TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_triagem_created ON triagem(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_triagem_handle  ON triagem(handle);
CREATE INDEX IF NOT EXISTS idx_triagem_pedido  ON triagem(pedido);
CREATE INDEX IF NOT EXISTS idx_triagem_status  ON triagem(status);

-- anon pode INSERT (a triagem grava) e SELECT/UPDATE (admin lê e atualiza status). Sem RLS — projeto interno.
ALTER TABLE triagem DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_triagem" ON triagem;
CREATE POLICY "anon_all_triagem" ON triagem FOR ALL USING (true) WITH CHECK (true);

-- ── Confirmação ──
SELECT
  COUNT(*)                                              AS total,
  COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '7 days') AS ultimos_7d,
  COUNT(*) FILTER (WHERE pedido = 'amostra_gratis')     AS pedidos_amostra,
  COUNT(*) FILTER (WHERE pedido = 'quero_ser_creator')  AS quer_ser_creator
FROM triagem;
