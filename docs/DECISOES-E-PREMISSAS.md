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

---

## P10 · Liquidação real da Mom Marmorizada REF588 (10/08/2026) ⏳

**Premissa declarada:** "liquidação média" = `conciliacao_pedido.settlement` real por pedido,
rateado por linha pelo share de GMV, dividido pelas **peças liquidadas** (não pelas vendidas) —
mesmo método de [[reference_liquidacao_cor_canal]]. É o que **entra na conta pra sacar**: já
descontou comissão TikTok, frete, R$4/item e comissão de afiliada; **não** desconta mídia
GMV Max (sai da conta de ads) nem imposto.

| Período | Peças | Preço/pç | **Liq/pç** | Taxa efetiva | Cobertura |
|---|---|---|---|---|---|
| mai/26 | 332 | 82,79 | **59,63** | 29,7% | 97% |
| jun/26 | 511 | 87,11 | **57,54** | 34,7% | 99% |
| jul/26 | 302 | 89,80 | **53,42** | 40,5% | 99% |
| **mai–jul (blend)** | **1.145** | **86,57** | **R$ 57,05** | 34,1% | 98% |

ago/26 ilegível (cobertura 12% — settlement atrasa).

**Achado — CORRIGIDO 10/08 pelo dono:** `custos_sku` trazia REF588 = R$ 52,00 (import de 23/06).
O CPV real é **R$ 44,00**. ✅ **Corrigido no Supabase** (6 tamanhos, `fonte='dono 10/08/2026'`).
A conciliação e a aba Liquidação SKU estavam mostrando a margem da Mom R$ 8 pra baixo.

**Regra do dono (10/08):** margem de SKU = **settlement − CPV**. Descontar só o que a
plataforma desconta; **imposto fica fora** (entra depois, no P&L, não na leitura de SKU).

### O "desconto" de R$ 85,72 era ficção de vitrine — ❌ minha leitura anterior

`gross_sales_amount` é **179,90 em 222/222 pedidos** — é o preço "de" riscado, não um preço
praticado. Logo `seller_discount` não é desconto: é só a distância até o preço real. **Mix real
de preço em jul (222 pedidos de 1 peça, sem devolução):** 99,90 = 51% · 89,90 = 40% · **79,90 = 9%**
(esse terceiro degrau não estava no radar do dono).

### O cupom do TikTok existe e NÃO sai do bolso do vendedor — ✅

Cupom da plataforma em **50% dos pedidos** (R$ 3,83/pç na média; R$ 5,00 ou R$ 8,99 quando
aparece). O cliente paga menos (R$ 92,80 médio), mas **`revenue_amount` é sempre exatamente o
preço do vendedor** (99,90 / 89,90 / 79,90 — 222/222). Quem banca é o TikTok. ✅ Suspeita do
dono confirmada quanto ao cupom, e a boa notícia é que o subsídio é da plataforma.

### O que realmente come a margem: FRETE GRÁTIS (não a taxa)

Fonte: `/finance/202309/statements/{id}/statement_transactions`, campos crus (jul, R$/peça):

| | R$/pç |
|---|---|
| Frete real cobrado pela transportadora | **−24,48** |
| Subsídio de frete do TikTok | +11,13 |
| Frete pago pelo cliente | +1,52 (**83% dos pedidos o cliente paga ZERO**) |
| **= a loja absorve** | **−11,83/pç** |

**R$ 11,83 é 2,1x a comissão de 6% (R$ 5,64).** Estável nos 3 canais (loja 12,26 · vídeo 11,47 ·
live 11,27) → é estrutural, não é mix. Isso **nomeia** o "serviço+frete acima do modelo" que
estava em aberto: era frete grátis subsidiado pela loja.

### Números finais REF588 · jul/26

| Recorte | Liq/pç | Margem (− CPV 44) |
|---|---|---|
| Pedidos que ficaram de pé (222) | **63,82** | **+19,82** |
| Blend com devolução (todos) | **53,42** | **+9,42** |

**A devolução vale −R$ 10,40/pç** (15% dos pedidos liquidam ≤ 0). É a maior alavanca isolada
do SKU. Bate com [[project_perda_produto_modelagem]].

**Veredito:** ✅ liquidação e frete confirmados no dado cru · ❌ a cascata de desconto que
publiquei primeiro estava distorcida (li `gross_sales` como preço praticado) · ⏳ **em aberto:**
`fee_amount` **não fecha** com a soma dos componentes nomeados pela API — sobra R$ 5 a R$ 15/pç,
variando por pedido e maior nos de 99,90. Regressão não achou estrutura (R² 0,44). Próximo passo:
bater contra o extrato itemizado do Seller Center antes de dar nome. Não prescrever preço até lá.

