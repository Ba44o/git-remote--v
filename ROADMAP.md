# Rhode Creator Hub — Roadmap

> **Como usar este arquivo:** fonte de verdade do projeto. Antes de iniciar trabalho novo, leia daqui em diante. Atualizar conforme features são concluídas ou repriorizadas.
>
> **Última atualização:** 2026-06-01

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

### Launch Video Infra (`tools/onboarding-recorder/` + `?demo=tour` no hub)
- **Tour mode** no hub.html (`?demo=tour`): bypassa auth com token preview, anonimiza nome/handle/cupom (Júlia + RHODEJÚLIA), suprime chrome (modais, sininho, suporte), navega autopilot pelas abas com cursor fantasma
- **Motion CSS** estilo Anthropic (`body.tour-mode`): panel crossfade, stagger fade-up cascading, Ken Burns sutil no #app, cursor com curve serena
- **Recorder Playwright + ffmpeg-static**: gera mp4 1:1 / 9:16 / 16:9 h264+AAC silencioso (WhatsApp-compat), cache buster CDN automático
- Uso: `cd tools/onboarding-recorder && node record.js --mode=tour --aspect=1x1 --duration=55`
- Documentação: [tools/onboarding-recorder/README.md](tools/onboarding-recorder/README.md)
- Reusável pra qualquer página (admin, dash-live, /flash, futuras landings) — basta implementar `?demo=tour` na página alvo

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

### ✅ 8. Hardening de Segurança e Escala — **CONCLUÍDO** (jun/2026)

**✅ ENTREGUE (jun/2026):** vazamento fechado. Todo o frontend (hub, bem-vinda, admin, cadastro, dash-live) lê/escreve via proxy autenticado `/api/get-hub` (service key no servidor). RLS deny-anon ligado em 21 tabelas sensíveis — probe confirma anon=0 linhas em `affiliates`/`eventos_creators`/`performance_periods`/etc; hub e admin idênticos (R$ 275.425,32 / R$ 2,7M batem). Admin com auth real (token server-side, não bypassável) + paginação server-side (sync 52s→6s). Service key saiu do source de 9 `api/*.js` → `process.env`. Detalhes por incremento: commits `852f0af` (Inc.1 Hub), `faaaa02` (Inc.2 Admin), `1770c30` (cadastro), `d14a611` (dash-live). SQLs: `sql/rls_hardening.sql` (rodado) + `sql/rls_dashlive.sql` (lives/store_daily).
**Pendências (não-bloqueantes):** (1) rodar `rls_dashlive.sql` p/ trancar lives/store_daily; (2) **rotação da service key** — a antiga está no histórico do git, mas **repo é privado e só o dono acessa → risco baixo**, rotação é boa prática pra "um dia" (rotacionar o JWT secret troca a anon junto → exige trocar anon no source de 4 arquivos + env + redeploy). Realtime nas notificações e gate de "1ª venda" (sub-partes originais 2 e 4) ficaram fora — são melhorias, não o vazamento; reabrir como itens próprios se quiser.

<details><summary>Contexto histórico (o risco que foi fechado)</summary>

**Contexto — risco conhecido e confirmado:** hoje todas as tabelas têm `RLS DISABLE` + policy `anon all (true)`, e a `anon key` do Supabase está no source de `hub.html`/`admin.html`. Consequência: qualquer pessoa que abrir o source, copiar a anon key e mandar `GET /rest/v1/affiliates?select=affiliate_id,access_token,pin_acesso` baixa **todos os `access_token` e `pin_acesso`** (= login bypass de qualquer creator), **todos os WhatsApp** (`eventos_creators.whatsapp`) e **GMV das 4.926 creators**. A auth PIN+token é cosmética — validação é client-side e os dados por baixo estão abertos. Testado: o GET funciona. ⚠️ **Não ligar RLS antes do proxy estar pronto — derruba hub e admin na hora** (os dois leem PostgREST direto com a anon key).

**Plano (nesta ordem):**

