# Conciliação / Profit Analytics — Rhode Jeans (TikTok Shop)

> Documentação técnica do módulo de **conciliação de repasse + profit analytics**
> da loja TikTok Shop da Rhode Jeans. Console admin-only, estilo *koncili*.
>
> Última revisão: 2026-06-24 · Projeto Supabase: `ivzpykuluxcxefhyzfsf`

---

## 1. Visão geral — para que serve

A loja vende em volume na TikTok Shop, mas o painel nativo do TikTok não responde,
de forma confiável, três perguntas de CFO:

1. **Quanto realmente entra na conta?** A receita reportada não é o que liquida — o
   TikTok desconta um *fee* (~26%), frete e ajustes. O número que importa é o
   **settlement** (repasse final), e ele atrasa semanas.
2. **A loja dá lucro, por produto?** GMV alto não é lucro. Precisa descer a cascata:
   GMV → contribuição (GMV − CPV) → margem líquida (após fee/afiliada/mídia) →
   lucro final (após imposto).
3. **O repasse está certo?** Pedidos pagos sem settlement: é só pendência recente
   ou cobrança/cancelamento que precisa de chamado? (a parte "*koncili*").

O módulo de Conciliação responde a isso reconstruindo a **DRE da loja** a partir do
dado **order-level exato** da Finance API do TikTok (settlement por pedido + cascata
de taxas), cruzado com **GMV por SKU**, **CPV** (custo de produto) e **gasto de
GMV Max**. Tudo é admin/CFO — não toca o que as creators veem no Hub.

**Onde fica:** `creators.rhodejeans.com.br/conciliacao.html` (login admin).

**Seções do console** (na ordem em que renderizam):

| Seção | O que mostra |
|-------|--------------|
| KPIs | GMV (vendas), Receita (settled), Settlement, Taxa TikTok + eficiência |
| Caminho do dinheiro (DRE) | Cascata Receita − Taxa − Frete + Ajustes = Settlement |
| Conciliação de repasse (*koncili*) | Liquidado / a receber / devolvido + para onde vai a taxa |
| Tendência mensal | DRE mês a mês (GMV, receita, taxa, frete, settlement, % taxa, eficiência) |
| Produtos campeões | Ranking de produtos por GMV de venda |
| Margem por produto | Contribuição (GMV − CPV) + margem líquida estimada |
| Lucro final | Margem líquida − imposto (Lucro Real, alíquotas editáveis) |
| GMV Max | Lente de ROI da mídia (gasto/receita/ROAS por campanha) |

---

## 2. Arquitetura

```
                  ┌──────────────────────────────┐
   Admin/CFO ───▶ │ conciliacao.html (frontend)  │  login → ADMIN_TOKEN (sessionStorage)
                  └──────────────┬───────────────┘
                                 │ POST /api/get-hub  { action:'admin_query', adminToken, method, path, paged }
                                 ▼
                  ┌──────────────────────────────┐
                  │ /api/get-hub.js (proxy Vercel)│  valida ADMIN_TOKEN → usa service_role
                  └──────────────┬───────────────┘
                                 │ PostgREST (service key = BYPASSRLS)
                                 ▼
                  ┌──────────────────────────────┐
                  │ Supabase Postgres            │  tabelas/views admin-only, RLS deny-anon
                  └──────────────▲───────────────┘
                                 │ upsert via service key
                  ┌──────────────┴───────────────┐
                  │ Coletores / Importadores (py) │  Finance API + Order API + planilhas/exports
                  └──────────────┬───────────────┘
                                 │ HMAC (coletar_dados.chamar)
                                 ▼
                       TikTok Shop API · Seller Center exports
```

### 2.1 Console (frontend)
- Arquivo único: **`rhode-vercel/public/conciliacao.html`** (HTML + CSS + JS inline).
- **Login admin:** `admLogin()` faz `POST /api/get-hub` com `action:'admin_login'` e a
  senha. O servidor compara com `ADMIN_PASS` (env) e devolve `ADMIN_TOKEN`, guardado
  em `sessionStorage` (`rhode-admin-token`). O mesmo token é compartilhado com o
  console de Creators (`admin.html`) — há um switcher entre os dois módulos.
- **Leitura de dados:** `admProxy(method, path, {paged})` chama `action:'admin_query'`.
  Nunca fala com o PostgREST direto; sempre via proxy.