**Também não dá pra afirmar (checado e descartado):** "subir de 89,90 pra 99,90 não chega na
conta". Na loja a média diz +R$0,92 mas a mediana diz −R$3,09 — dispersão alta, n=28. Sem sinal.

---

## P11 · "Desconto" do GMV Max — ❌ MINHA PRIMEIRA LEITURA ESTAVA ERRADA (10/08/2026)

**O que eu afirmei e está ERRADO:** *"(a) e (b) não se somam — o custo da campanha sai da conta
de ads, a comissão de ads sai do repasse; são coisas distintas."* **Falso para Vendas Líquidas.**
O dono apontou que existe um escopo onde o caminho do GMV Max aparece dentro das vendas líquidas —
e ele está certo. É o que a [[project_tiktok_fee_composition]] já registrava na correção de
10/07 e o que a §8.1 do `docs/CONCILIACAO.md` (leitura de junho) tinha deixado como ressalva
**e eu não li**.

### Os dois modelos são MECANICAMENTE diferentes

| | Cobrança | Onde aparece |
|---|---|---|
| **Tradicional** (`net_cost>0`) | pago antecipado | **conta de ads** — fora do settlement |
| **Vendas Líquidas** (`net_cost=0`) | % da receita bruta de cada pedido | **DENTRO do `fee_amount`** do settlement |

### Prova no dado cru (jul/26, 5.220 pedidos liquidados sem devolução)

Isolando o resíduo do fee — `fee_amount` − comissão 6% − afiliada − comissão de ads − frete
líquido − (serviço 6% + R$4) — a distribuição é **bimodal, não ruído**:

- **60% dos pedidos: resíduo ≈ 0** → só serviço/frete, sem mídia. Valida a régua 6% + R$4.
- **19% dos pedidos (996): resíduo = R$ 14.165,89 = 12,2% da receita deles** → é o
  pay-with-GMV. Compare: gasto VL de julho no `ads_campanha` = **R$ 16.087,22**. **88% batido.**

**E o cluster cai exatamente nos SKUs cujas campanhas são VL:**

| REF | % das linhas com cobrança VL | campanha |
|---|---|---|
| REF547 | 70,0% | mix VL |
| REF588 (Mom) | **66,5%** | `[GMV-MAX][MOM]` VL |
| REF528 | 62,0% | mix VL |
| REF587 | 59,7% | mix VL |
| REF562 | 49,1% | mix VL |
| **REF516 (hero)** | **12,2%** | `MARMORIZADA-CARD-PRINCIPAL` = **Tradicional** |

O hero fica no piso justamente porque a campanha dele é Tradicional. Por canal: loja 36,8% ·
vídeo afiliado 26,4% · live afiliada 7,5% (as lives VL são as **próprias**, que caem em "loja").

### Consequência que muda número

**1. Não subtrair o custo de ads inteiro do lucro.** Nos SKUs em campanha VL o settlement **já
está líquido de mídia**. Regra: **lucro = settlement − CPV − só ADS Tradicional** (`net_cost>0`).
Subtrair VL de novo é double-count.

**2. A margem da Mom (P10) melhora de leitura:**

| REF588 jul | n | Settlement | Margem − CPV 44 | Mídia embutida |
|---|---|---|---|---|
| Pedidos **com** cobrança VL | 145 (65%) | 61,04 | **+17,04 — já é PÓS-mídia** | 13,07 (13,5%) |
| Pedidos **sem** VL | 77 (35%) | 69,07 | +25,07 (falta a Trad rateada) | −1,70 (≈0) |
| Blend | 222 | 63,82 | +19,82 | — |

Os R$ 17,04 dos pedidos VL são margem **depois da mídia**, não antes como escrevi no P10.

### Os números de take (medidos, seguem válidos)

- **Comissão de ads no repasse** (`affiliate_ads_commission`, comissão do creator na taxa de
  ads): jul = 14% dos pedidos, níveis 8%/5%/3%, média 6,19%, peso 0,91% da receita. **Coisa à
  parte da mídia** — não confundir de novo.
- **Custo de campanha ÷ receita atribuída:** média jan–ago **12,6%** (R$ 444.429 / R$ 3.537.563).
  jul 13,4% · faixa 10,9% (fev) a 14,4% (mai).
- **Por campanha (jul):** hero card **17,7%** (era 15,1% jun), CPA R$ 18,19, 42% do gasto —
  pior take com o maior orçamento. Lives **8,5%**, CPA R$ 7,27. Mom 14,3%.

**Veredito:** ❌ minha leitura de que VL não toca o settlement — refutada no dado, 2 populações
separadas. ✅ **Resposta certa: o GMV Max cobra ~12–13% da receita, e ONDE ele cobra depende do
modelo** — Tradicional na conta de ads, Vendas Líquidas por dentro do fee de cada pedido.
⚠️ `docs/CONCILIACAO.md` §8.1 está **desatualizada** (conclusão de 08/07 baseada em junho, quando
VL era R$209; em julho virou R$16,1k = 35% do gasto). ✅ **Gap fechado (ver abaixo).**

