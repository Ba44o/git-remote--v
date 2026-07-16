-- =============================================================
-- Rhode — Módulo CLIENTES (CRM / inteligência de cliente) do admin.
-- 1 linha por cliente, identidade por CPF **HASHEADO** (sha256[:16]) — CPF cru NUNCA é gravado.
-- Populado por coletar_clientes.py (ROOT, cron). Orders API é a única fonte (não há tabela de cliente).
-- LGPD: só hash + agregados. Nome/CPF/telefone NÃO entram. Contato/campanha = fase 2 c/ base legal.
-- Segmento é DERIVADO nas views (usa current_date) → nunca fica velho.
-- Rodar no Supabase → SQL Editor → Run.
-- =============================================================
CREATE TABLE IF NOT EXISTS cliente (
  id               text PRIMARY KEY,        -- sha256(cpf)[:16] — pseudônimo estável
  n_pedidos        int     NOT NULL DEFAULT 0,
  gmv_total        numeric(12,2) NOT NULL DEFAULT 0,   -- LTV histórico
  primeiro_pedido  date,
  ultimo_pedido    date,
  uf               text,
  cidade           text,
  creator_origem   text,                    -- creator do 1º pedido ('' = loja/sem afiliada)
  updated_at       timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cliente_uf      ON cliente(uf);
CREATE INDEX IF NOT EXISTS idx_cliente_ultimo  ON cliente(ultimo_pedido);
CREATE INDEX IF NOT EXISTS idx_cliente_creator ON cliente(creator_origem);
ALTER TABLE cliente ENABLE ROW LEVEL SECURITY;   -- deny-anon; só service_role/proxy admin

-- ---- segmento derivado (thresholds da NOSSA realidade: discovery-commerce) ----
--   vip 3+ · recorrente 2 · unico_recente 1 pedido ≤60d · unico_frio 1 pedido >60d (churn)
CREATE OR REPLACE VIEW cliente_segmentado AS
SELECT c.*,
  CASE WHEN c.n_pedidos >= 3 THEN 'vip'
       WHEN c.n_pedidos = 2 THEN 'recorrente'
       WHEN c.ultimo_pedido >= current_date - 60 THEN 'unico_recente'
       ELSE 'unico_frio' END AS segmento
FROM cliente c;

CREATE OR REPLACE VIEW cliente_resumo AS
SELECT segmento,
       count(*)                              AS clientes,
       round(sum(gmv_total)::numeric, 2)     AS receita,
       round(avg(gmv_total)::numeric, 2)     AS ltv
FROM cliente_segmentado GROUP BY segmento;

CREATE OR REPLACE VIEW cliente_uf AS
SELECT uf, count(*) AS clientes, round(sum(gmv_total)::numeric,2) AS receita,
       round(avg(gmv_total)::numeric,2) AS ltv
FROM cliente WHERE uf IS NOT NULL GROUP BY uf ORDER BY clientes DESC;

-- LTV por creator de ORIGEM (1º pedido) — o que nenhuma ferramenta gringa faz.
-- volta_pct = % dos clientes que aquele creator trouxe e que RECOMPRARAM.
CREATE OR REPLACE VIEW cliente_creator AS
SELECT coalesce(nullif(creator_origem,''), '(loja / sem afiliada)') AS creator,
       count(*)                                                     AS clientes,
       round(sum(gmv_total)::numeric,2)                             AS receita,
       round(avg(gmv_total)::numeric,2)                             AS ltv,
       round((count(*) FILTER (WHERE n_pedidos>=2))::numeric / nullif(count(*),0) * 100, 1) AS volta_pct
FROM cliente GROUP BY 1 HAVING count(*) >= 20 ORDER BY clientes DESC;

SELECT 'cliente + views criadas' AS ok;
