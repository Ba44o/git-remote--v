# Rhode Creator Hub — Roadmap

> **Como usar este arquivo:** fonte de verdade do projeto. Antes de iniciar trabalho novo, leia daqui em diante. Atualizar conforme features são concluídas ou repriorizadas.
>
> **Última atualização:** 2026-05-02

---

## 📍 Estado atual

Operação ativa: 4.926 creators afiliadas, 5 períodos no warehouse (2026-01 a 2026-05). URLs únicas: `creators.rhodejeans.com.br/hub.html` (hub) e `creators.rhodejeans.com.br/admin.html` (admin), servidos pelo projeto Vercel `rhode-vercel`. Auditoria de integridade (`audit_data.py`) confirma 0 divergências entre exports do TikTok Shop e Supabase em todos os períodos.

---

## ✅ Concluído (em produção)

### Hub das creators (`rhode-vercel/public/hub.html`)
- Sistema visual Apple-inspired (Inter + JetBrains Mono, hairlines, sem sombras, single accent Rhode Red)
- 5 tiers com benefícios em seções (Bronze 20k / Silver 50k / Gold 80k / Diamond 150k / Black 500k acumulado)
- Cor de identidade por tier nos cards (Benefícios + Acessos)
- Status card sticky no topo com cor do tier ativo
- Filtro temporal no Painel (Mês atual / 3m / 6m / 12m) com delta MoM por KPI
- Aba **Performance** dedicada: range custom + chart SVG de GMV + tabela completa + export CSV
- Aba **Acessos**: entregáveis por tier com state locked/unlocked + ícones SVG geométricos
- Aba **Copy IA** (Claude API)
- Aba **Scripts** (histórico de copy gerada)
- Banner Wide Leg Marmorizada (anúncio R$ 99,90 + comissão +25%)
- Tabela responsiva (card-stacked no mobile via `data-label`)

### Admin (`rhode-vercel/public/admin.html`)
- Mesmo sistema visual
- Aba **Analista IA**: resumo cognitivo (Claude) + matriz de oportunidade 4 quadrantes (Stars / Cash Cows / Hidden Gems / Dormentes) + anomalias z-score + movimento MoM + análise IA por creator individual
- Aba **Evento 13/04** com VIP feed live + check-in de kit/live/follow-up
- Paginação automática (`sbGetPaged`) — não trunca mais em 1000 linhas
- Tiers alinhados com o programa atual

### Acesso (`rhode-vercel/public/acesso.html`)
- Fluxo de 2 telas: digita @ → WhatsApp + cria PIN num form só
- Auto-cadastro de phone para creators sem registro
- Rate limit client-side (5 tentativas / 5min cooldown por handle)
- Backend delay 1s anti brute-force

### ETL (`agente_rhode/etl_v2.py`)
- Disparo automático via GitHub Actions em push de `.xlsx` em `dados/creators/exports/`
- `pick_canonical_per_period()`: escolhe 1 arquivo por mês (Creator_List preferido, início dia 01, maior cobertura)
- Sanity check aborta se >30% das creators ativas têm `gmv_bruto = 0` (proteção contra renomeação silenciosa de colunas pelo TikTok)
- Aliases de header cobrem variações do TikTok ("a afiliados" e "ao criador")

### Sync Supabase (`agente_rhode/sync_supabase.py`)
- DELETE-then-UPSERT por período (remove creators fantasma de snapshots antigos)
- Dedup por (affiliate_id, periodo)

### Auditoria (`audit_data.py`)
- Compara exports canônicos vs Supabase, detecta divergências por KPI com tolerância configurável

### API
- `/api/get-hub.js` — auth com PIN, auto-cadastro de phone
- `/api/analyst.js` — Claude API para análise period/creator
- `/api/copy.js` — geração de copy IA
- `/api/relay.js` — Typebot bridge para Z-API
- `/api/cron-tier-milestones.js` — cron de milestones de tier
- Z-API integrado para envio de WhatsApp

