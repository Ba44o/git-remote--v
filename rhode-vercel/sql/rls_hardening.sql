-- ═══════════════════════════════════════════════════════════════════════════
--  Rhode — Inc.3 do hardening (item 8): VIRAR RLS deny-anon nas tabelas sensíveis
-- ═══════════════════════════════════════════════════════════════════════════
--
--  CONTEXTO: hoje a anon key (visível no source) lê 23 tabelas — access_token,
--  pin_acesso, whatsapp e GMV de todas as creators. Inc.1 (Hub) e Inc.2 (Admin)
--  já fizeram TODO o frontend ler/escrever via /api/get-hub (service key no
--  servidor). Este script fecha a porta: liga RLS e nega a anon.
--
--  ⚠️ RODAR SÓ DEPOIS de Inc.1+Inc.2 estarem em produção (já estão). O
--     service_role (usado pelo proxy) tem BYPASSRLS → proxy/admin continuam
--     funcionando. A anon key para de ler — que é o objetivo.
--
--  COMO RODAR: cole tudo no Supabase → SQL Editor → Run. Depois rode os SELECTs
--  de verificação no fim. Se algo quebrar, use o bloco ROLLBACK (no fim, comentado).
--
--  FORA DESTE SCRIPT (continuam abertas de propósito):
--    • lives, store_daily      → lidas pelo dash-live.html (ainda via anon; migrar depois)
--    • tier_milestones         → não exposta hoje (404), não mexer
-- ═══════════════════════════════════════════════════════════════════════════

-- ── 1. Derruba QUALQUER policy permissiva existente nas tabelas-alvo ──────────
--    (os scripts antigos criaram policies "anon_all_*" com USING(true); com RLS
--     ligado elas reabririam tudo. service_role ignora policies de qualquer jeito.)
DO $$
DECLARE
  r record;
  alvo text[] := ARRAY[
    'affiliates','eventos_creators','performance_periods','performance_diario',
    'amostras_enviadas','creator_profiles','scripts_gerados','notificacoes',
    'finance_statements','devolucoes','affiliate_perf','seeding',
    'affiliate_creator_product','produtos','campanhas','flash_sales',
    'disparos_log','mensagens_templates',
    'triagem','triagem_eventos','hub_eventos'
  ];
BEGIN
  FOR r IN
    SELECT policyname, tablename FROM pg_policies
    WHERE schemaname = 'public' AND tablename = ANY(alvo)
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', r.policyname, r.tablename);
  END LOOP;
END $$;

-- ── 2. Liga RLS nas tabelas que devem ficar 100% deny-anon ───────────────────
--    Com RLS ligado e SEM policy permissiva, anon/authenticated não leem nada.
--    service_role (proxy) continua lendo/escrevendo (bypassrls).
ALTER TABLE public.affiliates                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.eventos_creators          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.performance_periods       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.performance_diario        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.amostras_enviadas         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.creator_profiles          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.scripts_gerados           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notificacoes              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.finance_statements        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.devolucoes                ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.affiliate_perf            ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.seeding                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.affiliate_creator_product ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.produtos                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.campanhas                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.flash_sales               ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.disparos_log              ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.mensagens_templates       ENABLE ROW LEVEL SECURITY;

-- ── 3. Tabelas de analytics/lead: anon pode INSERIR, mas NÃO ler/alterar ──────
--    (hub.html grava hub_eventos; bem-vinda.html grava triagem + triagem_eventos
--     — todas com return=minimal, então INSERT-only basta.)
ALTER TABLE public.triagem          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.triagem_eventos  ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hub_eventos      ENABLE ROW LEVEL SECURITY;

CREATE POLICY anon_insert_only ON public.triagem
  FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY anon_insert_only ON public.triagem_eventos
  FOR INSERT TO anon, authenticated WITH CHECK (true);
CREATE POLICY anon_insert_only ON public.hub_eventos
  FOR INSERT TO anon, authenticated WITH CHECK (true);

-- ── 4. View flash_sales_ativas: RLS não cobre view (roda como dona) → REVOKE ──
--    O proxy lê via service_role (mantém acesso). anon perde a leitura da view.
REVOKE SELECT ON public.flash_sales_ativas FROM anon, authenticated;

-- ═══════════════════════════════════════════════════════════════════════════
--  VERIFICAÇÃO — rode estes SELECTs e confira:
-- ═══════════════════════════════════════════════════════════════════════════
-- (a) Quais tabelas têm RLS ligado agora (deve listar as 21 acima):
SELECT tablename, rowsecurity
FROM pg_tables WHERE schemaname='public'
  AND tablename IN ('affiliates','eventos_creators','performance_periods',
    'performance_diario','amostras_enviadas','creator_profiles','scripts_gerados',
    'notificacoes','finance_statements','devolucoes','affiliate_perf','seeding',
    'affiliate_creator_product','produtos','campanhas','flash_sales','disparos_log',
    'mensagens_templates','triagem','triagem_eventos','hub_eventos')
ORDER BY rowsecurity DESC, tablename;

-- (b) Policies de INSERT que sobraram (deve mostrar 3: triagem/triagem_eventos/hub_eventos):
SELECT tablename, policyname, cmd, roles
FROM pg_policies WHERE schemaname='public' ORDER BY tablename;

-- ═══════════════════════════════════════════════════════════════════════════
--  ROLLBACK DE EMERGÊNCIA (se o hub/admin quebrar) — descomente e rode:
-- ═══════════════════════════════════════════════════════════════════════════
-- ALTER TABLE public.affiliates                DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.eventos_creators          DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.performance_periods       DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.performance_diario        DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.amostras_enviadas         DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.creator_profiles          DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.scripts_gerados           DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.notificacoes              DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.finance_statements        DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.devolucoes                DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.affiliate_perf            DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.seeding                   DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.affiliate_creator_product DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.produtos                  DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.campanhas                 DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.flash_sales               DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.disparos_log              DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.mensagens_templates       DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.triagem                   DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.triagem_eventos           DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.hub_eventos               DISABLE ROW LEVEL SECURITY;
-- GRANT SELECT ON public.flash_sales_ativas TO anon, authenticated;
