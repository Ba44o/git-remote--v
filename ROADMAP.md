# Rhode Creator Hub — Roadmap

> **Como usar este arquivo:** fonte de verdade do projeto. Antes de iniciar trabalho novo, leia daqui em diante. Atualizar conforme features são concluídas ou repriorizadas.
>
> **Última atualização:** 2026-05-11

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
- Aba **Novidades**: catálogo de lançamentos curado (`NOVIDADES_SKUS` em hub.html) + botão "Pedir amostra" → fluxo de solicitação
- Tabela responsiva (card-stacked no mobile via `data-label`)
- **Tracking de comportamento**: `Track` (sendBeacon-like via fetch keepalive) grava `session_start`/`tab_view`/`session_end`/`action` em `hub_eventos` → consumido pela aba Comportamento do admin

### Admin (`rhode-vercel/public/admin.html`)
- Mesmo sistema visual
- Aba **Analista IA**: resumo cognitivo (Claude) + matriz de oportunidade 4 quadrantes (Stars / Cash Cows / Hidden Gems / Dormentes) + anomalias z-score + movimento MoM + análise IA por creator individual
- Aba **Comunicação**: disparo segmentado via Z-API com 7 templates pré-aprovados, filtros (tier, GMV range, refund, inativas, handles), preview dry-run, lote de 30/chamada, histórico auditável
- Aba **Comportamento**: analytics do hub das creators — tempo médio por sessão e por aba, abas mais vistas, distribuição por horário, creators mais ativas, ações registradas (copy gerada, amostra solicitada), últimas sessões. Dados de `hub_eventos` (tracking client-side no hub via fetch keepalive)
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
- `/api/disparo.js` — disparo segmentado via Z-API com filtros (tier, GMV, refund) e templates pré-aprovados
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

### ⛔ 3. ~~Status de Pagamento de Comissão~~ — REVERTIDO mai/2026

**Por que rejeitado:** comissão de venda é calculada e paga pelo **TikTok Shop** direto pra creator, não pela Rhode. Tentar replicar status no hub geraria divergência com a fonte oficial (creator vê no painel TikTok dela). Rhode não tem visibilidade nem controle sobre esse pagamento.

**Substituído por:** extensão da aba **Amostras → Entregas Rhode** (item 3.1 abaixo) — trackeia só o que a Rhode efetivamente entrega: placa de tier, kit surpresa, spark ads boost, prêmios de campanha.

**Manteve:** apenas a coluna "Comissão (R$)" no Ranking do admin (informativa, mostra valor estimado pago pela TikTok). Removido: badge "Pgto", botão "Marcar pagamentos", modal, schema `pagamento_status/pago_em/comissao_paga/pago_obs`.

---

### ✅ 3.1. Entregas Rhode (extensão da aba Amostras) — concluído mai/2026

**Entregue:**
- Coluna `tipo` em `amostras_enviadas`: `amostra` · `placa_tier` · `spark_ads` · `kit_surpresa` · `premio_evento` · `outro`
- `sku` virou opcional (tipos sem produto não precisam)
- Form do admin: dropdown de tipo controla se mostra produtos (amostra) ou bloco genérico (placa/spark_ads/kit/etc)
- Tabela do admin: nova coluna "Tipo" com ícone (📦/🏆/🚀/🎁/🎊/✨); coluna "Conteúdo" mostra produtos OU label do tipo
- Hub: card "Tarefas Rhode" adapta título, ícone e CTA por tipo:
  - Amostra: "Você recebeu amostras Rhode" + lista de SKUs
  - Placa: "🏆 Sua placa de tier chegou"
  - Spark Ads: "🚀 Spark Ads Rhode no seu conteúdo"
  - Kit surpresa: "📦 Sua caixa Rhode chegou"
  - Prêmio: "🎊 Você ganhou um prêmio Rhode"

---

### ✅ 4. Disparo Segmentado via Z-API (admin) — concluído mai/2026

