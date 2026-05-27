# Template de Export — Lives TikTok Shop

Este doc define **quais exports baixar** do TikTok Shop Seller Center pra alimentar o `dash-live`. Sem isso, o dash fica defasado ou com dados zerados.

---

## 🎯 Regra de ouro (leia isto antes de exportar)

**Não precisa decorar template nem acertar ordem de coluna. Marque TODAS as métricas disponíveis no export, sempre.** É a regra mais simples e a mais robusta.

Por que isso funciona — o parser ([etl_lives.py](../../agente_rhode/etl_lives.py)) casa coluna pelo **nome**, não pela posição:

| Situação | O que acontece | Quebra o ETL? |
|---|---|---|
| Colunas fora de ordem | Casadas por nome do mesmo jeito | ❌ Não |
| Coluna a mais que você marcou | Ignorada | ❌ Não |
| Coluna que o ETL espera não veio | Entra como `0` / `NULL` (perde **só** aquela métrica) | ❌ Não |
| Você marca tudo toda vez | Schema estável, nada se perde | ❌ Não |

➡️ **Você não consegue quebrar o ETL escolhendo "errado".** O único jeito de criar buraco na série é *parar* de marcar uma métrica que antes vinha. Por isso: **marque tudo.**

**Sobre a quebra v1→v2 (mai/2026):** não foi escolha de template. O TikTok *removeu do painel* `Gross revenue`, `Viewers` e `Peak viewers` quando virou v2 — não havia checkbox pra manter. É mudança da plataforma, registrada abaixo só pra explicar por que essas colunas estão `NULL` no histórico novo.

### ✅ Checklist v2 — confira que estão marcadas (36 colunas, ordem irrelevante)

`Livestream` · `Start time` · `Duration` · `Attributed GMV` · `Attributed items sold` · `Customers` · `AOV` · `Attributed orders` · `Attributed SKU orders` · `Views` · `LIVE impressions` · `Impressions per hour` · `GMV Per Hour` · `Show GPM` · `Avg. viewing duration` · `Tap-through rate` · `CTR` · `CTOR` · `LIVE CTR` · `SKU order rate` · `Product clicks` · `CTOR (SKU order)` · `Avg. viewing duration per viewer` · `Product impressions` · `Watch GPM` · `New followers` · `Follow rate` · `Comment rate` · `Share rate` · `Like rate` · `Likes` · `Comments` · `Shares` · `Ads ROAS` · `Ads Cost` · `Ads GMV`

> As 3 obrigatórias pra live ser válida: **`Start time`** (sem isso a linha é descartada), **`Duration`** (lives ≤ 5 min são ignoradas) e **`Livestream`** (título, compõe a chave). O resto, se faltar, só vira `NULL`.

---

## 📥 O que baixar (semanalmente, toda segunda)

