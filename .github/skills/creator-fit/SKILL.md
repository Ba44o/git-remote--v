---
name: creator-fit
description: >
  Analisa performance de creators e afiliados: engajamento, alcance,
  conversão e GMV gerado. Calcula score de fit e recomenda priorização
  para próximas campanhas.
  Use quando pedir análise de creators, score de afiliados,
  quais creators priorizar ou relatório de influenciadores.
---

# Skill: gestão e análise de creators

## Quando usar
- "analise os creators dessa semana"
- "quais creators geraram mais GMV?"
- "calcule o score dos afiliados"
- "quem devo priorizar na próxima campanha?"
- "relatório de influenciadores do mês"
- ao receber planilhas com dados de creators ou exports de afiliados

## Localização dos dados
- Planilhas de creators: `/dados/creators/`
- Dados de afiliados TikTok Shop: `/dados/marketplace/tiktokshop/afiliados/`
- Dados de afiliados Shopee: `/dados/marketplace/shopee/afiliados/`

## Campos esperados na planilha de creators

| Campo | Descrição |
|-------|-----------|
| `nome` | Nome do creator |
| `plataforma` | TikTok, Instagram, YouTube, etc. |
| `seguidores` | Total de seguidores |
| `posts_periodo` | Número de posts no período |
| `visualizacoes` | Total de visualizações |
| `engajamento` | Curtidas + comentários + shares |
| `taxa_engajamento` | engajamento / alcance × 100 |
| `cliques_loja` | Cliques gerados para a loja |
| `pedidos_gerados` | Pedidos atribuídos ao creator |
| `gmv_gerado` | GMV atribuído ao creator |
| `custo` | Cachê ou comissão paga |

## Processo passo a passo

1. **Leia o CLAUDE.md** e localize os arquivos em `/dados/creators/`
2. **Carregue os dados** do período
3. **Calcule métricas derivadas** para cada creator:

```
Taxa de engajamento = (curtidas + comentários + shares) / visualizações × 100
CPV (custo por visualização) = custo / visualizações
CPC (custo por clique) = custo / cliques_loja
CPA (custo por pedido) = custo / pedidos_gerados
ROAS creator = gmv_gerado / custo
```

4. **Calcule o Score de Fit** (0 a 100):

```
Score = (peso_roas × ROAS_normalizado)
      + (peso_engajamento × engajamento_normalizado)
      + (peso_gmv × gmv_normalizado)
      + (peso_consistencia × consistencia_normalizada)

Pesos sugeridos (ajustar conforme objetivo):
- ROAS: 35%
- GMV gerado: 30%
- Taxa de engajamento: 20%
- Consistência (posts no período): 15%

Normalização: valor_creator / valor_máximo_do_grupo × 100
```

5. **Classifique** os creators em 3 categorias:
   - **Tier A** (Score ≥ 70): priorizar, aumentar verba/cachê
   - **Tier B** (Score 40–69): manter, monitorar evolução
   - **Tier C** (Score < 40): reavaliar parceria

6. **Gere recomendações** para próxima campanha
7. **Salve** em `/relatorios/YYYY-MM/YYYY-MM-DD_creator-fit.md` e `.xlsx`

## Formato de output

```markdown
## Creators — [período]

| Creator | Plataforma | GMV | ROAS | Engaj. | Score | Tier |
|---------|-----------|-----|------|--------|-------|------|
| Nome A | TikTok | R$ X | X.Xx | X% | 85 | A |
| Nome B | Instagram | R$ X | X.Xx | X% | 62 | B |
| Nome C | TikTok | R$ X | X.Xx | X% | 38 | C |

### Recomendações para próxima campanha
- **Priorizar (Tier A):** [lista]
- **Monitorar (Tier B):** [lista]
- **Reavaliar (Tier C):** [lista com justificativa]

### Observações
- [qualquer creator com dado faltante ou inconsistência]
```

## Regras
- Score é comparativo dentro do grupo atual — não comparar entre períodos diferentes sem ajuste
- Se só há 1 ou 2 creators, o score tem pouco valor estatístico — indicar isso no relatório
- Sempre registrar se o GMV é atribuição direta (link rastreável) ou estimada