- `load()` dispara **5 queries em paralelo** (`finance_statements`, `pedidos_sku`,
  `custos_sku`, `ads_gmvmax`, `statement_tx_resumo`), todas paginadas, e monta o estado
  em memória (`FIN`, `GMV`, `PROD`, `CPVMAP`, `ADS`, `STX`). `render()` recalcula tudo
  para o período selecionado (mês específico ou "Todos os meses").
- **Alíquotas de imposto** (`TX_VENDA`, `TX_IR`) são editáveis na seção "Lucro final" e
  persistem em `localStorage` (`rhode_tx_venda`, `rhode_tx_ir`).

### 2.2 Proxy (`rhode-vercel/api/get-hub.js`)
Endpoint único do Hub (limite de 12 functions no plano Hobby). Para o módulo de
conciliação importam duas actions:

- **`admin_login`** (`handleAdminLogin`): compara `pass` com `process.env.ADMIN_PASS`
  (delay de 1 s anti brute-force) e devolve `process.env.ADMIN_TOKEN`.
- **`admin_query`** (`handleAdminQuery`): passthrough autenticado para o PostgREST.
  - Exige `adminToken === process.env.ADMIN_TOKEN` (senão 401).
  - Valida o `path` (precisa começar com letra; bloqueia `..`).
  - Com `paged:true` + `GET`, o servidor faz o loop de `offset` (páginas de 1000, teto
    de 200 000) e devolve tudo numa resposta só — evita N round-trips do cliente.
  - Usa a **service_role key** (`SUPABASE_SERVICE_KEY`, só no env do Vercel), que
    bypassa RLS. A chave nunca vai ao cliente.

### 2.3 Supabase + RLS
- Todas as tabelas/views do módulo são **admin-only** com **RLS deny-anon**: `ENABLE ROW
  LEVEL SECURITY` **sem policy permissiva** → `anon`/`authenticated` não leem nada. Só a
  `service_role` (ETL local + proxy admin) acessa, via `BYPASSRLS`. Mesmo padrão do
  `rls_hardening.sql`.
- **Exceção legada:** `finance_statements` e `devolucoes` ainda estão com
  `DISABLE ROW LEVEL SECURITY` + policy anon (padrão antigo — comentado nos próprios
  SQLs como "a fechar"). Como o console lê tudo via proxy/service key, fechá-las não
  quebra o console.

---

## 3. Dicionário de dados

> Convenção comum: `id` = chave de idempotência do upsert; `periodo` = `'YYYY-MM'`;
> `updated_at` = `now()`. Valores em BRL.

### 3.1 `pedidos_sku` — GMV por SKU (lado LOJA)
Detalhe por `(order_id, sku)` de cada pedido da loja. É a base de **GMV por produto**.
Diferente de `extrato_pedidos` (que é o lado afiliado/comissão, subconjunto).
Fonte: `/order/202309/orders/search` → `line_items`. Coletor: `coletar_pedidos_sku.py`.
SQL: `rhode-vercel/sql/conciliacao.sql`.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | text PK | `"{order_id}:{sku}"` |
| `order_id` | text | id do pedido |
| `sku` | text | `sku_name` do TikTok (variação) |
| `seller_sku` | text | `seller_sku` — costuma carregar o **REF do Bling** (chave do CPV) |
| `produto` | text | `product_name` |
| `cor` | text | extraída do nome quando possível (heurística leve) |
| `qty` | int | nº de unidades (cada `line_item` = 1 unidade; qty = contagem) |
| `gmv` | numeric | soma dos `sale_price` da linha (bruto) |
| `status` | text | status do pedido (COMPLETED / CANCELLED / …) |
| `order_time` | bigint | epoch (s) |
| `data` / `periodo` | date / text | derivados de `order_time` (data da **venda**) |

### 3.2 `custos_sku` — CPV (custo de produto vendido)
Cadastro de custo por produto, importado da planilha do Lucas. Importador:
`importar_cpv.py`. SQL: `conciliacao.sql`. **~326 REFs, cobertura ~99,6 % do GMV.**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | text PK | chave normalizada (= REF em uppercase) |
| `ref` | text | REF do Bling (casa com `pedidos_sku.seller_sku`) |
| `produto` / `cor` / `tam` | text | descrição |
| `cpv` | numeric | custo do produto vendido |
| `fonte` | text | `import` \| `manual` |

