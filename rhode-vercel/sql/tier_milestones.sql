-- Tabela de marcos de tier para creators Rhode
-- Cada (affiliate_id, tier) é único — uma creator só atinge cada tier uma vez.
-- O cron `api/cron-tier-milestones.js` insere a row quando detecta o cruzamento
-- e atualiza `notified_at` após enviar a notificação WhatsApp ao operador.

CREATE TABLE IF NOT EXISTS tier_milestones (
  id               BIGSERIAL PRIMARY KEY,
  affiliate_id     TEXT        NOT NULL,
  tier             TEXT        NOT NULL CHECK (tier IN ('bronze','silver','gold','diamond','black')),
  gmv_at_milestone NUMERIC     NOT NULL,
  reached_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  notified_at      TIMESTAMPTZ,
  placa_status     TEXT        NOT NULL DEFAULT 'pending'
                   CHECK (placa_status IN ('pending','shipped','delivered','skipped','na')),
  placa_shipped_at TIMESTAMPTZ,
  notes            TEXT,
  UNIQUE(affiliate_id, tier)
);

-- Otimiza o filtro do cron: rows ainda não notificadas
CREATE INDEX IF NOT EXISTS idx_tier_milestones_unnotified
  ON tier_milestones(notified_at) WHERE notified_at IS NULL;

-- Otimiza relatório operacional: o que ainda não foi despachado
CREATE INDEX IF NOT EXISTS idx_tier_milestones_pending_placa
  ON tier_milestones(placa_status) WHERE placa_status = 'pending';
