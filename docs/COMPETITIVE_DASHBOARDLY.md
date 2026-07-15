# Inteligência Competitiva — Dashboardly (dashboardly.io)

> Pesquisa 2026-07-15. Fontes primárias (site fetchado direto) + Capterra/GetApp/GetLatka.
> Contexto: referência/concorrente do SaaS BR de profit analytics (ver docs de produto / memória).

## Resumo executivo

Dashboardly é um SaaS **indie/bootstrapped, nichado 100% em TikTok Shop** — "Profit & Inventory
Analytics Platform for Brands and Agencies" — que calcula lucro real por pedido/SKU depois de fees,
ads, frete e COGS, reconcilia repasses e faz forecast de estoque. Fundado 2024, time ucraniano ~4-6
pessoas, sede Hallandale Beach/FL, sem funding, ~US$660K ARR (estimativa GetLatka). Preços
US$29/79/199/399/mês + "Flex Orders" medido por pedido; agência US$249-599; trial 14d com cartão,
sem freemium. Integra **só TikTok Shop + TikTok Ads + conector MCP de IA** — nada de Shopify/Amazon/
Meta/Google/gateways. Prova social externa ≈ zero; cresce por SEO programático.

> **Correção de premissa:** NÃO é analytics de e-commerce genérico/multi-marketplace. É
> **TikTok-Shop-exclusivo** — espelha exatamente a tese de conciliação de lucro/settlement de TikTok Shop.

## Posicionamento
- Tagline: "TikTok Shop Profit and Inventory Analytics Platform for Brands and Agencies."
- Promessa: "Track true margins after fees, ads, shipping & COGS. Forecast demand. Prevent stockouts."
  Auto-descrição "Profit Operating System (Profit OS)". Bordão: "Social metrics don't pay the bills. Profit does."
- Público: sellers TikTok Shop (SMB→enterprise), **agências multi-loja** (white-label), marcas DTC beleza/skincare.
- Diferenciação: construído só p/ TikTok Shop, "Official TikTok Shop Partner", API oficial (não scraping)
  → lucro "verificado" vs "estimado". Pitch: "gap entre lucro estimado e verificado = 10-20% da receita".

## Features / módulos
P&L por pedido/SKU (após fees/reembolso/ads/COGS) · **payout reconciliation** (casa fee/reembolso/clawback
com repasse real) · dedução auto de fees (referral, transaction, comissão afiliado, ajuste frete, admin de
reembolso) · revenue por canal (orgânico/sponsored/afiliado) · inventory forecast + alerta de ruptura ·
expense tracking · **LTV + segmentação/VIP** · insights top-produto/geo/hora · dashboards + smart alerts ·
multi-shop + times/white-label · **conector IA via MCP** (Claude/ChatGPT/Cursor, read-only) · KPIs: margem,
lucro líquido, ROI, TACoS, ROAS, LTV.
**Ausentes (confirmado):** CAC, cohort, atribuição multi-touch/blended, benchmarking.

## Pricing (USD · fonte = dashboardly.io/pricing)
Base fixa + uso por pedido ("Flex Orders") com teto mensal. Não cobra % de GMV. Anual -20%. Trial 14d com
cartão. Sem free.

| Plano | Mensal | Flex Orders/mês | Overage/ped | Teto | Lojas | Time |
|---|---|---|---|---|---|---|
| Starter | $29 | 1.500 | $0,01 | $44 | 1 | 2 |
| Growing (popular) | $79 | 5.000 | $0,008 | $80 | 3 | 5 |
| Pro | $199 | 20.000 | $0,005 | $150 | 5 | ilim. |
| Enterprise | $399 | 50.000 | $0,004 | $250 | 10 | ilim. |
| Custom | contato | >50k ped ou >$5M GMV/mês | — | — | — | — |

Agência: Starter $249 (10 lojas/30k) · Growth $399 (20/75k) · Pro $599 (40/ilim) — white-label + API + MCP.
> Preços-base batem em todas as fontes; caps divergem entre site vivo e Capterra/GetApp (versão antiga). Usar o site.

## Integrações (superfície estreitíssima)
**Só:** TikTok Shop (API: pedidos/devoluções/settlement) · TikTok Ads (spend por SKU) · conector IA MCP · FBS (frete).
**Não encontrado:** Shopify, Amazon, WooCommerce, Meta/Google Ads, Klaviyo, Stripe/PayPal, marketplaces BR.
`/integrations` retorna 404.

## Diferenciais vs gaps
**Moat:** modelagem de fees específica de TikTok Shop (comissão de afiliado por creator, clawback de subsídio,
cost-sharing de frete por Shop Performance Score, settlement 1-31d) que Shopify-tools (BeProfit/Lifetimely/
Sellerboard) e DTC-tools (Triple Whale/Polar) não fazem · dado verificado via API + reconciliação · preço de
entrada mais barato ($29 vs Triple Whale $100+/Polar $400+) · conector MCP de IA.
**Gaps (whitespace):** marketplace único · US/inglês (sem PT-BR/fisco BR/gateways BR) · zero review externo ·
sem CAC/cohort/atribuição · crescimento só por SEO auto-publicado · empresa minúscula sem funding.

## Prova social
Só depoimentos first-party (3 na home). **Reviews de terceiros = ZERO** (Capterra/GetApp/GoodFirms/ScoutForge
0; G2/Trustpilot/Product Hunt/Shopify App Store sem listagem). ⚠️ Não confundir com Dashly/dashly.io (chat) nem Dash0 (observability).

## Empresa
Founders: **Yaroslav Lugovatsky** (CEO, ex-ops Amazon 7 dígitos, Vancouver) · **Alex Pavlenko** (CTO). Time ~4-6,
predominantemente ucraniano. 2024, sede FL/EUA, **bootstrapped $0**, ~US$660K ARR/valuation US$2M (est. GetLatka).

## Implicações pro produto BR
**Copiar:** a tese central (lucro real por pedido/SKU reconciliado com settlement) · modelo de preço (base baixa +
por volume com teto + agência white-label) · motor de conteúdo SEO ("quanto o TikTok Shop tira", "GMV vs lucro real",
"X vs nós") — em PT-BR quase sem concorrência · conector IA MCP · foco em agências multi-loja.
**Diferenciar (a brecha):** (1) fisco BR (Lucro Presumido/ICMS/DIFAL/Simples) · (2) multi-marketplace BR
(Shopee/Shein/ML + TikTok) · (3) economia de creator/afiliado granular (comissão por creator, tiers, clawback,
seeding, contribuição por motor — já temos o dado) · (4) prova social real (o ponto fraco deles) · (5) gateways/
logística BR. **Risco:** se internacionalizarem p/ BR, viram concorrente direto — a janela é fisco+multicanal+afiliado BR.

## URLs
dashboardly.io (home/pricing/features/about/blog + 5 posts) · help.dashboardly.io (MCP) · /integrations=404 ·
capterra.com/p/10033082 · getapp.com/.../dashboardly · goodfirms/scoutforge · getlatka.com/companies/dashboardly.io ·
scamadviser · linkedin.com/company/dashboardly. **Não encontrado:** G2/Trustpilot/Product Hunt/Shopify App Store, nº de clientes, reviews independentes.