### ✅ Fechamento do gap (10/08) — não falta dinheiro, falta settlement

O gap de R$ 1,9k era **artefato de corte + cauda não liquidada**, não cobrança oculta.

**1. O corte de R$6 era grosseiro.** Sensibilidade (jul):

| corte | VL identificado | % do gasto |
|---|---|---|
| ≥ R$ 2 | 15.150,59 | 94,2% |
| **≥ R$ 3** | **15.070,97** | **93,7%** |
| ≥ R$ 6 | 14.384,11 | 89,4% |
| ≥ R$ 10 | 12.144,94 | 75,5% |

O baseline do cluster não-VL é **mediana R$ 0,00** (n=3.509) → não há viés a corrigir; o corte
certo é **≥ R$ 3** (abaixo disso a cobrança se confunde com o arredondamento do serviço).

**2. A série diária casa: r = 0,944.** Gasto VL por dia × VL detectado no fee por dia, 31 dias.
As diferenças alternam de sinal em dias vizinhos (28/07 −776 → 29/07 +405) = **lag de 1 dia
entre a data do anúncio e a do pedido**, não valor faltando.

**3. Os R$ 1.016 restantes estão na cauda não liquidada.** 951 pedidos de julho (13,6% do GMV)
ainda não tinham statement legível em 10/08. À taxa implícita medida (3,06% da receita, blend
de todos os pedidos), eles valem **+R$ 2.378** — mais que o gap.

| | R$ | % do gasto VL |
|---|---|---|
| Piso — só o que já liquidou | 15.070,97 | 93,7% |
| Teto — projetando a cauda | 17.448,66 | 108,5% |
| **Gasto real (`ads_campanha`)** | **16.087,22** | — |

**O gasto cai dentro do intervalo.** ✅ **Conta fechada** — o custo do Vendas Líquidas está
integralmente dentro do `fee_amount`, dentro do erro de medição (±6pp). Não há cobrança
não identificada nem repasse a recuperar.

### Recorte pedido: só a campanha da REF588 (Mom)

`[GMV-MAX][MOM]-TESTE DE VENDAS LIQUIDAS-27.05` — **100% Vendas Líquidas**, sem Tradicional.

| mês | custo | receita atrib. | **take** | pedidos | CPA |
|---|---|---|---|---|---|
| mai/26 | 4.845,24 | 24.051,92 | 20,1% ⚠️ teste | 225 | 21,53 |
| jun/26 | 4.554,31 | 32.038,90 | **14,2%** | 314 | 14,50 |
| jul/26 | 2.938,12 | 20.577,88 | **14,3%** | 202 | 14,55 |
| ago (parcial) | 255,38 | 1.786,00 | **14,3%** | 18 | 14,19 |
| **total** | 12.593,05 | 78.454,70 | 16,1% | 759 | 16,59 |

**A taxa é 14,3% e está travada desde junho.** Maio (20,1%) era fase de teste — tinha uma
campanha Tradicional `[MOM-BAGGY]-07.05` a 18,5% e a VL a 25,2%, ambas encerradas.

**Confirmação cruzada pelo detector** (253 pedidos de jul contendo REF588, liquidados):
**70% pagaram VL**, R$ 13,26/pedido, **taxa mediana 14,1%** (p75 14,3%) — bate com o take de
14,3% da campanha. Diluído em todas as peças de Mom: **R$ 9,24/peça**.

**Consequência:** a campanha da Mom não tem Tradicional → **a margem de R$ 19,82/pç do P10 já é
pós-mídia**, não falta subtrair nada.

**Limite que segue de pé:** "receita atribuída" do GMV Max **não é receita incremental**.

---

## P12 · Mega live da Amanda (06/08) — "live grande com muita mídia é boa" ❌ REFUTADA (10/08/2026)

**Premissa declarada antes de calcular:** uma live 2x maior em GMV, com ROAS de 8,6x, é um
resultado bom para a operação.

**Veredito: ❌ REFUTADA.** ROAS não é a régua desta operação — a margem por peça é. A live
**empatou**: +R$ 107,89 (cenário A) / −R$ 44,32 (cenário B, com a campanha 09.07). **A mídia
consumiu 96% da margem.**

> ⚠️ **Correção registrada em 10/08 (2ª rodada).** Minha primeira leitura disse −R$ 705,39 e
> estava errada: apliquei a taxa efetiva sobre o que o **cliente pagou**, quando a base do fee é
> o **revenue** (= produto pago + cupom da plataforma). Errei R$ 813 pra baixo. Ver "base do fee".

