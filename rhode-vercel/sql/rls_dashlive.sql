-- ═══════════════════════════════════════════════════════════════════════════
--  Rhode — Hardening follow-up: fechar lives + store_daily (dash-live.html)
-- ═══════════════════════════════════════════════════════════════════════════
--  O dash-live.html já foi migrado pro proxy (/api/get-hub action=dashlive), que
--  lê via service_role. Então dá pra ligar RLS deny-anon nessas 2 — fecha a
--  última leitura direta da anon key. São métricas agregadas da loja (sem
--  credencial/PII), por isso ficaram pro fim.
--
--  ⚠️ RODAR SÓ DEPOIS do deploy do dash-live novo estar em produção.
--  Cole no Supabase → SQL Editor → Run.
-- ═══════════════════════════════════════════════════════════════════════════

-- Derruba as policies permissivas (public read) dessas 2 tabelas:
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT policyname, tablename FROM pg_policies
    WHERE schemaname='public' AND tablename = ANY(ARRAY['lives','store_daily'])
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON public.%I', r.policyname, r.tablename);
  END LOOP;
END $$;

ALTER TABLE public.lives       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.store_daily ENABLE ROW LEVEL SECURITY;

-- Verificação (deve mostrar as 2 com rowsecurity = true):
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname='public' AND tablename IN ('lives','store_daily');

-- ROLLBACK de emergência (se o dash-live quebrar):
-- ALTER TABLE public.lives       DISABLE ROW LEVEL SECURITY;
-- ALTER TABLE public.store_daily DISABLE ROW LEVEL SECURITY;
