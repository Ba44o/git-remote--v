-- =============================================================
-- Rhode — Relatório de LIVE: dado por sessão (sala) + totais por período
-- Fonte: Business API /gmv_max/report/get/ dimensions=[room_id] filtering.campaign_ids
-- (campanhas LIVE_GMV_MAX) → custo/GMV/pedidos/VISUALIZAÇÕES por sala (sem export manual).
-- + Partner Analytics /analytics/202405/shop/performance → GMV de live TOTAL (org+ads).
-- Coletor: coletar_lives_api.py. Rodar no Supabase → SQL Editor → Run.
-- =============================================================

-- Por SESSÃO (sala × dia)
CREATE TABLE IF NOT EXISTS live_sessao (
  id          text PRIMARY KEY,      -- "{room_id}:{data}"
  room_id     text,
  data        date,
  periodo     text,
  campaign_id text,
  campanha    text,
  origem      text,                  -- 'propria' | 'creator'
  cost        numeric DEFAULT 0,     -- investimento (mídia)
  net_cost    numeric DEFAULT 0,
  receita     numeric DEFAULT 0,     -- GMV atribuído
  pedidos     integer DEFAULT 0,
  views       integer DEFAULT 0,     -- visualizações da LIVE
  updated_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_live_sessao_periodo ON live_sessao(periodo);
ALTER TABLE live_sessao ENABLE ROW LEVEL SECURITY;

-- Totais por PERÍODO (GMV de live orgânico+ads vs canais — do Analytics)
CREATE TABLE IF NOT EXISTS live_periodo (
  periodo      text PRIMARY KEY,
  gmv_loja     numeric DEFAULT 0,    -- GMV total da loja
  gmv_live     numeric DEFAULT 0,    -- GMV via LIVE (orgânico + ads)
  gmv_video    numeric DEFAULT 0,
  gmv_card     numeric DEFAULT 0,
  pedidos_live integer DEFAULT 0,
  buyers_live  integer DEFAULT 0,
  updated_at   timestamptz DEFAULT now()
);
ALTER TABLE live_periodo ENABLE ROW LEVEL SECURITY;

SELECT 'live_sessao + live_periodo criadas' AS ok;