1. **Fechar o vazamento — proxy via `/api/*` (caminho A escolhido):**
   - Toda leitura de dado sensível passa por serverless function que segura a `service_role` key no servidor e faz a checagem de token/PIN lá. Frontend nunca fala com PostgREST direto.
   - Já existe o padrão: `/api/get-hub.js` faz auth com PIN. Estender pra cobrir tudo que `hub.html` lê hoje (perf, profile, novidades, amostras, notificações) e o que `admin.html` lê.
   - Admin precisa de auth de verdade (hoje é `ADM_PASS='rhode2026'` checado client-side) — minimamente, mover o check pro servidor + rotas admin que exigem o header.
   - Depois que o proxy estiver no ar: `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` + policy `false` pra anon nas tabelas sensíveis (`affiliates`, `eventos_creators`, `performance_periods`, `amostras_enviadas`, `disparos_log`, `mensagens_templates`). `hub_eventos` pode ficar com insert anônimo (é só analytics).
   - Esforço: ~2-3 dias (reescrever data layer hub + admin + ~4-5 rotas novas).

2. **Realtime nas notificações (substitui o polling):**
   - Hoje `hub.html` faz `setInterval` 60s em `notificacoes` — escala linearmente com concorrência (hoje OK com dezenas de creators online; vira problema com centenas+).
   - Trocar por Supabase Realtime (WebSocket ouvindo a tabela). Tráfego só quando há notificação nova de fato.
   - Esforço: ~0.5-1 dia.

3. **RPCs de agregação (limpa o admin):**
   - Hoje o admin baixa ~5k linhas de `performance_periods` pra somar GMV client-side. Funciona (poucos MB, uso desktop por 1-2 pessoas) mas é sujo.
   - Criar functions Postgres (`select sum(gmv_liquido) ... group by periodo`) e o admin pede 1 linha em vez de 5k. Reduz transferência e memória.
   - Esforço: ~1 dia. Faria junto com o passo 1.

4. **Gate de acesso ao Hub por "1ª venda" (bloqueio duro, server-side):**
   - Hoje qualquer creator afiliada loga no Hub via `/acesso.html` mesmo com R$0 em vendas — o `/api/get-hub.js` não checa nada além de PIN/handle. A triagem (`bem-vinda.html`) já parou de **empurrar** o link do Hub pra quem não tem peça nem vendas (cards `ativar`/`nova`), mas o bloqueio é só "não mostrar o botão" — não impede o acesso direto.
   - **Regra a aplicar no `/api/get-hub.js`:** liberar o Hub só se a creator tiver ≥ 1 venda (algum `performance_periods.gmv_liquido > 0` OU `gmv_bruto > 0`) ou for parceira/VIP por `modelo`. Se não tiver, devolver uma resposta tipo `{ status: 'sem_acesso', motivo: 'primeira_venda' }` e o `acesso.html`/`hub.html` mostram a tela "faça sua primeira venda pra destravar o painel" (mesma mensagem do card `ativar` da triagem) em vez de carregar o dashboard.
   - Faz junto com o passo 1 (já vai mexer no data layer do Hub de qualquer jeito). Esforço incremental: ~0.5 dia.
   - Por que aqui: combina com a política da triagem ("não dar moral pra quem não provou") e o controle de amostra (amostra grátis só via missão/campanha) — fecha o loop pra não virar self-service de freebie.

**Decisão arquitetural pendente:** caminho A (proxy `/api/*` + RLS `false` pra anon) escolhido sobre B (RPC de validação de token + RLS por linha) e C (migrar pra Supabase Auth nativo) — A reaproveita o padrão `/api/get-hub.js` que já existe e resolve o admin (que lê todo mundo) sem complicação de policy. **← foi exatamente o caminho A que se implementou.**

</details>

---

### ✅ 9. Alinhar `TIER_RULES` do ETL ao programa público — concluído jun/2026