> Lookup pretendido em cascata: REF → produto+cor → produto. O console hoje faz o
> match por **REF** (`seller_sku` uppercase → `cpv`).

### 3.3 `ads_gmvmax` — gasto/ROI de GMV Max (Shop ads)
Agregado por `(período, campanha, produto)`. Fonte: export *"creative data for product
campaigns"* do Seller Center. Importador: `importar_gmvmax.py`. SQL: `ads_gmvmax.sql`.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | text PK | `"{periodo_ini}|{campaign_id}|{product_id}"` |
| `periodo` | text | `'YYYY-MM'` (do nome do arquivo) |
| `periodo_ini` / `periodo_fim` | date | janela do export |
| `campanha` / `campaign_id` / `product_id` | text | identificação |
| `is_gmvmax` | bool | nome começa com `[GMV-MAX]` |
| `custo` | numeric | gasto de ads |
| `pedidos` | int | pedidos de SKU atribuídos |
| `receita_bruta` | numeric | GMV gerado pelo anúncio |
| `roi` | numeric | `receita_bruta / custo` (ROAS) |
| `impressoes` / `cliques` | bigint | métricas de tráfego |

### 3.4 `statement_tx` — transações order-level (SETTLEMENT EXATO)
**Coração da conciliação.** Uma linha por `(statement_id, order_id)` com a **cascata
completa de taxas**. Substitui a estimativa "GMV × eficiência" pelo settlement exato.
Fonte: `/finance/202309/statements/{statement_id}/statement_transactions`.
Coletor: `coletar_statement_tx.py`. SQL: `statement_tx.sql`.
**~57.952 pedidos, Jan–Jun.**

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | text PK | `"{statement_id}:{order_id}"` |
| `statement_id` / `order_id` | text | identificação |
| `order_create_time` | bigint | epoch — atribuição ao período da **venda** |
| `data` / `periodo` | date / text | derivados (pela data da venda) |
| `customer_payment` | numeric | o que o cliente pagou |
| `settlement` | numeric | repasse final (o que a loja recebe) — **EXATO** |
| `fee_total` | numeric | dedução total TikTok (negativo) |
| `platform_commission` | numeric | comissão de plataforma |
| `affiliate_commission` | numeric | comissão de creator/afiliada |
| `affiliate_ads_commission` | numeric | comissão de shop ads (GMV Max) |
| `shipping` | numeric | custo de envio |
| `adjustment` | numeric | ajustes/correções (exclui os reembolsos com coluna própria) |
| `logistics_reimbursement` | numeric | **crédito (+)** por problema logístico (extravio/atraso). Ver nota. |
| `platform_reimbursement` | numeric | **crédito (+)** política "refund without return" (plataforma absorve). Ver nota. |
| `actual_shipping_fee` | numeric | frete **real** pago à transportadora (−) |
| `fbm_shipping_cost` | numeric | frete que a **loja** banca (merchant-fulfilled, −) |
| `platform_shipping_subsidy` | numeric | **subsídio (+)** de frete pago pela plataforma → `frete líquido = actual_shipping_fee − platform_shipping_subsidy` |
| `moeda` | text | `BRL` |

