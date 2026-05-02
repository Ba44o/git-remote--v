# Contexto do projeto

Este é um projeto de gestão de performance de marketing e marketplace.
O agente deve ler, analisar e compilar dados de múltiplas fontes e gerar
relatórios e projeções no padrão definido abaixo.

---

## 📚 Arquivos de referência (leia antes de começar trabalho novo)

- **`ROADMAP.md`** — fonte de verdade do que está pronto, em curso, e priorizado.
  Antes de iniciar feature nova, leia esse arquivo. Atualize após cada entrega.
- **`RUNBOOK.md`** — playbook de debugging quando algo quebra em produção.
  Cenários numerados (1-8) com sintoma → diagnóstico → fix conhecido. Quando
  o usuário disser *"tem um problema, [sintoma]"*, leia RUNBOOK.md primeiro.

**Workflow padrão de cada sessão:**
1. Trabalho de feature nova → `ROADMAP.md` → seção 🔜 Próximos
2. Bug em produção → `RUNBOOK.md` → identificar cenário → executar diagnóstico
3. Decisão arquitetural → registrar em `ROADMAP.md` → seção 🧠 Decisões
4. Novo modo de falha encontrado → adicionar ao `RUNBOOK.md`

---

## Estrutura de pastas

```
projeto/
├── CLAUDE.md                        ← este arquivo
├── dados/
│   ├── marketplace/                 ← exports de Shopee, Shein, TikTok Shop
│   ├── campanhas/                   ← exports de Meta Ads, Google Ads, TikTok Ads
│   └── creators/                    ← planilhas de creators e métricas
└── relatorios/                      ← outputs gerados pelo agente
    └── YYYY-MM/                     ← subpasta por mês
```

---

## Canais e plataformas ativas

### Marketplaces
- **Shopee** — principal canal de vendas
- **Shein** — canal de moda/lifestyle
- **TikTok Shop** — canal social commerce

### Mídia paga
- **Meta Ads** (Facebook + Instagram)
- **Google Ads**
- **TikTok Ads**
- **GMV Max Shopee** — campanha automatizada de GMV
- **GMV Max TikTok Shop** — campanha automatizada de GMV

### Orgânico
- Conteúdo orgânico TikTok e Instagram
- Creators e afiliados

---

## KPIs principais

| KPI | Descrição | Meta |
|-----|-----------|------|
| GMV | Volume bruto de vendas (todos os canais) | em construção |
| Faturamento líquido | GMV descontando devoluções e cancelamentos | em construção |
| ROAS | Receita gerada / investimento em mídia | em construção |
| ROI | Lucro / custo total | em construção |
| Taxa de conversão | Pedidos / sessões ou cliques | em construção |
| CPA | Custo por aquisição | em construção |
| CAC | Custo de aquisição de cliente | em construção |

> Nota: base de KPIs e metas em construção. O agente deve calcular variação
> vs período anterior sempre que não houver meta definida.

---

## Formato padrão de relatório

- **Formato de saída principal:** Excel (.xlsx) e Markdown (.md)
- **Periodicidade:** semanal (toda segunda-feira) e mensal
- **Estrutura obrigatória de todo relatório:**
  1. Resumo executivo (máximo 5 linhas)
  2. KPIs do período vs período anterior (tabela)
  3. Performance por canal (seção por canal)
  4. Destaques positivos e alertas
  5. Recomendações para próximo período

---

## Regras gerais para o agente

- Sempre comparar com o período imediatamente anterior ao analisado
- Quando faltar dado, registrar como "sem dado" — nunca inventar valores
- Arredondar percentuais para 1 casa decimal (ex: 12.3%)
- Salvar todo output em `/relatorios/YYYY-MM/` com nome `YYYY-MM-DD_tipo-relatorio`
- Antes de executar qualquer tarefa destrutiva (apagar, sobrescrever), pedir confirmação
- Tom dos relatórios: direto, objetivo, sem jargões desnecessários