**Entregue:**
- Schema `mensagens_templates` com 7 templates pré-aprovados (acesso_hub, boas_vindas, tier_up, alerta_refund, briefing_live, lancamento_sku, reativacao) + `disparos_log` pra auditoria · `rhode-vercel/sql/comunicacao.sql`
- Endpoint `POST /api/disparo` com modo `dry_run` (preview sem disparar) e modo real · `rhode-vercel/api/disparo.js`
- Filtros aplicados server-side: tiers (multi-select), GMV range (min/max), refund mínimo, apenas inativas, handles específicos
- Renderização de templates com variáveis `{{nome}} {{handle}} {{tier}} {{tier_comissao}} {{gmv_total}} {{refund_pct}} {{link_hub}}` (gera `access_token` automaticamente se template usar `{{link_hub}}`)
- Rate limit de 5min entre disparos + lote máximo de 30 envios por chamada (limite Vercel) com pausa de 1.5s entre cada
- Aba "Comunicação" no admin: template picker, filtros visuais com pills, dry-run preview com 3 alvos de amostra, confirmação antes de disparar, histórico dos últimos 30 disparos com KPIs do mês

**Decisão arquitetural:** opção por enviar em lotes pequenos (30/chamada) ao invés de queue async — simplicidade > volume. Se algum dia precisar disparar pra 500+ creators de uma vez, migrar pra Vercel Queue ou Inngest.

---

### 🟡 4.1. Performance Diária da Loja — **código no main, ativação adiada** (mai/2026)

**Status:** código merged em `main` e deployado, mas **inerte** porque a tabela
`performance_diario` ainda não foi criada no Supabase e o sync não rodou.
A sub-aba "Diário" no admin existe e mostra erro (`relation does not exist`)
até a ativação acontecer. Decisão de adiar: economia de tempo operacional —
retomar em sprint dedicada.

**Código pronto (commit `c14aea3`):**
- SQL idempotente: [rhode-vercel/sql/performance_diario.sql](rhode-vercel/sql/performance_diario.sql) — 1 linha/dia, loja toda, com GMV bruto/líq, pedidos, cancelados, itens, clientes, ticket, taxa_cancel
- ETL: [agente_rhode/etl_diario.py](agente_rhode/etl_diario.py) — lê aba "Diario" dos `Overview_*.xlsx`, dedup por data (mantém snapshot mais recente do mtime), exporta `warehouse/raw_diario.csv`
- Sync: `sync_performance_diario()` em [agente_rhode/sync_supabase.py](agente_rhode/sync_supabase.py) — UPSERT por `data` PK
- Admin UI: sub-aba "Diário (loja toda)" em Evolução, ao lado de "Mensal (por creator)" — chart SVG bar (filtros 30/60/90/Tudo) + tabela com Δ vs dia anterior + KPIs do recorte

**Pra ativar quando der (3 passos manuais):**
1. Aplicar o SQL no Supabase SQL Editor (cola conteúdo de `rhode-vercel/sql/performance_diario.sql`)
2. Rodar ETL local com `python3 agente_rhode/etl_diario.py` (já testado: 34 dias 18/02→23/03)
3. Sync com `python3 agente_rhode/sync_supabase.py --only performance_diario` (precisa `SUPABASE_SERVICE_KEY` no env)

**Janela coberta hoje:** apenas 18/02→23/03 (Overview xlsx em `dados/marketplace/tiktokshop/`). Pra estender, rodar `python3 coletar_dados.py --dias N` ou exportar manualmente do painel TikTok antes do passo 2.

**Decisão arquitetural (escopo):** granularidade *shop-wide diária* — NÃO é por creator/dia. Pra ter creator×dia precisaria de outro coletor (TikTok Order List API com timestamps individuais), trade-off não compensava esta sprint. O Transaction_Analysis export do TikTok não traz coluna de data — vem agregado da janela.

**Polimentos pra próxima sprint:**
- Trigger automático em GitHub Actions ao push de `Overview_*.xlsx` (mesmo padrão do `etl_v2.py`)
- Comparação YoY no chart (overlay do mesmo dia ano anterior)
- KPI "MTD vs MoM-pace" no Dashboard (projeção do mês baseada nos dias decorridos)
- UX: detectar `42P01` no admin e mostrar mensagem amigável ("feature aguarda ativação — ver ROADMAP 4.1") em vez do erro cru

---

### ✅ 5. Catálogo de Lançamentos (hub) — concluído mai/2026