> **O campo `type` das statement_transactions e o gap de conciliação.** Cada linha tem um
> campo `type`. `type='ORDER'` é a venda normal (tem `order_id`). Os demais tipos são
> lançamentos de **ajuste** que vêm com **`order_id` NULL** (pedido em `adjustment_order_id`)
> e valor duplicado em `settlement_amount` **e** `adjustment_amount`. Nos dados da Rhode
> (mai+jun/26, 16.570 tx) só aparecem **3** tipos:
>
> | `type` | Significado | Sinal |
> |--------|-------------|-------|
> | `ORDER` | liquidação normal do pedido | +/− |
> | `LOGISTICS_REIMBURSEMENT` | reembolso por problema logístico (extravio/atraso) | **+** |
> | `PLATFORM_REIMBURSEMENT` | "refund without return" — plataforma absorve e credita | **+** |
>
> O coletor antigo (`if not oid: continue`) **descartava** todo `type != ORDER`, então
> `sum(statement_tx.settlement)` ficava MENOR que `finance_statements` pelo total desses
> créditos. Reconciliação junho/26: gap de **R$ 3.096,59** → **R$ 0** após o fix
> (R$ 3.029,24 LOGISTICS + R$ 67,35 PLATFORM). Agora o coletor religa qualquer `type != ORDER`
> por `adjustment_order_id`, soma em `settlement` (fecha o gap), isola cada reembolso na sua
> coluna e mantém tipos **sem coluna própria** no `adjustment` genérico (com aviso no log
> pra virarem coluna quando aparecerem). Migração: `statement_tx_logistics.sql`.
>
> **Irmãos documentados (ainda não vistos na Rhode)** — mesmo campo `type`, tratar quando
> surgirem: `CHARGE_BACK`, `PLATFORM_PENALTY`, `DEDUCTIONS_INCURRED_BY_SELLER`,
> `GMV_PAYMENT_FOR_ADS` (débito −); `CUSTOMER_SERVICE_COMPENSATION`, `PLATFORM_COMPENSATION`,
> `SHIPPING_FEE_COMPENSATION`, `REBATE`, `SAMPLE_SHIPPING_FEE`, `PROMOTION_ADJUSTMENT`,
> `OTHER_ADJUSTMENT`, entre outros. A geração **202501** do endpoint entrega os mesmos
> números como breakdown tipado aninhado (`fee_tax_breakdown`, `revenue_breakdown`,
> `shipping_cost_breakdown`) em vez de campos `*_amount` achatados.

### 3.5 `statement_tx_resumo` (VIEW) — conciliação por período
Agrega `statement_tx` **por pedido** (across statements, somando todas as linhas do
mesmo `order_id`), classifica e soma por período. O console consulta a view (≈10 linhas)
em vez das ~60k linhas brutas. SQL: `statement_tx_resumo.sql`.

Classificação por pedido (após somar `settlement` de todas as linhas):
- `settle > 0,01` → **liquidado**
- `abs(settle) <= 0,01` → **a receber / pendente** (pago mas sem repasse ainda)
- `settle < -0,01` → **devolvido** (dinheiro que voltou)

| Campo da view | Descrição |
|---------------|-----------|
| `periodo` | `'YYYY-MM'` (`max(periodo)` por pedido) |
| `pedidos` / `liquidados` / `pendentes` / `devolvidos` | contagens |
| `pago_total` | soma de `customer_payment` |
| `settle_liq` / `pago_liq` | settlement e pagamento **só dos liquidados** (base da taxa real) |
| `a_receber` | `customer_payment` dos pendentes |
| `devolucao` | `settlement` (negativo) dos devolvidos |
| `comissao_plataforma` / `comissao_afiliada` / `comissao_ads_afil` / `frete` | decomposição do fee (valores absolutos) |
| `reembolso_logistica` / `reembolso_plataforma` | créditos (+) devolvidos pela TikTok no período (logística / "refund without return") |
| `frete_real` / `frete_fbm` / `subsidio_frete` / `frete_liquido` | frete real, frete que a loja banca, subsídio da plataforma e frete líquido (`frete_real − subsidio_frete`) por período |

### 3.6 Tabelas de apoio (já existentes)
| Tabela | Papel | Fonte / ETL |
|--------|-------|-------------|
| `finance_statements` | settlement nível-**statement** (receita − fee − frete + ajuste = settlement). Base da seção "Caminho do dinheiro". | `agente_rhode/etl_finance.py` (`GET /finance/202309/statements`) |
| `devolucoes` | 1 linha por item devolvido (`return_line_item`); `refund_return` para deduplicar por `return_id`. | `agente_rhode/etl_devolucoes.py` (`POST /return_refund/202309/returns/search`) |
| `extrato_resumo` / `extrato_pedidos` | lado **afiliado/comissão** (Central de Comissões das creators); subconjunto do GMV. | `coletar_extrato.py` (`/affiliate_seller/202410/orders/search`) |

> `finance_statements` (campo `fee_amount`) = mesma dedução agregada que `statement_tx`
> abre por pedido. O console usa `finance_statements` para a DRE de caixa e
> `statement_tx_resumo` para a conciliação exata por pedido.

---

## 4. Coletores / ETL

Todos os scripts python ficam na raiz do repo, carregam `.env` (com `SUPABASE_URL`,
`SUPABASE_SERVICE_KEY` e o token TikTok) e fazem **upsert idempotente** via service key
(`Prefer: resolution=merge-duplicates`). Rodar de novo no mesmo período não duplica.