Baixar **2 arquivos** do [TikTok Shop Seller Center](https://seller-br.tiktok.com/) e jogar em `dados/lives/exports/`:

### 1. Creator-Live-Performance (lives individuais)

- **Caminho no painel:** Analytics → LIVE → Creator LIVE Performance → **Export**
- **Período:** últimos 30 dias (ou desde o último import)
- **Nome de arquivo gerado:** `Creator-Live-Performance_YYYYMMDDHHMMSS.xlsx`

### 2. Shop Analytics Key Metrics (GMV diário da loja) ⚠️ nome novo

- **Caminho no painel:** Analytics → Shop Analytics → Key metrics → **Export**
- **Período:** últimos 30 dias (ou específico — abr/mai/26 separados se quiser cobrir tudo)
- **Nome de arquivo gerado:** `Shop Analytics_Key metrics_YYYYMMDD.xlsx`
- **Nome antigo (deprecated):** `Overview_My Business Performance_*.xlsx`

---

## 🧬 Schemas suportados pelo ETL

O parser ([agente_rhode/etl_lives.py](../../agente_rhode/etl_lives.py)) auto-detecta `v1` (antigo) ou `v2` (novo) por marker columns.

### Creator-Live-Performance · v1 (antes de abr/2026)

```
Livestream · Start time · Duration · Gross revenue · Direct GMV ·
Items sold · Customers · Avg. price · Orders paid for · GMV/1K shows ·
GMV/1K views · Views · Viewers · Peak viewers · New followers ·
Avg. view duration · Likes · Comments · Shares · Product impressions ·
Product clicks · CTR · CTOR (SKU orders)
```

### Creator-Live-Performance · v2 (mai/2026+) ⚠️

```
Livestream · Start time · Duration · Attributed GMV · Attributed items sold ·
Customers · AOV · Attributed orders · Attributed SKU orders · Views ·
LIVE impressions · Impressions per hour · GMV Per Hour · Show GPM ·
Avg. viewing duration · Tap-through rate · CTR · CTOR · LIVE CTR ·
SKU order rate · Product clicks · CTOR (SKU order) ·
Avg. viewing duration per viewer · Product impressions · Watch GPM ·
New followers · Follow rate · Comment rate · Share rate · Like rate ·
Likes · Comments · Shares · Ads ROAS · Ads Cost · Ads GMV
```

**Quebras vs v1:**

| v1 (antigo) | v2 (novo) | Impacto |
|---|---|---|
| `Gross revenue` | (removido) | Perdemos métrica de GMV total da live (incluindo venda não-atribuída) |
| `Direct GMV` | `Attributed GMV` | Equivalente — só renomeou |
| `Viewers` | (removido) | **Não temos mais audiência única** → NULL no banco |
| `Peak viewers` | (removido) | **Não temos mais pico** → NULL no banco |
| `Items sold` | `Attributed items sold` | Equivalente |
| `Orders paid for` | `Attributed orders` | Equivalente |
| `Avg. price` | `AOV` | Equivalente |
| `CTOR (SKU orders)` | `CTOR (SKU order)` | Note o singular |
| `Avg. view duration` (segundos) | `Avg. viewing duration per viewer` (segundos) | Equivalente |
| — | `LIVE impressions` | **Novo** — quantas vezes a live foi mostrada no feed |
| — | `GMV Per Hour` | **Novo** — eficiência temporal |
| — | `Show GPM` / `Watch GPM` | **Novo** — GMV per mille (impressions / views) |
| — | `Ads ROAS` / `Ads Cost` / `Ads GMV` | **Novo** — performance de mídia paga |
| — | Follow/comment/share/like rate | **Novo** — engajamento normalizado |

### Overview · v1 (jan–mar/2026)

```
Data · Valor bruto da mercadoria (R$) · Reembolsos (R$) ·
Valor bruto da mercadoria (com cofinanciamento do TikTok) ·
Itens vendidos · Clientes únicos · Visualizações de página ·
Visitas à página da loja · Pedido de SKU · Pedidos · Taxa de conversão
```

### Overview · v2 (mar/26) ⚠️

```
Data · GMV Bruto · GMV Líquido · Itens Vendidos · Clientes Únicos ·
Views · Visitas · Pedido SKU · Pedidos · Taxa Cancelamento
```

**Quebras vs v1:**

| v1 | v2 | Impacto |
|---|---|---|
| `Reembolsos (R$)` | (removido — derivar de `GMV Bruto - GMV Líquido`) | OK |
| `Valor bruto da mercadoria (com cofinanciamento)` | (removido) | Perdemos visibilidade do GMV cofinanciado |
| `Taxa de conversão` | `Taxa Cancelamento` | **NÃO É EQUIVALENTE** |

### Overview · v3 — "Shop Analytics_Key metrics" (abr/26+) ✅ atual

```
Data · GMV · Pedidos · Clientes · Itens vendidos · Itens reembolsados ·
Pedidos de SKU · Receita bruta · Visualizações de página · Visitantes ·
Taxa de conversão · Impressões do produto · Impressões únicas do produto ·
Cliques no produto · Cliques únicos · AOV
```

**Quebras vs v2:**

| v2 | v3 | Impacto |
|---|---|---|
| `GMV Bruto` | `GMV` | Renomeado |
| `GMV Líquido` | `Receita bruta` (separado de GMV) | Mais granular — Receita bruta é o total faturado, GMV é o realizado |
| `Visitas` | `Visitantes` | Equivalente |
| `Taxa Cancelamento` | `Taxa de conversão` (decimal 0-1) | **Volta a taxa correta**. Parser converte 0.015 → 1.5% |
| — | `Itens reembolsados` (count) | Novo — quantidade de itens devolvidos |
| — | `Impressões do produto` | Novo — funil de marketing |
| — | `Impressões únicas do produto` | Novo — alcance |
| — | `Cliques no produto` / `Cliques únicos` | Novo — engajamento de produto |
| — | `AOV` | Novo — ticket médio direto |

---

## 🔄 Como rodar o ETL após baixar

```bash
# Da raiz do projeto:
python3 agente_rhode/etl_lives.py

# Ou explicitando a pasta:
python3 agente_rhode/etl_lives.py --dir dados/lives/exports
```

O script é **idempotente** (upsert por `live_key` / `date`). Pode rodar várias vezes — só atualiza/insere o que mudou.

---

## ⚠️ Tentar restaurar `Viewers` no export

Verificar no TikTok Shop Seller Center se existe:

1. **Outra aba/filtro de export** que mantenha `Viewers` e `Peak viewers` no schema novo
2. **Configuração de colunas** ao exportar (alguns relatórios deixam você escolher)
3. **Relatório de "LIVE Analytics"** detalhado por live (não o resumo Creator-Live-Performance)

Se nenhuma alternativa existir, métricas dependentes de Viewers (R$/Viewer) ficam disponíveis só pro histórico v1. Pra v2, usar `Views` como proxy ou métricas alternativas: `Show GPM`, `Watch GPM`, `GMV Per Hour`.