**Entregue:**
- Migration `rhode-vercel/sql/lancamentos.sql`: adiciona `aprovada BOOLEAN DEFAULT TRUE` + `solicitada_em TIMESTAMPTZ` em `amostras_enviadas` (existing rows preservadas como aprovadas=true) + index parcial pra pendentes + RLS hardened
- **Hub** ganha 6ª aba "Novidades" na bottom-nav (3ª posição, entre Performance e Copy):
  - Lista produtos com `created_at >= hoje-30d` e `ativo=true`, ordenados desc
  - Card por produto: foto, nome, categoria, preço, **comissão da creator aplicada** (calculada via `TIER_COMM_PCT` do disparo.js — Bronze 10% / Silver 11% / Gold-Diamond-Black 12%)
  - Tag "Novo · Xd" (vermelho se ≤7d, cinza ≥8d)
  - Botão "Pedir amostra" → POST direto via anon key, idempotente (cache local de SKUs já solicitados → botão fica "✓ Solicitada")
- **Admin** (Operação > Amostras) ganha banner "🔔 X solicitações pendentes" no topo, antes dos KPIs:
  - Lista de pedidos vindos do hub com creator, tier, SKU+nome do produto, idade do pedido (Xmin / Xh / Xd)
  - **Aprovar:** UPDATE aprovada=true + data_envio=hoje (admin pode editar depois pela tabela normal)
  - **Recusar:** UPDATE dispensada=true (preserva histórico, some das listas)
- Reusa `data_lancamento` como `created_at` da tabela `produtos` — quando o sync_catalogo puxa SKU novo do `rhodejeans.com.br`, é o "lançamento" pro hub

**Decisão arquitetural:** sem tabela `solicitacoes_amostra` separada — o roadmap original sugeria reusar `amostras_enviadas` com `origem='solicitacao_creator'` (o CHECK constraint já permitia). Adicionei só `aprovada` + `solicitada_em` em vez de criar tabela nova, simplificando o admin. Item 4.1 dos pendentes desbloqueia: ROI por SKU já cruza com performance_periods, então pedidos aprovados entram no funil sem mudança.

**Pra ativar:** rodar `rhode-vercel/sql/lancamentos.sql` no SQL Editor do Supabase. Sem isso, a 6ª aba do hub vai 404 ao tentar inserir e o admin vai mostrar a query falhando (graceful — erro visível, não quebra outras features).

**Pendente (não-bloqueante):**
- Notificação Z-API quando admin aprova ("@creator, sua amostra foi aprovada!") — reusar template engine de #4
- Filtro no admin: ver pendentes por tier ou por idade do pedido
- Card de "Novidades" também no Painel (home) com 3-4 destaques + link "ver todos"

---

### ✅ 6. Inbox de Notificações (hub) — concluído mai/2026

**Entregue:**
- Schema `rhode-vercel/sql/notificacoes.sql`: tabela `notificacoes(id, creator_id, tipo, titulo, corpo, link, lida, created_at, read_at)` + index principal `(creator_id, lida, created_at desc)` + RLS anon all
- **Hub** ganha botão sininho `position:fixed` top-right (sempre visível em qualquer aba):
  - Badge vermelho com contador de não-lidas (pulsa via `notifPulse` 2s)
  - Drawer slide-in da direita (90vw mobile, 420px desktop) com lista
  - Item lê: ícone categorizado (🏆 tier, 📦 amostra, ⚡ flash, ✨ lançamento, ⚠️ alerta, 🤍 sistema), título, corpo, label de tempo (agora/min/h/d/data)
  - Click no item: PATCH lida=true + read_at + se tem `link` interno (regex `^[a-z]+$`) chama `goTab(link)`, senão abre URL externa
  - "Marcar todas" no header → bulk PATCH WHERE lida=false
  - Polling: setInterval 60s + listener `visibilitychange` (recarrega quando volta pra aba)
  - Bootstrap automático no fim de `boot()` após creator identificado
- **Disparador piloto** plugado no admin (Operação > Amostras):
  - `aprovarSolicitacao` → cria notif `tipo='amostra_aprovada'`, link='novidades'
  - `recusarSolicitacao` → cria notif `tipo='amostra_recusada'`
  - Helper `createNotif(creatorId, tipo, titulo, corpo, link)` é best-effort (try/catch silent), não quebra o fluxo de aprovação se a tabela não existir ou o POST falhar
- Tipos canônicos definidos no SQL header: `amostra_aprovada · amostra_recusada · tier_up · flash_sale · lancamento · alerta_refund · sistema`

**Pra ativar:** rodar `rhode-vercel/sql/notificacoes.sql` no SQL Editor do Supabase. Sem isso, sininho vai mostrar "Nada por aqui ainda" (a query falha silenciosa) e o admin vai aprovar/recusar normalmente — só perde a notificação no inbox.