### 4.1 Cliente HMAC — `coletar_dados.py`
Base de todos os coletores que falam com a TikTok Shop API.
- `chamar(method, path, params, body)`: monta `app_key`, `timestamp`, `sign_method`,
  `shop_cipher`; assina HMAC-SHA256 (`assinar()` = `APP_SECRET + path + pares + body + APP_SECRET`);
  manda no header `x-tts-access-token`. Base `https://api.tiktok-shops.com`. 3 retries em timeout.
- Token: `token_store.get_access_token()` (tabela `api_tokens`, fonte de verdade na nuvem)
  com fallback para `TIKTOK_ACCESS_TOKEN` do `.env`.
- Helpers reusados: `buscar_pedidos()`, `buscar_finance()`, `buscar_affiliate_orders()`,
  `buscar_produtos()`.

### 4.2 `coletar_pedidos_sku.py` → `pedidos_sku`
- **O que faz:** puxa pedidos da loja (`buscar_pedidos`, endpoint
  `POST /order/202309/orders/search`), agrega por `(order_id, sku_name)` e faz upsert.
  `qty` = nº de `line_items`; `gmv` = soma dos `sale_price`.
- **Rodar:** `python3 coletar_pedidos_sku.py --dias 21`
  (ou `--inicio 2026-01-01 --fim 2026-06-30`).
- **Frequência:** diária (janela retroativa de 21 dias) + backfill por range quando preciso.

### 4.3 `coletar_statement_tx.py` → `statement_tx`
- **O que faz:** lista os statements do período (`buscar_finance`), e para cada um pagina
  `GET /finance/202309/statements/{statement_id}/statement_transactions`. Acumula por
  `(statement_id, order_id)` somando a cascata. Retry no rate-limit (`code 36009002`,
  backoff). Idempotente (`id = statement:order`).
- **Rodar:** `python3 coletar_statement_tx.py --dias 60`
  (ou `--inicio … --fim …`). Reportar `pago`, `settlement` e `taxa média` ao fim.
- **Frequência:** semanal / sob demanda (statement liquida com atraso de semanas —
  reprocessar a janela recente captura novos settlements de vendas antigas).

### 4.4 `importar_cpv.py` → `custos_sku`
- **O que faz:** lê a planilha de CPV (aba `CPV`, colunas REF · Produto · Cor · Tamanho ·
  CPV — nomes tolerantes a variação), parseia valor BR (`R$`, vírgula decimal), deduplica
  por REF (last-wins, avisa conflitos) e faz upsert. Chave = REF uppercase.
- **Rodar:** `python3 importar_cpv.py ~/Downloads/cpv-rhode-AAAA-MM-DD.xlsx`.
- **Frequência:** sob demanda (quando o Lucas manda planilha atualizada).

### 4.5 `importar_gmvmax.py` → `ads_gmvmax`
- **O que faz:** lê o(s) export(s) *"creative data for product campaigns …​.xlsx"* (aba
  `Data`), tira o **período do nome do arquivo** (regex `YYYY-MM-DD HH ~ YYYY-MM-DD`),
  lê IDs como string (precisão de 16-17 dígitos), agrega por `(campaign_id, product_id)`
  e calcula `roi = receita_bruta / custo`. Idempotente.
- **Rodar:** `python3 importar_gmvmax.py` (todos em `dados/campanhas/tiktok/`) ou passar
  o caminho de um arquivo.
- **Frequência:** mensal (1 export por período) ou quando chegar export novo.

### 4.6 ETLs de apoio (já no pipeline)
| Script | Alimenta | Endpoint |
|--------|----------|----------|
| `agente_rhode/etl_finance.py` | `finance_statements` | `GET /finance/202309/statements` |
| `agente_rhode/etl_devolucoes.py` | `devolucoes` | `POST /return_refund/202309/returns/search` |
| `coletar_extrato.py` | `extrato_resumo`, `extrato_pedidos` (+ `performance_periods` forward-only) | `/affiliate_seller/202410/orders/search` |

> ⚠️ `coletar_extrato.py` é **local/untracked de propósito**: precisa do token TikTok
> (que o GitHub Action não tem) e fica fora de `agente_rhode/` para **não** disparar o
> `etl_sync.yml` (que reescreve a `performance_periods` em produção).

