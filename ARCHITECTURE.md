# Rhode Creator Hub — Arquitetura & Pipelines

> **Última atualização:** 2026-05-05 · **Stack:** Vercel (frontend + serverless) + Supabase (PostgreSQL + REST) + GitHub Actions (ETL) + Z-API (WhatsApp) + Anthropic Claude (IA) + TikTok Shop API
>
> **Para quem está chegando agora:** começa por [📍 Visão geral](#-visão-geral) → [🧭 Mapa de arquitetura](#-mapa-de-arquitetura). Para um item específico, pula direto pra seção indicada. Para o que está pronto vs. em desenvolvimento, ver [`ROADMAP.md`](ROADMAP.md). Para debugar produção quebrada, [`RUNBOOK.md`](RUNBOOK.md).

---

## 📍 Visão geral

Sistema de gestão do programa de creators afiliadas da **Rhode Jeans** (TikTok Shop). 4.926 creators ativas, 5 períodos de histórico, 5 tiers (Bronze 20k → Black 500k GMV acumulado).

Três grandes superfícies:

| Superfície | Quem usa | URL pública |
|---|---|---|
| **Hub** | Creator afiliada (auto-serviço) | `creators.rhodejeans.com.br/hub.html` |
| **Admin** | Time interno Rhode | `creators.rhodejeans.com.br/admin.html` |
| **Acesso** | Criar PIN no primeiro login | `creators.rhodejeans.com.br/acesso.html` |

Tudo servido pelo projeto Vercel `rhode-vercel`. Banco no Supabase (`ivzpykuluxcxefhyzfsf.supabase.co`). Pipeline de dados via GitHub Actions sobre os exports do TikTok Seller Center.

---

## 🧭 Mapa de arquitetura

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         FONTES DE DADOS EXTERNAS                          │
│  TikTok Shop API     TikTok Seller Center      rhodejeans.com.br site    │
│  (REST + HMAC)       (xlsx exports manuais)    (sitemap + JSON-LD)        │
│  ↓                   ↓                          ↓                          │
└──┼───────────────────┼──────────────────────────┼─────────────────────────┘
   │                   │                          │
   │ coletar_dados.py  │ git push xlsx            │ sync_catalogo (Vercel/CLI)
   │ (manual local)    │ ↓                        │
   ↓                   │ GitHub Actions:          │
 Excel local           │   etl_v2 (xlsx→warehouse) │
 dados/marketplace/    │   etl_lives (lives→DB)   │
 dados/creators/       │ ↓                        │
                       │ warehouse/*.csv (commit) │
                       │ ↓                        │
                       │ sync_supabase.py         │
                       │ (DELETE-then-UPSERT      │
                       │  por período)            │
   │                   ↓                          ↓
┌──┼───────────────────┼──────────────────────────┼─────────────────────────┐
│  ↓               SUPABASE (PostgreSQL + PostgREST + RLS)                  │
│                                                                            │
│  affiliates · performance_periods · performance_diario🟡 · produtos       │
│  amostras_enviadas · campanhas · flash_sales · tier_milestones            │
│  eventos_creators · creator_profiles · scripts_gerados · disparos_log     │
│  mensagens_templates · notificacoes                                       │
│                                                                            │
│  Views: amostras_lotes · amostra_roi_por_sku · flash_sales_ativas         │
│  RLS: DISABLE em todas + POLICY anon all (auth de domínio é client-side)  │
└──┬─────────────────────────────────────────────────────────────────────────┘
   │
   │ REST PostgREST (anon key client-side, service key server-side)
   │
┌──┼─────────────────────────────────────────────────────────────────────────┐
│  ↓                  VERCEL (rhode-vercel)                                  │
│                                                                            │
│  Static (public/):                                                         │
│    hub.html · admin.html · acesso.html · cadastro.html · index.html       │
│    bem-vinda.html · dash-live.html                                         │
│                                                                            │
│  Serverless (api/):                                                        │
│    Auth/Hub:     get-hub · request-access                                  │
│    IA:           copy · analyst · analyze (Claude API)                    │
│    Comunicação:  disparo · relay (Z-API)                                  │
│    Sync:         sync-catalogo · sync-flash-sales                         │
│    Crons:        cron-recovery · cron-reminder · cron-tier-milestones     │
└──┬─────────────────────────────────────────────────────────────────────────┘
   │
   │ HTTPS
   │
┌──┼─────────────────────────────────────────────────────────────────────────┐
│  ↓                          USUÁRIOS                                       │
│  Creator → hub.html (auto-serviço)                                        │
│  Time Rhode → admin.html (operação)                                       │
│  Operador → WhatsApp Z-API (notificações de marco / fluxos)               │
└────────────────────────────────────────────────────────────────────────────┘
```

🟡 = código pronto, ativação adiada (ver [ROADMAP item 4.1](ROADMAP.md))

---

## 🖥 Frontend ([rhode-vercel/public/](rhode-vercel/public/))

Static HTML+CSS+JS, sem framework. Cada arquivo é monolítico (CSS e JS inline). Padrão de design: Apple-inspired (Inter + JetBrains Mono, hairlines, single accent Rhode Red).

| Arquivo | Função | Audiência |
|---|---|---|
| [`hub.html`](rhode-vercel/public/hub.html) | Dashboard pessoal da creator | Creator |
| [`admin.html`](rhode-vercel/public/admin.html) | Painel operacional | Time Rhode |
| [`acesso.html`](rhode-vercel/public/acesso.html) | Login PIN + auto-cadastro de phone | Creator |
| [`cadastro.html`](rhode-vercel/public/cadastro.html) | Form do evento Missão Extra (13/04) | Creator de evento |
| [`bem-vinda.html`](rhode-vercel/public/bem-vinda.html) | Triagem multi-step de creator nova → 8 diagnósticos + redirecionamento (grupos, afiliação, amostra, flash) | Nova creator / lead |
| [`dash-live.html`](rhode-vercel/public/dash-live.html) | Painel live de evento (VIP feed) | Operador |
| [`index.html`](rhode-vercel/public/index.html) | Redirect / landing | Geral |

### Hub das creators

6 abas na bottom-nav: **Painel · Performance · Novidades · Copy · Acessos · Scripts**

- **Painel** — KPIs do mês (GMV, comissão, conteúdos), filtro temporal, tier card sticky
- **Performance** — recorte custom + chart SVG + tabela
- **Novidades** — SKUs criados nos últimos 30d com botão "Pedir amostra"
- **Copy** — gerador IA (Claude) baseado em produto + perfil da creator
- **Acessos** — entregáveis por tier, locked/unlocked
- **Scripts** — histórico de copy gerada
- **Sininho fixed top-right** — inbox de notificações com drawer + polling 60s

### Admin

8 abas: **Dashboard · Ranking · Alertas · Evolução · Analista IA · Operação · Comunicação · Evento 13/04**

- **Dashboard** — 6 KPIs com projeção MTD + status header com gap vs pace, top 10, concentração, críticos, upgrade-ready
- **Ranking** — todas as creators ordenadas por GMV líquido com filtros
- **Alertas** — refund alto, alto AOV/baixa atividade (potencial), inativas
- **Evolução** — sub-tabs Mensal (por creator) e Diário (loja toda 🟡)
- **Analista IA** — resumo cognitivo Claude + matriz oportunidade 4 quadrantes + anomalias z-score + análise individual
- **Operação** — sub-tabs Amostras · Campanhas · Flash Sales · Catálogo
- **Comunicação** — disparo Z-API com 7 templates, filtros, dry-run
- **Evento 13/04** — VIP feed + check-in de kit/live/follow-up

### Seletor de período (admin)

Dropdown mobile-first com 7 buckets (Mês atual / Mês anterior / Últimos 3m / 6m / Trimestre / YTD / Custom) + toggle "vs anterior". Implementação: `loadRange(spec)` resolve períodos → `aggregatePeriods()` soma metrics por affiliate_id reusando `PERIOD_CACHE`. Detalhes em [`admin.html` lines 1450–1700](rhode-vercel/public/admin.html#L1450).

---

## ⚡ Backend ([rhode-vercel/api/](rhode-vercel/api/))

Funções serverless Vercel (Node.js). Cada uma é arquivo único `.js`. Todas com `export default async function handler(req, res)`.

| Endpoint | Função | maxDuration | Trigger |
|---|---|---:|---|
| [`get-hub.js`](rhode-vercel/api/get-hub.js) | Auth com PIN, auto-cadastro phone, gera token de acesso | default | POST do hub/acesso |
| [`request-access.js`](rhode-vercel/api/request-access.js) | Valida @ + envia código WhatsApp pra criar PIN | default | POST de acesso.html |
| [`copy.js`](rhode-vercel/api/copy.js) | Gera copy de vídeo via Claude API (carrega brand intelligence de 27 UGCs) | 60s | POST do hub |
| [`analyst.js`](rhode-vercel/api/analyst.js) | Análise Claude por período ou creator individual | default | POST do admin |
| [`analyze.js`](rhode-vercel/api/analyze.js) | Análise IA (variante) | 30s | POST do admin |
| [`disparo.js`](rhode-vercel/api/disparo.js) | Disparo segmentado Z-API com filtros + dry-run + lote 30/chamada | 60s | POST do admin |
| [`relay.js`](rhode-vercel/api/relay.js) | Bridge Typebot → Z-API (eventos_creators) | 10s | POST do Typebot |
| [`sync-catalogo.js`](rhode-vercel/api/sync-catalogo.js) | Lê sitemap rhodejeans.com.br + extrai JSON-LD + UPSERT em `produtos` | 60s | Botão admin |
| [`sync-flash-sales.js`](rhode-vercel/api/sync-flash-sales.js) | Sync com planilha Google Sheets de flash sales | 30s | Manual |
| [`cron-recovery.js`](rhode-vercel/api/cron-recovery.js) | Z-API recovery msg pra creators do evento Missão Extra | 60s | **Cron Vercel** |
| [`cron-reminder.js`](rhode-vercel/api/cron-reminder.js) | Lembrete WAITING_VIDEO → WAITING_VIDEO_REMINDED (anti-duplicate) | 60s | **Cron Vercel** |
| [`cron-tier-milestones.js`](rhode-vercel/api/cron-tier-milestones.js) | Detecta cruzamento de tier + notifica operador | 60s | **Cron Vercel diário** |

### Cron schedule ([vercel.json](rhode-vercel/vercel.json))

```
cron-recovery       → 14/04 e 15/04 às 12:00 BRT (one-shot do evento)
cron-reminder       → 13/04 e 14/04 múltiplos horários (one-shot do evento)
cron-tier-milestones → 0 12 * * * (todo dia ao meio-dia UTC = 09:00 BRT)
```

Os crons de evento já passaram (era 13-15/04), mantidos pra histórico. O único cron ativo recorrente é `tier-milestones`.

### Padrões internos

- **Headers Supabase:** `apikey + Authorization: Bearer ${KEY}`. Endpoints server-side usam `SB_SVC` (service_role); endpoints chamados client-side usam `SB_KEY` (anon).
- **Z-API:** instância `3F173410FA03D317C69AAAE399BC1248` + token + Client-Token header obrigatório.
- **Claude:** `api.anthropic.com/v1/messages`, modelo `claude-opus-4-7-1m` (default Opus mais recente).
- **Tratamento de erro:** catch + log + retornar `{ error: msg }` com 4xx/5xx.

---

## 🗄 Supabase

Cluster: `ivzpykuluxcxefhyzfsf.supabase.co` · região default · PostgreSQL 15.

### Padrão de RLS

**Todas as tabelas operam com:**
```sql
ALTER TABLE x DISABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "anon_all_x" ON x;
CREATE POLICY "anon_all_x" ON x FOR ALL USING (true) WITH CHECK (true);
```

Auth de domínio é **client-side** (PIN + token de 24 chars). O `anon key` está embutido no admin/hub HTML — projetado pra ser público; segurança vem do design lógico (sem dados sensíveis de pagamento, dados de creator são pseudonimizados pelo handle TikTok).

### Tabelas (inventário)

| Tabela | Propósito | Migration |
|---|---|---|
| `affiliates` | 1 creator = 1 row. `affiliate_id` (UPPERCASE) é PK natural; tem `tiktok_handle`, `current_tier`, `gmv_live_mtd`, `gmv_video_mtd`, `phone`, `pin` | (criada cedo, schema em [warehouse/supabase_schema.sql](warehouse/supabase_schema.sql) ou Studio direct) |
| `performance_periods` | 1 creator × 1 período (`YYYY-MM`). Métricas: gmv_bruto, gmv_liquido, refund, pedidos, aov, videos, lives, comissao, tier. **Chave única** `(affiliate_id, periodo)` | idem |
| `performance_diario` 🟡 | 1 dia (loja toda agregada). gmv_bruto/liq, pedidos, cancelados, itens, clientes, ticket, taxa_cancel | [`performance_diario.sql`](rhode-vercel/sql/performance_diario.sql) |
| `produtos` | Catálogo de SKUs (`sku` PK). Atualizado por `sync_catalogo` lendo o site | [`amostras.sql`](rhode-vercel/sql/amostras.sql) + [`amostras_v2.sql`](rhode-vercel/sql/amostras_v2.sql) |
| `amostras_enviadas` | 1 envio físico. Campos: creator_id, sku, quantidade, custo_unitario_snapshot, data_envio, data_recebimento, **origem** ('manual'/'tiktok_import'/'evento'/'solicitacao_creator'), tier_no_envio, **aprovada**, **solicitada_em**, **dispensada**, lote_id, campanha_id, **tipo** | [`amostras.sql`](rhode-vercel/sql/amostras.sql) + v2 + [`entregas_tipo.sql`](rhode-vercel/sql/entregas_tipo.sql) + [`lancamentos.sql`](rhode-vercel/sql/lancamentos.sql) |
| `campanhas` | Agrupador estratégico de envios. briefing_creator, meta, prazos | [`amostras_v2.sql`](rhode-vercel/sql/amostras_v2.sql) |
| `flash_sales` | Promoções tempo-limitado. SKU + janela datetime + tier_minimo | [`flash_sales.sql`](rhode-vercel/sql/flash_sales.sql) |
| `tier_milestones` | UPSERT de marcos cruzados (1 row por affiliate × tier). `notified_at` controla idempotência do Z-API | [`tier_milestones.sql`](rhode-vercel/sql/tier_milestones.sql) |
| `eventos_creators` | Linha-base do evento Missão Extra (13/04). Registros + estado WAITING_VIDEO + recovery + missão. **Phone canônico fica aqui** (ver [RUNBOOK caso 3D](RUNBOOK.md)) | (Studio direct) |
| `creator_profiles` | Dados pessoais opt-in (nome, altura, peso, quadril, tamanho) usado pra personalizar copy | (Studio direct) |
| `scripts_gerados` | Histórico de copy gerada via Claude por creator | (Studio direct) |
| `mensagens_templates` | 7 templates Z-API com variáveis `{{nome}} {{tier}} {{tier_comissao}} {{link_hub}}` | [`comunicacao.sql`](rhode-vercel/sql/comunicacao.sql) |
| `disparos_log` | Auditoria de cada disparo (filtro_aplicado JSONB, total_alvos, total_enviados, etc) | [`comunicacao.sql`](rhode-vercel/sql/comunicacao.sql) |
| `notificacoes` | Inbox do hub. tipo, titulo, corpo, link, lida, read_at | [`notificacoes.sql`](rhode-vercel/sql/notificacoes.sql) |

### Views

| View | Origem | Uso |
|---|---|---|
| `amostras_lotes` | GROUP BY lote_id em amostras_enviadas | Admin renderiza "1 envio físico" |
| `amostra_roi_por_sku` | JOIN amostras × performance_periods janela 60d | Aba Operação > ROI |
| `flash_sales_ativas` | flash_sales WHERE inicio<=NOW()<=fim | Banner sticky no hub |

### Padrões de query

- **Paginação:** `?limit=1000&offset=0` (PostgREST default cap em 1000). Cliente faz loop até batch < 1000. Função `sbGetPaged()` no admin/hub.
- **Filtros bool com NULL:** `dispensada=not.eq.true` cobre `false` E `null` (importante! `is.null` não pega `false` — ver [commit 085bbd6](https://github.com/Ba44o/git-remote--v/commit/085bbd6)).
- **UPSERT:** `POST /tabela?on_conflict=col1,col2` + header `Prefer: resolution=merge-duplicates`.
- **Aggregate functions:** **bloqueado pelo PostgREST** (`PGRST123`). Soma/count tem que ser client-side.
- **Coluna não existe:** retorna `42703`. Sempre `IF NOT EXISTS` em ALTER TABLE.

---

## 🔄 ETL & Pipelines

Quatro pipelines distintos, com fluxos próprios:

### 1. Pipeline principal — Performance por creator (mensal)

```
Operador (humano)
   │ download manual no TikTok Seller Center
   ↓
Transaction_Analysis_*.xlsx
   │ git push em dados/creators/exports/
   ↓
GitHub Actions: etl_sync.yml
   │ trigger: push de xlsx ou de agente_rhode/**
   │ ┌─ Baixa raw_imports.csv anterior do Google Sheets
   │ ├─ Roda agente_rhode/etl_v2.py
   │ │     └─ pick_canonical_per_period() escolhe 1 xlsx por mês
   │ │     └─ sanity check: aborta se >30% creators ativas com gmv_bruto=0
   │ │     └─ Outputs: warehouse/raw_imports.csv, creators_master.csv,
   │ │                 period_summary.csv, sync_ready.csv
   │ ├─ Roda agente_rhode/sync_v2.py → escreve nas abas do Google Sheets
   │ ├─ Roda agente_rhode/sync_supabase.py
   │ │     └─ DELETE-then-UPSERT por período (remove "fantasmas")
   │ │     └─ Tabelas: affiliates, performance_periods
   │ └─ Commit warehouse/*.csv de volta no repo (etl-bot)
   ↓
Supabase live
```

**Frequência:** sempre que o operador exporta novo xlsx (1-3x/semana). Idempotente.

### 2. Pipeline Lives

```
Operador → exports lives → dados/lives/exports/*.xlsx → git push
   ↓
GitHub Actions: etl_lives.yml
   ↓
agente_rhode/etl_lives.py → tabela `lives` no Supabase
```

### 3. Pipeline Diário 🟡 (código pronto, ativação adiada)

```
Operador → coletar_dados.py (TikTok Shop API + DAY granularity)
   ↓
Overview_*.xlsx (aba "Diario")
   ↓
agente_rhode/etl_diario.py → warehouse/raw_diario.csv
   ↓
agente_rhode/sync_supabase.py --only performance_diario
   ↓
performance_diario (1 row/dia)
```

Detalhes e steps de ativação em [ROADMAP item 4.1](ROADMAP.md).

### 4. Pipeline Catálogo

```
sync_catalogo.py (CLI local) ou /api/sync-catalogo (botão admin)
   ↓
GET https://rhodejeans.com.br/sitemap.xml
   ↓
GET cada produto.html → extrai JSON-LD
   ↓
UPSERT em produtos (idempotente por SKU)
```

**Frequência:** botão "↻ Atualizar do site" no admin/Catálogo. ~5s pra 56+ produtos.

### Helpers Python adicionais

| Script | Uso |
|---|---|
| [`coletar_dados.py`](coletar_dados.py) | Pull TikTok Shop API com HMAC SHA256 (loja + lives) → Excel local |
| [`obter_token.py`](obter_token.py) | OAuth one-time pra obter `TIKTOK_ACCESS_TOKEN` |
| [`audit_data.py`](audit_data.py) | Compara xlsx canônico × Supabase, detecta divergências |
| [`disparar_hub.py`](disparar_hub.py) | One-shot CLI: dispara link do hub via Z-API pra creators ativas |
| [`recuperar_missao_extra.py`](recuperar_missao_extra.py) | Cruza histórico Z-API × eventos_creators pra detectar quem postou vídeo do evento |
| [`sync_sheets.py`](sync_sheets.py) | Sync Sheets ↔ Supabase (legado, antes do etl_v2) |
| [`gerar_dashboard.py`](gerar_dashboard.py) | Gera dashboard local em Excel (legado) |

---

## 🔌 Integrações externas

| Serviço | Uso | Auth |
|---|---|---|
| **TikTok Shop API** (`api.tiktok-shops.com`) | `/affiliate/*`, `/order/*`, `/analytics/202309/reports/shop_analytics`, `/live/*` | HMAC SHA256 + APP_KEY + ACCESS_TOKEN |
| **Z-API** (`api.z-api.io`) | `/send-text` para WhatsApp | INSTANCE + TOKEN + CLIENT_TOKEN |
| **Anthropic Claude** (`api.anthropic.com/v1/messages`) | Geração de copy + análise cognitiva + analista IA | `x-api-key` |
| **Google Sheets** (gspread + oauth2client) | Backup/preview do warehouse + flash sales | `credentials.json` (Service Account) |
| **rhodejeans.com.br** | Scrape do sitemap + JSON-LD pra catálogo | (público, sem auth) |
| **Vercel** | Hosting + serverless + cron | Token CLI |
| **GitHub Actions** | CI/CD do ETL | secrets: `GCP_CREDENTIALS`, `SUPABASE_SERVICE_KEY` |

### Z-API — pontos de atenção

- **Phone canônico:** `eventos_creators.whatsapp` (não `affiliates.phone`, que é sempre NULL hoje). Ver [RUNBOOK caso 3D](RUNBOOK.md).
- **Rate limit:** disparo bate em lotes de 30 com `await sleep(1500ms)` entre cada.
- **Templates** definidos em [`comunicacao.sql`](rhode-vercel/sql/comunicacao.sql), variáveis renderizadas em [`api/disparo.js`](rhode-vercel/api/disparo.js).

---

## 🔁 Workflows operacionais

### A. Onboarding de creator nova

```
TikTok aprova creator
   → operador adiciona phone em eventos_creators (manual)
   → creator entra em creators.rhodejeans.com.br/acesso.html
   → digita @ → recebe código WhatsApp via /api/request-access
   → cria PIN → /api/get-hub valida + gera access_token de 24 chars
   → redirect pra hub.html?token=<token>
```

### B. Creator no dia-a-dia

```
hub.html?token=X
   → boot() resolve creator via affiliates ou eventos_creators
   → renderiza Painel (loadPerf + loadProfile)
   → polling notif inbox (60s + visibilitychange)
   → creator navega: Performance / Novidades / Copy / Acessos / Scripts
   → ações: pedir amostra (Novidades), gerar copy (Copy), confirmar entrega (Acessos)
```

### C. Admin operando

```
admin.html
   → SBH headers com anon key
   → ↻ Sincronizar carrega: PERIODS + PERIOD_META + EVO_DATA + ALL_DATA do range corrente
   → operação por aba:
        Operação/Amostras → ver Solicitações Pendentes → Aprovar/Recusar → cria notif pra creator
        Operação/Catálogo → ↻ Atualizar do site → /api/sync-catalogo
        Comunicação → escolher template + filtros → dry-run → confirmar → /api/disparo
        Analista IA → /api/analyst gera resumo cognitivo do período
```

### D. Ciclo Pedido de Amostra (item 5+6 integrados)

```
Hub: creator clica "Pedir amostra" em Novidades
   → POST amostras_enviadas { origem='solicitacao_creator', aprovada=false, solicitada_em=NOW }
   → botão fica "✓ Solicitada"

Admin: banner "🔔 X solicitações pendentes" no topo de Op > Amostras
   → Aprovar: PATCH aprovada=true + data_envio=hoje
              + createNotif tipo='amostra_aprovada' link='novidades'
   → Recusar: PATCH dispensada=true
              + createNotif tipo='amostra_recusada'

Hub: sininho pulsa em até 60s
   → drawer mostra "Amostra aprovada! 📦"
   → click → marca lida + goTab('novidades')
```

### E. ETL automático

```
operador faz git push de xlsx novo em dados/creators/exports/
   → GitHub Actions etl_sync.yml dispara
   → ~3 min depois: warehouse/*.csv commitado [etl-bot]
   → ~30s depois: Supabase atualizado
   → admin precisa só clicar ↻ Sincronizar pra ver
```

---

## 🚀 Deploy & CI/CD

### Vercel

- **Projeto:** `rhode-vercel`
- **Domain:** `creators.rhodejeans.com.br` (alias canônico — nunca usar `dash.rhodejeans.com.br`)
- **Deploy:** `npx vercel --prod --yes` (ou auto via git push, mas o padrão do projeto é deploy manual após commit verificado)
- **Cache:** `Cache-Control: no-cache, no-store, must-revalidate` em `(admin|hub|acesso|cadastro|index).html` ([vercel.json](rhode-vercel/vercel.json))

### GitHub Actions

- [`.github/workflows/etl_sync.yml`](.github/workflows/etl_sync.yml) — pipeline principal (xlsx → warehouse → Supabase + Sheets)
- [`.github/workflows/etl_lives.yml`](.github/workflows/etl_lives.yml) — pipeline lives

Ambos: `runs-on: ubuntu-latest`, `python: 3.11`, dependências instaladas em runtime, `commit warehouse/*.csv` de volta com permissions: contents: write.

### Secrets necessários

| Secret | Onde | Para |
|---|---|---|
| `SUPABASE_SERVICE_KEY` | Vercel env + GitHub secrets | Server-side writes |
| `ANTHROPIC_API_KEY` | Vercel env | /api/copy, /api/analyst, /api/analyze |
| `GCP_CREDENTIALS` | GitHub secrets | gspread no etl_sync.yml |
| `TIKTOK_APP_KEY` / `_SECRET` / `_ACCESS_TOKEN` / `_SHOP_CIPHER` | `.env` local (operador) | coletar_dados.py |

---

## 📚 Referências auxiliares

| Doc | Quando ler |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Padrões do projeto, KPIs, estrutura de pastas, regras pro agente |
| [`ROADMAP.md`](ROADMAP.md) | Fonte de verdade do que está pronto, em curso, próximo |
| [`RUNBOOK.md`](RUNBOOK.md) | Cenários de debug em produção (1-8) |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Este arquivo |

### Convenções

- **Linguagem:** PT-BR no produto e nos commits; código (variáveis, funções, comentários) em PT-BR também (legacy do projeto).
- **Datas em memórias:** sempre absolutas (`2026-05-05`), nunca relativas (`amanhã`).
- **URL canônica:** `creators.rhodejeans.com.br/...` — nunca mencionar `dash.rhodejeans.com.br`.
- **Phone:** sempre via `eventos_creators.whatsapp`, formato com DDD sem +55 (a normalização adiciona).
- **Migration aplicada via SQL Editor:** todo `.sql` em `rhode-vercel/sql/` é idempotente (`IF NOT EXISTS`, `DROP IF EXISTS`, `ON CONFLICT DO NOTHING`). Pode rodar de novo sem dano.
- **Deploy após edit:** padrão do projeto é commit + push + `npx vercel --prod` (não parar no commit).