**Pendente (não-bloqueante, próximas sprints):**
- Disparador automático no `cron-tier-milestones.js`: criar notif `tipo='tier_up'` ao detectar marco (hoje só notifica operador via Z-API; estende para criar notif do creator também)
- Disparador no cron de flash sales: notif `tipo='flash_sale'` quando flash entra em janela
- Disparador no `sync_catalogo.js`: notif `tipo='lancamento'` em batch quando N produtos novos forem criados num sync
- Cron de alertas: refund>25% por creator → notif `tipo='alerta_refund'` (deduplicação semanal pra não spammar)
- Push real (FCM/APNS) — drawer in-hub já cobre 80%, push é next-level

---

### ✅ 7. Triagem de Creators Novas + Redirecionamento (`bem-vinda.html`) — concluído mai/2026

**Por que:** havia gap entre "TikTok aprovou / creator chegou" e "creator no caminho certo". A `bem-vinda.html` antiga só classificava por `modelo`/GMV com `CONFIG` vazia e sem formulário — virou um fluxo de triagem multi-step de verdade.

**Entregue (`rhode-vercel/public/bem-vinda.html` — reescrita):**
- Máquina de estado client-side, 2–4 passos conforme o caminho, visual Plus Jakarta (consistente com o hub)
- **Pergunta 1 — relação com a Rhode:** já vendo / já me afiliei mas não vendi / sou creator mas não me afiliei / só quero flash sale
- **Pergunta 2 (só "já vendo") — faixa de GMV declarado:** R$0 / até 5k / 5–20k / 20–80k / +80k
- **Pergunta 3 — tem peça Rhode em casa:** sim / não / quero modelos novos (controla o CTA de amostra)
- **Identidade no fim:** nome + @ TikTok + WhatsApp → grava em Google Sheets via Apps Script (`CONFIG.sheetsTriagemURL`, mesmo padrão de `cadastro.html`; vazio = não grava)
- **8 diagnósticos → cards de destino:** `vip` (grupo Rhode VIP + hub + contato direto) · `parceira_track` (grupo Rhode em Ação + hub + flag p/ time) · `fechado` (grupo Rhode em Ação + hub + amostra se precisar) · `ativar` (passo a passo da 1ª venda + amostra + grupo + hub) · `nova_com_peca` (convite afiliada TikTok Shop + cadastro + "grava já") · `nova_sem_peca` (convite + cadastro + solicitar amostra) · `flash_only` (WhatsApp da equipe com msg pré-preenchida → lista de avisos de flash) · `onboarding` (fallback: cadastro + WhatsApp)
- Cada card tem `steps-list` (passo a passo numerado) quando faz sentido + CTAs priorizados
- **Token de afiliada já cadastrada** (`?token=`) → pula a triagem, classifica direto por `modelo`/GMV-60d real (`classifyKnown`); token de `eventos_creators` → pré-preenche e roda a triagem; token inválido / sem token → triagem normal
- Modos de teste: `?triagem=1` força o questionário · `?diagnostico=vip&peca=nao` faz preview de card · `?gmv=&nome=&modelo=` compat com o teste antigo
- `bem-vinda.html` adicionado ao regex de `no-cache` em `vercel.json`

**Pendente (não-bloqueante — preencher e redeployar):**
- `CONFIG.linkGrupoVIP`, `CONFIG.linkGrupoAcao` — convites dos grupos de WhatsApp
- `CONFIG.linkAfiliacaoTikTok` — link do convite de colaboração da Rhode no TikTok Shop
- `CONFIG.linkFormAmostra` — Google Form / página de solicitação de amostra (hoje cai no WhatsApp da equipe)
- `CONFIG.sheetsTriagemURL` — Apps Script `doPost` da planilha de Triagem (campos: tipo, nome, tiktok/handle, whatsapp, relacao, gmv_faixa, tem_peca, diagnostico, origem, ts)
- Admin: aba/visão "Triagem" lendo a planilha (ou tabela própria) — quem caiu em cada bucket, conversão por diagnóstico
- Auto-disparo Z-API pós-triagem (boas-vindas + link do grupo) reusando o template engine do #4
- Promover automaticamente `parceira_track` → criar alerta no admin pra avaliar entrada no grupo VIP

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
