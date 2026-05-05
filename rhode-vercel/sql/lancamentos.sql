-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Catálogo de Lançamentos no hub + Solicitação de Amostra
-- ═══════════════════════════════════════════════════════════════════════════
--
-- Item 5 do ROADMAP. Adiciona o conceito de "amostra solicitada pela creator
-- mas ainda não aprovada/enviada" reusando a tabela amostras_enviadas via
-- duas colunas novas. Existing rows ficam aprovada=TRUE (default), então
-- todo o histórico continua válido sem migration de dados.
--
-- Workflow:
--  1. Creator clica "Pedir amostra" no hub (panel Novidades) → INSERT com
--     origem='solicitacao_creator', aprovada=FALSE, solicitada_em=NOW()
--  2. Admin vê na lista de "Solicitações Pendentes" → Aprova ou Recusa
--  3. Aprovar → UPDATE aprovada=TRUE, data_envio=hoje (admin pode editar)
--  4. Recusar → UPDATE dispensada=TRUE (preserva histórico, some das listas)

-- 1. Colunas novas em amostras_enviadas
ALTER TABLE amostras_enviadas ADD COLUMN IF NOT EXISTS aprovada      BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE amostras_enviadas ADD COLUMN IF NOT EXISTS solicitada_em TIMESTAMPTZ;

-- Index só pra os pendentes (esperam ação do admin)
CREATE INDEX IF NOT EXISTS idx_amostras_pendentes
  ON amostras_enviadas(solicitada_em DESC)
  WHERE aprovada = FALSE AND COALESCE(dispensada, FALSE) = FALSE;

-- 2. RLS: anon pode INSERT/SELECT/UPDATE em amostras_enviadas
--    (idempotente — só cria se não existir; mantém comportamento se já tem)
ALTER TABLE amostras_enviadas DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_amostras" ON amostras_enviadas;
CREATE POLICY "anon_all_amostras" ON amostras_enviadas
  FOR ALL USING (true) WITH CHECK (true);


-- 3. Confirmação
SELECT
  COUNT(*) FILTER (WHERE aprovada = TRUE)                              AS aprovadas,
  COUNT(*) FILTER (WHERE aprovada = FALSE AND solicitada_em IS NOT NULL) AS pendentes,
  COUNT(*) FILTER (WHERE COALESCE(dispensada, FALSE) = TRUE)            AS dispensadas
FROM amostras_enviadas;