**Problema (primeira passada):** ETL tinha sistema legado `Ferro/Bronze/Prata/Ouro/Diamante` em 0/2k/8k/25k/60k @ 5/7/9/11/13%. Resolvido com TIER_RULES alinhado a 5 tiers + Iniciante em 20k/50k/80k/150k/500k.

**Problema (segunda passada — descoberto depois):** a primeira passada usou comissões `0/10/11/12/12/12%` (números da `hub.html TIERS` que estavam hardcoded e _também_ desalinhados). A fonte de verdade real é a [`parceria.html`](rhode-vercel/public/parceria.html) que publicamos com estrutura DUAL: **% orgânica + bônus em vendas via ADS**.

| Tier | Org | + ADS |
|---|---|---|
| Bronze (20k) | 8% | +3% |
| Silver (50k) | 9% | +3% |
| Gold (80k) | 10% | +3% |
| Diamond (150k) | 12% | +5% |
| Black (500k) | 12% | +5% |

**Entregue:**
- ETL [`etl_v2.py TIER_RULES`](agente_rhode/etl_v2.py): `rate` = org rate (8/9/10/12/12%) usado em `comissao_calculada` como projeção. ADS é condicional, não dá pra projetar sem split por tipo de venda.
- Hub [`hub.html TIERS`](rhode-vercel/public/hub.html): `comm:N` virou `commOrg:N, commAds:M`. Rendering atualizado (status card + benefit eyebrow) pra mostrar "8% + 3% ads" — bate visualmente com parceria.html.
- Hub [`TIER_COMM_PCT`](rhode-vercel/public/hub.html): atualizado pra org rate (Novidades mostra "ganho por venda" = org, que é o piso garantido). Adicionado `TIER_COMM_ADS` pra quando precisar do bônus.
- API [`disparo.js TIER_COMM`](rhode-vercel/api/disparo.js): templates WhatsApp `{{tier_comissao}}` agora renderizam `"8% (+3% em ads)"` explícito.
- Sync labels legados (ferro/prata/ouro/diamante/starter) → equivalentes novos via `cleanup_legacy_tier_labels()` em `sync_supabase.py` (mantido da primeira passada).
- ROADMAP estado atual e tabela de Riscos atualizados.

**Fonte de verdade:** `rhode-vercel/public/parceria.html`. Qualquer ajuste futuro de % parte dali e cascateia pros 4 lugares acima.

**Não muda:** `comissao` real (paga pelo TikTok Shop direto, vem do export). O `comissao_calculada` do ETL é só projeção/sanity-check com a % oficial orgânica.

---

### 🟢 10. Migrar dados por-creator pra API — **FORWARD-ONLY NO AR** (jun/2026)

**✅ ENTREGUE (forward-only, jun/2026):** Jan–Mai continuam do **export** (congelados, intocados); **Jun+ vem da API** (Affiliate Orders) direto na `performance_periods`. Implementado em `coletar_extrato.py::build_performance_forward` (roda no daily local — não dispara o etl_sync). Guarda `periodo >= FORWARD_FROM (2026-06)` protege o passado. `gmv_liquido = liquidado + a_liquidar` (exclui reembolso/inelegível; mesma base dos meses passados, não encolhe). Validado: Jan–Mai inalterados, junho R$96,5k/85 creators, Hub hero e admin passam a mostrar junho. **Ressalvas:** (a) creators 100%-novas de junho ficam de fora até existirem na `affiliates` (FK) — pequenas; (b) `vídeos`/`lives` de junho vêm da API (content_id distinto ≈ conteúdo que gerou venda), não do export. Coleta diária às 8h mantém fresco.

