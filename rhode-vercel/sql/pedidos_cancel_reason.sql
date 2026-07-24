-- =============================================================
-- Rhode — Motivo de CANCELAMENTO nos pedidos (destrava o número de RUPTURA).
-- Escrito por coletar_pedidos_sku.py. A Orders API expõe cancel_reason /
-- cancellation_initiator / cancel_time (e cancel_reason + cancel_user por line_item).
--
-- Por que importa: sem isso, "cancelamento" era um balde único (jun/26: 2.051 pedidos,
-- R$173k de GMV) e parecia ruptura. Com o motivo, a leitura real de jun/26 é:
--   · Pagamento atrasado do cliente (SYSTEM) ... 59,4% · R$103.981  ← checkout/Pix, não fábrica
--   · Arrependimento (não precisa/engano/cupom)  ~30%  · R$ 55.000
--   · FORA DE ESTOQUE (ruptura real) ..........   0,7% · R$  1.548  ← 50x menor que devolução
--
-- ⚠️ RODAR ANTES do próximo daily. O coletor tem upsert self-healing (dropa a coluna e
--    segue) — então não quebra a coleta, mas grava sem o motivo até isto rodar. RUNBOOK #13.
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
ALTER TABLE pedidos_sku       ADD COLUMN IF NOT EXISTS cancel_reason    text;
ALTER TABLE pedidos_sku       ADD COLUMN IF NOT EXISTS cancel_user      text;  -- BUYER/SELLER/SYSTEM
ALTER TABLE pedido_pagamento  ADD COLUMN IF NOT EXISTS cancel_reason    text;
ALTER TABLE pedido_pagamento  ADD COLUMN IF NOT EXISTS cancel_initiator text;
ALTER TABLE pedido_pagamento  ADD COLUMN IF NOT EXISTS cancel_time      bigint;

CREATE INDEX IF NOT EXISTS idx_psku_cancel ON pedidos_sku(cancel_reason);
CREATE INDEX IF NOT EXISTS idx_ppag_cancel ON pedido_pagamento(cancel_reason);

-- ---- leitura pronta: cancelamento por motivo e por mês ----
--   perda_bucket separa o que é FÁBRICA (ruptura) do que é CHECKOUT (pagamento não completou)
--   e do que é ARREPENDIMENTO — três donos diferentes, três ações diferentes.
CREATE OR REPLACE VIEW cancelamento_motivo AS
SELECT
  periodo,
  coalesce(cancel_reason, '(sem motivo)')            AS motivo,
  CASE
    -- meses ANTERIORES à instrumentação (jul/26) têm cancel_reason NULL. Sem esta guarda
    -- eles caíam no ELSE e apareciam como 100% "arrependimento" — leitura falsa (jan-mar/26).
    WHEN cancel_reason IS NULL OR cancel_reason = '' THEN 'sem_motivo_coletado'
    WHEN cancel_reason ILIKE '%fora de estoque%'  THEN 'ruptura'
    WHEN cancel_reason ILIKE '%pagamento%'
      OR cancel_reason ILIKE '%pagar%'
      OR cancel_reason ILIKE '%overdue to pay%'
      OR cancel_reason ILIKE '%payment method%'
      OR cancel_reason ILIKE '%método de pagamento%' THEN 'checkout_pagamento'
    WHEN cancel_reason ILIKE '%perdido%'
      OR cancel_reason ILIKE '%entregar%'
      OR cancel_reason ILIKE '%a tempo%'
      OR cancel_reason ILIKE '%endereço%'            THEN 'logistica'
    ELSE 'arrependimento'
  END                                                AS dono,
  cancel_initiator                                   AS iniciador,
  count(*)                                           AS pedidos,
  round(sum(total_amount)::numeric, 2)               AS gmv_perdido
FROM pedido_pagamento
WHERE status = 'CANCELLED'
GROUP BY 1,2,3,4;

-- resumo por dono do problema (é a linha que vai pro relatório)
CREATE OR REPLACE VIEW cancelamento_resumo AS
SELECT periodo, dono,
       sum(pedidos)                     AS pedidos,
       round(sum(gmv_perdido), 2)       AS gmv_perdido
FROM cancelamento_motivo GROUP BY 1,2 ORDER BY 1 DESC, 4 DESC;

SELECT 'cancel_reason adicionado + views cancelamento_motivo/cancelamento_resumo' AS ok;