---

## 🚧 Em desenvolvimento

_(nada no momento)_

---

## 🔜 Próximos — priorizados

### ✅ ~~1. Amostras Enviadas (admin)~~ — concluído mai/2026

**Entregue:**
- Tabelas Supabase: `produtos` (10 SKUs pré-cadastrados) + `amostras_enviadas` + view `amostra_roi_por_sku`
- Aba "Operação" no admin com sub-aba "Amostras"
- 4 KPIs (custo mês · qtd mês · acumulado ano · top SKU)
- Form quick-add com autocomplete de creator e tier auto-snap
- Tabela com filtros (período, busca por creator/SKU)
- Edição inline de `data_recebimento` direto na tabela
- Vista de ROI por SKU (cruzamento com performance_periods, janela 60d pós-envio)

**Pendente (não-bloqueante):**
- Importação automática do export TikTok `affiliate/estatisticas/detalhes` filtro Amostras
- Aba "Suas amostras" no hub das creators (visão da creator do que ela recebeu)
- Custo unitário por SKU em `produtos.custo_unitario` (atualmente NULL — preenchimento manual quando souber)

---

### ✅ ~~2. Flash Sales (admin + pop-up no hub)~~ — concluído mai/2026

**Entregue:**
- Tabela Supabase `flash_sales` + view `flash_sales_ativas` (computa status em runtime)
- Admin sub-aba "Flash Sales" em Operação:
  - Lista com filtros (Todas / Ativas agora / Agendadas / Expiradas)
  - Form modal de criação com SKU + janela datetime + tier mínimo + briefing
  - Atalhos de duração (2h / 6h / 12h / 24h / 48h / 7d)
  - Cálculo automático preço↔desconto bidirecional
  - Toggle pause/ativar sem apagar
- Hub das creators:
  - **Banner sticky vermelho** abaixo da global nav com countdown ao vivo (HH:MM:SS)
  - **Modal pop-up automático** na primeira visita da sessão (sessionStorage)
  - Filtra por `tier_minimo` da creator + `creators_convidadas` (se especificado)
  - Banner desaparece automaticamente quando expira

**Pendente (não-bloqueante):**
- Flash sale multi-SKU (hoje 1 flash = 1 SKU; pra promover N SKUs cria N flashes)
- Notificação Z-API quando flash é criada/iniciada
- Tracking: vendas atribuídas ao link da creator durante a flash

---

### ✅ ~~3. Status de Pagamento de Comissão (admin + hub)~~ — concluído mai/2026

**Entregue:**
- 4 colunas novas em `performance_periods`: `pagamento_status` (pendente/pago/disputado/ajustado), `pago_em`, `comissao_paga`, `pago_obs`
- Admin Ranking: nova coluna "Comissão" e "Pgto" com badges visuais (✓ Pago / Pendente / Disputado / Ajustado)
- Resumo no header da busca: "Pago R$ X (N) · Pendente R$ Y (M)"
- Modal "💰 Marcar pagamentos em lote" com filtros (período + tier + valor min)
- Preview ao vivo da quantidade afetada e do valor total antes de confirmar
- PATCH em batches de 100 creators
- Hub: card de "Próximo pagamento" vira "✓ Pagamento confirmado" verde quando paga
- Hub: lista de períodos mostra "✓ pago DD/MM" em verde nas barras

**Pendente (não-bloqueante):**
- `comissao_paga` específico por linha (atualmente herda de `comissao` quando não setado)
- Histórico de auditoria (quem marcou como pago)

---

### 4. Disparo Segmentado via Z-API (admin)

**Por que:** Z-API já funciona (`request-access.js`, `disparar_hub.py`). Falta UI e templates pra escalar comunicação.

