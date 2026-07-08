-- =============================================================
-- Rhode — Margem de contribuição por PRODUTO de live (painel interno dash-live).
-- Fonte: export "Live products" do Seller Center (por produto/live) × CPV (mapa
-- product_id→SKU via pedidos). Populado por atualizar_live_produto.py.
-- Lido pelo painel via proxy /api/get-hub action=dashlive which=live_produto.
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE TABLE IF NOT EXISTS live_produto (
  id          text PRIMARY KEY,   -- "{periodo}:{product_id}"
  periodo     text,
  product_id  text,
  produto     text,
  gmv         numeric DEFAULT 0,
  unidades    integer DEFAULT 0,
  pedidos     integer DEFAULT 0,
  lives       integer DEFAULT 0,  -- em quantas lives o produto vendeu
  cpv_un      numeric,
  margem      numeric,            -- margem de contribuição R$ (GMV − CPV − taxas − imposto)
  margem_pct  numeric,            -- margem / GMV (0-1... ou %? guardamos %)
  updated_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_live_produto_periodo ON live_produto(periodo);
ALTER TABLE live_produto ENABLE ROW LEVEL SECURITY;
SELECT 'live_produto criada' AS ok;