**Lente do headline:** o número da live é **R$ 28.477,84 — o GMV da SALA** (`/shop_lives`, é o que
o painel/Seller Center mostra, ~28.493 com drift de snapshot). Os R$ 33.465,81 são a atribuição
do **link da Amanda**, a preço **pré-cupom**. Cascata: extrato 33.465,81 − cupom 2.242,09 =
produto pago 31.223,72 − nunca pago 6.765,17 (80 pedidos) − pagou-e-cancelou 1.245,82 (16) =
**23.356,76 de produto vivo** (bate ao centavo com `pedido_pagamento.sub_total`, 260 ped / 326 pç).
A sala tem 390 itens contra 343 pagos no link dela — **a sala inclui quem comprou sem o link da
creator**, e a API não devolve `order_id` por sala, então as lentes não fecham pedido a pedido.

### ✅ A BASE DO FEE É O REVENUE, NÃO O QUE O CLIENTE PAGOU (provado, não é premissa)

Duas coisas testadas em `statement_tx` de julho:

1. **O cupom da plataforma volta pra loja.** `revenue = sub_total + platform_discount` em
   **1.146 de 1.149** pedidos liquidados com cupom. O TikTok reembolsa — o desconto sai do
   bolso dele, não do da loja.
2. **A comissão da creator incide sobre o revenue.** Comissão ÷ revenue cai em % de tabela
   redondo (12 / 10 / 8 / 9%) em **99,1% de 1.188 pedidos**; comissão ÷ o-que-o-cliente-pagou
   vira ruído (8,2%). Ou seja: a loja paga comissão sobre uma base que ela **de fato recebe**.
   Não há vazamento aqui — a leitura de que "paga comissão sobre dinheiro que não entrou" é FALSA.

**Régua correta:** `settlement ÷ revenue = 68,97%` (julho, subset comissão de afiliada >8%,
n=2.502). Fee = 31,03% do revenue: afiliada 10,79% + plataforma 6,00% + frete 1,03% + tarifas.
**Nunca aplicar taxa sobre `sub_total`** — subestima o revenue pelo cupom (7,8% nesta live).

### Os números, na régua certa

| | mega live 06/08 | live 19/07 (melhor anterior) |
|---|---:|---:|
| GMV da sala (headline) | **28.477,84** | — |
| GMV atribuído ao link (pré-cupom) | 33.465,81 | 15.933,00 |
| Produto pago e vivo | 23.356,76 | 11.432,78 |
| Revenue (base do fee) | 25.189,53 | 12.168,10 |
| Ticket/pedido · peças/pedido | **89,83 · 1,25** | 71,45 · 1,06 |
| Ads | **2.507,33** | 150,00 |
| ROAS · CPA | 8,58x · 9,64 | 32,84x · 0,94 |
| Margem antes da mídia | 2.615,22 | 775,34 |
| **Margem por peça** | **8,02** | 4,59 |
| Ads por peça | **7,69** | 0,89 |
| **Resultado pós-mídia** | **+107,89** | **+625,34** |

**Por que refuta:** a economia unitária da mega live é a **melhor** da creator (R$ 8,02/peça de
margem contra R$ 4,59) — o formato funciona. Mas a mídia entrou a R$ 7,69/peça e comeu tudo.
**Teto de mídia por live = margem por peça × peças projetadas**, não "enquanto o ROAS for alto".
Break-even desta live: R$ 2.615,22 — e gastar até o break-even é trabalhar de graça.

**O que ficou CONFIRMADO ✅ (o formato funciona):** ticket +25,7%, 1,25 peças/pedido e margem
por peça +74,8% vs a live anterior. O produto se paga.

**Achado colateral ✅:** no extrato do afiliado, `INELIGIBLE` **é exatamente o pedido cancelado**
(107 linhas, cruzamento 1:1 contra `pedidos_sku`). Não é regra de programa. Base de comissão
elegível = `TO-SETTLE`. Amanda: base R$ 25.189,53 → **R$ 2.860,92 (11,36%)**.

**Segunda alavanca — cancelamento:** 25,2% do GMV cancelou; 63% disso por "pagamento atrasado"
(R$ 4.980,29 · 69 peças). Recuperar só isso vale **~+R$ 560** de margem — 5x o lucro da live.

**Alerta de dado:** `affiliate_perf` (agregado da API) diverge R$ 135,56 (3,7%) da soma linha a
linha de `extrato_pedidos` no mesmo dia. **Pagar pelo extrato por pedido**, que é auditável.

**⏳ Em aberto:** a campanha `LIVE-AMANDA-09.07` gastou R$ 152,21 em 06/08 sem linha por `room_id`
em `live_sessao` — não dá pra cravar se é mídia desta live. Obriga o P&L a ter 2 cenários.

Relatório: `relatorios/2026-08/Relatorio Mega Live Amanda 06-08_2026-08-10.{md,xlsx}`
