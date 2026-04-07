---
name: kpi-analysis
description: >
  Analisa dados de performance, calcula KPIs (GMV, faturamento, ROAS, ROI,
  taxa de conversão, CPA, CAC) e projeta tendências para o próximo período.
  Use quando pedir análise de dados, projeção de KPI, variação de performance
  ou qualquer cálculo de indicadores de negócio.
---

# Skill: análise de KPI e projeção

## Quando usar
- "analise os dados de [período]"
- "qual foi o ROAS da semana?"
- "projete o GMV do próximo mês"
- "compare performance vs mês anterior"
- "calcule os KPIs do período"
- sempre que receber arquivos .xlsx, .csv ou .gsheet com dados de vendas

## Processo passo a passo

1. **Leia o CLAUDE.md** para entender o contexto do projeto
2. **Identifique os arquivos** na pasta `/dados/` relevantes ao período pedido
3. **Carregue os dados** — priorize: marketplace > campanhas > creators
4. **Calcule os KPIs principais:**
   - GMV total = soma de vendas brutas de todos os canais
   - Faturamento líquido = GMV - devoluções - cancelamentos
   - ROAS = receita atribuída / investimento em mídia (por canal e consolidado)
   - Taxa de conversão = pedidos / sessões (ou cliques para campanhas pagas)
   - CPA = investimento total / número de pedidos
   - Variação % = (valor atual - valor anterior) / valor anterior × 100
5. **Projete o próximo período** usando média móvel dos últimos 3 períodos disponíveis
6. **Identifique destaques e alertas:**
   - Destaque: variação positiva > 10%
   - Alerta: variação negativa > 10% ou dado faltante crítico
7. **Gere o relatório** no formato definido no CLAUDE.md
8. **Salve** em `/relatorios/YYYY-MM/YYYY-MM-DD_kpi-analysis.md` e `.xlsx`

## Cálculos de referência

```
ROAS = receita_atribuida / investimento_midia
ROI = (receita - custo_total) / custo_total * 100
Taxa de conversão = (pedidos / sessoes) * 100
CPA = investimento / pedidos
Variação % = ((atual - anterior) / anterior) * 100
Projeção = média(últimos_3_períodos) * fator_sazonalidade
```

## Formato de output esperado

```markdown
## KPIs — [período]

| KPI | Atual | Anterior | Variação |
|-----|-------|----------|----------|
| GMV total | R$ X | R$ Y | +Z% |
| ROAS consolidado | X | Y | +Z% |
| Taxa de conversão | X% | Y% | +Z pp |
| CPA | R$ X | R$ Y | -Z% |

### Projeção próximo período
- GMV estimado: R$ X (base: média móvel 3 períodos)
- Confiança: alta/média/baixa (depende da consistência dos dados)
```

## Regras
- Nunca inventar dados — marcar como "sem dado" se não encontrar
- Sempre indicar a fonte de cada número (qual arquivo, qual aba)
- Se os dados tiverem inconsistência, reportar antes de calcular
