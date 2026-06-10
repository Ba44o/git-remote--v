# Arquitetura & Pipeline de Dados — Rhode Creator Hub

> Visão técnica de ponta a ponta: o que o Hub entrega, com que tecnologias,
> quais APIs e como o dado flui da TikTok Shop até a tela da creator.
> **Última atualização:** 2026-06-09 · domínio único de produção: `creators.rhodejeans.com.br`

---

## 1. Visão geral em 30 segundos

```
   FONTES                COLETA (Python)            ARMAZÉM            ENTREGA
 ┌──────────┐        ┌──────────────────────┐   ┌────────────┐   ┌──────────────┐
 │ TikTok   │        │  GitHub Actions       │   │  Supabase  │   │ Vercel        │
 │ Shop API │──HMAC─▶│  (crons, sem Mac)     │──▶│  Postgres  │──▶│ /api/get-hub  │──▶ hub.html
 │ (Partner)│        │  • daily-collect 14h  │   │ +PostgREST │   │ (proxy Node)  │   (creator)
 └──────────┘        │  • flash-sales /30min │   │  RLS deny  │   └──────────────┘
 ┌──────────┐        │  • etl_sync (push)    │   │  anon      │   ┌──────────────┐
 │ Exports  │──xlsx─▶│  • etl_lives (push)   │   │            │──▶│ Vercel crons  │──▶ WhatsApp /
 │ (jan–mai)│        └──────────────────────┘   └────────────┘   │ (notif/tiers) │    notificações
 └──────────┘                                          ▲          └──────────────┘
 ┌──────────┐                                          │          ┌──────────────┐
 │ Anthropic│◀─────────── "Copy IA" (Sonnet 4.6) ──────┴──────────│ /api/copy     │
 │ Claude   │                                                     └──────────────┘
```

**Princípio central de segurança:** o front nunca fala com o Supabase direto.
Tudo passa pelo proxy `get-hub.js`, que resolve a identidade pelo **token** no
servidor e usa a `service_role` key. A `anon key` está bloqueada por RLS.

---

## 2. Stack & linguagens

| Camada | Tecnologia | Observação |
|--------|-----------|------------|
| **Frontend** | HTML + CSS + **JavaScript vanilla** (single-file `hub.html`) | Sem framework. Fontes: JetBrains Mono, Inter, Crimson Pro |
| **Backend / API** | **Node.js** serverless (Vercel Functions) | `rhode-vercel/api/*.js` |
| **Banco** | **Supabase** (Postgres + PostgREST) | Projeto `ivzpykuluxcxefhyzfsf`, RLS deny-anon |
| **Coleta / ETL** | **Python 3.11** | `pandas`, `openpyxl`, `requests`, `python-dotenv`, `Pillow` |
| **Orquestração** | **GitHub Actions** (crons + push triggers) | Roda na nuvem — saiu do Mac em 09/jun/2026 |
| **IA** | **Claude `claude-sonnet-4-6`** (Anthropic API) | Geração de copy/roteiros para creators |
| **Hospedagem** | **Vercel** (frontend + funções + CDN) | Deploy `vercel --prod` |

---

## 3. O Hub — o que já está pronto (por aba)

O acesso da creator é por **token na URL** (`?token=…`), entregue via fluxo
PIN/WhatsApp. O servidor resolve `affiliates.access_token` → se não achar,
`eventos_creators.access_token`. Segredos (`pin_acesso`, `access_token`) nunca
voltam ao cliente.

| Aba (`panel-*`) | Entrega | Usabilidade |
|-----------------|---------|-------------|
| **Painel** (`perf`) | KPIs do período (GMV, pedidos, comissão, vídeos·lives) com delta vs período anterior; tiers/benefícios; missões; ranking; banner de flash | Filtros temporais **Mês atual / 3m / 6m / 12m**. "Mês atual" ancorado no calendário + **estado-zero** quando não houve venda no mês |
| **Performance** (`perfdetail`) | Detalhe por período (range custom) + **produto-herói** (top SKU da creator) | Tabela + **exportar CSV** |
| **Central de Comissões** (`comissoes`) | Extrato: comissão **a receber** vs **paga**, GMV liquidado/inelegível, reembolsos | Drill-down pedido a pedido com **filtros + CSV + modal de ajuda** dos termos de settlement |
| **Copy IA** (`copy`) | Geração de legendas/roteiros com Claude | Salva histórico; marca o que converteu |
| **Entregáveis** (`entregaveis`) | Amostras/seeding: confirmar recebimento, anexar vídeo | Pedir amostra direto do Hub |
| **Histórico** (`hist`) | Linha do tempo de períodos | — |
| **Novidades** (`novidades`) | Anúncios e novidades | — |

**Privacidade (regra firme):** cada creator vê **só os próprios números** —
inclusive nas flash sales, que são filtradas pelo `@handle` dela (nunca "Geral").

---

## 4. APIs integradas

| API | Uso | Detalhes técnicos |
|-----|-----|-------------------|
| **TikTok Shop Partner/Affiliate API** | Fonte primária de vendas, comissões, devoluções, finanças, flash sales, creator×produto | Assinatura **HMAC-SHA256**; **OAuth** com refresh (access ~7 dias, refresh de longa duração). Token em `api_tokens` (table-first, `.env` fallback) |
| **Anthropic Claude API** | Aba "Copy IA" | Modelo `claude-sonnet-4-6`, `max_tokens 2048`, via `/api/copy.js` (key server-side `ANTHROPIC_API_KEY`) |
| **Supabase PostgREST** | API de dados (CRUD) | Acessada só pelo backend com `service_role` |
| **Google Sheets** | Espelho de `raw_imports` / classificação de seeding | `sync_sheets.py` |

