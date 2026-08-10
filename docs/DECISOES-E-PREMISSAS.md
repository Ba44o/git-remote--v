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
| R8 | **"O 'GMV gerado' do relatório de seeding é o retorno da amostra e fecha com o mês"** | **Não fecha e não é retorno.** A atribuição não tem data-limite: soma toda venda de afiliada da creator depois do convite, pra sempre. Julho foi **R$ 57,7k (31/07) → R$ 67,6k (01/08) → R$ 75,5k (02/08)** sem **nenhuma amostra nova**. Pior: comparar meses era maçã com laranja — junho puxado até 06/07, julho até 02/08. E **84% do número é 1 creator** (@tacianecreator, já top afiliada) | 02/08/26 | Métrica passa a exigir **janela fixa após o convite** + **coorte de observação completa** + leitura **com e sem a maior creator**. Painel de julho implementa os 3. Veredito da eficiência real: em toda janela fixa, **sem a maior creator o seeding dá prejuízo** (7d −R$1,1k · 14d −R$1,7k · 30d −R$436) |
| R9 | **"`affiliate_perf.gmv` é o GMV influenciado por creator — dá pra dizer '% do GMV que vem de afiliada'"** | **Não dá.** Em **abr/26 o GMV de afiliada bate R$981.789 contra R$917.399 de GMV oficial = 107%** — impossível. A série inteira fica em 80–96%, incompatível com o mix real por pedido (`tracker_canais`: **45,1% jun · 46,8% jul** das peças em video/live de afiliada). A API de Affiliate Orders atribui no **pedido criado** (não pago), inclui `SHOP`/`LINKSHARE` (vitrine) e credita a live própria rodada via programa de afiliado | 03/08/26 | `affiliate_perf` serve pra **ranking/tier de creator** (uso atual, ok) e **nunca** como numerador de share do GMV. Share de creator = `tracker_canais` (por pedido). Número citável: **~45% das peças**, ~71% se incluir live própria com creator |
| R10 | **"CTOR 2,52% = conversão por visualização, logo CO = 2,52 ÷ 28,4 = 8,9%"** (premissa do brief da extensão DashLive) | **Invertido.** `lives.ctor` **é** a taxa de compra após clique (o CO): bate ao 4º decimal em **182/182** lives v1 (`orders ÷ product_clicks`) e em **53/53** lives v2/v2-api (`attributed_sku_orders ÷ product_clicks`). A conversão por visualização é a **derivada**: CTR × CO = **0,79%** em abril (0,62% ponderada), não 2,52%. Logo o CO real de abril é **2,78%**, não 8,9% — o bench estava **3,2× inflado** por ter dividido onde devia multiplicar | 08/08/26 | Bench de CO deixa de ser "provisório derivado" e vira **medido** (`lives.ctor`). Sem isso o semáforo da extensão marcaria CO em ~31% do bench = **vermelho permanente** a live inteira, com gatilho falso de "conversão pós-clique baixa" |
| R11 | **"O CTR da live caiu de 28% (abr) para 6,6% (jun/jul)"** | **Não caiu — trocou de denominador.** Em v1/v2 `ctr = product_clicks ÷ views` (28,51% em abril, exato em 235/235 testáveis); em v2-api `ctr = product_clicks ÷ product_impressions` (5,14% = 1766/34371, exato). São métricas diferentes na mesma coluna. Comparar as duas séries lado a lado é maçã com laranja | 08/08/26 | Benchmark de CTR **não pode ser lido sem saber o schema**. Antes de usar 28,4% como meta ao vivo é preciso confirmar qual denominador a tela do Seller Center mostra hoje. `schema_version` vira filtro obrigatório em qualquer série de funil de live |
| R12 | **"O AOV é baixo porque o ticket é baixo"** (leitura ao abrir a aba CRM) | **É quantidade, não preço.** 91,8% dos pedidos têm **1 peça** (28.511 de 31.057) e 70,3% dos clientes ficam na faixa R$60–89, que é exatamente o preço do hero. **Attach rate = 8,2% · 1,10 peças/pedido.** O pedido de 2 peças tem ticket R$147,48 vs R$77,72 | 10/08/26 | AOV só sobe por **attach**, não por preço. E o par co-comprado real é **calça+calça em outra lavagem** (203x e 182x nos multi-produto) — a bata aparece só 49x. Cross-sell é por **cor**, não por categoria |
| R13 | **"Recompra é um ciclo de 60–90 dias"** | Medido nos 2.295 clientes com exatamente 2 pedidos: mediana **10 dias**, p75 = 28d, p90 = 51d. **41,8% recompram em ≤7d · 77,4% em ≤30d** | 10/08/26 | A janela de CRM é **D+0 a D+30 pós-entrega**, não reativação trimestral. Corolário duro: **14.563 clientes (66% da base)** já estão fora da janela — reativá-los exige motivo novo, não lembrete. Muda a ordem de prioridade do CRM inteiro |
| R14 | **"Devolução é ruído operacional"** | **73,5% das devoluções são "Item doesn't fit"** = 4.406 casos e **R$346.327** em 3,5 meses (**≈R$99k/mês**), em 16,7% dos pedidos. **95,5% viram `RETURN_AND_REFUND`** (dinheiro de volta), não troca | 10/08/26 | É o **maior público único de CRM da Rhode** e hoje ninguém fala com ele. Ação: interceptar antes do reembolso com troca de tamanho + Size Finder. Confirma e quantifica R2 pelo lado do cliente |
| R15 | **"Cliente trazido por creator vale mais"** | **Loja direta retém melhor que qualquer afiliada:** 4.775 clientes (21,7%), LTV R$110,68 e **volta 18,8%** — contra 4,6% a 16,4% das creators. Exceção: `alinecavanellas` (LTV R$124,70 · AOV R$102,09, vs R$82 da média) | 10/08/26 | Afiliada é motor de **aquisição**, não de retenção — e retenção é o que o CRM controla. O público da loja direta é o alvo #1 do CRM próprio. Vale estudar o que a `alinecavanellas` vende (AOV sugere combo) |

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

