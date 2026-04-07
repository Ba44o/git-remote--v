---
name: marketplace-data
description: >
  Consolida dados de vendas dos marketplaces Shopee, Shein e TikTok Shop.
  Padroniza campos entre plataformas e gera visão unificada de GMV,
  pedidos, ticket médio, devoluções e performance por canal.
  Use quando pedir relatório de marketplace, análise de canal ou
  comparativo entre plataformas.
---

# Skill: consolidação de marketplace

## Quando usar
- "como foi a Shopee essa semana?"
- "compare os canais de marketplace"
- "qual canal teve mais GMV?"
- "consolide os dados de todos os marketplaces"
- ao receber exports de Shopee, Shein ou TikTok Shop

## Canais e localização dos dados

| Canal | Pasta | Formato esperado |
|-------|-------|-----------------|
| Shopee | `/dados/marketplace/shopee/` | .xlsx ou .csv (export do Seller Center) |
| Shein | `/dados/marketplace/shein/` | .xlsx ou .csv (export do Shein Seller) |
| TikTok Shop | `/dados/marketplace/tiktokshop/` | .xlsx ou .csv (export do TikTok Seller) |

## Processo passo a passo

1. **Leia o CLAUDE.md** para confirmar canais e período
2. **Localize os exports** em `/dados/marketplace/`
3. **Para cada plataforma, padronize os campos:**

### Campos obrigatórios (extrair de cada canal)
- `data` — data do pedido
- `pedidos` — número total de pedidos
- `pedidos_cancelados` — cancelamentos
- `pedidos_devolvidos` — devoluções
- `gmv_bruto` — valor bruto de vendas
- `gmv_liquido` — gmv_bruto - cancelamentos - devoluções
- `ticket_medio` — gmv_bruto / pedidos
- `taxa_cancelamento` — cancelados / pedidos × 100
- `taxa_devolucao` — devolvidos / pedidos × 100

4. **Monte a tabela consolidada** com todos os canais
5. **Calcule participação de cada canal** no GMV total (%)
6. **Identifique variação** vs período anterior
7. **Gere análise de mix de canais** — crescimento/queda de participação
8. **Salve** em `/relatorios/YYYY-MM/YYYY-MM-DD_marketplace-data.md` e `.xlsx`

## Atenção por plataforma

### Shopee
- GMV Max aparece separado no relatório de campanhas — não duplicar aqui
- Verificar se o export inclui pedidos em disputa (excluir ou sinalizar)
- Campo de GMV pode vir em centavos em alguns exports — dividir por 100

### Shein
- Confirmar se os dados são de GMV confirmado ou apenas pedidos feitos
- Verificar moeda (alguns exports vêm em USD — converter para BRL)

### TikTok Shop
- Separar vendas orgânicas de vendas via GMV Max / afiliados
- Live commerce pode vir em relatório separado — consolidar

## Formato de output

```markdown
## Marketplace — [período]

| Canal | GMV Bruto | GMV Líquido | Pedidos | Ticket Médio | Cancel. | Devol. | Mix % |
|-------|-----------|-------------|---------|-------------|---------|--------|-------|
| Shopee | R$ X | R$ Y | N | R$ X | X% | X% | X% |
| Shein | R$ X | R$ Y | N | R$ X | X% | X% | X% |
| TikTok Shop | R$ X | R$ Y | N | R$ X | X% | X% | X% |
| **TOTAL** | **R$ X** | **R$ Y** | **N** | **R$ X** | **X%** | **X%** | 100% |

### Variação vs período anterior
- GMV total: [valor] ([variação]%)
- Canal com maior crescimento: [canal]
- Canal com queda: [canal] (atenção)

### Alertas
- [qualquer canal com taxa de cancelamento > 5% ou devolução > 3%]
```