**Contexto histórico (a exploração que levou aqui):**
**Hoje:** o per-creator (Hub + ranking/mensal do admin → `performance_periods`/`affiliates`) vem dos **exports manuais xlsx/Sheets via `etl_v2.py`**. Só o shop-wide diário (`performance_diario`) é API (ver 4.1). Granularidade do per-creator: **mensal** (decisão #5 — o export `Creator_List` não tem `transactionDate`).

**Proposta:** trocar a fonte do per-creator de export manual → **Order List API** (`/order/202309/orders/search`, escopo **já ATIVO** — confirmado no probe, ver decisão #11). Cada pedido traz timestamp individual → dá pra montar **creator × dia** e eliminar o upload manual de planilha.

**Ganhos:** Hub e admin com dados diários por creator (não só mensal); fim da dependência de export manual; base pra automação tipo o 4.1 (cron semanal/diário).

**Trade-offs / perguntas em aberto (resolver antes de comprometer):**
- **Atribuição:** confirmar que o payload do Order List traz o identificador da creator/afiliada (handle/affiliate_id) por pedido. Se não trouxer, não dá pra fazer creator×dia direto — vira bloqueio.
- **Volume/rate limit:** 4.926 creators, milhares de pedidos/dia → paginação + rate limit. Order List API estoura timeout em janelas grandes (mesmo padrão do analytics — ver 4.1); vai precisar de chunking.
- **Consistência com a fonte oficial:** GMV/comissão por creator precisa bater com o painel TikTok da própria creator (hoje o export já é a fonte de verdade) — validar com `audit_data.py` antes de cortar o xlsx.
- **Escopo de impacto:** mexe no data layer do Hub → fazer **depois** do item 8 (hardening/proxy), pra não retrabalhar.

**Por que não foi feito agora:** ativação do 4.1 (shop-wide) era self-contained e não tocava o Hub. Migrar o per-creator é projeto à parte, com risco de impacto no Hub — exige sprint dedicada e validação de atribuição primeiro.

**⭐ ATUALIZAÇÃO jun/2026 — caminho mudou (melhor):** não é Order List, é a **Affiliate Orders API** (`/affiliate_seller/202410/orders/search`) — **já ATIVA e em uso** nos painéis de creator (Afiliadas/Seeding/Creator×Produto). Ela traz `creator_username` por pedido → creator×dia direto. Mapeamento do export `Creator_List` → API:

| Coluna do export | Vem da API? |
|---|---|
| Creator name, GMV atribuído, Pedidos, Itens vendidos, AOV, Média diária, Comissão estimada | ✅ direto (affiliate orders: `creator_username`, `estimated_commission_base`, `estimated_paid_commission`, `quantity`, `orders`) |
| Reembolsos, Itens reembolsados | ⚠️ do campo `fully_return` do affiliate order (+ refund amount via Return API, já ativa) |
| Vídeos, Transmissões ao vivo | ⚠️ `content_id` distinto por `content_type` (VIDEO/LIVE) — conta conteúdo que **gerou venda** (≈, não idêntico ao export que conta tudo) |
| Amostras enviadas | ⚠️ Target Collaborations (seeding, já ativa) |

→ ~80% mapeia direto; o resto (refund amount, contagem de vídeo/live, amostras) cruza com APIs que **já temos ligadas**. Caveat: o **Hub lê `performance_periods`** — a migração tem que continuar alimentando essa tabela (fonte API em vez de xlsx), e fazer **depois do item 8** (proxy).

**📦 ARMAZENAMENTO HISTÓRICO (esquema definido jun/2026):** o limite de 90 dias é só **por request** da API, não de storage. As tabelas Supabase **acumulam** (sync faz UPSERT por id-com-data, nunca DELETE) → histórico cresce pra sempre. Plano de "histórico que só cresce":
1. **Coleta diária incremental** — launchd diário puxando só ~14d (leve) + UPSERT → base cresce 1 dia/dia, sempre fresca (hoje o launchd é semanal · 90d).
2. **Backfill único** em chunks de 90d voltando até ~jan/2026 → popula o passado de uma vez.
3. **Janelas longas nos painéis** (180d/365d/Tudo) — filtro client-side, funciona pra qualquer período que a tabela tiver (não chama a API).
> Vale pra TODAS as bases via API (diário, finance, devoluções, affiliate_perf, creator_product). Implementar como feature dedicada.

**🔒 PROTOCOLO DE MIGRAÇÃO SEGURA (vinculante — definido com o usuário jun/2026).** A migração export→API alimenta a `performance_periods` que o **Hub das creators** lê. Regra firme do usuário: *não perder dado/informação e não afetar as usuárias do Hub* (ver memória `feedback_hub_dados_intocaveis`). A migração é segura **por construção**, nesta ordem:
1. **Shadow mode** — a ETL nova grava numa tabela SEPARADA (`performance_periods_api`), sem encostar na `performance_periods` que o Hub lê. Creators veem o de hoje durante toda a validação. Impacto zero.
2. **Validação número a número** — `audit_data.py` compara as duas por **creator × período** (GMV líq/bruto, pedidos, comissão, AOV, reembolso) com tolerância definida. Soma aliases de handle juntos (`natmarquesss`=`natmarquesvi`). Só avança quando bate.
3. **Aditivo, nunca destrutivo** — sync é UPSERT por id, NUNCA DELETE. Histórico só cresce.
4. **Snapshot antes do 1º write** na `performance_periods` real → restore point / rollback instantâneo.
5. **Cutover = flip de config, não move dado** — a ETL passa a alimentar a MESMA `performance_periods` (UPSERT). Hub não muda (mesma tabela, mesmo proxy). Se divergir, não flipa.
6. **Export de paraquedas** — roda export + API em paralelo por ~semanas; se a API abrir gap, o export preenche. Só desliga o export depois de estável.
7. **Coleta fail-loud** — coletor aborta em timeout/parcial (bug já corrigido), nunca grava pela metade.

**⭐ DECISÃO DE CAMPO (usuário escolheu "A", jun/2026):** GMV/pedidos/comissão/AOV/reembolso migram pra API (mapeiam 1:1). **`vídeos` e `lives` continuam vindos do EXPORT** — porque a definição diverge (export conta tudo que a creator postou; API contaria só o que gerou venda). Não trocar esses 2 campos pela API sem novo OK do usuário.

---

### 🔵 11. ROI de Seeding por SKU (v2b — atribuição cirúrgica) — **não iniciado** (jun/2026)

**Hoje (v2a, no ar):** painel "Seeding ROI" (admin → Evolução) cruza `amostras_enviadas` × `affiliate_perf` por creator (match handle lowercased). **Limitação conhecida:** o GMV é o **total de afiliação da creator (todos os produtos, 30d)**, não só o item seedado → ROI é **estimativa superestimada**. Custo da peça é premissa ajustável (custo real não está em `custo_unitario_snapshot`, 0% preenchido).

**v2b (atribuição real):**
- Re-coletar affiliate orders guardando `product_id`/`sku_id` → agregar **GMV por creator × SKU**.
- Mapear `sku_id` (numérico) → `seller_sku` (`REF...`) pra casar com `amostras_enviadas.sku` (via Product API ou tabela `produtos`).
- Janela "desde a `data_envio`" (hoje é fixo 30d) → ROI do **produto seedado** especificamente.

**Bônus de dados:** `amostras_enviadas.video_postado_em` está 0/55 e `confirmada_em` 4/55 — se preenchidos, dá pra mostrar "postou conteúdo?" e funil amostra→conteúdo→venda. Custo real por peça destravaria ROI monetário exato.

---

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

### ✅ 4.1. Performance Diária da Loja — **ativado via API** (jun/2026)

**Status:** **ATIVO.** Tabela `performance_diario` criada no Supabase e populada via
API (não mais xlsx manual). 89 dias carregados (2026-03-04 → 2026-05-31, GMV líquido
R$ 1.870.495,62). A sub-aba "Diário (loja toda)" do admin já popula direto.

**Fonte de dados (substituiu o xlsx):**
- ETL: [agente_rhode/etl_diario.py](agente_rhode/etl_diario.py) `--source api` (default) → puxa de `coletar_dados.buscar_analytics()` (`GET /analytics/202405/shop/performance`, ver decisão #12). Chunking de 10 dias + retry por chunk (API estoura timeout em janelas grandes) + respeito ao lag de ~2 dias (descarta dias não finalizados). Modo `--source xlsx` mantido como legado.
- Mapeamento API→coluna documentado em `_map_interval()`: `gmv_liquido = gmv − refunds`, `pedidos = orders`, `cancelados = cancellations_and_returns`, `itens = units_sold`, `clientes = buyers`, `ticket = avg_order_value`, `taxa_cancel = cancelados/pedidos`.
- Sync: `sync_performance_diario()` em [sync_supabase.py](agente_rhode/sync_supabase.py) — UPSERT por `data` PK. **Roda com `python3 agente_rhode/etl_diario.py --source api --dias N` + sync** (precisa `SUPABASE_SERVICE_KEY` no env).
- Admin UI: sub-aba "Diário (loja toda)" em Evolução — chart SVG bar (filtros 30/60/90/Tudo) + tabela com Δ vs dia anterior + KPIs do recorte.

**Próximos polimentos:** rodar ETL+sync via cron (semanal) pra manter atualizado; backfill < 03-04 se quiser histórico mais longo (rodar com `--dias` maior). ⚠️ Nota de consistência: linhas API-era usam `gmv_liquido = gmv − refunds`; se houver linhas antigas do xlsx (GMV_CF) pra datas sobrepostas, o UPSERT da API prevalece.

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

**Macro:** Manychat (capta a creator e manda o link) → **triagem** (`bem-vinda.html`, classifica) → **executável** (a ação concreta). A triagem é o roteador.

**Entregue (`rhode-vercel/public/bem-vinda.html` — reescrita):**
- Máquina de estado client-side, visual Plus Jakarta (consistente com o hub)
- **Pergunta 1 — relação com a Rhode (2 opções):**
  - "💸 Já sou afiliada da Rhode no TikTok Shop" → Passo 2 (faixa de GMV) → Passo 3
  - "✨ Quero me tornar uma Creator Rhode" (não-afiliada) → formulário (nome/@/WhatsApp) → card `analise` ("Na fila de análise" — equipe avalia o perfil no TikTok e te chama se fizer sentido pra uma campanha). **Fila de espera, não amostra de graça self-serve.**
- **Pergunta 2 (só "já sou afiliada") — faixa de GMV declarado:** R$0 (ainda não vendi) / até 5k / 5–20k / R$20k ou mais — gravada na planilha pra a equipe ver na hora da análise
- **Pergunta 3 (só "já sou afiliada") — "O que você quer fazer agora?" (4 opções):**
  - "👖 Ver meu lugar no programa" (tenho peça, já tô gravando) → formulário → card por GMV (`ativar` / `fechado` / `parceira_track`)
  - "📦 Pedir uma amostra grátis" (não tenho peça) → formulário → card `analise` (perfil pra análise)
  - "✨ Aplicar pra receber mais modelos" → tela `screenMaisModelos` explicando que **é sujeito ao desempenho e às metas** + botão "Aplicar — mandar meu perfil pra análise" → formulário → card `analise`
  - "⚡ Solicitar uma flash sale pra minha live" → redireciona direto pro WhatsApp do suporte (`CONFIG.whatsappEquipe`) com `CONFIG.flashSaleWhatsMsg`. *(Antes era opção do Passo 1; movido pra cá porque flash sale é coisa de quem já é afiliada.)*
- **Formulário (identidade):** nome + @ TikTok + WhatsApp → `saveTriagem()` faz INSERT na tabela Supabase **`triagem`** (`rhode-vercel/sql/triagem.sql`; campos: nome, handle, whatsapp, relacao, gmv_faixa, **pedido** (`ver_lugar`/`amostra_gratis`/`mais_modelos`/`quero_ser_creator`), tem_peca, diagnostico, origem, status, referrer, user_agent) — best-effort, igual `eventos_creators`/`hub_eventos`. Também faz POST opcional pro Google Sheets se `CONFIG.sheetsTriagemURL` estiver preenchido. É o "formulário rápido" — quem pede amostra/mais modelos/virar creator preenche aqui.
- **Cards de resultado:**
  - `analise` ("🤍 Na fila de análise") — "Recebemos teu cadastro, você entrou na fila. A equipe analisa teu perfil no TikTok…" + 4 passos. **Sem botão** (é confirmação, não tem ação).
  - `ativar` ("🚀 Bora ativar", afiliada R$0 + tem peça) — "grava e faz tua 1ª venda — ela destrava grupo + painel" (CTA "falar com a equipe"). *(A variante "sem peça" do card só aparece via `?diagnostico=ativar` sem `peca=sim` — no fluxo real, "sem peça" → `analise`.)*
  - `fechado` ("✅ Creator ativa", vendeu até R$20k) — grupo Rhode em Ação + hub + amostra se precisar.
  - `parceira_track` ("🔥 Quase Parceira", R$20k+) — grupo Rhode em Ação + hub + flag p/ time avaliar VIP.
  - `vip` ("⭐ Parceira VIP") — **só via `classifyKnown`** (token c/ `modelo=parceira` ou GMV-60d ≥ 80k), não auto-declarável. Fallback `onboarding` (cadastro + WhatsApp).
- **Princípio de gating:** hub e amostra só pra quem já vendeu (`fechado`/`parceira_track`/`vip`). Quem não vendeu ou não tem peça → vai pra `analise` (fila/análise do time). Amostra/peça de graça nunca é self-serve na triagem — sempre passa por análise (ou via missão/campanha). Cards `nova_com_peca`/`nova_sem_peca` removidos. `CONFIG.linkLojaRhode` = `rhodejeans.com.br` (usado só na variante de preview de `ativar`).
- **Admin → aba "Triagem"** (`admin.html`): lista das submissões (mais recentes primeiro) — nome, @ TikTok (link pro perfil + `·hist` que abre o histórico Rhode via `openModal`), WhatsApp (link wa.me), pedido, GMV declarado, badge "✓ R$X/mês" se a handle bate com uma afiliada no `performance_periods` do mês atual, e `<select>` de status (novo/em_analise/aprovada/recusada → PATCH na tabela). Filtros por tipo de pedido + busca por @ · 4 KPIs (total / 7d / pedidos de amostra / quer ser creator). Carregamento lazy via `loadTriagem()`.
- **Token de afiliada já cadastrada** (`?token=`) → pula a triagem, classifica direto por `modelo`/GMV-60d real (`classifyKnown`); token de `eventos_creators` → pré-preenche e roda a triagem; token inválido / sem token → triagem normal
- Modos de teste: `?triagem=1` força o questionário · `?diagnostico=analise|ativar|fechado|parceira_track|vip|onboarding` (`&peca=sim` p/ a variante de `ativar`) · `?gmv=&nome=&modelo=` compat com o teste antigo
- `bem-vinda.html` adicionado ao regex de `no-cache` em `vercel.json`

**Status:** ✅ tabela `triagem` criada no Supabase (12/05), teste end-to-end passou (ver `relatorios/2026-05/2026-05-12_teste-triagem-bem-vinda.md`), em produção. Bug do `wa.me` corrompendo emoji no `?text=` → corrigido (`waLink()` usa `api.whatsapp.com/send` direto).

**Pendente — config (não-bloqueante, degrada elegante):**
- `CONFIG.linkGrupoVIP` — convite do grupo "Rhode VIP" (top creators) — ainda vazio (`linkGrupoAcao`, grupo geral, já preenchido)
- `CONFIG.linkAfiliacaoTikTok` — link do convite de colaboração no TikTok Shop (hoje nenhum card no fluxo real usa — só a variante de preview de `ativar`)
- `CONFIG.linkFormAmostra` — Google Form / página de solicitação de amostra (hoje cai no WhatsApp da equipe)
- `CONFIG.sheetsTriagemURL` — opcional, Apps Script `doPost` se quiser espelhar numa planilha além do Supabase

**Polimentos / otimizações (priorizado — detalhe e frameworks em `relatorios/2026-05/2026-05-12_teste-triagem-bem-vinda.md`):**
1. ✅ **Instrumentação de funil** — `bem-vinda.html` grava `step` por tela (`passo1`/`passo2`/`passo3`/`mais_modelos`/`form`/`submit`/`flash`/`result`) na tabela `triagem_eventos` (`rhode-vercel/sql/triagem_eventos.sql`, fetch keepalive, best-effort). Aba Triagem do admin tem o **Funil — últimos 30 dias** (sessões por step + conversão = submit/passo1). **Rodar `triagem_eventos.sql` no Supabase pra ativar.** *(concluído 12/05)*
2. ✅ **Soft CTA no card "Na fila de análise"** — fecha com "Enquanto isso, conhece as peças da Rhode" → `CONFIG.linkLojaRhode` (peak-end; não fura o gating). *(concluído 12/05)*
3. ✅ **Rate-limit + honeypot no formulário** — cooldown 90s por sessão (`sessionStorage`), guard anti-double-INSERT na mesma visita, honeypot `#f_hp` (bot → não grava). *(concluído 12/05)*
4. **Auto-notificar a equipe** numa submissão nova (Z-API pro número da equipe, ou digest diário via cron, reusando `disparo.js`). (~0.5d)
5. **Validação leve do @** — strip de URL do TikTok, lowercase, regex. (~20min)
6. **Flag de submissão repetida** no admin (mesmo `handle` já na `triagem`). (~20min)
7. **Mover a opção de flash do meio do Passo 3** pra um link discreto abaixo das 3 opções (Hick's Law). (~15min)
8. **`status_changed_at` na tabela** + "X dias na fila" no admin (mede SLA de processamento). (~20min)
9. Auto-disparo Z-API pós-triagem (boas-vindas + link do grupo) reusando o template engine do #4
10. Promover automaticamente `parceira_track` → alerta no admin pra avaliar entrada no grupo VIP

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
| 11 | **Mapa de escopos da API TikTok Shop** (app `6jebftqsep751`): ATIVOS = Order, Finance (`seller.finance.info`), Shop Analytics (`data.shop_analytics.public.read`), Affiliate Messages (`seller.affiliate_messages.write`). INATIVOS (toggle, self-enable + reauth) = Product (suíte), Logistics, TAP campaigns. "Aplicar"/sensíveis (não usar) = Customer Service, Content Posting, test scope. | Levantado via `probe_scopes.py` + painel "Gerenciar API" do Partner Center (jun/26). 0 escopos em análise/rejeitados. Catálogo vem do site (`rhodejeans.com.br`), não da Product API → **não ligar Product**. Finance ativo destrava *Faturamento líquido* (KPI hoje em construção). | jun/26 |
| 12 | **Shop Analytics path corrigido.** Era `/analytics/202309/reports/shop_analytics` (morto). Path vivo descoberto e verificado: **`GET /analytics/202405/shop/performance`** com `start_date_ge` / `end_date_lt` (exclusivo) / `granularity` (`1D`\|`ALL`). Retorna `data.performance.intervals[]` (GMV, buyers, avg_order_value, cancellations, breakdown LIVE/VIDEO/PRODUCT_CARD). `buscar_analytics()` reescrita e testada — mas **ainda não wirada no main()** (ativação = item 4.1, adiado). Endpoint pode dar `36009007` timeout transiente → função já faz retry. | Descoberto via `discover_analytics.py` + `confirm_analytics.py` com token vivo (jun/26): só versão 202405 valida, demais dão "invalid version". | jun/26 |

---

## ⚠️ Riscos conhecidos

| Risco | Mitigação atual | Próximo passo |
|-------|-----------------|---------------|
| 🔴 **RLS desligado + anon key pública** → qualquer um baixa todos os `access_token`/`pin_acesso`/WhatsApp/GMV via `GET /rest/v1/affiliates` | **Nenhuma** — testado e confirmado vazável | **Item #8 do roadmap** (proxy `/api/*` + RLS `false` pra anon) |
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