---

## P8 · Meta agosto/2026 = "R$230k faturados" (03/08/2026) ⏳

**Premissa declarada:** "230k faturado" = **faturamento LÍQUIDO** (settlement/liquidado, ~75% do GMV), NÃO GMV bruto.
- **Evidência:** julho GMV oficial R$589.510 · líq/GMV=76% (settle 328k/pago 433k). Agosto MTD (3d) 405 pç / R$30.867 → run-rate GMV **R$318.959** / líquido **R$239.219**. Se "230k"=GMV bruto seria −61% vs julho E já abaixo do run-rate (sem sentido como meta). Se =líquido, 230k ≈ o run-rate atual (R$239k) → coerente.
- **Tradução:** R$230k líq = **R$306.667 de GMV = ~4.024 peças** (AOV R$76). Run-rate já entrega ~R$239k líq — cushion FINO (4%) e frágil (agosto −46% vs julho pela mídia cortada; MTD 90% live, 73% live afiliada = concentração).
- **Veredito:** ⏳ **PENDENTE de confirmação do Humberto** — se faturado=GMV bruto, o plano inteiro muda. Atingível no ritmo atual SE segurar as lives; premium mix + re-escalar mídia dão a folga.
- **Ação:** confirmar a régua (líquido vs bruto) → baco a redistribuição SKU×canal + premium mix no workbook.

**CORREÇÃO (03/08, mesmo dia):** P8 estava contaminada com a operação toda. O dono corrigiu: **230k é meta de LIVE PRÓPRIA e só.** Régua = GMV do canal (não líquido). Base EXATA live_attr: jun R$205.788 · jul R$174.300 · ago MTD R$2.877 (só dia 01, frio). 230k = +32% vs jul. **É quase 100% FREQUÊNCIA** (68→88 lives, ~3/dia, ~103 pç/dia vs 73 em jul). Premium mix NÃO leva aos 230k (spread hero R$75×premium R$86 é pequeno → AOV só 77→79); payoff dele é MARGEM (+~R$4,7k). VL é folga (se paga). Plano: `relatorios/2026-08/Projecao Agosto/Meta 230k Live Propria Agosto_2026-08-03.xlsx`. Veredito ⏳ stretch, atrás do pace.

---

## P9 · Card de produto despina sozinho aos 30s (03/08/2026) ✅

**Premissa declarada:** "o card fixado permanece até o operador trocar de peça" — foi o
que publiquei no módulo de live em 01/08, e estava **errado**.

- **Evidência:** TikTok Seller University é explícita ("Pin product card every 30 seconds.
  Otherwise it will disappear"). O guia BR do Seller Center dava a entender persistência
  (métrica "Tempo com card fixado"). **Conflito resolvido pelo dono: o card some aos 30s.**
- **Consequência:** o bloco de venda tem 40s e o card vive 30s → quem pina só na abertura
  chega no **fechamento sem card na tela**. O CTA de comprar dispara sem porta.
- **Veredito:** ✅ card despina sozinho — mas ⚠️ **os 30s NÃO são exatos** (dono, 03/08).
  **REVERTIDO no mesmo dia:** eu tinha publicado um framework pin/repin/despin com gatilho
  aos ~25s. Falsa precisão em cima de um mecanismo que nunca medi — e a evidência que eu
  já tinha apontava contra. Rebaixado a **higiene** ("mantém um card no ar, tira quando
  trocar"), sem prescrição de cadência.

**Sub-premissa testada no mesmo passo — ❌ REFUTADA:** *"fixar mais = vender mais"*.
Nas 65 lives de julho a exposição de card varia 2,8x (p90/p10 de impressões de produto
por hora). Isolando o tamanho da audiência, as lives com **2,11x** mais impressão de
produto **por espectador** fizeram só **1,15x** de GMV/hora e converteram **pior** por
clique (**0,94x**); CTR 0,74x. Impressão a mais com o mesmo clique dilui o CTR.
→ **O ganho é de _timing_ (card vivo na hora de fechar), não de volume de repin.**
Não instruir a equipe a "pinar sem parar".

**Limite do dado:** "Tempo com card fixado" e "Qtd de vezes com card fixado" existem na UI
do Seller Center mas **não vêm no export** de SKU por live — a disciplina de repin foi
medida por proxy (impressões de produto), não diretamente.

**Ranking das alavancas (03/08) — só o medido, por valor mensal:**

| # | Alavanca | Vale/mês | Evidência |
|---|---|---|---|
| 1 | Duração 1,8h → 2,5h | **+R$ 67,4k** | top16 130min × bottom16 84min (1,55x) + TikTok oficial + guia BR + painel US |
| 2 | Compra após clique 2,33% → 2,80% | **+R$ 35,4k** | único diferencial forte top×bottom (1,62x); 94.461 cliques sem compra |
| 3 | Pagamento não concluído (metade) | +R$ 13,9k | taxa de pgto do hero = 80%, medido no export SKU |
| 4 | Card / pin | **não medido** | proxy aponta ao contrário (0,94x compra/clique) |

Soma de 1+2+3 = **+R$ 116,6k/mês** sobre base de R$ 173,3k. O card não entra no 80/20.
