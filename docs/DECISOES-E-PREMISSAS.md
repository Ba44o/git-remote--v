# Decisões & Premissas — ledger

Registro de **premissas testadas contra dado real**: o que se confirmou, o que caiu, e o que
segue em aberto. Existe porque o histórico só guardava os erros — premissa certa era consumida
em silêncio e evaporava.

**Contrato:** toda análise declara a premissa antes de calcular e fecha com veredito explícito
(✅ confirmada · ❌ refutada · ⏳ em aberto). Confirmação entra aqui igual à refutação.

> Decisões **arquiteturais** (stack, contrato de API, design) ficam no `ROADMAP.md` → 🧠 Decisões.
> Aqui é raciocínio de **negócio**: por que acreditamos no que acreditamos.

---

## ✅ Confirmadas

| # | Premissa | Evidência | Data | O que mudou |
|---|---|---|---|---|
| C1 | **Vídeo de creator é o motor principal de GMV** | Vídeo = 43% do GMV; o vídeo #1 sozinho = 23,7% | jul/26 | Justificou o seeding em escala e o Radar de creators |
| C2 | **O modelo de taxas do TikTok BR é decomponível e previsível** | Validado em 480 pedidos com **resíduo 0**: settlement = receita − fee − frete; fee = comissão 6% + frete 6% + R$4/item + afiliada + GMV Max | jul/26 | Base de toda a conciliação esperado×real (`conciliacao_pedido`) |
| C3 | **Dá pra ter um GMV que bate com o Seller Center, sem atraso** | GMV oficial (Orders API, `total_amount` onde `paid_time>0`) fecha em **+0,3%** | jun/26 | Virou o número-headline do console |
| C4 | **A operação tem margem de contribuição positiva** | jun/26: R$149.656 (R$9,85/peça), settlement − CPV reconciliado | jul/26 | Tirou "estamos no vermelho" da mesa; foco virou onde vaza |
| C5 | **Live própria é muito mais barata que live afiliada** | CPA por motor: live própria **R$7** · card R$14,60 · live afiliada parada em R$406 | jul/26 | Priorização de motor na Posição de Escala |
| C6 | **Mix por canal é dado real, não estimativa** | Tabela `tracker_canais`, atribuição por pedido | jul/26 | Proibido estimar mix — sempre consultar a fonte |

---

## ❌ Refutadas

| # | Premissa | O que o dado mostrou | Data | O que mudou |
|---|---|---|---|---|
| R1 | **"O preço subiu R$69,90→R$109,90 e derrubou julho"** (briefing levado a consultoria externa de copy) | Preço **parado em ~R$80 há 3 meses** (mai 80,93 · jun 79,64 · jul 80,15). Causa real: **corte de mídia −42%** (R$52k→R$30k) com **ROI intacto** (7,78→7,81) | 22/07/26 | Derrubou todo o diagnóstico da consultoria ("reposicionar, justificar premium"). Ação vira: **voltar a verba** |
| R2 | **"Ruptura de estoque come a margem"** | Ruptura = **R$1.548/mês** (ruído). Devolução por **modelagem** = R$76.974/mês, 77% das devoluções são "não serviu", pior no tam 46. **50× maior** | jul/26 | Dono do problema mudou de logística para **fábrica** (gradação 42/44/46) |
| R3 | **"Vídeo de afiliada é orgânico, sem custo de mídia"** | **47,2% é amplificado**. Pós-mídia: vídeo R$11,70 > live R$10,92 > **loja própria R$7,08 (a pior)** | jul/26 | Contribuição por canal passou a ter 3 lentes; ranking inverte depois da mídia |
| R4 | **"Rhode é Lucro Real (34% de IR)"** | É **Lucro Presumido**, ~6,4% sobre faturamento, sem os 34% | jul/26 | Console corrigido (TX_VENDA=6,4 / TX_IR=0) — estávamos **subestimando** o lucro |
| R5 | **"O custo de GMV Max sai do settlement"** | Sai da **conta de ads**, tanto no Tradicional quanto em Vendas Líquidas. Provado com 98 statements | jul/26 | Lucro subtrai `ads_custo` inteiro; `affiliate_ads_commission` é comissão de creator, não custo |
| R6 | **"Tem divergência de repasse do TikTok pra recuperar"** | Comissão exata 6%, repasse faltante **R$0** com base completa (abr–jun) | 15/07/26 | Matou o modelo de success-fee por recuperação no SaaS. Valor = **visibilidade**, não recuperação |
| R7 | **"Se a contagem bate, a paginação está certa"** | Sem `order=<pk>`, o offset pula/duplica linhas e **a contagem não denuncia** (4.842 de 4.842 com PKs repetidos). Split por canal saiu enviesado: 1.157/1.897/2.961 quando o certo era **1.423/2.438/2.154** | 27/07/26 | Contrato de leitura do Supabase; 10 coletores varridos; RUNBOOK #17 |

---

## ⏳ Em aberto

| # | Premissa | Status | O que falta |
|---|---|---|---|
| A1 | **"Mais criativo derruba o CAC do card"** (vídeo → GMV-Max → CAC → pedidos) | **Aposta declarada.** A favor: starvation real — só **27 de 3.375** criativos entregam. Mas a queda de CAC (R$14,60→~R$11) **nunca foi medida** | Teste controlado: subir volume de seed e medir CAC do card antes/depois |
| A2 | **"O preço de etiqueta não subiu"** | Só enxergo o preço **realizado** (líquido). Catálogo tem etiqueta bem maior (REF529/552 R$142,41) com ~44% de desconto no PDV. Se a etiqueta subiu e o desconto absorveu, **não aparece** no realizado e ainda pode machucar conversão | `produtos` não guarda histórico de preço → **só o Humberto confirma** |
| A3 | **Gap da meta 10k = +12% em pedidos com 2 alavancas custo-zero** | Modelado (reativar creator 206→160 + kit 2ª peça Marmorizada+Stone 130×), não testado | Executar uma das alavancas e medir |
| A4 | **Impacto de ICMS na cascata de lucro** | Não modelado | Confirmar com o Lucas |
| A5 | **Vazamento de R$104k/mês em pagamento não completado** (Pix expira, ~59% dos cancelamentos) | Medido, **causa-raiz não investigada** | É prazo do Pix? UX do checkout? Fora do nosso controle no TikTok? |

---

## Como usar

- **Antes de investigar algo**: procurar aqui primeiro. R1–R7 já custaram trabalho.
- **Ao fechar uma análise**: adicionar a linha (premissa → evidência → veredito → data → ação).
- **Premissa confirmada envelhece.** A data está aqui pra isso — base velha pode ter virado.
- Quando uma premissa vira decisão de arquitetura, ela **também** entra no `ROADMAP.md` → 🧠.