### 4.7 Live — duas lentes (aba **Lives**)

O GMV de live tem **duas atribuições diferentes**; a aba Lives usa `live_attr` como headline
e cai pra `live_sessao` (GMV Max) quando não há dado no período.

| Tabela | Fonte | Atribuição | Coletor |
|--------|-------|-----------|---------|
| **`live_attr`** ← headline | Seller Center · Livestream (**"Attributed GMV"**) | conteúdo (a live como canal: orgânico + ads) | `coletar_lives_attr_api.py` + `importar_live_performance.py` |
| `live_sessao` | Business API GMV Max (`/gmv_max/report/get/` room-level) | **ads** (`gross_revenue`) | `coletar_lives_api.py` |
| `live_periodo` | Partner Analytics `/analytics/202405/shop/performance` | canal LIVE da loja inteira (mix) | `coletar_lives_api.py` |

- **`coletar_lives_attr_api.py` → `live_attr`** (fonte da verdade): API
  `GET /analytics/202509/shop_lives/performance` (**só a versão 202509 funciona**), pagina
  todas as salas atribuídas à loja e filtra `username == "rhodejeans"` (lives da própria
  Rhode). Reproduz o export do Seller Center a ~0,02% (é snapshot ao vivo, converge). Traz
  `gmv/pedidos/clientes/aov` — **não traz views**. Preserva `views` já existentes no upsert.
- **`importar_live_performance.py` → `live_attr`** (enriquecimento): lê o export
  *"Creator-Live-Performance_*.xlsx"* / Livestream (`dados/lives/exports/`), casa por
  `room_id`, grava o **GMV exato do fechamento + views**. Só processa exports com Room ID
  (formato novo) — os antigos, sem Room ID, ficam pra API (evita duplicar). Parser BR/US.
- **Cron:** `refresh_performance_diario.sh` passos `15d` (API) → `15e` (import de views),
  nessa ordem (o export refina o mês fechado por cima do snapshot da API).
- **Junho/26 validado ao centavo:** 54 salas = **R$ 205.591,75**.

---

## 5. Metodologia

### 5.1 A cascata de lucro (a DRE da loja)

```
GMV (vendas)                            pedidos_sku.gmv   (data da VENDA)
  │
  ├─ − CPV                              custos_sku.cpv × qty (por REF)
  ▼
Margem de contribuição = GMV − CPV      (exata; só onde há REF cadastrado)
  │
  ├─ aplica eficiência de settlement    (deduz fee+afiliada+GMV Max, ver §6.1)
  ▼
Margem líquida = GMV × eficiência − CPV (estimativa; rateia o fee por GMV)
  │
  ├─ − imposto s/ venda (PIS/COFINS+ICMS, editável; default 9,25%)
  ├─ − IRPJ + CSLL (34%, só sobre lucro positivo; editável)
  ▼
Lucro final
```

**Fórmulas (como o `render()` calcula):**

- **Eficiência de settlement** (fração que sobra após o fee):
  - **REAL** quando há `statement_tx_resumo`: `eficFrac = Σ settle_liq / Σ pago_liq`
    (só pedidos liquidados → taxa real ≈ 26 %, eficiência ≈ 74 %).
  - **Fallback** (sem statement): `A.set / A.rev` do `finance_statements` (ou global,
    ou 0,74).
- **`GMV com CPV` (`mGmvCpv`)** = GMV só das linhas que têm REF de custo casado.
  `cobertura = mGmvCpv / GMV total`.
- **Contribuição** = `mGmvCpv − Σ(cpv×qty)`.
- **Margem líquida** = `mGmvCpv × eficFrac − Σ(cpv×qty)`.
- **Imposto s/ venda** = `mGmvCpv × TX_VENDA%`.
- **Lucro antes do IR** = margem líquida − imposto s/ venda.
- **IRPJ+CSLL** = `max(0, lucroAntesIR) × TX_IR%`.
- **Lucro final** = lucroAntesIR − IRPJ+CSLL. `lucroPct = lucroFinal / mGmvCpv`.

> A margem líquida é **estimativa otimista**: usa GMV bruto (descontos de vendedor e
> devoluções reduzem um pouco o líquido real) e rateia o fee por GMV (não por SKU). O
> valor exato por SKU exigiria o detalhe order-level cruzado com o SKU — próximo passo.

