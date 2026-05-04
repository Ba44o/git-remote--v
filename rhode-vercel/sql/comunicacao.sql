-- ═══════════════════════════════════════════════════════════════════════════
-- Rhode — Comunicação Segmentada via Z-API
-- ═══════════════════════════════════════════════════════════════════════════

-- 1. Templates de mensagem
CREATE TABLE IF NOT EXISTS mensagens_templates (
  id          TEXT PRIMARY KEY,
  nome        TEXT NOT NULL,
  categoria   TEXT,                                 -- 'onboarding','tier_up','alerta','briefing','lancamento','reativacao'
  corpo       TEXT NOT NULL,                        -- texto com {{variaveis}}
  ativo       BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT NOW(),
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE mensagens_templates DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_templates" ON mensagens_templates;
CREATE POLICY "anon_all_templates" ON mensagens_templates FOR ALL USING (true) WITH CHECK (true);

DROP TRIGGER IF EXISTS update_templates_updated_at ON mensagens_templates;
CREATE TRIGGER update_templates_updated_at
  BEFORE UPDATE ON mensagens_templates
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Templates iniciais (idempotente via ON CONFLICT)
INSERT INTO mensagens_templates (id, nome, categoria, corpo) VALUES
('acesso_hub', 'Convite pro Hub', 'onboarding',
'Olá {{nome}}! 🤍

Criamos seu acesso ao *Creator Hub Rhode Jeans*.

No hub você acompanha sua performance, comissões, missões e benefícios:
{{link_hub}}

Qualquer dúvida, é só responder aqui.'),

('boas_vindas', 'Boas-vindas afiliada', 'onboarding',
'Bem-vinda à Rhode Jeans, {{nome}}! 🤍

Você está oficialmente no nosso programa de afiliadas.

✨ Tier atual: *{{tier}}*
💰 Comissão: *{{tier_comissao}}* sobre cada venda
📅 Pagamentos: todo dia 15

Acesse seu hub: {{link_hub}}'),

('tier_up', 'Subiu de tier', 'tier_up',
'{{nome}}, parabéns! 🏆

Você acaba de subir para *{{tier}}*.

Sua nova comissão: *{{tier_comissao}}*

Confira os benefícios desbloqueados no seu hub:
{{link_hub}}'),

('alerta_refund', 'Alerta refund alto', 'alerta',
'{{nome}}, oi!

Notamos que seu refund está em *{{refund_pct}}* no último período. Quer
trocar uma ideia sobre o que pode estar causando?

A gente pode te ajudar com troca de tamanho, ajuste de comunicação ou
direcionamento de produto.'),

('briefing_live', 'Briefing de live oficial', 'briefing',
'{{nome}}, oi!

🔴 Live oficial Rhode amanhã às 19h.

Pede pra sua audiência acompanhar e usar seu link de afiliada — comissão
extra durante a live.

Confirma se você consegue divulgar?'),

('lancamento_sku', 'Lançamento de produto', 'lancamento',
'{{nome}}, novidade fresca! 🔥

Lançamos um produto novo já disponível no seu link de afiliada.

Quem postar primeiro com o produto novo ganha amostra extra na próxima
campanha.

Confira no hub: {{link_hub}}'),

('reativacao', 'Reativação de creator', 'reativacao',
'{{nome}}, sentimos sua falta! 🤍

Faz um tempo que você não posta com link Rhode. Tudo bem?

Se for questão de produto novo, conteúdo ou comissão, me avisa que
a gente conversa.

Seu hub continua ativo: {{link_hub}}')
ON CONFLICT (id) DO UPDATE SET
  nome      = EXCLUDED.nome,
  categoria = EXCLUDED.categoria,
  corpo     = EXCLUDED.corpo,
  updated_at = NOW();


-- 2. Log de disparos (auditoria + rate limit)
CREATE TABLE IF NOT EXISTS disparos_log (
  id              BIGSERIAL PRIMARY KEY,
  template_id     TEXT REFERENCES mensagens_templates(id) ON DELETE SET NULL,
  filtro_aplicado JSONB,                            -- snapshot dos filtros usados
  total_alvos     INT DEFAULT 0,                    -- creators que bateram filtro
  total_enviados  INT DEFAULT 0,                    -- enviados com sucesso
  total_falhas    INT DEFAULT 0,
  duracao_ms      INT,
  preview         TEXT,                             -- primeira mensagem renderizada (debug)
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_disparos_log_created ON disparos_log(created_at DESC);

ALTER TABLE disparos_log DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_disparos" ON disparos_log;
CREATE POLICY "anon_all_disparos" ON disparos_log FOR ALL USING (true) WITH CHECK (true);


-- 3. Confirmação
SELECT 'templates' AS info, COUNT(*) AS rows FROM mensagens_templates
UNION ALL
SELECT 'disparos_log', COUNT(*) FROM disparos_log;
