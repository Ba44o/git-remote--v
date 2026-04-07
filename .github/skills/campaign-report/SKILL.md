---
name: campaign-report
description: >
  Consolida e analisa performance de campanhas de mídia paga: Meta Ads,
  Google Ads, TikTok Ads, GMV Max Shopee e GMV Max TikTok Shop.
  Use quando pedir relatório de campanhas, análise de mídia paga,
  performance de anúncios ou ROAS por canal.
---

# Skill: relatório de campanhas

## Quando usar
- "relatório de campanhas da semana"
- "como foi o Meta Ads esse mês?"
- "compare ROAS entre os canais"
- "quais campanhas estão performando melhor?"
- "analise o GMV Max"
- ao receber exports de Meta Ads, Google Ads ou TikTok Ads

## Canais a consolidar (sempre nesta ordem)

1. **Meta Ads** — Facebook + Instagram (buscar em `/dados/campanhas/meta/`)
2. **Google Ads** — Search + Shopping (buscar em `/dados/campanhas/google/`)
3. **TikTok Ads** — In-feed + TopView (buscar em `/dados/campanhas/tiktok/`)
4. **GMV Max TikTok Shop** — campanha automatizada TikTok (buscar em `/dados/campanhas/tiktok/` ou `/dados/marketplace/tiktokshop/`)
5. **GMV Max Shopee** — campanha automatizada Shopee (buscar em `/dados/campanhas/shopee/` ou `/dados/marketplace/shopee/`)
6. **Orgânico** — registrar separadamente, não misturar com pago

## Processo passo a passo

1. **Leia o CLAUDE.md** para confirmar canais ativos
2. **Localize os exports** do período em `/dados/campanhas/`
3. **Para cada canal, extraia:**
   - Investimento total
   - Impressões e alcance
   - Cliques / sessões geradas
   - Conversões / pedidos atribuídos
   - Receita atribuída (quando disponível)
   - ROAS (calcular se não vier pronto)
4. **Monte a tabela consolidada** com todos os canais lado a lado
5. **Calcule o ROAS blended** (total de receita / total investido)
6. **Identifique:**
   - Melhor canal por ROAS
   - Canal com maior volume de GMV
   - Campanhas com CPA acima da média (alerta)
   - Oportunidades de redistribuição de verba
7. **Salve** em `/relatorios/YYYY-MM/YYYY-MM-DD_campaign-report.md` e `.xlsx`

## Métricas por tipo de campanha

### Meta Ads / Google Ads / TikTok Ads (pago direto)
- Investimento, Impressões, CPM, CTR, Cliques, CPC, Conversões, CPA, Receita, ROAS

### GMV Max (Shopee e TikTok Shop)
- Investimento, GMV gerado, ROAS, Pedidos, Ticket médio
- Nota: GMV Max é automatizado — comparar eficiência vs campanhas manuais

### Orgânico
- Alcance, Impressões, Engajamento, Cliques para loja
- Não tem investimento direto — calcular custo de produção se disponível

## Formato de output

```markdown
## Campanhas — [período]

| Canal | Investimento | GMV/Receita | ROAS | Pedidos | CPA |
|-------|-------------|-------------|------|---------|-----|
| Meta Ads | R$ X | R$ Y | X.Xx | N | R$ X |
| Google Ads | R$ X | R$ Y | X.Xx | N | R$ X |
| TikTok Ads | R$ X | R$ Y | X.Xx | N | R$ X |
| GMV Max TikTok | R$ X | R$ Y | X.Xx | N | R$ X |
| GMV Max Shopee | R$ X | R$ Y | X.Xx | N | R$ X |
| **TOTAL PAGO** | **R$ X** | **R$ Y** | **X.Xx** | **N** | **R$ X** |
| Orgânico | — | R$ Y | — | N | — |

### Destaques
- Melhor ROAS: [canal] (X.Xx)
- Maior volume: [canal] (R$ X GMV)

### Alertas
- [canal] com CPA acima da média: R$ X vs média R$ Y

### Recomendação
- [1-3 ações concretas para o próximo período]
```