### 5.2 Caminho do dinheiro (DRE de caixa)
Agrega `finance_statements` por mês: `Receita bruta − Taxa TikTok − Frete + Ajustes =
Settlement`. `%taxa = |fee| / receita`; `eficiência = settlement / receita`.

> **Dois relógios.** "GMV vendas" conta pela **data da venda** (`pedidos_sku`);
> "Receita/Settlement" pela **data em que o dinheiro liquidou** (`finance_statements`,
> que atrasa ~semanas). Por isso o mês corrente mostra GMV alto e settlement parcial —
> não são uma soma direta; a conciliação reconcilia ao longo do tempo.

### 5.3 Conciliação de repasse (estilo *koncili*)
Lê `statement_tx_resumo` (dado **exato por pedido**, não estimativa):

- **Liquidado** = `settle_liq` (`liquidados` pedidos).
- **A receber** = `a_receber` (`pendentes`: pagos sem settlement — pendência recente ou
  a investigar).
- **Devolvido** = `devolucao` (`devolvidos`: dinheiro que voltou).
- **Taxa real** = `1 − settle_liq / pago_liq` (só liquidados) ≈ 26 %.
- **Para onde vai a taxa** (decomposição do fee, % do pago liquidado): comissão de
  plataforma, comissão de afiliada, comissão de ads-afiliada, frete, e **Serviço/SFP +
  mídia GMV Max** = resíduo `(pago_liq − settle_liq) − (plat + afi + ads + frete)`.

A taxa real medida aqui é exatamente a `eficFrac` que alimenta a margem líquida em §5.1.

### 5.4 GMV Max (lente de ROI)
Agrega `ads_gmvmax` por mês e por campanha: `gasto`, `receita atribuída`,
`ROI = receita/gasto`, e `Ads/GMV = gasto / GMV` (intensidade de mídia, **informativo,
NÃO dedução** — ver §6.1). ROI ~7,9x, ~R$24k/mês.

---

## 6. Achados / notas críticas

### 6.1 ⚠️ O fee do TikTok JÁ INCLUI a comissão de afiliada E a mídia GMV Max — não subtrair de novo
O `fee` (~26 % da receita) descontado direto do settlement **já embute** a comissão de
afiliada (~11 %) **e** o custo de mídia GMV Max. Confirmado por **decomposição
order-level**: o resíduo não-comissão do fee bate ~98 % com o gasto de mídia.

Consequência: **a margem líquida (settlement − CPV) já é líquida de ads.** Subtrair o
gasto de GMV Max de novo é **double-count** — gerava falso prejuízo (bug já corrigido).
Por isso a seção "GMV Max" é a **lente de ROI da mídia**, e não uma dedução extra; e a
nota em "Margem por produto" explicita que o fee "já inclui comissão de afiliada E a
mídia/GMV Max".

### 6.2 Taxa real ≈ 26 % — só sobre os pedidos liquidados
A taxa de ~26 % vale para pedidos **liquidados** (referência Fev–Abr). Pedidos com
pagamento e `settlement = 0` **não** são prejuízo: são "**a receber**" (pendência recente)
ou cancelados (antigos). O motor de divergências (`statement_tx_resumo`) separa
liquidado / a receber / devolvido — por isso a taxa real é medida só sobre
`settle_liq / pago_liq`, e não sobre o total pago.

### 6.3 GMV Max NÃO está na Marketing API
O GMV Max **real** (~R$24k/mês, ROI ~7,9x) **não** aparece na TikTok Marketing API — lá
só há brand ads / Spark Ads (~R$15k em 3 meses). O dado de GMV Max vem **exclusivamente
do export do Seller Center** ("creative data for product campaigns"), importado por
`importar_gmvmax.py`. Não tente puxar GMV Max pela Marketing API.

### 6.4 GMV oficial — bate 1:1 com o Seller Center (Orders API, sem atraso)
O headline "GMV" do console é o **GMV oficial**, definido como **`Σ payment.total_amount` dos pedidos com `paid_time > 0`** (Orders API). Valida contra o Seller Center quase exato: **Mai R$523,8k vs SC R$522,1k (+0,3%)**, **Jun R$628,5k vs SC R$626,3k (+0,3%)**.