---

## 5. Camada de dados (Supabase)

Principais tabelas, agrupadas por domínio (schema em `rhode-vercel/sql/`):

- **Identidade & acesso:** `affiliates`, `eventos_creators`, `creator_profiles`, `api_tokens`
- **Performance:** `performance_periods` (mensal — base do painel), `performance_diario`, `affiliate_perf`, `affiliate_creator_product`
- **Financeiro / extrato:** `extrato_resumo`, `extrato_pedidos`, `finance_statements`, `devolucoes`
- **Comercial:** `flash_sales`, `produtos`/catálogo, `campanhas`, `lancamentos`, `lives`, `store_daily`
- **Operação creator:** `amostras_enviadas`/seeding, `scripts_gerados`, `notificacoes`, `tier_milestones`, `triagem` / `triagem_eventos`

---

## 6. Pipeline de dados — o workflow completo

### 6.1 Os 4 workflows (GitHub Actions)

| Workflow | Gatilho | O que faz |
|----------|---------|-----------|
| **daily-collect.yml** | cron `0 14 * * *` (≈11h BRT) + manual | Roda `refresh_performance_diario.sh` (14 passos abaixo) |
| **flash-sales.yml** | cron `*/30 * * * *` | `coletar_flash_sales.py` → `flash_sales` (Promotion API, por creator) |
| **etl_sync.yml** | **push** em `agente_rhode/**` ou exports + manual | `etl_v2.py` reprocessa o armazém histórico — ⚠️ **push = deploy de PRODUÇÃO** |
| **etl_lives.yml** | **push** em exports de lives + manual | `etl_lives.py` → `lives` |

### 6.2 A coleta diária (`refresh_performance_diario.sh`, 14 passos)

```
 [1]  obter_token.py --refresh ............... renova OAuth TikTok
 [2-3]  etl_diario.py (api, 14d) ............. → performance_diario
 [4-5]  etl_finance.py (14d) ................. → finance_statements
 [6-7]  etl_devolucoes.py (14d) ............. → devolucoes
 [8-9]  etl_affiliate.py (90d) .............. → affiliate_perf
 [10-11] etl_seeding.py ..................... → seeding
 [12-13] etl_creator_product.py ............. → affiliate_creator_product
 [14]  coletar_extrato.py (21d) ............. → extrato_resumo + extrato_pedidos
                                               + performance_periods (forward, junho+)
```

Cada ETL escreve via `sync_supabase.py` (upsert idempotente com `on_conflict`).

### 6.3 Regra "forward-only" (decisão-chave)

- **Jan–Mai/2026:** congelado, vindo dos **exports imutáveis** (via `etl_sync`/`etl_v2`).
- **Jun/2026+:** ao vivo da **API** (`coletar_extrato.py`, guard `periodo < '2026-06'`).
- Vídeos/lives continuam do export. Isso evita reprocessar/corromper o histórico
  já validado e mantém o mês corrente sempre fresco.

### 6.4 Entrega & automações (Vercel)

- **`get-hub.js`** — proxy único (limite de 12 functions no plano Hobby ⇒ várias
  ações num endpoint). Ações por token: leitura (`bootstrap`, `perf`, `leaderboard`,
  `flash`, `tarefas`, `notifs`, `novidades`, `profile`, `scripts`, `extrato_resumo`,
  `extrato_pedidos`, `top_produtos`) e escrita (`confirmar_tarefa`, `anexar_video`,
  `pedir_amostra`, `marcar_notif`, `salvar_profile`, `salvar_script`…). Admin/ops:
  `admin_login`, `admin_query`, `cadastro`, `dashlive`.
- **Crons serverless:** `cron-tier-milestones`, `cron-reminder`, `cron-recovery`
  → geram `notificacoes` e disparos (WhatsApp via `disparo.js`).

---

## 7. Segurança (estado atual)

- **RLS deny-anon** ativo — a `anon key` não lê nada; todo acesso é server-side
  com `service_role`.
- **Token nunca confia no cliente:** identidade resolvida no servidor a partir do
  token; segredos removidos das respostas.
- **Flash sales isoladas por creator** (nunca vaza flash de loja/outra creator).
- Pendência conhecida: rotação da `service_role` key (baixo risco, repo privado).

---

## 8. Decisões & estado operacional

- **Coleta 100% na nuvem** desde 09/jun/2026 — launchd do Mac desligado; o cron
  agendado roda sozinho (validado 2 dias seguidos). GitHub atrasa o disparo 2–3h
  e a janela de 21 dias auto-corrige eventuais pulos.
- **Tom & UX:** linguagem direta pra creator; "Mês atual" honesto (estado-zero
  quando não vendeu) — ver `RUNBOOK.md` cenário 10.

> Fontes de verdade vivas: **`ROADMAP.md`** (o que está pronto/priorizado) e
> **`RUNBOOK.md`** (playbook de incidentes). Este arquivo descreve a arquitetura.