**Admin:**
- Tela "Comunicação" com filtros: tier, GMV range, refund crítico, status missão
- Templates pré-aprovados (lançamento, parabéns tier, alerta refund, briefing live)
- Preview antes de enviar
- Histórico de disparos (auditoria de quem recebeu o quê)

**Schema:**
```sql
CREATE TABLE disparos_log (
  id BIGSERIAL PRIMARY KEY,
  template_id TEXT,
  filtro_aplicado JSONB,
  total_enviados INT,
  total_falhas INT,
  enviado_por TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Esforço:** ~2 dias.

---

### 5. Catálogo de Lançamentos (hub)

**Por que:** hoje creator descobre lançamento por WhatsApp. Conecta com #1 (Amostras).

**Hub:**
- Aba ou seção "Lançamentos" com SKUs novos dos últimos 30 dias
- Foto, preço, comissão dela aplicada
- Botão "Pedir amostra" → grava em `amostras_enviadas` com `origem='solicitacao_creator'`
- Aparece no admin para aprovação/envio

**Schema:** reusa `amostras_enviadas` + tabela `produtos`:
```sql
CREATE TABLE produtos (
  sku TEXT PRIMARY KEY,
  nome TEXT,
  foto_url TEXT,
  preco NUMERIC,
  data_lancamento DATE,
  ativo BOOLEAN DEFAULT TRUE
);
```

**Esforço:** ~1.5 dias.

---

### 6. Inbox de Notificações (hub)

**Por que:** reduz dependência de WhatsApp para comms operacionais.

**Schema:**
```sql
CREATE TABLE notificacoes (
  id BIGSERIAL PRIMARY KEY,
  creator_id TEXT NOT NULL,
  tipo TEXT,
  titulo TEXT,
  corpo TEXT,
  link TEXT,
  lida BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Hub:**
- Sininho no topo com contador de não-lidas
- Drawer com lista
- Persistência por creator

**Disparadores:**
- `cron-tier-milestones.js` (já existe) — "Você subiu pra Silver"
- Novo cron: refund alto, live oficial agendada, novo lançamento

**Esforço:** ~1.5 dias.

---

### 7. Onboarding de Novas Afiliadas (admin)

**Por que:** hoje há gap entre "TikTok aprovou" e "creator aparece no admin com 1 venda". Sem fluxo de bootstrap.

**Admin:**
- Aba "Pendentes": creators recém-criadas em `affiliates` sem PIN ainda
- Botão "enviar boas-vindas + link do hub" (Z-API)
- Template de boas-vindas com link de `acesso.html`

**Esforço:** ~1 dia.

---

## 🅿️ Parking lot (não priorizado)

| Item | Por que está aqui |
|------|-------------------|
| **Coach proativo no hub das creators** | Sistema detecta padrões e sinaliza pra creator: *"Suas lives estão convertendo melhor que vídeos — produza mais lives essa semana"*, *"Você recebeu 2 amostras semana passada e ainda não postou"*, *"Seu refund está em 22% — revise o tamanho que está indicando no link"*. Requer engine de regras + UI de cards de insight no hub. Conversado com user mai/2026, fica para depois das integrações operacionais (amostras, flash sales, pagamentos) maduras. |
| TikTok Analytics nativo | Depende OAuth do TikTok. 2-3 semanas de trabalho. ROI baixo (creator já vê no painel dela) |
| Order List ETL (granularidade diária + por-SKU) | Depende de novo export que não está sendo baixado. Útil quando precisarmos de "qual SKU vende mais por creator" |
| Remover alias antigo `dash.rhodejeans.com.br` do projeto Vercel | URL não usada oficialmente — usuário pediu para nunca mencionar/testar contra ela. Alias ainda existe tecnicamente. Remover quando for prudente. |
| OTP via WhatsApp na primeira vez | Custo R$ 0,03/acesso. Mata vetor TOFU. Implementar quando aparecer caso real de hijack |
| Rede social creator-creator | Custo de moderação alto. Risco de virar tóxico. Sem ROI claro |
| Gamificação avançada (badges, streaks) | Sistema de tier+missões já cobre 80%. Mais badges = ruído visual |
| Audit Tipo 2 (spot-check com TikTok Shop) | Precisa do usuário fazer manualmente. Pendente |

---

## 🧠 Decisões arquiteturais (log)

| # | Decisão | Por quê | Quando |
|---|---------|---------|--------|
| 1 | Sistema visual Apple-inspired com Inter + JetBrains Mono | SF Pro é proprietário; Inter é o substituto open-source mais próximo | abr/26 |
| 2 | Rhode Red (#FE2C55) como single accent | Apple usa Action Blue; mantemos a gramática do single-accent mas com cor da marca | abr/26 |
| 3 | Cor de identidade por tier (Bronze copper, Silver slate, Gold amber, Diamond cyan, Black dark) | Diferenciação visual sem competir com Rhode Red (que sinaliza ESTADO, não tier) | abr/26 |
| 4 | Supabase como fonte de verdade, não localStorage | localStorage não sincroniza entre dispositivos; data não fica auditável | mar/26 |
| 5 | Granularidade mensal (não diária) | Export `Creator_List` do TikTok não tem `transactionDate`. Order List teria mas não está na pipeline | abr/26 |
| 6 | URL canônica única: `creators.rhodejeans.com.br/...` | User definiu como regra firme. Não usar ou referenciar outros domínios mesmo que tecnicamente alcancem o mesmo projeto. | mai/26 |
| 7 | Trust-on-first-use no auth (sem OTP) | Custo zero, complexidade baixa. Risco aceito até primeiro caso de hijack | mai/26 |
| 8 | ETL processa 1 arquivo canônico por mês | Snapshots intermediários geravam duplicatas e o dedup pegava o errado | mai/26 |
| 9 | DELETE-then-UPSERT no sync_supabase | Sem isso, creators que somem do export ficavam fantasmas | mai/26 |
| 10 | Tiers Bronze 20k / Silver 50k / Gold 80k / Diamond 150k / Black 500k (GMV acumulado lifetime) | Calibrado em cima de 982 creators reais — 8% atinge Bronze | abr/26 |

---

## ⚠️ Riscos conhecidos

| Risco | Mitigação atual | Próximo passo |
|-------|-----------------|---------------|
| TikTok renomear coluna do export silenciosamente | `etl_v2.py` aborta se >30% das creators ativas tiverem `gmv_bruto = 0` | Monitor das colunas no GitHub Actions |
| Hijack de @ via TOFU no auth | Delay 1s no PIN errado + rate limit client-side 5/5min | OTP via WhatsApp se ocorrer caso real |
| Deploy do hub afeta admin (mesmo projeto Vercel) | Documentado | Separar em 2 projetos quando user pedir |
| ANTHROPIC_API_KEY tem custo recorrente | Cache em memória do navegador para análises | Cache em Supabase para análises históricas |
| Sem rate limit server-side | localStorage suficiente para casos comuns | Implementar quando ataque automatizado for detectado |
| GitHub Actions pode rodar ETL com `raw_imports.csv` desatualizado e regredir | Workflow baixa do Sheets antes — verificar se Sheets está sempre OK | — |

---

## 📋 Como me invocar

| Quando | Diga | Eu faço |
|--------|------|---------|
| Quero ir para a próxima feature | "vamos pra próxima do roadmap" | Leio ROADMAP.md → pego item #1 de 🔜 → começo |
| Quero pular pra item específico | "vamos para o item X (ex: Flash Sales)" | Leio o escopo do item X → começo |
| Quero adicionar coisa nova | "adiciona no roadmap: [descrição]" | Atualizo a seção apropriada |
| Sistema quebrou | "tem um problema, [breve descrição]" | Leio RUNBOOK.md → diagnóstico → fix |
| Quero revisar status | "qual o estado atual do projeto" | Resumo desse arquivo |