Por que não usar `statement_tx`/settlement como headline: o settlement **atrasa ~2-4 semanas**, então no **mês corrente** o "pago liquidado" fica muito abaixo do real (ex.: Jun pago-settlement R$367k vs GMV oficial R$628k). A Orders API traz o `total_amount` **na hora do pedido**, sem lag → completo no mês corrente.

**Ponte de receita** (decomposição mostrada no console):
```
GMV oficial (= Seller Center)        Σ total_amount (paid_time>0)
  − Frete pago pelo cliente           Σ shipping_fee
  = Produto (pago)                     Σ sub_total
  − Produto pago-e-cancelado           sub_total de status CANCEL pagos
  = GMV produto válido                 base de margem/lucro
```

**Dados:** tabela `pedido_pagamento` (1 linha/pedido) + view `gmv_oficial_resumo` (ponte por período). Coletor: `coletar_pedidos_sku.py → agregar_pagamento()` (mesma chamada da Orders API; roda no daily-collect `--dias 21` → mantém o mês corrente fresco). DDL: `rhode-vercel/sql/pedido_pagamento.sql`.

> **Gotcha de deploy:** o Vercel Hobby limita **12 Serverless Functions**/deploy. Ao estourar, `vercel --prod` falha silenciosamente e a live trava na versão antiga. Os 3 crons foram consolidados num dispatcher `api/cron/[job].js` (+ handlers em `api/_crons/`, pasta `_` ignorada). Conferir o que está live: `curl -s ".../conciliacao.html?cb=$(date +%s%N)" | grep MARCADOR`.

---

## 7. Como manter / operar

### 7.1 Atualizar os dados (rotina sugerida)
```bash
# 1) GMV por SKU (lado loja) — diário, janela recente
python3 coletar_pedidos_sku.py --dias 21

# 2) Settlement exato por pedido — semanal (statements liquidam com atraso)
python3 coletar_statement_tx.py --dias 60

# 3) Finance agregado (caminho do dinheiro) — ETL existente
python3 -m agente_rhode.etl_finance        # alimenta finance_statements

# 4) CPV — quando chegar planilha nova
python3 importar_cpv.py ~/Downloads/cpv-rhode-AAAA-MM-DD.xlsx

# 5) GMV Max — quando chegar export novo (período vem do nome do arquivo)
python3 importar_gmvmax.py        # lê tudo em dados/campanhas/tiktok/
```
Todos exigem `.env` com `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` e token TikTok válido
(`api_tokens` / `TIKTOK_ACCESS_TOKEN`). Upserts são idempotentes — pode rodar de novo.

### 7.2 (Re)criar as tabelas / a view (Supabase → SQL Editor → Run)
```
rhode-vercel/sql/conciliacao.sql          → pedidos_sku, custos_sku (+ RLS)
rhode-vercel/sql/statement_tx.sql         → statement_tx (+ índices, RLS)
rhode-vercel/sql/statement_tx_resumo.sql  → VIEW statement_tx_resumo
rhode-vercel/sql/ads_gmvmax.sql           → ads_gmvmax (+ RLS)
```
A view é `CREATE OR REPLACE` — rodar de novo é seguro. Após mudar `statement_tx`, rode o
`statement_tx_resumo.sql` de novo para refletir colunas novas.

### 7.3 Acesso ao console
- `creators.rhodejeans.com.br/conciliacao.html` → senha admin (`ADMIN_PASS` no env do
  Vercel). O token de sessão é o `ADMIN_TOKEN` (também env do Vercel).
- Envs obrigatórios no Vercel: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `ADMIN_PASS`,
  `ADMIN_TOKEN`.
- Sem login válido, toda `admin_query` retorna 401. A service key nunca chega ao cliente.

### 7.4 Sanity checks rápidos
```sql
SELECT * FROM statement_tx_resumo;                          -- conciliação por período
SELECT periodo, COUNT(*), SUM(gmv) FROM pedidos_sku GROUP BY periodo ORDER BY periodo;
SELECT COUNT(*), MIN(cpv), MAX(cpv), AVG(cpv) FROM custos_sku;   -- cobertura de CPV
SELECT periodo, SUM(custo), SUM(receita_bruta) FROM ads_gmvmax GROUP BY periodo;
```
Conferência cruzada: a **taxa real** da `statement_tx_resumo` (≈26 %) deve bater com o
`%taxa` da `finance_statements` no mesmo período (ajustando o defasamento dos dois
relógios — §5.2).
