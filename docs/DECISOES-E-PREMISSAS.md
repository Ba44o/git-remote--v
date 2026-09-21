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
| R16 | **"CPO ≤ R$13 é a meta de mídia e R$16,90 o limite de corte"** (régua do Plano de Ação TikTok v1) | **R$13 é o BREAK-EVEN, não a meta.** A R$79,90 com afiliada a margem é R$11,20/peça × 1,10 peça/pedido = **R$12,32 de margem por pedido**. Escalar até R$16,90 é pagar R$4,58 para vender cada pedido | 25/08/26 | Régua vira **CPO teto = margem por pedido do SKU** (função do preço), meta operacional 60–70% do teto. Calculadora viva na aba `Economia Unitária` do plano |
| R17 | **"Um SKU-isca a R$41,90 (como o herói da Gaven) destrava alcance sem furar o liquidado"** | **Impossível:** o CPV real é **R$44–45** (dono, 10/08). A R$41,90 a peça sai abaixo do custo antes de qualquer taxa — perda de ~R$30/peça. A Gaven chega nesse preço com outra estrutura de custo | 25/08/26 | Ação substituída pelo **combo 516+588 com cupom R$15** (R$26,85 de margem/pedido = **9,5×** o corte de preço). Copiar preço sem copiar custo é vender prejuízo com escala |
| R18 | **"Escalar mídia é a alavanca de menor risco do plano"** (raio-x de Ads) | **Parcialmente certo — e minha 1ª estimativa (25/08) estava errada.** Estimei +R$2,1k cruzando ROAS blended 7,8 com margem COM afiliada — combinação que **não corresponde a campanha nenhuma**. Medido por campanha (R19): recompor R$22k vale **+R$15,4k no card** ou **+R$41,7k na live da sala Rhode**. Mídia não é empate | 25/08/26 · corrigido 25/08/26 | Mídia **volta** para o meio da fila de alavancas. O que continua valendo: recompor **depois** do attach subir, e **não no card** — ver R19 |
| R19 | **"Basta separar campanha 'com afiliada' de 'sem afiliada' para saber onde pôr a verba"** (minha própria formulação de A6) | **A partição limpa não existe** — atribuição de ads e de afiliada se **sobrepõem**: em jun/26 os ads reivindicam 61,3% dos pedidos enquanto só 38,9% das peças não têm afiliada, logo **no mínimo 15,6%–36,4% dos pedidos pagos carregam comissão**. Mas a pergunta certa (onde rende mais) tem resposta limpa: **card/vitrine 71% da verba, ROAS 7,00, CPO R$12,62 → +R$8,85/pedido** · **live da sala Rhode 26% da verba, ROAS 10,73, CPO R$7,42 → +R$14,05/pedido**. A verba está 71% no canal que rende menos | 25/08/26 | Fecha A6. Verba recomposta vai para **LIVE da sala Rhode**, não para o card. Sem sinal de saturação no card (corr. gasto×ROAS = +0,552, n=8) — mas há **declínio secular** de eficiência (card 7,62→6,06 · live 11,88→9,24 em 8 meses) |
| R20 | **"O GMV por creator ativo é uma constante de ~R$1.900 — produtividade estável"** (RaioX Afiliados) | ❌ **REFUTADA — é artefato de média sobre distribuição assimétrica.** A **mediana** é R$95–199 (média/mediana de 10,7× a 23,2×) e o decil superior carrega **85,5%–92,3%** do GMV em todos os meses. A média ficou parada porque o topo caiu **e** a cauda foi ceifada junto. A prova: GMV/creator **sem o top 5** caiu **44%** (R$1.186 em mar → R$666 em ago) | 27/08/26 | Nunca usar a média dessa base. Creator marginal vale a **mediana (R$199)**, não a média. Derruba R27 |
| R21 | **"A janela de 11–16h rende quase o dobro por live"** (export de live) | ❌ **REFUTADA — é duração disfarçada de horário.** Sem controle: coef −37,2, t = −0,17, **R² = 0,001**. Controlando duração o coeficiente vira **−583,1 (t = −2,34)**. Mecânica: lives de 11–16h duram **1,85 h**; as de 20h+, **1,22 h**. Controle por oferta (texto do título, inferência): n.s. Apresentadora: 🔒 não mensurável | 27/08/26 | Sai do plano. Não marcar live por horário — marcar live **longa** |
| R22 | **"Duração da live é o único driver significativo de GMV/hora"** | ✅ **CONFIRMADA.** +R$364,6/h por hora extra de sessão (t = +3,86, R² = 0,466, n = 46). Peças/1k views também sobe com duração (+1,9/h, t = +4,45). 32 das 46 lives de ago tiveram <2h | 27/08/26 | Alavanca nº2 do plano: **toda live com no mínimo 2h**, consolidando sessões curtas. Ganho medido +R$3.939/mês de contribuição a 1 h/semana de equipe |
| R23 | **"O refund de 24% é gargalo de crescimento"** (RaioX Afiliados, ação Sem 3) | ❌ **REFUTADA.** Correlação refund% × GMV mensal = **r −0,068** (t = −0,14, n = 6). Falsificação limpa: **maio teve o MENOR refund da série (16,1%) e foi o pior mês até então**. Por coorte D+14 a série real é 18,2 · **21,0** · 16,1 · 21,6 · **26,4** · 20,6 — abril **não** foi o melhor mês (não é 14,1%) e o pico é **julho**, não agosto. Motivo dominante: "Item doesn't fit" **76,3%**; lag mediano 6 dias | 27/08/26 | Refund é **dreno de margem já embutido no settlement**, não alavanca de marketing. Sai do plano de marketing (libera ~3 h/sem). Continua sendo problema de **grade de tamanho** — ver R2/R14 |
| R24 | **"Contribuição de R$32,95/peça antes de fee e comissão"** (briefing) | ❌ **REFUTADA por fator ~3.** Cascata pedido a pedido (`pedidos_sku` × `statement_tx` × `devolucoes` × `custos_sku`): **R$10,59/peça antes de mídia e R$7,57 depois** (ago 1–23); R$12,62 e R$7,61 em julho. Fator de conversão medido: GMV bruto → contribuição = **12,9%** antes de mídia, **9,2%** depois | 27/08/26 | **Todo cálculo de "vale +R$X mil/mês" nos 8 relatórios precisa ser dividido por três.** Usar 12,9% como fator padrão de GMV→contribuição |
| R25 | **"A live própria é o canal mais rentável"** | ❌ **REFUTADA.** Contribuição/peça líquida por canal — jul: **vídeo de afiliada R$21,19 > loja própria R$15,65 > live de afiliada R$4,58**; ago: R$13,65 > R$12,66 > R$7,19. Live de afiliada acumula comissão **e** a maior devolução (15,3%) — e é o canal que virou 66% do mix | 27/08/26 | Reativar **vídeo de afiliada** é alavanca de margem, não só de mix. Migrar peça de live de afiliada p/ vídeo vale +R$6,46/peça |
| R26 | **"A amostra virou spray e deve ser congelada"** (RaioX Amostras + Plano 7-15-30 ação 4) | ❌ **REFUTADA — é a melhor porta de entrada medida.** Quem entrou **após amostra**: mediana de GMV vitalício **R$719** (vs R$152 sem amostra), **39%** ainda vendendo em ago (vs 12%), **44%** ativos ≥3 meses (vs 8%). `tacianecreator` (nº2 de ago, R$722k acumulados), `numarchi` e `ba.nasc_` entraram por amostra. ⚠️ Ressalvas: viés de seleção + base incompleta (172 de 1.045) → **direcional, não conclusivo**. O RaioX ainda se contradiz: ROI 45d de jul = 0,3× convive com "taciane, 2 amostras, R$123.630" no mesmo arquivo | 27/08/26 | **Mirar, não congelar.** Trocar a régua de seleção + aceite de 3 conteúdos/14d + cobrança D7 + lista negra D14. Ver R8 (atribuição sem data-limite) |
| R27 | **"R$16 mil/dia = 268 creators ativos"** (Plano 7-15-30) | ✅ **conta aritmética correta** · ❌ **conclusão REFUTADA.** R$1.789 é a **média**; a mediana é R$199 (R20). Recrutar os +117 que o plano pede entrega **R$9.778/dia** (pela mediana) ou **R$11.601/dia** (pela média sem top 5) — não R$16.000. Para chegar de fato a 16 mil/dia pela mediana seriam **+1.056 creators** | 27/08/26 | **A meta é inalcançável por recrutamento.** O caminho é o topo da distribuição: resgatar baleia adormecida + blindar baleia ativa. Libera ~4 h/sem de recrutamento em volume |
| R28 | **"Pedidos atribuídos ao GMV Max incluem orgânico e afiliada"** | ✅ **CONFIRMADA — fator 1,40×.** Ago/26: ads reivindicam 54,6% do GMV oficial e afiliadas 85,4% → **soma 139,9%**; em pedidos 137,4%. Sobreposição **mínima de 39,9 p.p.** Jun chegou a 158,9% (58,9 p.p.). 🔒 Por SKU/pedido não é mensurável: `ads_campanha` não traz `order_id` | 27/08/26 | **Nunca somar ads + afiliada.** Placar sempre em `gmv_oficial_resumo`. Estende R9 e R19 |
| R29 | **"`affiliate_perf` é fonte confiável de GMV por creator"** | ❌ **REFUTADA — BUG ABERTO.** A tabela carrega **R$504.022 de GMV duplicado**: `tacianecreator` e `tacianemoraisofc` são a mesma pessoa e têm **127 linhas idênticas ao centavo** entre 10/mai e 06/ago (troca de @ gravada nos dois handles). Jun inflado em R$250.956 · jul em R$152.543. `HANDLE_ALIASES` (agente_rhode/etl_v2.py) cobre `TACIANECREATOR→TACIANETORRESS` mas **não** `TACIANEMORAISOFC`. Também: `mirellaadriane.r` do RaioX é `psi.mirellarodrigues` na API | 27/08/26 | **Fix de raiz:** incluir `TACIANEMORAISOFC` no alias map + detector automático de linhas idênticas entre handles no ETL. Série corrigida (dedup): mar 742.628 · abr 981.789 · mai 500.456 · jun 548.100 · jul 478.086 · ago 329.243 |
| R30 | **"3 gigantes adormecidos valiam R$340 mil/mês"** (RaioX Afiliados, ação nº1) | ✅ **CONFIRMADA e subestimada.** Na API (dedup): natmarquesvi pico R$188.461 · psi.mirellarodrigues R$157.953 · maiconeandreia R$88.391 = **R$434.804** de pico somado. Hoje somam **R$2.672/mês**. Correção de fato do relatório: **amandadjehdian estreou em JULHO com R$105.357**, não "do zero em agosto" | 27/08/26 | Continua sendo a **alavanca nº1** por retorno/hora de equipe: 2 de 3 voltando a 40% do próprio pico = +R$14.957/mês de contribuição a 3 h/sem |
| R31 | **"FastMoss serve para comparação relativa de live"** (régua #4 do Plano 7-15-30) | ❌ **REFUTADA — não serve nem para relativo.** Subconta **15% das sessões** (39 lives em 28d vs **46 válidas em 25d**) e, pior, **troca o denominador**: o "0,50 peças/1k espectador" bate com peças/1k **impressões** (0,63), não com views — o real é **7,26 peças/1k views**, fator **14,5×**. ROAS "3,74" vs conta real **7,70** (+106%) | 27/08/26 | Cai o "0,50 peças/1k", o "Gaven vende 5,6× mais" e a meta de "0,80 peças/1k". Orçamento e metas de live **só** por `ads_custo_resumo` e pelo export do Seller Center |
| R32 | **"GMV/hora de R$1.919 se mantém quando as horas sobem"** (premissa central do plano de live) | ⏳ **NÃO MENSURÁVEL — fora do suporte dos dados.** Sem controle não há saturação intradiária (horas acumuladas: t = +0,27; views/hora: r = −0,015); com controle, t = −1,47, n.s. **Mas nenhum dia da série passa de 6h de live.** Alerta que apareceu: views/hora cai **R$88/dia** ao longo de ago (t = −3,55) — o alcance está drenando, a conversão compensa | 27/08/26 | Não extrapolar para 8–12 h/dia. **Rodar 4 dias-teste a 8h** antes de assumir o patamar. Concentração de risco: ago tem **53,6% do GMV em 2 creators** |
| R33 | **"A amostra reembolsável é um canal de seeding em operação"** | ❌ **REFUTADA — o programa não opera.** Varredura completa do carimbo `system_refund_sample_buy_now_refund_later`: **1 evento em toda a base** (2.683 reembolsos jul-ago via API; 8.090 no Supabase mar-ago). Agosto = 1 peça, julho = 0. No mesmo agosto o seeding grátis entregou **62 peças**. Não é canal — é um acidente isolado | 01/09/26 | Decidir em setembro: meta de volume ou desligar. Relatório em `relatorios/2026-08/Relatorio Amostras Reembolsaveis Agosto 2026_2026-09-01` |
| R34 | **"A amostra reembolsável custa mais que a grátis (a Rhode devolve o dinheiro E perde a peça)"** | ❌ **REFUTADA — é mais barata.** Custo real **medido ao centavo**: R$ 55,69/peça (CPV R$ 49,00 + R$ 6,69 de settlement que não volta: fee não devolvido R$ 5,69 + frete R$ 1,00). A grátis custa **R$ 65,00** na premissa do seeding (R$ 40 peça + R$ 25 frete). O ganho é o **frete**: no fluxo de pedido a plataforma bancou R$ 7,60 e a Rhode absorveu R$ 1,00 | 01/09/26 | ⚠️ Comparação é **medido × premissa** — a premissa de R$ 25 de frete do seeding nunca foi medida. Medir uma vez fecha os dois relatórios |
| R35 | **"O ROI de 15,9x da amostra reembolsável prova que o mecanismo funciona"** | ❌ **REFUTADA — é a armadilha da R8 de novo.** A atribuição soma toda venda da creator após a compra (R$ 4.042 até 31/08) numa creator que **já vendia**. Na leitura incremental (mesma lente `affiliate_perf`, normalizada por dia): **R$ 383,90/dia antes** × **R$ 106,37/dia depois** = **−72,3%**. A creator vinha de R$ 32,4 mil/mês em jan e fechou ago em R$ 2,6 mil | 01/09/26 | Todo ROI de amostra (grátis ou reembolsável) passa a exigir a leitura incremental antes×depois ao lado da atribuição. n=1 não conclui sobre o mecanismo — conclui que **este caso não jogou a favor** |

---

## ⏳ Em aberto

| # | Premissa | Status | O que falta |
|---|---|---|---|
| A1 | **"Mais criativo derruba o CAC do card"** (vídeo → GMV-Max → CAC → pedidos) | **Aposta declarada.** A favor: starvation real — só **27 de 3.375** criativos entregam. Mas a queda de CAC (R$14,60→~R$11) **nunca foi medida** | Teste controlado: subir volume de seed e medir CAC do card antes/depois |
| A2 | **"O preço de etiqueta não subiu"** | Só enxergo o preço **realizado** (líquido). Catálogo tem etiqueta bem maior (REF529/552 R$142,41) com ~44% de desconto no PDV. Se a etiqueta subiu e o desconto absorveu, **não aparece** no realizado e ainda pode machucar conversão | `produtos` não guarda histórico de preço → **só o Humberto confirma** |
| A3 | **Gap da meta 10k = +12% em pedidos com 2 alavancas custo-zero** | Modelado (reativar creator 206→160 + kit 2ª peça Marmorizada+Stone 130×), não testado | Executar uma das alavancas e medir |
| A4 | **Impacto de ICMS na cascata de lucro** | Não modelado | Confirmar com o Lucas |
| A5 | **Vazamento de R$104k/mês em pagamento não completado** (Pix expira, ~59% dos cancelamentos) | Medido, **causa-raiz não investigada** | É prazo do Pix? UX do checkout? Fora do nosso controle no TikTok? |
| ~~A6~~ | ~~Quanto do GMV pago carrega comissão de afiliada?~~ | **✅ FECHADA 25/08/26 → R19** | Resolvida por `ads_campanha` × `live_sessao` × `tracker_canais` |
| A7 | **Elasticidade de preço 79,90 → 89,90** | Maior ⏳ do negócio: sobe 1 degrau e a margem/peça quase **dobra** (R$11,20 → R$19,56). 33,6% dos pedidos estão em 79,90 | Exige teste A/B controlado. Já listado como não medido na seção de teto de cupom |

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

---

## Cupom: quem banca o quê, e quanto cabe — 12/08/26

**Premissa declarada pelo dono:** *"liberar cupons da loja que se SOMEM ao que o TikTok subsidia,
pra aumentar o ticket médio."*

**Base:** `statement_tx` (72.908 linhas / 68.689 pedidos) + `pedido_pagamento` (83.367) +
`pedidos_sku`. Recorte principal jun–ago/26 (12.133 pedidos liquidados com peças casadas).

### As duas pontas, separadas

| | O que é | Quem paga | Tamanho |
|---|---|---|---|
| `seller_discount` | distância do preço "de" (159,99/179,90) até o preço praticado | **ninguém** — é contábil | R$ 1,4M = 46,9% do preço riscado |
| `platform_discount` | **cupom real do TikTok** | **TikTok** (`revenue = sub_total + platform_discount`) | 8,24% do revenue · R$ 70.075 em jun |

Cobertura do cupom TikTok por mês: mai **76,9%** · jun **85,1%** · jul **68,5%** · ago **68,9%**
(era 50% em jul/26 na leitura anterior — subiu). Instrumento próprio da loja hoje = só
**Flash Sale por creator** (Promotion API, 18 ativas, `pct_off` sobre o preço riscado).

### ❌ REFUTADA — o cupom da loja NÃO se soma ao do TikTok, ele o encolhe

O cupom do TikTok é **percentual do revenue (~9,5%), não valor fixo, e sem limiar**. Testado faixa
a faixa de R$60 a R$400+: fica em 9–10% do revenue em todas. Não existe "gaste X, ganhe Y".

Logo, `revenue` é a base — e o cupom da loja derruba a base. Cada R$ 10 de cupom próprio:

| | R$ |
|---|---:|
| custo real p/ loja (economiza 16,4% de comissão sobre o valor cortado) | **8,36** |
| subsídio TikTok perdido junto | −0,95 |
| desconto que a cliente enxerga | **9,05** |
| **eficiência** | **R$ 0,92 de custo por R$ 1,00 percebido** |

**Consolo:** canibaliza 9,5%, mas a comissão economizada compensa e sobra. Cupom próprio é
eficiente (<1:1) — só não é aditivo ao TikTok.

### ✅ CONFIRMADA — cesta maior puxa mais subsídio do TikTok, em R$

| peças | % peds | revenue méd | cupom TT méd | % c/ cupom |
|---|---:|---:|---:|---:|
| 1 | 91,5% | 87,32 | 6,72 | 76,1% |
| 2 | 6,8% | 158,87 | 15,74 | 90,3% |
| 3 | 1,4% | 210,67 | 27,15 | 97,4% |

+R$ 85 de revenue traz **+R$ 11,80 de subsídio TikTok junto (13,8% do incremento)**.
**A alavanca é QUANTIDADE, não corte de preço** — cortar preço reduz a base e o TikTok paga menos.

### ❌ REFUTADA — "a 2ª peça é quase toda margem porque dilui o frete"

Regressão do resíduo de fee (n=12.133): **R$ 0,98/pedido + R$ 10,59/PEÇA**. O frete grátis
**se repete por peça** — a 2ª peça dilui só R$ 0,98.

**Modelo marginal:** `margem/peça = P × (1 − 6,0% plataforma − 10,4% afiliada) − 10,59 frete − CPV`
· break-even **R$ 66,50** (CPV 45, com afiliada) · R$ 71,29 (CPV 49) · R$ 59,14 (sem afiliada).

### ⚠️ ALERTA — o preço de hoje não financia cupom nenhum

| preço vitrine | margem/pç c/ afiliada | teto de cupom | % dos pedidos |
|---|---:|---:|---:|
| 69,90 | **2,84** | 3,40 | 11,8% |
| 79,90 | 11,20 | 13,40 | **33,6%** |
| 89,90 | 19,56 | 23,40 | 17,3% |
| 99,90 | 27,92 | 33,40 | 18,1% |

**14,8% dos pedidos saem abaixo do break-even quando têm afiliada.** Numa corrida de vídeos
(100% afiliada, comissão sempre), o degrau R$ 69,90 trabalha de graça.

A R$ 79,90 o teto é R$ 13,40 — e gastar o teto é chegar no break-even. **Um "2ª peça R$10 off"
em cima de 79,90 deixa a 2ª peça a R$ 2,84 de margem.** Cupom de leve-2 só é financiável com
vitrine em **89,90+**.

**Veredito:** ❌ "cupons se somam ao TikTok" · ✅ "cesta maior puxa mais subsídio" ·
❌ "2ª peça dilui frete" · ⏳ elasticidade de 79,90 → 89,90 não medida (exige teste A/B).

### ❌ REFUTADA (2ª vez, agora com teste controlado) — "combar dilui o frete" · 12/08/26

**Premissa do dono:** *"combando eu reduzo minha taxa de frete, dilui."*

**Teste 1 — regressão múltipla** (n=12.102): resíduo = −0,80/pedido + 1,58/peça + 12,45% do
revenue (R²=0,35; termo fixo negativo = colinearidade). O resíduo é **proporcional ao
revenue (~13%)**, não custo fixo de pacote.

**Teste 2 — controlado por preço** (o decisivo): mesmo preço/peça, 1 peça vs 2 peças:

| preço/pç | margem/pç c/ 1 peça | margem/pç c/ 2 peças | ganho |
|---:|---:|---:|---:|
| 79,90 | 14,94 (n=4.144) | 14,75 (n=235) | **−0,19** |
| 89,90 | 22,31 (n=2.056) | 23,22 (n=23) | +0,91 |
| 99,90 | 27,15 (n=2.132) | 28,33 (n=62) | +1,18 |

Se o frete fosse por pacote, o resíduo/peça cairia ~50% de 1→2. Cai de 11,58 para 10,97.
**No settlement, combar não dilui praticamente nada.**

### ✅ CONFIRMADA — mas o instinto comercial está certo: dilui o VÍDEO

O custo fixo do canal vídeo não é frete, é **a peça de seeding (R$45) + a atenção da
creator**. Um vídeo que vende o combo gera **R$ 165,13** de revenue contra R$ 85,49 do
avulso (**+93%**). A peça seedada se paga em **1,7 pedidos combo** contra 2,8 avulsos.
Num canal cujo gargalo é **oferta de vídeo**, é aí que o combo paga.

### ✅ CONFIRMADA — combar é estritamente melhor que descer preço

| | cliente paga | por peça | margem do pedido |
|---|---:|---:|---:|
| Hero a 69,90 | 63,26 | 63,26 | **2,84** |
| **Combo 516+588, cupom R$15** | 149,44 | **74,72** | **26,85** |

**Mesmo apelo de vitrine, 9,5× a margem.** E descer preço encolhe a base sobre a qual o
TikTok paga: cada R$1 cortado leva R$0,095 de subsídio junto. O combo faz o oposto —
puxa **+R$ 7,57** de subsídio TikTok por pedido.

**Veredito:** ❌ diluição de frete (2ª refutação, agora controlada) · ✅ diluição do custo
por vídeo · ✅ combo domina corte de preço. Ver `docs/MECANICA_CORRIDA_CUPOM.md` §7.

---

### ✅ CONFIRMADA — o diagnóstico do raio-x de afiliados está certo · 25/08/26

**Premissa do raio-x:** *"o programa não perdeu creators — os grandes pararam de produzir;
resgatar é mais barato que recrutar."*

Confirmada pelo próprio dado: os top-20 de março/abril **continuam cadastrados e vendendo
residual** em agosto (18 a 20 deles). `natmarquesvi` foi de R$150.244 (abr) para R$1.881 (ago),
`mirellaadriane.r` de R$128.168 para R$255, `maiconeandreia` de R$61.506 para R$292 — queda de
>98% sem saída do programa. E `amandadjehdian` provou o inverso no mesmo mês: R$82.350 do zero
em 23 dias com live de queima.

Convertido em dinheiro (margem 14,0% do GMV a R$79,90 com afiliada), resgatar 2 de 3 a 60% do
pico vale **+R$28 mil/mês de contribuição** — a maior alavanca do plano de agosto, e a de menor
custo (três telefonemas). **A prioridade nº1 do raio-x está certa e foi mantida sem alteração.**

**Veredito:** ✅ diagnóstico confirmado · ✅ prioridade nº1 mantida · ❌ as réguas financeiras do
plano v1 (ver R16–R18). Plano completo em
`relatorios/2026-08/Relatorio Plano de Acao TikTok 7-15-30_2026-08-25.xlsx`.

---

### ✅ FECHADA — A6: onde colocar a verba de mídia recomposta · 25/08/26

**Pergunta:** quanto do GMV pago carrega comissão de afiliada? (decidia se recompor a verba
valia +R$2,1k ou +R$20k/mês)

**A pergunta estava mal formulada.** Não existe partição limpa: a atribuição de GMV Max e a de
afiliada **se sobrepõem no mesmo pedido**. Em jun/26 os ads reivindicam 61,3% dos pedidos da loja
enquanto apenas 38,9% das peças não têm afiliada — logo, no piso, **15,6% a 36,4% dos pedidos
pagos carregam comissão** (jun 36,4% · jul 17,3% · ago 15,6%).

**Mas a pergunta útil tem resposta limpa.** Composição da receita paga (8 meses, `ads_campanha`
com as campanhas LIVE resolvidas por `live_sessao.origem`):

| tipo | verba | ROAS | CPO | margem − CPO | receita paga |
|---|---:|---:|---:|---:|---:|
| Card / vitrine | **71,0%** | 7,00 | R$ 12,62 | **+R$ 8,85** | 61,7% |
| Live da sala Rhode | 26,2% | **10,73** | **R$ 7,42** | **+R$ 14,05** | 34,9% |
| Live de creator nomeada | 2,8% | 7,01 | R$ 11,45 | +R$ 0,88 | 2,4% |

**A verba está 71% no canal que rende menos.** Recompor os R$22k cortados rende **+R$15,4k/mês**
no card e **+R$41,7k/mês** na live da sala Rhode (+R$14,5k se ela carregar comissão) — nos dois
casos, longe do "empate" que eu tinha estimado.

**Validação forte do modelo de margem:** aplicando a calculadora ao CPO medido do card em jun
(R$14,39) sai **R$7,08/pedido de contribuição pós-mídia** — exatamente o número que R3 mediu de
forma independente em jul/26 ("loja própria R$7,08, a pior"). O modelo do plano está calibrado.

**Ressalvas honestas:** (a) sem sinal de saturação no card (correlação gasto×ROAS = **+0,552**,
n=8), mas correlação positiva aqui é **confundida** — gastaram mais quando a demanda estava
melhor; não é prova de headroom; (b) há **declínio secular** de eficiência independente do gasto
(card 7,62→6,06 · live da sala 11,88→9,24 em 8 meses); (c) `live_sessao.origem='propria'`
significa *sala da Rhode*, **não** *sem comissão* — R9 diz que live própria rodada via programa
de afiliado é creditada como afiliada.

**Veredito:** ✅ A6 fechada · ❌ minha estimativa de +R$2,1k (R18) refutada · ✅ modelo de margem
validado contra R3 · ⏳ saturação do card continua não testada de forma causal.

---

### ⏳ EM ABERTO + ✅ CONFIRMADA — fechamento de agosto/26: a queda continua sendo volume, mas apareceu um vazamento novo · 31/08/26

**Premissas declaradas antes de calcular:**
1. *"A queda de GMV segue sendo corte de mídia + volume, não preço"* (herdada de jul/26 — ver
   `project_queda_julho_root_cause`).
2. *"Com a mídia caindo, o ROAS cai junto"* (intuição a testar).
3. *"A live própria continua sendo o motor mais rentável"* (herdada de C5 e do relatório de julho).

**1 → ✅ CONFIRMADA.** Agosto fechou GMV oficial R$518.748,96 (−12,0% vs jul; −8,4% na régua limpa
[01–30], porque o dia 31 foi coletado no próprio dia). Peças caíram −9,9% (6.823 → 6.150) e o
**preço médio por peça ficou praticamente parado** (R$81,55 → R$78,47, −3,8%). Mídia cortada pelo
terceiro mês seguido: R$64.061,74 (jun) → R$45.651,75 (jul) → **R$36.997,35** (ago). É volume, não preço.

**2 → ❌ REFUTADA.** O ROAS **subiu** enquanto a verba caía: 7,45x → **8,10x**, com CPA de R$12,32
para R$10,88. Corte de topo de funil não degradou a eficiência do que ficou no ar — o que reforça
que há demanda não comprada, não campanha saturada.

**3 → ❌ REFUTADA (mudança de estado).** A live própria **empatou em agosto**: lucro **−R$71,09**
(−R$0,03/peça) contra R$10.146,89 em julho e R$7.896,39 em junho. Causa aritmética, não de execução:
o **teto de mídia por peça** caiu de R$7,57 para **R$4,43** enquanto a mídia real subiu para
R$6,38/peça — 144% do teto. O teto caiu porque o preço por peça na live foi de R$76,95 → R$73,12 **e**
a taxa efetiva subiu, com CPV parado em R$44,93. O ROAS da live (9,75x, acima de julho) **não denuncia
nada disso** — confirma de novo que a régua da live é teto de mídia por peça, não ROAS.

**⏳ ACHADO NOVO EM ABERTO — a taxa efetiva do TikTok virou o maior vazamento do trimestre.**
19,64% (jun) → 25,33% (jul) → **26,09%** (ago), medida sempre da mesma forma
(`1 − settle_liq/pago_liq` de `statement_tx_resumo` do próprio mês). Só a subida ago-vs-jul custou
**R$3.667,46 de lucro em agosto**; contra junho o buraco é muito maior. **Não sabemos qual componente
do fee subiu** — a decomposição (comissão 6% + frete 6% + R$4/item + afiliada + GMV Max) ainda não foi
rodada sobre agosto. Isso é maior do que qualquer alavanca de mix discutida no mês e está ganhando
sozinho, sem decisão de ninguém.

**Efeito no P&L:** lucro de contribuição R$43.571,41 (jul) → **R$26.791,11** (ago); contribuição por
peça R$6,39 → **R$4,36**; ROI real (lucro ÷ mídia total) 0,95x → **0,72x**.

**Seeding — premissa declarada:** *"o gargalo do seeding é curadoria/conversão de creator"*.
**❌ REFUTADA.** O gargalo é **operacional**: entraram 442 pedidos de amostra (+166,3% vs jul) e só
**62 peças saíram** (14,0%); **289 venceram sem envio** (OVERDUE_CANCELLED). A conversão de quem
recebeu ficou estável (28,2% vs 29,4%) — ou seja, a curadoria não piorou, a porta é que não abriu.
ROI do seeding 0,59x → **1,38x**, mas **0,87x sem a maior creator** (@ba.nasc_ = 47,8% do GMV
atribuído) e mediana de GMV por creator ativada = **R$0,00**.

**Veredito:** ✅ queda = volume/mídia (confirmada pelo 3º mês) · ❌ "menos mídia = menos ROAS"
refutada · ❌ live própria como motor rentável **caiu neste mês** · ❌ gargalo do seeding não é
curadoria, é despacho · ⏳ **composição da alta da taxa efetiva: não testada — próxima investigação
prioritária**.

Relatórios: `relatorios/2026-08/Relatorio Fechamento Agosto 2026_2026-08-31.xlsx` ·
`Relatorio Margem por SKU e Live Agosto_2026-08-31.xlsx` ·
`Relatorio Seeding Agosto 2026_2026-08-31.xlsx` (cada um com `.md` gêmeo).

---

### ✅ FECHADO — ⏳ da taxa efetiva: é decisão de mídia, não mudança de preço do TikTok · 01/09/26

**Pergunta aberta em 31/08:** qual componente do fee fez a taxa efetiva subir de 19,64% (jun) para 26,09% (ago)?

**Decomposição do fee** (`statement_tx`, pedidos LIMPOS sem devolução, % sobre **revenue** — a base do fee):

| componente | jun afil | jul afil | ago afil | jun vend | jul vend | ago vend |
|---|---:|---:|---:|---:|---:|---:|
| comissão de plataforma | 6,00% | 6,00% | 6,00% | 6,00% | 6,00% | 6,00% |
| comissão de afiliada | 6,55% | 8,09% | 8,01% | — | — | — |
| frete | 1,20% | 1,06% | 0,91% | 1,34% | 1,15% | 1,17% |
| **resíduo** (frete 6% + R$4/item + GMV Max VL) | **11,05%** | **12,37%** | **14,96%** | **10,10%** | **15,13%** | **15,57%** |

A plataforma está **travada em 6,00%** nos dois lados nos três meses; a comissão de afiliada subiu jun→jul e parou.
**O que cresce é o resíduo.**

**O detector bimodal fecha a causa.** O resíduo por pedido é claramente bimodal: um modo baixo (~10–12% do
revenue) e um modo alto (~23–26%). A diferença entre os modos é o **GMV Max Vendas Líquidas cobrado dentro
do fee** (confirma [[reference_gmvmax_vl_dentro_do_fee]]). A fatia de pedidos no modo alto:

- jun/26: **9,1%** (606 de 6.657 pedidos limpos) · resíduo médio 22,63%
- jul/26: **18,1%** (992 de 5.488) · resíduo médio 24,85%
- ago/26: **22,7%** (932 de 4.103) · resíduo médio 25,95%

**Veredito:** ✅ causa identificada. A taxa efetiva **não** subiu porque o TikTok mudou preço — subiu porque a
operação passou a comprar mais mídia no modelo que cobra por dentro do settlement. **É uma decisão de mídia
disfarçada de taxa**, e ela não aparece na conta de ads. O modo baixo também subiu (9,55% → 12,27%), consistente
com R$4/item + frete 6% pesando mais sobre um preço por peça menor.

⚠️ **Correção de régua vs. o relatório de 31/08:** aquele relatório aplicou a taxa de `statement_tx_resumo`
(base `customer_payment`, 26,09%) sobre o GMV oficial. As duas coisas têm denominadores diferentes. A régua
correta é o **settlement medido por pedido**. Com ela, agosto fecha em **R$ 35.030 de contribuição após mídia**
(R$ 5,59/peça) contra os R$ 26.791 publicados ontem. Direção idêntica, magnitude corrigida.

---

### ❌ REFUTADAS + ⚠️ — as três perguntas de canal de agosto/26 · 01/09/26

**Premissa 1:** *"o ticket de R$ 99,90 travou o volume"*. **❌ REFUTADA.** R$ 99,90 moveu 250 peças em agosto
(4,0% do volume) — patamar estável: 328 (jun) · 324 (jul) · 250 (ago). O teste decisivo é o vídeo de afiliada,
único canal onde esse preço pesa: lá a fatia de peças ≥ R$ 90 **caiu** de 70,8% (jul) para 42,1% (ago) — ou seja,
**baixaram o preço** — e o volume caiu 23,9% assim mesmo. Se preço fosse a restrição, volume teria subido.
O gargalo é **alcance por conteúdo**: vídeos novos subiram 14,4% (2.239→2.562) e as impressões caíram
(3,62 M → 3,49 M); cada vídeo entrega 1.363 impressões contra 2.168 em junho (−37%).

**Premissa 2:** *"a base de afiliada continua concentrada em uma pessoa"*. **⚠️ SIM na dependência, NÃO na pessoa.**
Top-1 47,8% (jun) → 34,1% (jul) → 28,7% (ago); HHI 2.517 → 1.479. Mas **2 creators = 50% do GMV nos três meses**
(em agosto somam 51,7%). A dependência foi **transferida** de @tacianetorress (R$190.170 jun → R$64.772 ago) para
@amandadjehdian (R$80.840), não diluída. E veio pelo lado ruim: a cauda fora do top-2 encolheu de R$158.325 para
R$136.192 e a base ativa de 198 para 156 creators. **A cabeça caiu mais rápido que a cauda — é encolhimento, não
diversificação.** (Ranking exige colapsar TACIANEMORAISOFC e MIRELLAADRIANE.R, que o `etl_v2` ainda não cobre — R29.)

**Premissa 3:** *"o mix vídeo × live andou pro lado que a gente queria (vídeo)"*. **❌ REFUTADA, 3º mês seguido.**
Razão vídeo/live em peças na afiliada: 1,34 (jun) → 0,55 (jul) → 0,49 (ago). E o preço da migração é medível —
contribuição por peça em agosto: **vídeo de afiliada R$ 12,43 · live de afiliada R$ 5,26** (2,4x), com devolução
**6,4% vs 12,4%**. Cada peça que saiu do vídeo e entrou na live de afiliada custou ~R$ 7,17 de contribuição.

**Contribuição por peça por canal (ago/26, antes de mídia):** vídeo loja R$ 27,29 · card de produto R$ 26,19 ·
vídeo afiliada R$ 12,43 · card/vitrine afiliada R$ 12,06 · live loja R$ 10,22 · **live afiliada R$ 5,26**.

**⚠️ GOTCHA de canal:** a **vitrine (`shop_tab`) NÃO é aditiva** — é uma superfície que atravessa os outros canais.
Os 6 canais de atribuição somam exatamente o total; a vitrine (R$ 100.533 bruto em agosto) é leitura cruzada.
Somar dá dupla contagem.

**GMV Max:** ✅ **o refresh de criativo de 11/08 funcionou** — CPA das campanhas de produto R$ 14,39 (jun) →
R$ 17,15 (jul) → R$ 16,01 (ago 01–11) → **R$ 14,43** (ago 12–31), ROAS 6,07x → 6,74x. Ressalva: a verba diária caiu
de R$ 781 para R$ 519/dia no mesmo movimento, então parte do ganho é leilão, não criativo — o teste limpo é subir a
verba mantendo o criativo. ⚠️ E o ROAS esconde o essencial: **nenhuma campanha Tradicional pagou a própria mídia**
(ROI = contribuição ÷ custo, no teto de 100% de incrementalidade: LIVE-TESTE 0,74x · Product GMV Max 0,81x ·
LIVE AMANDA 0,62x · MARMORIZADA 0,49x · BAGGY 0,38x). ROI < 1 no teto é conclusivo.

**CAC:** ⚠️ **por SKU segue sem dado e é estrutural** (a API do GMV Max não separa cliente novo por campanha).
O **blended** saiu depois de reprocessar a tabela `cliente` (o 503 na fatia de março era transitório; passou no retry):

| | jun/26 | jul/26 | ago/26 |
|---|---:|---:|---:|
| clientes novos | 5.259 | 4.336 | 3.685 |
| CAC (mídia total) | R$ 12,18 | R$ 10,53 | **R$ 10,42** |
| CAC (só Tradicional) | R$ 10,37 | R$ 6,82 | R$ 6,50 |
| contribuição gerada pelo cliente | R$ 21,35 | R$ 15,75 | **R$ 12,15** |
| **payback** | **1,75x** | **1,50x** | **1,17x** |

**O CAC caiu e a situação piorou.** Ele caiu porque cortaram verba; a contribuição por cliente novo caiu mais
rápido. O payback foi de 1,75x para 1,17x em dois meses — agosto está a um passo de o cliente novo não pagar a
própria aquisição. Censuras declaradas: a janela começa em 2026-01-01 (quem comprou pela primeira vez em 2025
aparece como novo → CAC real um pouco MAIOR) e a % de recompra de agosto é censurada por tempo.

Relatório: `relatorios/2026-08/Relatorio Fechamento Agosto por Canal_2026-09-01.xlsx` (+ `.md`).

---

## P13 · "O TikTok me subsidia 10% off, por isso a peça sai a R$ 71" ✅ CONFIRMADA (com correção de nível)

**Premissa declarada pelo dono (02/09/2026), antes de calcular:** o preço baixo por peça na live
não é desconto da Rhode — é `platform_discount`, subsídio que o TikTok banca. Logo a régua de
margem não pode ser lida sobre o preço que a cliente paga.

**Veredito: ✅ CONFIRMADA no mecanismo — ❌ desatualizada no nível.**

Medido em `statement_tx` × `pedidos_sku`, pedidos **sem devolução** e com `settlement > 0`:

| | jun/26 | jul/26 | ago/26 |
|---|---:|---:|---:|
| Preço anunciado / peça | R$ 89,60 | R$ 87,96 | R$ 86,00 |
| **Subsídio TikTok / peça** | **R$ 8,33** | R$ 5,68 | **R$ 5,98** |
| **% do que a cliente paga** | **10,2%** | 6,9% | **7,5%** |
| Cliente paga / peça | R$ 81,27 | R$ 82,28 | R$ 80,02 |
| Rhode recebe (settlement) / peça | R$ 65,83 | R$ 62,21 | R$ 59,93 |
| **Contribuição / peça** (− imposto − CPV) | **R$ 16,69** | R$ 13,30 | **R$ 11,16** |

- **O dono está certo:** o subsídio existe, é real, e em **junho foi exatamente 10,2%** — o
  número que ele carregava. Não é desconto do próprio bolso.
- **Mas caiu:** 10,2% → 6,9% → 7,5%. São **R$ 2,35 a menos por peça**, ≈ **R$ 10 mil/mês** que a
  plataforma parou de bancar, sem que ninguém tenha decidido isso.
- **Contribuição por peça caiu 33% em dois meses** (16,69 → 11,16) com a operação igual.
- Consistente com [[reference_cofinanciamento_e_cpv_real]] (11/08): lá o co-financiamento foi
  medido como **~3–4% do `gross_sales`**; aqui como **7,5% do que a cliente paga**. É a mesma
  grandeza em bases diferentes — `gross_sales` é preço de catálogo (ficção, R$ 189).
  **Não são leituras conflitantes.**

**Consequências:**

1. **A régua de preço é o anunciado, não o pago.** Break-even = **R$ 78,65 anunciado**
   (`(CPV 44,93 + mídia 6,38) ÷ 0,70`). Virou a régua "R$ 79" do `BANCO_ROTEIROS_LIVE.md`.
2. **Corrigi minha própria conta no meio do trabalho:** eu havia fixado break-even em R$ 76 sobre
   o preço *pago*, aplicando taxa efetiva sem considerar que o settlement já embute o subsídio.
   Base errada. O número certo é R$ 78,65 sobre o **anunciado**.
3. **O co-financiamento é gated por campanha**, não default. Recuperar os 10,2% de junho vale
   ~R$ 10k/mês — mais que qualquer ganho de pitch disponível. **É conversa com o parceiro TT,
   não com a operação.**

**⏳ Em aberto:** por que o subsídio caiu entre junho e julho. Junho tinha a campanha 6.6 ativa
(ver [[project_campanha_66_tiktok]]) — a hipótese é que o nível de junho era gated pela campanha
e não pelo relacionamento. Não testado.

---

## P14 · Tipologia de sala de live: "saldão vende muito, então ajuda" ❌ REFUTADA (02/09/2026)

**Premissa declarada antes de calcular:** salas de saldão, por moverem muito volume, contribuem
para o mês mesmo com preço menor.

**Veredito: ❌ REFUTADA.** Classificando as 58 salas de agosto pelo título e usando o preço médio
do mês (R$ 73,12) como break-even da base `live_attr` — válido porque a live própria fechou em
~zero (−R$ 71,09):

| Tipo | Salas | Peças/sala | Preço/peça | Contrib/peça | Total |
|---|---:|---:|---:|---:|---:|
| REPOSIÇÃO | 9 | 13,1 | R$ 79,97 | +R$ 4,80 | +R$ 567 |
| PROMO/CUPOM | 6 | 76,2 | R$ 76,62 | +R$ 2,45 | +R$ 1.121 |
| ROTINA | 35 | 36,6 | R$ 75,18 | +R$ 1,44 | +R$ 1.849 |
| ÚLTIMA CHANCE | 6 | 55,8 | R$ 73,23 | +R$ 0,08 | +R$ 26 |
| **SALDÃO** | **2** | **142,0** | **R$ 55,26** | **−R$ 12,52** | **−R$ 3.556** |
| TOTAL | 58 | 42,7 | R$ 73,12 | ~0 | +R$ 6 |

> **Duas salas de saldão (284 peças, 11,5% do volume) apagaram R$ 3.556 — exatamente o lucro que
> as outras 56 salas geraram (R$ 3.562).** Agosto não teve problema difuso de margem: teve duas noites.

**Achados laterais:**
- **"Promo" no título não corta preço.** Salas de promo venderam a R$ 76,62 (acima da rotina) com
  **2,1x mais peças por sala**. O rótulo puxa audiência; o cupom de valor fixo preserva a peça.
  **É o formato a escalar.**
- **Reposição é a sala mais rentável do mês e roda com 1/3 do volume da rotina.** Escassez real.
- **Saldão tem o melhor attach do mês (1,40 vs 1,19).** A mecânica de segunda peça dele funciona;
  o preço é que não. Aplicar a mecânica na rotina vale mais que rodar saldão.

**⏳ Ressalva:** as 2 salas de saldão foram "SHORTS E SAIA" (CPV R$ 35–42, não R$ 44,93) — o
prejuízo real é menor que R$ 12,52/peça. **O sinal é robusto** (negativo em qualquer CPV entre 35
e 45); o tamanho não está cravado. Falta o export por-live de agosto.

Registrado em `docs/BANCO_ROTEIROS_LIVE.md`.

---

## P15 · "A taxa do TikTok subiu de novo em agosto e comeu o lucro" ❌ REFUTADA (03/09/2026)

**Premissa declarada antes de calcular** (herdada do `Relatorio Fechamento Agosto 2026_2026-08-31`):
a taxa efetiva do TikTok subiu pelo terceiro mês seguido — 19,64% (jun) → 25,33% (jul) → 26,09%
(ago) — e essa alta de +0,76 pp custou **R$ 3.667,46** de lucro em agosto.

**Veredito: ❌ REFUTADA.** Era artefato de **mês aberto**. Aquele relatório foi gerado no dia 31/08,
com o statement de agosto ainda imaturo (4.895 pedidos). Rerodando os coletores em 03/09 (statement
com **5.253** pedidos) e medindo a taxa na base não enviesada — `1 − settlement/customer_payment`
nos pedidos **limpos** (sem devolução) que já liquidaram:

| | Junho | Julho | Agosto | Δ ago-jul |
|---|---:|---:|---:|---:|
| Taxa efetiva (pedidos limpos) | 19,04% | 24,47% | **24,59%** | **+0,12 pp** |
| Custo da variação no lucro | — | — | — | **R$ 587,69** |

A taxa ficou **parada**. O custo real da variação é R$ 587,69 — **6,2x menor** que o alarme.

**O que continua VERDADEIRO:** o degrau jun → jul (+5,43 pp) é real e já está incorporado. Não é
vazamento novo. Confirma [[project_taxa_efetiva_subindo]] no que ela afirma (o degrau existiu) e
corrige a extrapolação de que ele seguiria subindo.

**Consequência:** a investigação de decomposição do fee aberta na recomendação nº 1 do fechamento
de 31/08 **pode ser fechada** — a alavanca não vale a hora. Prioridade volta para volume.

**Régua que evita a recaída:** não medir taxa efetiva de mês corrente antes do statement maturar.
A cobertura do statement em agosto só chegou a **87,5%** dos pedidos pagos em 03/09 (jun e jul
estão em ~100%). Medir sempre em pedidos LIMPOS e projetar sobre o GMV válido — somar o realizado
subestima o mês recente.

---

## P16 · "O lucro de agosto caiu porque a operação piorou" ❌ REFUTADA · a economia unitária ficou IGUAL (03/09/2026)

**Premissa declarada antes de calcular:** a queda do lucro de julho para agosto (−R$ 13.152,22 na
régua de contribuição) reflete deterioração da economia da operação — margem, preço ou custo.

**Veredito: ❌ REFUTADA. A economia unitária empatou; caiu volume.**

Ponte do Δ do lucro, decomposição aritmética (resíduo **R$ 0,41**, não é estimativa):

| Efeito | Impacto | Leitura |
|---|---:|---|
| **Volume (GMV válido)** | **−R$ 44.407,79** | o único efeito genuinamente negativo |
| CPV (peças × custo) | +R$ 26.279,60 | espelho da queda de volume, não eficiência |
| Mídia tradicional | +R$ 5.563,25 | 3º mês de corte de verba |
| Taxa efetiva TikTok | −R$ 587,69 | neutra (ver P15) |
| **= Δ lucro** | **−R$ 13.152,22** | |

**Lucro após devolução por peça: R$ 3,43 (ago) vs R$ 3,42 (jul).** Empate técnico. Preço médio por
peça R$ 76,81 vs R$ 79,35; CPV estável em R$ 44,99. **A operação não ficou pior — ficou menor.**

**⚠️ Ressalva que impede comemorar:** dos R$ 31.255,16 que amortizaram a queda, **R$ 5.563,25 vieram
de cortar mídia** — e o corte alimenta a queda de volume do mês seguinte. É lucro comprado com
combustível do mês que vem. Terceiro mês seguido (R$ 54.545,82 → R$ 29.564,53 → R$ 24.001,28) com
**ROAS SUBINDO** (8,14x): há demanda não comprada.

**Consequência:** recuperar o volume de julho vale **+R$ 3.301,34**/mês na mesma economia unitária —
5,6x mais que zerar a alta da taxa. Volume é a alavanca; margem não é o problema.

---

## P17 · "Devolução custa o valor reembolsado" ❌ REFUTADA · custa ~1/6 disso (03/09/2026)

**Premissa declarada antes de calcular:** o custo da devolução para o lucro é o valor reembolsado
ao cliente (agosto: R$ 88.428,53).

**Veredito: ❌ REFUTADA. O custo líquido de agosto foi R$ 13.772,11 — 15,6% do reembolsado.**

A devolução custa o **settlement que deixa de vir**, menos o **CPV da peça que volta ao estoque** e
o **crédito de imposto**. Em agosto, **97,2%** das devoluções são `RETURN_AND_REFUND` (a mercadoria
retorna); só 2,8% são `REFUND` puro (dinheiro sem peça de volta).

| | Agosto | Julho | Junho |
|---|---:|---:|---:|
| Fatia do valor devolvida | 18,32% | 21,97% | 19,27% |
| Settlement que deixa de vir | R$ 70.899,33 | R$ 100.099,42 | R$ 107.703,46 |
| (+) CPV recuperado | R$ 51.354,86 | R$ 67.280,91 | R$ 68.373,16 |
| (+) Imposto creditado | R$ 5.772,36 | R$ 7.823,76 | R$ 7.894,36 |
| **= Custo líquido** | **R$ 13.772,11** | **R$ 24.994,75** | **R$ 31.435,93** |
| por peça vendida | R$ 2,21 | R$ 3,66 | R$ 3,94 |

**✅ Achado lateral que vale mais que a refutação:** a fatia devolvida **caiu de 21,97% para 18,32%**,
o que devolveu **R$ 11.222,64** de lucro em agosto. Sem essa melhora o mês teria fechado em
**R$ 10.185,63** em vez de R$ 21.408,27 — a devolução sozinha explica mais da metade do lucro do mês.
**Foi o maior ganho silencioso do trimestre e ninguém o creditou.**

**⏳ Em aberto — e é a prioridade:** *por que* a devolução caiu em agosto. Mix de tamanho? Size
Finder exposto na compra? Gradação corrigida na fábrica? Não medido. É a alavanca mais barata da
operação e a mais fácil de perder sem perceber. Ver [[project_perda_produto_modelagem]].

**Premissas do modelo (não é medição direta):** (P1) fatia devolvida = participação dos pedidos
devolvidos no valor pago da coorte com statement; (P2) peça devolvida volta vendável (97,2%);
(P3) venda estornada gera crédito de imposto. Peça que volte avariada aumenta o custo real.

**Consequência de régua:** todo relatório de lucro passa a ter **duas lentes** — contribuição
(comparável com o histórico) e **após devolução** (o que sobra). A segunda é a que responde
"quanto lucramos". Ambas são de contribuição: nenhuma desconta despesa fixa, folha ou estrutura.

---

## P18 · "O faturamento do TikTok está caindo" ✅ CONFIRMADA — mas o buraco é 100% AFILIADA, e são 4 pessoas (04/09/2026)

**Premissa declarada antes de calcular:** o faturamento vem caindo desde maio e a causa provável é
alguma combinação de preço, taxa, estoque e corte de mídia — as suspeitas que circulavam nos
fechamentos de jun/jul/ago.

**Veredito: ✅ a queda é real (−42% abr→ago) · ❌ nenhuma das quatro causas suspeitas explica.**
O buraco inteiro está no motor de **afiliadas**, e dentro dele em **4 creators**.

### 1. O tamanho (GMV produto válido, `pedidos_sku` sem cancelado)

| | jan | fev | mar | abr | mai | jun | jul | ago | set (3d) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| peças | 12.708 | 12.427 | 11.227 | 11.419 | 6.038 | 7.976 | 6.823 | 6.234 | 440 |
| GMV | 868k | 904k | 827k | 828k | 478k | 622k | 541k | 479k | 34,8k |
| R$/peça | 68,31 | 72,76 | 73,69 | 72,54 | 79,12 | 78,01 | 79,35 | 76,81 | 79,03 |

Set/26 roda a **R$ 11,6k/dia** contra R$ 15,4k/dia em agosto (**−24%**) nos 3 primeiros dias.
A queda não estabilizou.

### 2. Onde o dinheiro sumiu (canal REAL por pedido, `pedidos_sku` × `extrato_pedidos`)

| GMV | mar | abr | mai | jun | jul | ago | Δ mar→ago |
|---|---:|---:|---:|---:|---:|---:|---:|
| **vídeo afiliada** | 389.637 | 323.222 | 155.673 | 249.857 | 145.337 | **106.846** | **−282.791** |
| **live afiliada** | 229.585 | 389.035 | 191.350 | 147.932 | 201.721 | **174.732** | **−54.853** |
| loja própria | 208.041 | 116.075 | 130.703 | 224.402 | 194.326 | **197.242** | −10.799 |

> **Afiliada: 619,2k → 281,6k (−337,6k). Loja própria: praticamente parada (208k → 197k).**
> **97% da queda do negócio está no motor de afiliadas.** A loja própria — que é o que a mídia
> compra — segurou o nível mesmo com a verba caindo.

### 3. Dentro da afiliada, são 4 pessoas (GMV atribuído, deduplicado por handle)

| creator | tipo | mar | abr | mai | jun | jul | ago | dias ativos abr→ago |
|---|---|---:|---:|---:|---:|---:|---:|---|
| psi.mirellarodrigues | LIVE | 94,8k | **158,0k** | 3,2k | 0,4k | 0,7k | **0,2k** | 30 → **2** |
| natmarquesvi | LIVE | 73,4k | **188,5k** | 39,3k | 3,5k | 1,3k | **2,2k** | 30 → 12 |
| maiconeandreia | LIVE | 0 | **80,2k** | 88,4k | 0,3k | 0 | **0,3k** | 14 → **2** |
| tacianecreator | VÍDEO | 80,0k | 115,9k | 86,1k | **251,0k** | 152,5k | **77,9k** | 30 → **7** |
| *(entrou)* amandadjehdian | — | 0 | 0 | 0 | 0 | 105,4k | 97,9k | — |

- **Os 4 juntos: R$ 542,5k em abril → R$ 80,6k em agosto.** Uma a uma, em meses diferentes —
  mirella e maicone pararam em maio, natmarques em junho, taciane em agosto.
- **Concentração:** top10 = **79–81%** do GMV de afiliada em todos os meses. Creators faturando
  ≥ R$5k/mês: **22 (abr) → 10 (ago)**. É uma carteira de baleias, não uma base.
- **A reposição secou:** creators com 1ª venda no mês **302 (abr) → 131 → 114 → 90 → 71 (ago)**.
  Ativas no mês: **428 → 155**. Amanda (jul) prova que uma baleia nova cobre ~R$100k/mês —
  entrou **uma** em cinco meses.
- **Não é falta de conteúdo:** vídeos postados 2.919 (abr) → 2.152 (ago) (−26%) e creators
  postando 921 → 642 (−30%) — muito menos que os −67% de GMV. Caiu **quem vende**, não quanto se posta.

### 4. O que foi DESCARTADO (com dado, não com opinião)

- **Preço ❌** — R$ 72,54 (abr) → R$ 76,81 (ago). O preço *subiu* 6% enquanto o GMV caiu 42%.
- **Estoque/ruptura ❌** — hero REF516: **6–7 tamanhos ativos todo mês, venda em 31/31 dias,
  mínimo diário 17–45 peças**. Nenhuma assinatura de ruptura em nenhum mês, maio incluído.
- **Taxa TikTok ❌** — já refutada em P15 (parada em ~24,6%; custo real da variação R$ 587).
- **Mídia — parcial.** Verba 51,9k (abr) → 38,4k (ago) (−26%), tradicional 54,5k (jun) → 24,0k (ago)
  (−56%), **com ROI subindo (7,56 → 8,16)**. Há demanda não comprada — mas o canal que a mídia
  alimenta (loja própria) é justamente o que **não** caiu. Vale ~R$3k/mês (P16), não R$350k.

### Consequência — a alavanca mudou de lugar

O negócio é uma **carteira de 10–20 creators**, não uma operação de mídia e preço. O KPI que
governa o mês é **nº de creators faturando ≥ R$5k** (hoje 10, precisa ~22 para voltar a 830k) e,
para as de live, **dias ativos no mês**. Recuperar/repor **2 lives afiliadas diárias** vale mais
que qualquer ajuste de preço, taxa ou verba já discutido em 2026. Seeding deixa de ser custo de
relacionamento e passa a ser o **único mecanismo de reposição de receita**.

**⏳ Em aberto (o que o dado não responde):** *por que* cada uma parou — saiu para concorrente,
brigou com comissão, perdeu alcance, ou parou de fazer live. É pergunta de conversa, não de query.
São 4 telefonemas e provavelmente o item de maior valor da semana.

**Ressalvas de régua:** (1) `affiliate_perf` é GMV **atribuído** (soma > GMV oficial; serve como
índice de participação/tendência, não como nível) e tem o bug de handles duplicados
(taciane em 2 handles com valores idênticos em jun/jul) — números acima **deduplicados** pelo máximo.
(2) `extrato_pedidos` de setembro ainda não populou → o split por canal de set/26 não vale.
(3) `ads_campanha` para em 31/08 → **não há visibilidade de mídia de setembro**; rodar o coletor.

---

## P19 · "O gargalo da live está na janela de horário / na apresentadora dessa janela" ❌ REFUTADA (08/09/2026)

**Premissa declarada antes de calcular:** a queda da live está concentrada na janela 06–09 /
19:30–22, e o desempenho da apresentadora desse turno é a causa.

**Veredito: ❌ REFUTADA. O gargalo é MÍDIA, e é um número só:**
**a peça marginal custa R$ 16,09 de mídia e entrega R$ 8,21 de contribuição bruta — 1,96×.**

Dose-resposta dentro das 55 salas com mídia (ago+set), regressão de peças/h contra mídia/h:
r = **+0,556** · t = **+4,87** · inclinação **0,0621 peça/h por R$ 1/h**. A mídia **funciona** —
ela traz peça com significância. O preço é que está errado.

| Quartil de mídia/hora | mídia/h | peças/h | **contrib/hora** |
|---|---:|---:|---:|
| Q0 · sem mídia (n=17) | R$ 0 | 18,8 | **R$ 158,92** |
| Q1 · menor (n=13) | R$ 24,68 | 9,6 | **R$ 86,65** |
| Q2 (n=13) | R$ 100,73 | 16,4 | −R$ 3,08 |
| Q3 (n=13) | R$ 158,44 | 24,2 | −R$ 5,23 |
| Q4 · maior (n=16) | R$ 285,60 | 29,5 | R$ 8,11 |

**Conta marginal:** cortar R$ 1 de mídia economiza R$ 1 e sacrifica 0,0621 × R$ 8,21 = R$ 0,51 →
**sobra R$ 0,49 líquidos por R$ 1 cortado.** Cortar 50% da mídia de setembro (R$ 1.375) devolve
**+R$ 674** — mais que os R$ 535 que o mês inteiro produziu. Em agosto o mesmo corte valeria +R$ 4.062.

**Viés joga A FAVOR:** o GMV Max realoca verba para salas que já convertem, o que infla a
eficiência aparente. O custo real da peça marginal é **≥ R$ 16,09**, nunca menor.

### O que a janela realmente diz (e por que não é a apresentadora)

| Janela | mês | salas | h/sala | peças/h | **contrib/h** |
|---|---|---:|---:|---:|---:|
| NOITE 19:30–22 | ago | 7 | 2,12 | 26,1 | **R$ 80,27** ← melhor slot da loja |
| FORA (11h etc.) | ago | 51 | 1,82 | 24,0 | R$ 37,76 |
| **MANHÃ 06–09** | set | 6 | **2,82** | **6,4** | **R$ 10,03** |
| NOITE 19:30–22 | set | 2 | 2,37 | 9,1 | −R$ 5,62 |
| FORA | set | 6 | 2,52 | 14,4 | R$ 25,97 |

- **A janela da noite foi o MELHOR slot medido da operação** (ago). Ela não é o problema.
- A janela 06–09 **não existia em agosto** — é nova em setembro e consome **46% das horas do mês**.
- **O teste da R21 se inverte aqui:** a manhã tem as lives MAIS LONGAS (2,82 h/sala) e a MENOR
  produção (6,4 pç/h). Controlar por duração **reforça** o achado — o slot é ruim de verdade.
- **A queda de setembro é do mês inteiro:** o horário das 11h também caiu (R$ 37,76 → R$ 25,97/h).

🔒 **Continua não mensurável quem apresentou** (confirma R21). A janela é proxy, não identidade.
Ação de destravamento: 1 campo "apresentadora" no controle da operação.

---

## P20 · "Setembro está pior que agosto" ✅ CONFIRMADA — mas por VOLUME, não por margem (08/09/2026)

**Veredito: ✅ CONFIRMADA.** Contribuição por hora de live: **R$ 78,67 (jul) → R$ 43,64 (ago) →
R$ 14,56 (set) = −81% em dois meses.**

Ponte aritmética (resíduo **R$ 0,00**, não é estimativa):

| Transição | Δ contrib/hora | efeito VOLUME | efeito MARGEM |
|---|---:|---:|---:|
| julho → agosto | −R$ 35,03 | +R$ 23,21 | **−R$ 58,25** |
| agosto → setembro | −R$ 29,08 | **−R$ 25,60** | −R$ 3,48 |

**São dois problemas diferentes.** Agosto foi PREÇO (R$ 77,00 → R$ 73,40/peça, com volume
subindo). Setembro é VOLUME (peças/hora 24,29 → 10,04, −59%), com o preço até se recuperando
(R$ 75,04). Tratar os dois com a mesma alavanca — mais mídia — produziu o resultado atual.

**O ROAS subiu nos três meses (9,02 → 9,90 → 10,46) enquanto a contribuição caiu 81%.**
Prova direta de que ROAS não é a régua desta operação. Ver [[reference_regua_midia_contribuicao]].

**⚠️ Faixa de setembro — única incerteza material:** só 213 pedidos de setembro liquidaram (~3%
do mês) e a taxa parcial veio em 76,18% vs 72,39% de agosto. Testei se a amostra precoce prevê o
fechamento: julho **+1,9 p.p. acima**, agosto **4,3 p.p. abaixo** — **não prevê**. O relatório roda
na régua de agosto (conservadora). Na régua parcial de setembro, a contribuição/hora seria
R$ 43,14 em vez de R$ 14,56. **O que não muda em nenhum cenário: peças/hora caíram 59% — é contagem.**

### Ajustes em premissas anteriores

- **R22 ("live sempre ≥ 2 h") ⏳ AJUSTADA.** Ela mediu GMV/hora. Em CONTRIBUIÇÃO/hora o ótimo é
  **1–3 h**: 1–2 h rende R$ 70,90/h · 2–3 h R$ 52,88/h · 3 h+ **−R$ 16,15/h** (R$ 47,09 sem saldão),
  porque acima de 3 h o preço por peça cede de R$ 77,06 para R$ 75,55. Volume continua subindo,
  margem não. Não é refutação — é troca de métrica.
- **P14 (saldão) ❌ REFUTADA de novo.** 2 salas em ago+set: **−R$ 2.571**, 27% de tudo que as
  salas positivas construíram. Preço R$ 55,24 contra CPV R$ 44,99.
- **`live_sessao` subnotifica ⏳ REVISAR.** Medido agora, a atribuição por sala cobre **97,1% (jul),
  98,9% (ago) e 99,9% (set)** do headline de `ads_campanha`. Nesta janela dá para fazer P&L por live.

Relatório: `relatorios/2026-09/Relatorio Geral de Live Agosto e Setembro_2026-09-08.{md,xlsx}`

---

## P21 · Promoção relâmpago na live de 04/09 — "o impulso paga o desconto" ✅ CONFIRMADA (08/09/2026)

> ⚠️ **Esta premissa foi registrada ERRADA na primeira versão (08/09) e corrigida no mesmo dia.**
> Eu tratei o cupom de 10% da plataforma como se saísse do bolso da loja e conclui que a rajada
> destruía contribuição. **O dono corrigiu: quem subsidia o cupom é o TikTok.** Ele estava certo —
> e eu já tinha provado isso numa análise anterior sem aplicar aqui. Ver "a régua" abaixo.

**Premissa declarada antes de calcular:** a rajada de preço no hero durante a live das 11:00
impulsionou volume o bastante para pagar o desconto.

**Veredito: ✅ CONFIRMADA, com folga de 2,1×.**

**Desenho:** a própria live como controle — rajada × resto da mesma sessão (mesma audiência, mesmo
dia, mesma apresentadora). Universo: peça **paga, não cancelada e não devolvida** (dado de 08/09).

| segmento | min | peças | **peças/hora** | cliente pagou | **loja faturou** | contrib/peça | contrib/hora |
|---|---:|---:|---:|---:|---:|---:|---:|
| **RAJADAS** (3 blocos) | 35 | 57 | **97,7** | 62,88 | **69,89** | 3,68 | **359,70** |
| resto da live | 151 | 34 | 13,5 | 74,57 | 82,01 | 12,71 | 171,76 |

**Lift 7,23× · necessário 3,45× · folga 2,10×.** Contribuição/hora +109% na rajada.
Live fechou em **R$ 350,56** depois da mídia; sem as rajadas teria feito R$ 240,92 →
**as rajadas valeram +R$ 109,63**.

### ✅ A RÉGUA CERTA: a base é o REVENUE, não o que o cliente paga

`revenue = preço pago + platform_discount` em **2.130 de 2.143** pedidos liquidados de agosto
(99,4%), ao centavo. **A loja fatura +10,2% acima do que o cliente paga — o cupom é subsídio do
TikTok.** Isso já estava provado na P12 (mega live da Amanda, 10/08) e em
`reference_extrato_inelegivel_cancelado`; eu simplesmente não apliquei.

| | lista (loja fatura) | (−) cupom TT | = cliente paga | contrib/peça |
|---|---:|---:|---:|---:|
| base da live | 78,90 | −7,89 | 71,01 | **+10,75** |
| promoção | 69,99 | −7,00 | 62,99 | **+4,45** |
| **PISO** | **63,69** | −6,37 | 57,32 | 0,00 |

**Régua:** `settlement ÷ revenue = 70,66%` (agosto, pedidos COM cupom, n=2.143 — mesma natureza
desta live). **Nunca aplicar taxa sobre o que o cliente pagou.**

### ❌ O desconto NÃO atraiu comprador ruim

Sobrevivência da peça (paga, não cancelada, não devolvida): **79,2% na rajada contra 65,4% no
resto da live**. Compra por impulso costuma cancelar mais; aqui foi o contrário.
Funil: 124 peças na janela → −30 nunca pagas → −2 canceladas pós-pagamento → −1 devolvida →
**91 líquidas**.

### ✅ O halo é real e positivo

Não-hero a **54,9 peças/hora** na rajada contra 7,9 fora (**6,9×**), somando **+R$ 81,18**.
O cupom pegar o catálogo inteiro **ajudou**. Não escopar só ao hero.

### ⚠️ A ressalva que importa — incrementalidade

A rajada só é lucrativa se a venda for de fato incremental:

| hipótese | Δ contribuição |
|---|---:|
| 100% incremental | **+109,63** |
| 70% | −77,42 |
| 50% | −203,12 |
| 0% (só antecipou) | −514,64 |

O ritmo de 7,2× sugere incrementalidade alta — ninguém compra sete vezes mais rápido por acaso —
mas **isso é inferência, não medição**. É o ponto fraco do relatório.

### Regra que fica

1. **Repetir o formato** — melhor mecânica de conversão medida na operação, e ela se paga.
2. **R$ 69,99 de lista é bom ponto** (folga 2,1×). R$ 67,90 exige 3,61× — margem fina.
3. **Piso de lista R$ 63,69.** Abaixo disso nenhum volume salva.
4. **Não escopar o cupom só ao hero** — o halo paga.
5. Registrar a promoção: `flash_sales` só guarda ONGOING, as 3 janelas (11:57–12:04 · 12:56–13:06 ·
   13:48–14:06) foram inferidas pelo cluster de preço.

### ⚠️ ADENDO (08/09, após o dono revisar): A PROMOÇÃO VAZOU

O dono avisou que promoveu **só REF516 e REF551**. Testei comparando o preço de lista praticado na
live com a mediana dos 15 dias anteriores, por família:

| família | grupo | pç | preço normal | na live | desconto | CPV | contrib/pç |
|---|---|---:|---:|---:|---:|---:|---:|
| REF516 | INTENCIONAL | 22 | 78,90 | 69,89 | −9,01 (11%) | 45 | 4,38 |
| REF551 | INTENCIONAL | 14 | 89,90 | 69,81 | −20,09 (22%) | 45 | 4,32 |
| REF525 | colateral | 3 | 78,90 | 69,99 | −8,91 (11%) | 45 | 4,45 |
| REF527 | colateral | 2 | 78,90 | 69,99 | −8,91 (11%) | 45 | 4,45 |
| **REF549** | **VAZOU** | 7 | **94,90** | 70,18 | **−24,72 (26%)** | **49** | **0,59** |
| **REF550** | **VAZOU** | 4 | **94,90** | 69,99 | **−24,91 (26%)** | **49** | **0,45** |
| **REF562** | **VAZOU** | 9 | **94,90** | 69,99 | **−24,91 (26%)** | **49** | **0,45** |

Cada família é um **`product_id` separado** (verificado em `affiliate_creator_product`) — não são
variações do mesmo anúncio. REF525/527 caindo é inofensivo (mesma economia do hero). O problema são
**REF549/550/562: CPV R$ 49 e preço normal R$ 94,90**, que foram a ~R$ 70.

**Custo: as 20 peças que vazaram contribuíram R$ 10,04 quando teriam contribuído R$ 361,13 →
−R$ 351,09.** Isso é **3,2× o ganho de +R$ 109,63** da promoção inteira. Sem o vazamento a live
teria fechado em ~R$ 702 em vez de R$ 350,56.

**Segundo achado:** "R$ 69,90 para as duas" virou **11% de desconto na REF516 e 22% na REF551**,
porque os preços-base eram diferentes (78,90 × 89,90). **Definir promoção em % ou em
contribuição-alvo, não em preço fixo.**

**Ação #1 do relatório passa a ser:** auditar a lista de `product_id` no painel de promoção antes
de ativar. Vale mais que qualquer ajuste de preço ou de formato.

| Premissa | Veredito |
|---|---|
| A promoção atingiu só REF516 e REF551 | ❌ **REFUTADA** — 5 famílias extras caíram; 3 delas caras |
| Preço único de promo serve para o catálogo | ❌ **REFUTADA** — R$ 4,37/pç no CPV 45 · R$ 0,50 no CPV 49 |

Relatório: `relatorios/2026-09/Relatorio Impacto Promocao Relampago Live 04-09_2026-09-08.{md,xlsx}`

---

## P22 · Registro de apresentadora por live — ✅ DESTRAVADO pela escala do dono (08/09/2026)

**A R21 continua correta e agora está exaustivamente confirmada.** Varredura multi-fonte
(3 agentes independentes, verificação adversarial):

- **Supabase:** 80 tabelas, **1.034 colunas** — grep por `apresent|host|staff|equipe|turno|bloco|
  escala|cronogram|schedul|shift|anchor|operador|locutor` = **zero hits**. Nenhuma tabela que
  carrega `room_id`/`live_key` carrega coluna de pessoa. Não há caminho de join.
- **Exports do Seller Center:** 148 .xlsx, 3 schemas, 94 colunas distintas, 43.716 células de
  texto varridas — **nenhuma coluna identifica quem apresentou**.
- **Proxies testados e refutados:** `live_sessao.campanha` com nome de pessoa cobre 4,6% das
  linhas (e é nome de campanha de ads, não de apresentadora) · `live_attr.titulo` com @handle
  = 1 live em 827 · `extrato_pedidos.creator` **NÃO mapeia apresentadora** (é comissão de
  afiliada; das 137 datas com live própria só 38 têm comissão LIVE, e a contagem de creators/dia
  não bate com a de salas/dia).

> **Conclusão: apresentadora não é extraível — tem que ser INSTRUMENTADA.** A escala do dono é
> a instrumentação. Salva em `dados/lives/escala_setembro_2026.csv`.

### O casamento funciona

Escala × sala por **data + janela do bloco** (tolerância de 60 min antes do início previsto):
**15 de 15 salas reais casaram, zero órfãs, zero turnos com sala de outro bloco.** Setembro tem
3 blocos fixos: 06:00–09:00 e 19:30–22:00 (Ingrid) · 11:00–14:00 (Gabriela seg–sex, Ingrid sáb).

### ⚠️ E o desenho da escala IMPEDE comparar as duas

Ingrid e Gabriela têm blocos fixos e **disjuntos**. A única sobreposição em 01–08/09 é o sábado
05/09 (Ingrid no bloco 11–14): **n=1, e sábado não é dia útil**. Comparar as duas é comparar
blocos. Vale a mesma armadilha da R21 (horário que some ao controlar por duração), agravada pela
amostra. **Para separar pessoa de contexto seria preciso rodízio na escala.**

Números descritivos (01–08/09, 15 salas, 39,67h): Ingrid 9 salas · 7,1 pç/h · R$ 38,53/h ·
Gabriela 6 salas · 15,1 pç/h · R$ 71,33/h. **Não usar como avaliação individual.**

### Achados operacionais que o registro destravou

- **Aderência de 81,0%** — 39,67h no ar contra 49,0h escaladas nos turnos já passados.
- **3 turnos não rodaram** (8,0h): 03/09 19:30 (sem motivo no dado) · 07/09 11:00 e 19:30 (feriado
  da Independência).
- **07/09 06:00 rodou 1h das 3h e fechou com GMV zero** — live que abriu e não vendeu.
- **Bloco 11–14 é o motor:** 45% das horas e 69% da contribuição. Bloco da noite rodou 2 de 5
  escalas e é o de menor retorno por hora (R$ 19,89).

### ⚠️ Gotcha de coleta encontrado no caminho

**A atribuição do TikTok ainda liquida dias depois.** Entre duas coletas no mesmo dia, 05/09 subiu
de R$ 1.848,08 para R$ 2.001,37 e a live de 07/09 **caiu de R$ 232,69 para zero**. Consequência:
**GMV zero NÃO pode ser critério de "reinício técnico"** — a de 07/09 durou 1h e é live real que
não vendeu. Critério correto: **duração < 15 min**, só isso.

Relatório: `relatorios/2026-09/Registro de Lives Setembro 01-08_2026-09-08.{md,xlsx}`

---

## P23 · "Devo subir outra campanha?" ❌ NÃO para live — e o ROAS estava enganando a decisão (09/09/2026)

**Premissa declarada antes de calcular:** se a live está fraca, subir uma segunda campanha de live
dividiria a entrega em dois leilões e recuperaria o clique.

**Veredito: ❌ REFUTADA.** A saturação é por **volume/dia**, não por número de campanhas.

| dia | impressões | impressão→view |
|---|---|---|
| 26/08 | 563.767 | 4,29% |
| 08/09 | 252.558 | 5,15% |
| 05/09 | 43.042 | 8,84% |
| 07/09 | 11.614 | 12,28% |

Os 3 dias com 2+ campanhas simultâneas deram i2v 10,58% — mas com 72k impressões/dia contra 199k
dos dias de campanha única. **O efeito é do volume, e a "vantagem" das 2 campanhas é confundimento.**
Dentro de 01–23/08 (antes do degrau) o contraste cai para 8,70% × 10,58% com a mesma diferença de
volume. Não há evidência de que dividir a MESMA entrega em duas campanhas melhore o clique.

Somando: peça marginal de live custa **R$ 16,18** de mídia e o teto que a peça aguenta pagar em
setembro é **R$ 14,25** (ticket bruto R$ 84,21 × 0,7084 − CPV R$ 45,40). Mídia adicional em live
destrói contribuição.

### ✅ CONFIRMADO de quebra: o ROAS inverte a decisão

Janela 10/08–09/09, mesma régua (`ticket × 0,7084 − CPV − CPA`):

| motor | gasto | ROAS | ticket bruto | contrib/peça pós-mídia |
|---|---|---|---|---|
| Live | R$ 15.255 | **10,80×** | R$ 83,18 | **R$ 5,83** |
| Produto | R$ 18.543 | 6,31× | R$ 96,14 | **R$ 7,48** |

Live tem quase o **dobro** do ROAS e entrega **menos** contribuição por peça, porque o CPV é fixo
em R$ 45,40 e o ticket da live é R$ 13 menor. **Decidir alocação por ROAS leva ao lado errado.**
Reforça `reference_regua_midia_contribuicao`.

### A alavanca real é subtração, não adição

Campanhas de produto negativas na janela: **R$ 4.492 de mídia produzindo −R$ 1.430** de contribuição.
A pior é `[GMV-MAX]-[MIX_PRODUTOS]-14.07.26` — 31 dias seguidos, R$ 3.214, CPA R$ 15,60,
ticket R$ 77,29 → **−R$ 1.287**. Cortar recupera isso **com certeza**; realocar é aposta.

**Nota contra a própria tese:** subir campanha nova não é o gargalo — o dono já subiu duas em 02–03/09
e a taxa de acerto foi ~50%: `[WIDE LEG's]-03.09` fez **+R$ 843** em 7 dias (R$ 10,67/peça) e
`[BAGGY][R.B]-02.09` fez **−R$ 124** em 8 dias (CPA R$ 35,38). O problema é seleção, não volume de
campanhas.

Relatório: aba "Subir outra campanha" em `relatorios/2026-09/Diagnostico Queda da Live Setembro_2026-09-09.xlsx`

---

## P24 · Live de 10/09 — ROAS 7,3× e PREJUÍZO de R$ 1.409. A saturação existe DENTRO da live (10/09/2026)

**Premissa declarada antes de calcular:** uma live com ROAS 7,3× e R$ 21 mil de GMV pago é uma live saudável.

**Veredito: ❌ REFUTADA.** A live 11:00–15:12 (4h12, sala 7683907251237997332) fechou em **−R$ 1.409,52**
(−R$ 335,60/hora). ROAS não paga CPV: com preço médio de R$ 68,86 e CPV de R$ 45,40, cada peça deixa
**R$ 7,16** de contribuição. 305 peças × R$ 7,16 = R$ 2.183 de contribuição bruta, contra R$ 3.383 de
mídia e R$ 210 de apresentadora.

### O prejuízo tem um endereço: a hora das 12:00

| | 11h e 13h (base) | 12h | |
|---|---:|---:|---|
| Gasto | R$ 373,27 | R$ 2.380,38 | **6,4×** |
| Pedidos | 75,0 | 99 | 1,32× |
| Live views | 5.226 | 9.814 | 1,88× |
| CPA | R$ 4,98 | R$ 24,04 | 4,8× |
| Custo/live view | R$ 0,0714 | R$ 0,2425 | 3,4× |

**CPA marginal = R$ 83,63** por pedido a mais, contra contribuição de **R$ 7,97** por pedido → destruiu
R$ 75,66 × 24 pedidos = **R$ 1.815,86**. Sem esse excesso a live fecharia em **+R$ 478,14**.

Isto é a mesma curva de saturação de [[P23]], agora medida **dentro de uma única transmissão** graças à
granularidade horária recém-descoberta (`stat_time_hour`, ver `reference_gmvmax_sem_funil_api`).

### ✅ CONFIRMADO: não foi o leilão nem a promoção

- **Não foi o leilão:** as campanhas de PRODUTO rodaram nas mesmas horas com CPA R$ 25,26 / 17,10 / 6,04
  — nenhuma inflação às 12h. Um leilão que infla por concorrência não desinfla em 1 hora (0,2425 → 0,0641).
- **Não foi a promoção:** preço mediano às 11h e às 12h foi **idêntico** (R$ 63,92; hero R$ 63,20) e o CPA
  quintuplicou. A oferta não mudou — o orçamento mudou. Promoção mexe na margem/peça, não no preço da impressão.

### ✅ A meta de ROI travada em 10,0 virou FREIO, não proteção

Às 14h e 15h o sistema entregou ROI **14,60×** e **23,64×** (46% a 136% acima da meta) com o tráfego no
preço mais barato do dia (R$ 0,0607/view) — e mesmo assim o gasto caiu 91%. Ele **não achou tráfego barato:
ele travou**. Meta de ROI alta = teto de agressividade de lance.

### ⚠️ Achados laterais

- **Inversão hero:** REF516 é 41% do volume a R$ 65,20 e deixa **R$ 4,37**/peça; o não-hero (REF549/550/562)
  vende a ~R$ 78 e deixa **R$ 14,35** — 3,3× mais. Reforça [[reference_liquidacao_cor_canal]].
- **24,7% das peças não viraram receita:** 88 UNPAID (R$ 6.109,84) + 12 CANCELLED (R$ 791,90). ⏳ remedir em
  48h para separar atraso de perda — a mídia já foi paga por esses pedidos.
- **Furo de grade:** REF551 (sem 44/46), REF525 e REF527 (sem 40/42) — zeros NO MEIO da curva, com vizinhos
  vendendo. Assinatura de ruptura, não de demanda. Rotação de pin deve checar saldo dos tamanhos centrais.

### ❌ Não medido (testado, não presumido)

15 min (hora é o piso da API) · CPM · CPC · impressões · CTR/CTOR · ATC · PCU · pago×orgânico. Todas
rejeitadas pelo endpoint como "Invalid metric" — só `live_views` é aceita. CTOR por SKU não existe em
fonte nenhuma; o export do Seller Center dá CTOR só por SALA.

Relatório: `relatorios/2026-09/Relatorio Live 10-09 Analise Completa_2026-09-10.xlsx` (8 abas)

### 🔴 P24 · CORREÇÃO DE BASE (10/09/2026, mesma noite) — o veredito INVERTEU

**O dono pegou o erro:** *"tem um contexto, o tiktok subsidiou cupom, deixou isso de fora?"* — sim, deixei.

`pedidos_sku.gmv` é o **sub_total** (o que o cliente pagou), confirmado em **394/394** pedidos do dia.
O `platform_discount` — **R$ 4.056,35** na janela da live, R$ 13,30/peça — é subsídio do TikTok e **volta
para a loja**. Eu apliquei um gross-up médio de **1,0774**, que foi calibrado sobre `live_attr.gmv` (outra
base). O gross-up **real** do dia é **1,1931** — subestimei a receita em 10,7%.

| | errado | correto |
|---|---:|---:|
| Receita | R$ 22,6k (gross-up 1,0774) | **R$ 25.059,75** (lista) |
| Contribuição/peça | R$ 7,16 | **R$ 12,80** |
| Contribuição total | R$ 2.183,43 | **R$ 3.905,33** |
| **Resultado da live** | **−R$ 1.409,52** | **+R$ 312,38** |

**A live PAGOU.** Margem apertada (R$ 74,38/hora), mas positiva.

**O que NÃO mudou:** o estouro das 12:00 segue destruindo valor — CPA marginal R$ 83,63 contra contribuição
por pedido de R$ 14,25 (era R$ 7,97). O subsídio melhora a margem da peça, **não** o preço da impressão
marginal. Saturação, trava de ROI e furo de grade seguem de pé. Sem o estouro a live daria **R$ 2.200,04**
— 7× o resultado real.

**O que ficou MAIOR:** a contribuição travada nos 88 UNPAID sobe de R$ 668 para **R$ 1.194,16** — quase
4× o resultado inteiro da live. Virou a ação nº 3 do plano, à frente do preço do hero.
Hero passa a R$ 10,61/peça e não-hero R$ 15,50 (1,46×, não 3,3× — o subsídio cai justamente sobre as peças
mais descontadas, que são as do hero).

### 🔧 FIX DE RAIZ — terceira reincidência do mesmo erro

Mega-live 06/08, rajada 04/09 e agora live 10/09: três vezes calculando taxa sobre o preço pago. Pela regra
de reincidência ([[feedback_fix_raiz_na_reincidencia]]), criado **`lib/receita.py`** como fonte única:

- `receita_itens(itens, pagamentos)` — rateia o `platform_discount` do pedido para os itens, proporcional ao pago
- `gross_up_real(...)` — fator **medido**, para auditar; nunca para estimar
- **canário** (`python3 lib/receita.py`) — falha se `pedidos_sku.gmv` deixar de bater com `sub_total` (hoje 394/394)
  ou se o `platform_discount` sumir da fonte

⚠️ **Regra dura:** nunca aplicar fator de gross-up médio sobre `sub_total`. Fatores calibrados numa base não
transferem para outra.

---

## P25 · Linha do tempo das intervenções na live de 10/09 — as duas custaram R$ 3.087 (10/09/2026)

**Premissa declarada antes de calcular:** a API do TikTok tem log de alterações de campanha, dá para ler
o que foi mexido e quando.

**Veredito: ❌ REFUTADA — não existe log.** 11 endpoints testados, **todos 404**: `/log/get/`,
`/operation_log/get/`, `/tool/operation_log/`, `/campaign/log/get/`, `/gmv_max/campaign/log/get/`,
`/advertiser/log/get/`, `/audit/log/get/`, `/change_log/get/`, `/gmv_max/campaign/history/get/`,
`/campaign/update_log/get/`, `/tool/action_log/get/`.

### ⚠️ ARMADILHA: `modify_time` NÃO é log de operação

`gmv_max/campaign/get` traz `modify_time`, e é tentador usar. **Não use.** As 11 campanhas da conta
aparecem "modificadas" em 10/09 entre **16:47:09 e 16:48:41** — 11 alterações em 92 segundos, depois da
live já ter acabado (15:12). É varredura do próprio TikTok recalculando status quando o ativo da live
ficou indisponível. Usar isso como log produz narrativa inteiramente falsa. Quase caí nela.

### ✅ A linha do tempo é RECONSTRUÍVEL pelas digitais

| Intervenção | Digital | Resolução | Confiança |
|---|---|---|---|
| Verba | curva `stat_time_hour` de cost/orders/roi | 1 hora | ALTA (salto de 6,4×) |
| Promoção | **piso** do preço pago por produto em faixas de 15 min | 15 min | ALTA (piso idêntico em 9 faixas e some) |
| Trava de ROI | — | — | ❌ **não datável** |

O piso do REF516 ficou travado em **R$ 59,92** em todas as faixas de 11:00 a 13:15 e desaparece a partir
de 13:30 → promoção desligada em **≈13:22**. Mesmo padrão simultâneo em REF551/525/527.
A trava de ROI **não é separável** de um teto de verba (mesmo efeito observável) e não há campo `roi_goal`
na API ("does not exist"). Fica em aberto até o dono informar o horário.

### ✅ A promoção estava PAGANDO — e cortá-la custou R$ 1.200

Teste limpo **dentro da hora 13** (mídia constante de R$ 373,06, então tráfego constante):

| faixa | promo | peças/min | contrib/min |
|---|---|---:|---:|
| 13:00–13:15 | ON | **2,60** | R$ 32,03 |
| 13:15–13:30 | OFF | 1,47 | R$ 25,13 |
| 13:30–13:45 | OFF | 0,80 | R$ 10,85 |
| 13:45–14:00 | OFF | **0,20** | R$ 2,48 |

Queda monotônica atravessando exatamente a fronteira do corte, com tráfego constante → é efeito de
**oferta**, não de tráfego. Com o estouro das 12:00 excluído da comparação: líquido/min cai de
**R$ 15,23 → R$ 4,33** (−71,6%). Ganhou-se R$ 1,62 de margem por peça e perdeu-se 1,10 peça/minuto.
Custo de oportunidade nos 110 min finais: **R$ 1.199,69**. Confirma [[P21]] (desconto em live se paga
pelo ritmo, não pelo preço) — agora visível minuto a minuto dentro da mesma transmissão.

### As duas intervenções, somadas

| | custo |
|---|---:|
| Estouro de verba às 12:00 | R$ 1.887,66 |
| Corte da promoção às 13:22 | R$ 1.199,69 |
| **Total** | **R$ 3.087,35** |

Contra uma live que fechou em **+R$ 312,38**. Elas puxam para lados opostos — a primeira gastou demais,
a segunda vendeu de menos. Sem as duas, a live estaria na casa dos R$ 3 mil.

⚠️ O custo da promoção é **estimativa**: audiência de live decai perto do fim e a mídia também caiu depois
das 14h. Por isso o teste foi restrito à hora 13, onde a mídia é constante.

### ⏳ EM ABERTO: proteção de ROI

A campanha está com `roi_protection_compensation_status: **IN_EFFECT**` e a hora das 12:00 entregou
ROI 3,46× contra meta 10,0. **O valor não sai por API** — 5 endpoints de compensação testados, todos 404.
Conferir no Seller Center (Ads > GMV Max > proteção de ROI). "IN_EFFECT" significa cobertura ativa, não
que há valor a receber — pode ser R$ 0.

Relatório: `relatorios/2026-09/Relatorio Log GMV Max e Impacto na Live 10-09_2026-09-10.xlsx` (6 abas)

### ↻ P24/P25 · REMEDIÇÃO 11/09 — o UNPAID era PERDA, não atraso

Refeita a coleta de `pedidos_sku` de 10/09 com os pedidos já pagos e finalizados (522 pedidos contra
394 na primeira medição; 409 pagos contra 301).

**Na janela da live 1 (11:00–15:12):**

| status | 10/09 (2h após) | 11/09 (remedido) | Δ |
|---|---:|---:|---:|
| pagos (AWAITING_COLLECTION + SHIPMENT) | 304 | **309** | +5 |
| UNPAID | 88 | **78** | −10 |
| CANCELLED | 12 | **17** | +5 |

**Veredito: ❌ a hipótese "parte do UNPAID é só atraso" está REFUTADA.** Passadas ~20 horas, só 10 das 88
peças saíram do limbo — e **metade virou cancelamento, não venda**. Taxa de conversão do UNPAID: 11%.
Contribuição travada cai de R$ 1.194,16 para **R$ 1.071,74** — ainda **2,9×** o resultado inteiro da live.
Segue sendo o maior valor isolado do relatório, e o nº de cancelados ainda pode subir.

**P&L atualizado da live 1:**

| | 10/09 | 11/09 |
|---|---:|---:|
| Peças pagas | 305 | **310** |
| Receita de lista | R$ 25.059,75 | **R$ 25.473,94** |
| Contribuição bruta | R$ 3.905,33 | **R$ 3.971,74** |
| Mídia | R$ 3.382,95 | R$ 3.393,51 |
| **Resultado** | R$ 312,38 | **R$ 368,23** |

Custo do corte da promoção recalculado: **R$ 1.243,38** (era R$ 1.199,69). Somado ao estouro das 12:00
(R$ 1.887,66) = **R$ 3.131,05** de intervenções, contra uma live de +R$ 368,23.

**⚠️ Descoberto na remedição:** houve uma **2ª live em 10/09** (sala 7684045713017146133, 20:02–22:09,
R$ 2.328,71, 32 itens) que NÃO entra em nenhum dos dois relatórios — eles cobrem só a live de 11:00–15:12.

**Nota de método:** o `ADS` do relatório de intervenções estava hard-coded; passou a ler da curva horária
recoletada, para que a remedição propague sozinha.

### 🔍 Auditoria de escopo (11/09) — a 2ª live de 10/09 está FORA

Confirmado pelo dono: *"a segunda live nao entra"*. Auditoria feita no gerador, não só no texto.

**Cálculos: já estavam corretos.** Os filtros são `11<=hora<=15` em `pedidos_sku` e `range(11,16)` na
curva de mídia — a sala das 20:02 nunca entrou em número nenhum dos dois relatórios.

**Textos: tinham contaminação.** 14 afirmações diziam **"do dia"** onde o correto era **"da live"** — e
depois que a 2ª live apareceu na recoleta, "do dia" virou factualmente errado. Corrigidas, e os valores
passaram a ser **calculados** em vez de escritos à mão, para não envelhecerem na próxima remedição:

| era | virou |
|---|---|
| "70% da mídia do dia" | "70% da mídia DESTA LIVE" (2.380,38 ÷ 3.393,51 = 70,1%) |
| "ROI 23,64× — o mais alto do dia — com R$ 33,95" | "ROI 17,97× — o mais alto DA LIVE — com R$ 44,51" |
| "tráfego mais barato do dia" | "mais barato da live" (no dia inteiro é 20h, R$ 0,0254) |
| "maior audiência do dia" | "maior audiência da live" |
| "394 pedidos brutos na loja no dia" | escopo da janela, sem número de dia |
| "gross-up real do dia" | "gross-up medido na janela da live" |
| "394/394 pedidos" | "100% dos pedidos (canário)" — hoje 493/493 |

**Lição de método:** número escrito à mão no texto de um relatório recolhível envelhece calado. Se o
relatório pode ser re-rodado, todo número do texto tem que vir de variável. Vale para todo gerador novo.

---

## P26 · Relatório Semanal Head — a semana 37 não pagou a estrutura, e 4 premissas caíram no caminho (14/09/2026)

Pedido do dono: um head de dados olhando o core inteiro, principalmente TikTok Shop, **toda terça 08:00**
(semana seg–dom), com check curto na sexta. Construído em `automacao/{dados_semana,recomendacoes,
gerar_relatorio_head,check_sexta,monitor_semanal}.py`, rodando na mesma corrente de jobs dos relatórios de
live e loja. Primeira prévia: semana 37 (07–13/09).

### ❌ Premissa 1 — "uma taxa de settlement única (0,7084) serve para todo canal"

Calibrada em 5.041 pedidos liquidados e sem devolução (criados 20/07–19/08):

| canal | settlement ÷ receita |
|---|---:|
| loja própria | 0,7549 |
| live própria | 0,7224 |
| live afiliada | 0,6935 |
| vídeo afiliada | 0,6475 |

10 pontos de diferença. O semanal recalibra toda semana numa janela já liquidada.

### ❌ Premissa 2 — "VL é mídia que sai do caixa"

A Vendas Líquidas é cobrada dentro da taxa e já está no settlement. Subtraí-la de novo dupla-conta:
7,8% do custo de GMV Max (31/08–13/09). **Mídia de caixa = só Tradicional.** Corrigido também no
relatório diário da loja e no e-mail.

### ❌ Premissa 3 — "`pedidos_sku.data` é a data de Brasília"

É **UTC**: 18,6% das peças (pedido após 21h BRT) caem no dia seguinte. Live noturna perdia metade:
10/09 20:02 **21 → 42 peças**, R$ 60,96 → **R$ 297,46**. Loja 13/09 **344 → 274 peças**. Três relatórios de
live e o da loja republicados. Ver memória `reference_pedidos_sku_data_utc`.

### ❌ Premissa 4 — "extrato_pedidos está completo até ontem"

Estava incompleto em vários dias; sem ele pedido de afiliada vira "loja própria". Depois de coletar:
loja própria **476 → 88 peças**, live afiliada 280 → 520, vídeo afiliada 305 → 466.

### ✅ CONFIRMADA — P23 estava certa: a campanha de live de 09/09 não se paga

`LIVE GMV-MAX- EXECUTACAO TESTE Dia 09/09`, subida contra a recomendação: **CPA de caixa R$ 10,18 contra
R$ 8,47 de contribuição líquida por peça** de live própria na W37. Primeiro loop de recomendação fechado com
medição.

### Veredito da W37 (07–13/09)

| | |
|---|---:|
| Receita de lista | R$ 154.522,86 · 1.851 peças |
| Resultado operacional | **−R$ 2.902,34** |
| Estrutura da semana | R$ 16.098,56 |
| **Resultado final** | **−R$ 19.000,91** |

Tendência do operacional, mesma régua: +R$ 2.246 → +R$ 2.161 → −R$ 901 → **−R$ 2.902**.
8 de 12 lives com estouro de verba numa hora (R$ 3.210,26). Nenhuma das 6 recomendações do registro com
sinal verde.

### 🔧 Modos de falha fechados na raiz

- **Rótulo "= …" virava `#ERROR!`** no Sheets (openpyxl marca como fórmula). Estava em **todos os 12
  relatórios de live e no da loja** — 14 células corrigidas no lugar, links preservados. Fix no publicador
  (vale para todo gerador) + nos geradores (vale para o .xlsx).
- **Canário pós-publicação:** `_publicar_drive.py` agora varre o que o Sheets renderizou e reporta células de
  erro em toda publicação. Era regra manual e foi pulada.
- **Verde falso:** "nenhum estouro — o teto funciona" aparecia com 1 live, ou com live curta demais para o
  detector disparar. Agora vermelho basta observar; **verde exige 3+ lives mensuráveis**.

### ⏳ Em aberto (perguntar ao dono)

O que está dentro dos R$ 70k · a apresentadora está dentro dos R$ 70k · site/Shopee/Shein faturam ·
base do imposto é a lista ou o pago. Todos os donos das recomendações estão "a definir".


### ↻ P26 · ADENDO 14/09 — respostas do dono mudam a régua (e uma conclusão acima)

**Respostas:** (1) composição dos R$ 70k: **sem acesso** → usado como declarado; (2) **apresentadora já está dentro**
dos R$ 70k → deixa de ser subtraída de novo; (3) **~90% do faturamento é TikTok** → o TikTok carrega 90% da estrutura
(R$ 63 mil/mês); (4) **regime é LUCRO REAL**, não Presumido — substitui o registro de jul/26. Lucas não vai responder.

**❌ Premissa refutada — "Rhode é Lucro Presumido (6,4% sobre faturamento)".** Lucro Real: PIS/COFINS **9,25% não
cumulativo** + IRPJ/CSLL **24%** (+10% acima de R$ 20k/mês) **só sobre lucro**. A incógnita que manda no número é o
**crédito de PIS/COFINS sobre o CPV** — só o contador confirma.

| W37 (07–13/09) | régua antiga | com crédito s/ CPV | sem crédito |
|---|---:|---:|---:|
| PIS/COFINS (Presumido: R$ 9.889,46) | — | R$ 6.520,09 | R$ 14.293,36 |
| Resultado operacional | −R$ 2.902,34 | **R$ 2.326,66** | — |
| Estrutura (parte do TikTok) | −R$ 16.098,56 | −R$ 14.488,71 | −R$ 14.488,71 |
| **Resultado final** | −R$ 19.000,91 | **R$ -12.162,05** | **R$ -19.935,33** |

A operação **se paga antes da estrutura** (antes não aparecia — a apresentadora contava duas vezes), mas **o TikTok não
paga a sua parte da estrutura em nenhum cenário de imposto**. Final semana a semana: R$ -8.693 → R$ -8.513 → R$ -11.465 → R$ -12.162.

**Campanha de live de 09/09 com a régua nova:** ⚠️ **depende do imposto** — CPA de caixa R$ 10,18: se paga COM crédito de PIS/COFINS (teto R$ 10,34/peça) e não se paga SEM (teto R$ 6,14). A confirmação de P23 registrada acima ("não se paga", com a régua do Presumido) fica **suspensa até o contador dizer se há crédito**.

Consumidores ainda no Presumido (atualizar quando mexer): `conciliacao.html` (TX_VENDA=6,4 / TX_IR=0) e a tabela por
peça de `project_estrutura_nao_paga`. Perguntas abertas agora: crédito de PIS/COFINS sobre o CPV · ICMS (ST ou destacado).


---

## P27 · "O que vende no horário da live é venda da live" ❌ REFUTADA (14/09/2026)

**Achado pelo dono:** o e-mail da live de 14/09 11:00 mostrou **R$ 8.885** e o painel de live do TikTok **R$ 6.255**.

**Ponte medida** (números da API no momento da medição, R$ 6.340,58 / 92 peças — o print era anterior):

| | peças | valor |
|---|---:|---:|
| Receita de LISTA no horário (pagos) — o que o e-mail mostrou | 106 | R$ 8.885,04 |
| (−) cupom subsidiado pelo TikTok — **lente, não erro** | | −R$ 1.490,87 (58,6%) |
| (−) pedidos de **vídeo de afiliada** no horário — **erro** | −6 | −R$ 579,42 (22,8%) |
| (−) **card/busca da loja** no horário — **erro** | −8 | −R$ 474,17 (18,6%) |
| **= GMV atribuído à sala pela API (painel)** | **92** | **R$ 6.340,58** |

**41,4% da diferença era erro de atribuição**: o gerador de live contava tudo que foi pago no horário da sala.

### ✅ Verificado em 14 lives (07–14/09)

- **O GMV da API está na base do PAGO** (mais perto do pago que da lista em 12/14; as 2 exceções: uma live de 3 peças e
  a de 08/09 11:06, com janela muito inflada).
- **A janela erra muito POR LIVE — de 0,81× a 1,43× as peças da sala** (08/09 11:06 inflava 43%). No agregado da
  semana dá só 1,02×, e por isso a média escondia o problema.

### Régua nova do relatório de live

- **Totais** (GMV, peças, receita de lista, contribuição, resultado) = **o que a API atribui à sala**. A receita de
  lista aplica o gross-up medido nos pedidos do horário.
- **Afiliada sai pedido a pedido** (`extrato_pedidos`), e o monitor passa a coletar o extrato antes de gerar.
- **Composição** (produto, grade, curva de preço, corte de promoção) = pedidos do horário **sem afiliada** — nenhuma
  fonte liga pedido a sala por SKU. A planilha ganha a ponte fixa horário → sala.
- **O e-mail abre com o GMV atribuído (o número do painel)**; receita de lista vira linha secundária ("base da margem").
- Bug de texto corrigido: "velocidade **caiu** de 0,49 para 1,23" — agora diz a direção certa.

**Live de 14/09 11:00 recalculada:** GMV R$ 6.340,58 · 92 peças · contribuição R$ 1.290,92 ·
**resultado R$ 610,80** (o e-mail tinha R$ 801,64). Todos os relatórios de live republicados no mesmo link.

---

## P28 · Lives da Ingrid — "a 2ª semana melhorou só porque entrou mais gente" ❌ REFUTADA (14/09/2026)

**Pedido do dono:** um relatório para a apresentadora acompanhar as janelas dela (manhã, noite e sábado), didático,
com elogios e pontos de melhoria. Entregue em `relatorios/2026-09/Relatorio Performance Ingrid Lives Setembro_2026-09-14.docx`
(build em `relatorios/2026-09/_build_relatorio_ingrid/`).

**Premissa testada:** a alta de vendas da 1ª para a 2ª semana veio do volume de público (horário, mídia), não da condução.

| 16 lives da Ingrid (01–14/09) | 01–07/09 (8) | 08–14/09 (8) | Δ |
|---|---:|---:|---:|
| GMV atribuído | R$ 12.722 | R$ 23.154 | +82% |
| GMV por hora | R$ 596 | R$ 947 | +59% |
| Entradas (views) por hora | 1.572 | 1.833 | **+17%** |
| Retenção média | 26,7s | 30,3s | +14% |
| Peças a cada 1.000 views | 4,9 | 6,7 | **+36%** |

**Veredito ❌:** o público cresceu 17%, mas as peças por 1.000 entradas cresceram 36%. A maior parte do ganho foi
conversão. ⏳ **Não prova** que foi o plano de 09/09: são 8 lives por semana, 1 sábado em cada, e o calendário
(feriado 07/09, dia 10) também mexe.

**O que os dados mostraram (e viraram as recomendações do relatório):**
- **Manhã converte mal o clique:** CTOR 1,7% contra 2,3% da loja. Em 14/09 teve a MAIOR retenção (36s) e CTOR de 1,1%:
  o público ficou e não fechou.
- **Ritmo oposto entre janelas** (peças pagas por meia hora, sem afiliada):
  - a manhã sobe de 2,4 para 5,0 depois de 2h30;
  - a noite cai de 7,6 para 4,5;
  - o sábado cai de 9,5 (pico) para 4,0.
  - Os trechos finais têm n=2.
- **Noite:** maior CTR (8,9% contra 8,3%) e mais pedidos com 2+ peças (10,6%).
- **Manhã:** traz 70% dos novos seguidores (248/352).

**Regras do relatório para apresentadora:**
- Não nomear a outra apresentadora; a régua principal é ela contra ela mesma.
- A média da loja entra só como referência, com a ressalva de horário (a manhã tem ~1.600 views/h, as lives das 11h ~2.400).
- Nada de margem ou contribuição.

**Gotcha corrigido na raiz:** `automacao/funil_live.py` relia a página 1 cinco vezes, sem repassar o `page_token`. A
janela tem 1.900+ sessões (afiliadas incluídas) ordenadas por GMV, e as lives próprias de GMV baixo ficavam sem funil
(as duas de 14/09). Agora pagina até acabar o token; testado com as salas de 12–14/09, todas com funil.

---

## P29 · Vídeos das creators — orgânico × GMV Max POR VÍDEO dá para medir, em duas lentes (15/09/2026)

Pedido do dono: um relatório de vídeos das creators (orgânicos e em GMV Max) para acompanhar a performance
de cada uma. Semana 07–14/09 contra 30/08–06/09. Entregue em
`relatorios/2026-09/Relatorio Videos Creators Organico x GMV Max_2026-09-15` (build `_build_relatorio_videos.py`).

| # | premissa | veredito | evidência |
|---|---|---|---|
| 1 | As métricas da `shop_videos` são lifetime por vídeo | ❌ | São **da janela consultada**: o mesmo vídeo deu R$ 10.398 em 01–14/09 e R$ 11.954 em 15/08–14/09. `video_perf` guarda a última janela coletada. |
| 2 | O GMV da `shop_videos` é a venda do vídeo | ❌ | Outra base (≈ pago): 01–14/09 somou R$ 54,4 mil contra R$ 82,4 mil de vídeo no extrato. Venda por vídeo sai da Affiliate Orders API. |
| 3 | O split vídeo orgânico × vídeo impulsionado não é mensurável (jul/26) | ❌ | A Affiliate Orders API traz `content_id` e `estimated_paid_shop_ads_commission` por item. 01–14/09: 38,8% da venda de vídeo de afiliada teve comissão de anúncio; 07–14/09: 41,4% (33,3% na semana anterior). |
| 4 | Comissão de anúncio = tudo que o GMV Max vende | ❌ | Nos vídeos da campanha Marmorizada (07–14/09): o painel atribui **294 pedidos**, só **152 itens** tiveram comissão de anúncio, de **322 vendidos**. |
| 5 | Custo/ROI/gancho por vídeo no GMV Max só existem na UI | ✅ | Confirmado. A raspagem precisa de `product_id` na URL. Sem filtro de status, a tabela vem ordenada por custo desc e a pág. 1 cobre ~92% do custo. |
| 6 | As datas da URL (`campaign_start_date`) definem a janela da tabela de criativos | ❌ | A tabela usa o próprio seletor ("últimos 7 dias"). As duas semanas vieram iguais: R$ 738,24 × R$ 738,73. Quem manda é `list_start_date/_end`, e o raspador confere as datas na tela. As raspagens inválidas foram para `criativos/semanas/_invalido_datas_ignoradas_0809_1509/`. |

**Regra que sai daqui — duas lentes de atribuição do GMV Max por vídeo:**
- **Painel** (pedidos que o GMV Max atribui ao criativo) absorve venda orgânica → **otimista**.
- **Comissão de anúncio** (item com comissão de Shop Ads) → **piso**.
- Veredito de corte pela régua de mídia (teto vídeo afiliada R$ 14,11, ago/26) só é **conclusivo quando as duas
  lentes concordam**. Exemplo: o principal vídeo da thami.brambilla custa R$ 13,04 por pedido pelo painel
  (SEGURAR) e R$ 19,97 por item com comissão (PREJUÍZO). Divergência = teste de pausa, não corte.

**Ferramentas novas:**
- `tools/tiktok-seller-scraper/raspar_criativos_semana.py`: campanha × produto × janela, carimba a janela no JSON.
- `tools/tiktok-seller-scraper/raspar_semana_produtos.py`: acha a campanha de cada produto.

---

## P30 · Corrida de Vídeos V1 — "a gamificação funcionou perfeitamente e se paga" (15/09/2026)

Pedido do dono: relatório para a diretoria justificando mais orçamento para a próxima corrida. Entregue em
`relatorios/2026-09/Relatorio Diretoria Corrida Rhode V1_2026-09-15.docx` (+ `.md`).

| # | premissa | veredito | evidência |
|---|---|---|---|
| 1 | A gamificação gera conteúdo em massa | ✅ | 244 posts na # (TikTok, 14/09); 239 vídeos de afiliadas com produto marcado + 3 da marca (Shop API, 15/09); 24 creators, 14 sem vídeo Rhode na semana anterior |
| 2 | Conteúdo orgânico barato | ✅ | Custo R$ 4.012–4.330 → R$ 16,8–18,1/vídeo; R$ 167–180/creator |
| 3 | Converte em venda com bom custo de aquisição | ⏳ | Venda direta dos vídeos # (Affiliate Orders, pedidos 07–14/09): **R$ 983,94 · 11 peças**, 7/239 vídeos, 80,3% thami. Três lentes de retorno (contrib R$ 17,11/pç): direto −R$ 3,8 a −4,1 mil · Marmorizada acima da tendência da loja (+68 pç) −R$ 2,8 a −3,2 mil · toda a alta da Marmorizada (+378 pç) +R$ 2,1 a +2,5 mil |
| 4 | "Funcionou perfeitamente" | ❌ | Prêmio de GMV apurado antes de maturar (só 3 creators com venda); 35,1% dos vídeos de 1 creator, 15,9% < 50 views; cupom "Corrida V1" com mínimo R$ 88,90 (1 peça); 47/100 usos em perfis sem vídeo # |
| 5 | "O +59% da Marmorizada é sinal limpo da corrida" (impacto v2, 14/09) | ❌ | A loja inteira subiu +46,9% em peças; a Marmorizada ganhou só +3,7 p.p. de participação (52,6% → 56,2%). Mídia GMV Max total +77,4% sobre a média (live +121,9%, produto +41,8%); campanha dedicada da Marmorizada desligada desde 16/08 |
| 6 | "A corrida vendeu por HALO: loja própria +99%, vídeo afiliada só +9%" (impacto v2, 14/09) | ❌ | Artefato do extrato incompleto (P26 premissa 4) + `pedidos_sku.data` em UTC (P26 premissa 3). Refeito com extrato completo e `order_time` BRT: **vídeo afiliada +65,1%** (468 vs 284), live afiliada +55,9%, loja própria +34,3% |

**Cupons "Corrida V1-@handle" (Promotion API, detalhe por id):** 15 criados entre 10 e 12/09 (2 duplicados, 2 desativados),
121 resgates / 100 usos: thami 49, tacianemorais 37, nandaemackreal 10 = 96. 10 dos 15 com zero uso.
`usage_stats` só vem no GET de detalhe — o search devolve `null`. `create_time` em milissegundos.

**Regra que sai daqui:** relatório de campanha de creator não credita alta da loja sem checar (a) a mídia da mesma
semana e (b) o share do produto foco na loja. Lente defensável = produto acima da tendência da loja, com a mídia
congelada. Pedido à diretoria virou V2 de R$ 5 mil com mídia de produto congelada + gate para V3 (custo por peça
incremental ≤ R$ 14,11 e ≥ 150 vídeos/20 creators).

⚠️ O `Relatorio Impacto Corrida na Loja_2026-09-14` (Drive) ainda mostra a leitura de halo — não republicado sem ok do dono.

---

## P31 · Premiação final da Corrida V1 — apuração de 15/09 14h (15/09/2026)

Pedido do dono: tabelas de pagamento (Top 5 GMV, Top 5 postagem) e checklist de PV para pagar hoje.
Entregue em `relatorios/2026-09/Relatorio Premiacao Pagamentos Corrida Rhode V1_2026-09-15.docx`.

| # | premissa do pedido | veredito | evidência |
|---|---|---|---|
| 1 | O bônus de R$ 100 do Top 5 de postagem é devido | ❌ | Gate de 500 vídeos; a # teve 244 (TikTok, 14/09). O template do pódio já dizia "sem bônus de volume". |
| 2 | A apuração de 14/09 serve para pagar | ❌ | Tinha 162 vídeos verificados; em 15/09 são 242. Entraram 4 classificadas (@jhenniferlet, @rosaacesariinoo, @taniaribeiro_creator, @kellypsilvaa_) e o volume da @natcorreaofc foi de 56 para 84. |
| 3 | O Top 5 GMV é o mesmo em qualquer base | ❌ | Pedidos de afiliada: 3º @amandadjehdian (R$ 94,91; o painel da shop_videos mostra R$ 0). Placar do grupo (shop_videos): @_mareiis no 5º. Recomendado: pedidos, a mesma base que a V2 adota. |
| 4 | O cupom 10% "ativado no perfil" já existe | ❌ | Os 15 cupons "Corrida V1-@handle" estão EXPIRED (fim 14/09 23:59; gleicysoares4 12/09). 6 das 16 classificadas nunca tiveram cupom. |
| 5 | As regras de hoje são as divulgadas | ❌ | Divulgado (V3/template): peça para quem fez >5 vídeos e para o Top 5, comissão turbinada para o 2º e 3º. Regra de hoje: amostra para quem fez ≥5. Diferença: +2 com exatamente 5 vídeos; −2 do Top 5 com <5 vídeos. Decisão do dono. |
| 6 | Quem vendeu entra no Top 5 mesmo com menos de 5 vídeos | ❌ | Regra confirmada pelo dono em 15/09: o Top 5 GMV exige 5+ vídeos com # de 07 a 14/09. Saem @amandadjehdian (4 com a # + 5 sem a #, R$ 94,91) e @thainabeautyoficial (2, R$ 0). Com o mínimo aplicado, a base (pedidos × placar) deixa de mudar o pódio: nas duas, o Top 5 elegível é o mesmo. |

**Top 5 GMV (base pedidos, só quem fez 5+ vídeos):**

| # | creator | venda | Pix |
|---|---|---:|---:|
| 1 | @thami.brambilla | R$ 890,47 | R$ 600 + Ads |
| 2 | @natcorreaofc | R$ 98,46 | R$ 400 |
| 3 | @adv.dayane | R$ 0 · 1.908 views | R$ 250 |
| 4 | @_mareiis | R$ 0 · 1.603 views | R$ 125 |
| 5 | @jhenniferlet | R$ 0 · 1.231 views | R$ 125 |

- **Ads:** vídeo 7684298796381080852 da thami (R$ 532,01 · 6 pedidos · 4.823 views).
- **Top 5 postagem:** natcorreaofc 84 · adv.dayane 15 · jackmundomabu 14 · _mareiis 13 · thami 12 — bônus R$ 0.

---

## P32 · Impacto da Corrida V1 em vídeo de afiliada e no GMV Max, sem live (15/09/2026)

**Pergunta do dono:** "conseguimos medir o impacto dessa corrida? especialmente em vídeo e GMV Max? sem contar com lives"

**Entregue:**
- `relatorios/2026-09/Relatorio Impacto Corrida em Video e GMV Max_2026-09-15` (sheet `1wu1E3Z7HOEAZ3PBhLKekKw_jgRQOCxFDjFl0zE86anM`)
- build `_build_impacto_corrida_video_gmvmax.py`
- dados em `dados/creators/impacto_corrida/`

Corrida = 07–13/09. Base = semana anterior (31/08–06/09) e média de 10/08–06/09. Só itens VIDEO de afiliada, sem cancelados.

| # | premissa | veredito | evidência |
|---|---|---|---|
| 1 | A venda de vídeo de afiliada cresceu na corrida | ✅ | R$ 40.333 vs média R$ 24.435 (+65,1%) e vs anterior R$ 33.771 (+19,4%) |
| 2 | O crescimento veio da corrida | ❌ | **Sem a thami, a semana empata com a anterior (−1,2%)**; orgânico sem thami −12,6%. Um vídeo dela de 27/08 (7678796145417522452), turbinado pelo GMV Max, vendeu R$ 9,2 mil. Vídeos da # = R$ 984 (2,4%). |
| 3 | Participantes venderam mais que não participantes | ⏳ | Sem thami: participantes +59,8% vs média (+23,6% vs anterior); não participantes +18,5% (−4,6%). Diferença das diferenças ≈ **R$ 1.076/semana** (R$ 951 contra a anterior), base de R$ 2,6 mil. Sinal positivo e fraco. |
| 4 | Os vídeos da corrida alimentaram o GMV Max | ❌ | Raspagem 07–14/09 (~95% do custo): 2,5% do gasto (R$ 144), 22 de 242 vídeos com gasto, 9 pedidos. Custo por pedido R$ 15,98, ≈ aos antigos (R$ 16,07). Gancho 2s 26,6% vs 32,3% dos vídeos antigos. Vídeos antigos levaram 90,4% do gasto. |
| 5 | O efeito continuou depois | ⏳ | 14/09: venda de vídeo R$ 2.710 vs R$ 5.762/dia na corrida, com mídia de produto R$ 500 no dia (≈ metade). Vídeos da # R$ 99,90 em 14–15/09. Releitura 28/09. |

**Contexto que confunde:**
- Mídia de produto na corrida: R$ 6.294 (+41,8% vs média).
- Venda via anúncio por R$ 1 de mídia: 2,65 com thami; **1,63 sem thami**, abaixo da média de 1,88.
- A semana anterior já tinha subido (começo de mês).
- Vídeos de afiliadas postados: 629 vs média 579 (+8,7%), com 239 da #. Fora da corrida postou-se menos.

**Regra que sai daqui:** impacto de campanha de creator se mede com três checagens obrigatórias:
1. Rodar sem o maior vídeo/creator (outlier).
2. Comparar participantes × não participantes (diferença das diferenças).
3. Olhar a mídia da mesma semana.

O total bruto engana, como já tinha acontecido em P30.

**Refresh 16/09/2026 10h (P32):**
- **Pedidos:** a recoleta bate semana a semana com a de 15/09. Só entram os pedidos de 14/09 em diante e alguns cancelamentos.
- **Números:** venda de vídeo na corrida R$ 40.250 (+64,7% vs média). Sem a thami fica −1,5% vs a semana anterior. A diferença das diferenças dá R$ 1.087.
- **Premissa 5 virou ❌:** de 14 a 15/09, a venda de vídeo foi R$ 2.553/dia contra R$ 5.750/dia na corrida (−55,6%). A mídia de produto caiu na mesma proporção (R$ 436 vs R$ 899/dia). A venda não ficou; ela acompanha a mídia.
- **⚠️ API com atraso:** apareceram **10 vídeos com a # postados em 14/09** (natcorreaofc 5, realmanumarques 2, monikandrade__, taniaribeiro_creator, andreaferreira.shop). A apuração de 15/09 dizia "nenhum vídeo com a # em 14/09", e isso ficou **refutado**.
  - Pela regra do dono (período 07–14/09), **@andreaferreira.shop chega a 5 vídeos** e vira classificada (cupom + amostra). O Top 5 GMV e o Top 5 de postagem não mudam.
  - Na análise de impacto, "participante" passou a ser quem postou de 07 a 13/09 (24). O vídeo de 14/09 não define grupo.
- **Regra:** vídeo recém-postado leva 1 a 2 dias para aparecer na shop_videos. Não fechar premiação no dia seguinte ao fim da janela sem uma recoleta D+2.

---

## P28 · adendo — atualização do relatório da Ingrid (16/09/2026)

**Entregue:**
- `relatorios/2026-09/Relatorio Performance Ingrid Lives Setembro_2026-09-16.docx`
- Build reutilizável em `relatorios/2026-09/_build_relatorio_ingrid_v2/`: `dados_ingrid.py` gera os dados, os destaques e os gráficos; `build.js` não tem nenhuma data de live fixa.

**Correção do dono:** a noite de 14/09 (19:30, R$ 10.212) foi feita pela **Dayane**.
- Saiu da conta da Ingrid pela lista `EXCLUIR` do script e fica só na média da loja.
- **Regra:** a janela de horário não prova quem apresentou. Antes de atribuir uma live à apresentadora, conferir a escala; sem escala, perguntar.

**Objetivos de 14/09, primeiras 2 lives (15/09 noite e 16/09 manhã):**

| objetivo | antes | agora | veredito |
|---|---:|---:|---|
| conversão da manhã | 1,7% | 2,7% | ✅ |
| retenção | 28,8s | 37s (2 de 2 ≥ 30s) | ✅ |
| pedidos com 2+ peças | 8,0% | 10,9% | ✅ |
| manhã com 2h30+ | — | 1 de 1 | ✅ |
| noite de 3h | — | a de 15/09 durou 2h08, com 925 entradas/h | ⏳ |

Amostra de 2 lives: sinal, não prova.

---

## P33 · Diagnóstico de funil das lives: pico (10–14/09) × queda (15–16/09) (16/09/2026)

**Pedido:** quebrar a queda do GMV das lives em topo, meio e fundo de funil.

**Base:** export "Creator Live Performance" do Seller Center (`dados/lives/funil_1016/`), mais GMV Max de live por hora e pedidos não pagos no horário.

**Entregue:** `relatorios/2026-09/Relatorio Diagnostico Funil Lives Pico x Queda_2026-09-16` (build `_build_diagnostico_funil_lives.py`).

Venda por hora: **R$ 2.172 → R$ 661 (−69,6%)**. A decomposição em log (impressões/h × entrada × clique × pedido × ticket) dá o peso de cada etapa:
- **impressões/h −59% → 76%** da queda;
- **clique em produto por view −30% → 30%**;
- pedido por clique −6% → 5%;
- taxa de entrada +9% e ticket +4% seguraram.

| # | premissa | veredito | evidência |
|---|---|---|---|
| 1 | O algoritmo parou de entregar | ❌ | A verba de live do GMV Max caiu de R$ 250/h para R$ 90/h (−64%). ~90% das views vêm do anúncio. O custo por mil impressões ficou parecido. É orçamento. |
| 2 | O CTR do feed caiu | ❌ | A taxa de entrada (views ÷ impressões) subiu de 4,71% para 5,14%. |
| 3 | A vitrine fadigou | ✅ | As exibições de produto por view ficaram iguais (5,06 → 5,04), mas o clique por exibição caiu de 8,9% para 6,3%. Coincide com o fim das promoções: peça de R$ 72 para R$ 78. |
| 4 | Retenção caiu | ⏳ | 38,1s → 34,0s. Comentários/1.000 views: 49 → 28. |
| 5 | Conversão e abandono pioraram | ❌ | Pedido por clique −6%. Não pagos no horário (proxy de abandono): 23,7% → 18,7%. |

**Achado que vira regra:** sem oferta, a mídia de live comprou peça mais cara, R$ 8,29 → R$ 10,62 por peça, acima do teto de live de ago/26 (R$ 9,40). Não liberar verba de live sem condição especial programada.

**Semântica do export:**
- `Tap through rate` = views ÷ impressões.
- `LIVE CTR` = cliques em produto ÷ views.
- `CTR` = cliques ÷ exibições de produto.
- `CTOR` = pedidos ÷ cliques.
- Não traz abandono de carrinho.

---

## P34 · "A queda de mídia de live vem do ROI alvo 12 estar alto" — ⏳ em parte (16/09/2026)

**Dados:**
- A campanha ativa é "LIVE GMV-MAX- EXECUTACAO TESTE Dia 09/09".
- A API (`gmv_max/campaign/get`) **não expõe ROI alvo nem orçamento**. Ela mostra só `modify_time` = **14/09 20:10** e `roi_protection_compensation_status = IN_EFFECT`.
- O dono informou alvo 12. Em 10/09 o alvo era 10 (análise daquele dia).

| dia | gasto live | ROI entregue |
|---|---:|---:|
| 10/09 | R$ 3.500 | 8,1 |
| 11/09 | R$ 949 | 9,0 |
| 12/09 | R$ 561 | 10,2 |
| 14/09 | R$ 1.820 | 12,0 |
| 15/09 | R$ 445 | 9,7 |
| 16/09 (parcial) | R$ 304 | 12,2 |

**Leitura:** o alvo funciona como teto de entrega. O GMV Max só compra leilão cuja conversão prevista cabe no ROI. Com oferta (14/09, "PROMOS ESPECIAIS"), gastou R$ 1.820 entregando 12,0. Sem oferta (15/09), a conversão prevista cai e quase nada cabe. **Alvo e oferta agem juntos**; o alvo sozinho não explica a queda.

**O 12 está alto? Depende do crédito de PIS/COFINS.** Base: teto da live própria no semanal W37, receita GMV Max por pedido de R$ 84,52 (10–16/09) e 1,11 peça/pedido.
- ROI de empate ≈ **7,3 com crédito**.
- ROI de empate ≈ **12,4 sem crédito**.

Sem o contador confirmar, **12 é o valor seguro** (≈ empate no pior cenário). Baixar para 10 só dá lucro se o crédito valer.

A média também esconde a hora cara: 10/09 12h gastou R$ 2.380 com ROI 3,5. Baixar o alvo libera principalmente horas assim.

**Recomendação:**
1. Manter 12 nas lives sem condição especial.
2. Testar 10 apenas em live com oferta programada, medindo a mídia por peça contra o teto.
3. Fechar a pergunta do crédito com o contador (já aberta em `recomendacoes.json`).

**Adendo 16/09 15h (P32) — vendas dos vídeos da corrida no orgânico:** nova aba "Corrida no orgânico". A venda direta na semana (07–13/09) foi de R$ 983,94.

| lente | orgânico |
|---|---:|
| teto (item sem comissão de anúncio) | R$ 357,42, 4 peças |
| piso (nem comissão nem painel veem anúncio) | R$ 94,91, 1 vídeo da amandadjehdian |

- Via anúncio: R$ 626,52. Cancelado: R$ 273,77.
- **R$ 9,18 de orgânico a cada 1.000 views, contra R$ 30,10 da base de vídeos de afiliadas (3,3× menos).**
- Depois da corrida (14–16/09): R$ 99,90 orgânico (thami).
- Veredito ❌ para "os vídeos da corrida venderam sozinhos".

---

## P35 · "A receita da loja caiu porque o TikTok parou de entregar tráfego" — ❌ REFUTADA (21/09/2026)

**Pergunta do dono:** qual o motivo da queda de receita da loja nos últimos 2 meses, e como estão conversão, visitante e impressão.

**Janela:** 22/07–19/09 (60 dias) × 01/06–21/07 (51 dias). Tudo por dia. O funil consolida em D-2, então a janela fecha em 19/09.
**Relatório:** `relatorios/2026-09/Relatorio Diagnostico Queda de Receita da Loja_2026-09-21.xlsx` · [planilha](https://docs.google.com/spreadsheets/d/1AGIjSxHlydsLkTaoPnVmAfl6IuA9jmrVYPDhoJ6zp6c/edit)

**GMV R$ 20.988/dia → R$ 17.132/dia (−18,4%). O tráfego SUBIU:**

| fator | anterior | atual | Δ | fatia da queda |
|---|---:|---:|---:|---:|
| impressões de produto/dia | 302.320 | 313.520 | +3,7% | −17,9% |
| CTR (clique ÷ impressão) | 5,79% | 5,72% | −1,2% | 6,0% |
| **conversão clique → pedido** | **1,40%** | **1,12%** | **−19,7%** | **108,0%** |
| ticket médio | R$ 88,74 | R$ 88,94 | +0,2% | 3,8% |

- Visitantes de página de produto **+7,5%**, page views **+2,4%**. Não é entrega, é conversão.
- **O degrau é carrinho → pedido:** carrinho ÷ clique ficou igual (8,3% → 8,1%), pedido ÷ carrinho caiu **−17,5%** (16,8% → 13,8%).
- **Não é mix de canal** (shift-share sobre R$/clique): mix +R$ 0,041, taxa −R$ 0,287 — **116,9% da queda é o mesmo canal vendendo menos por clique**, nos cinco canais.
- **Preço não subiu:** peça R$ 81,51 → R$ 79,75; subsídio da plataforma 9,7% (jun) → 6,7% (jul) → 8,6% (set).
- Recolocar a conversão em 1,40% vale **~R$ 126 mil/mês** sem R$ 1 a mais de mídia.

**Achados laterais:**
- **`product_page_views` da API da loja == `product_clicks` da API de produto** — a mesma métrica, conferida nas duas janelas.
- **A vitrine (`shop_tab`) SOBREPÕE os outros canais:** somar os seis dá 16% a mais que o GMV real; os cinco primeiros ficam a −1,4% do total. Nunca somar a vitrine (completa a nuance já registrada na memória do endpoint 202605).
- **Vídeo do vendedor queima clique:** 8,9% dos cliques da loja a **R$ 0,09/clique**, contra R$ 2,03 da live do vendedor.
- **Perda pós-pedido subiu:** peças que não viram caixa 21,7% (jun) → 24,8% (ago) = R$ 155.260 no mês.
- Reembolso do carro-chefe 17,6% → 20,9% do GMV, com ~75% das devoluções em "não serviu" (modelagem).

**⛔ Não medível hoje:** nota/avaliação da loja (nenhuma fonte instrumentada) — é a maior hipótese que sobrou sem teste. Sessão de site próprio também não existe: "visitante" aqui é visitante de página de produto dentro do TikTok Shop.

**⚠️ Viés da base:** o período anterior inclui junho (campanha 6.6, subsídio 9,7%). Mesmo sem junho a linha cai: conversão pv→pedido 1,23% (jul) → 1,06% (ago) → 1,01% (set).

**Adendo 21/09 (P35) — "o canal INTEIRO caiu de conversão?" ❌ não por igual.** O dono questionou a
generalização, com razão. As duas janelas de 2 meses misturam o pico de junho com as quebras. Em
**semanas fechadas — 01/06–12/07 × 10/08–19/09**:

| canal | antes | hoje | Δ | share de cliques | fatia da queda |
|---|---:|---:|---:|---:|---:|
| Live do vendedor | 3,24% | 2,86% | −11,6% | 19,0% | 17,1% |
| Live de afiliada | 2,43% | 1,85% | −24,1% | 15,6% | 21,9% |
| Vídeo de afiliada | 1,00% | 0,58% | −42,2% | 42,4% | 42,8% |
| Card do vendedor | 0,47% | 0,28% | −40,6% | 10,6% | 4,8% |
| Vídeo do vendedor | 0,65% | 0,08% | −88,4% | 12,3% | 17,0% |

- **A LIVE segurou:** live somada 2,79% → 2,40% (−13,9%). **Vídeo + card: 0,89% → 0,43% (−51,0%)**.
- **Não foi ladeira, foram dois degraus:** semana de **13/07** (loja 1,49% → 1,15%) e semana de
  **10/08** (1,25% → 0,98%); entre eles, estável.
- **Parte é diluição, não perda:** na semana de 10/08 o vídeo do vendedor saltou de 1.244 para
  15.592 cliques/semana (×12,5) convertendo 0,08% — hoje 12,3% dos cliques da loja. **Tirando esse
  canal, a queda passa de −27,2% para −18,5%.** Coincide com 11/08: `[MARMORIZADA-CARD-PRINCIPAL]`
  parou e `Product GMV Max_Receita bruta` começou. **Coincidência de data, não causa provada** —
  teste: pausar 7 dias e ver se o clique some e o GMV fica.
- Fica de pé o núcleo do P35: o tráfego não caiu e a perda é de conversão. Muda a mira: **vídeo de
  afiliada (42,8% da queda) é o alvo**, não "a loja inteira".

**Adendo 21/09 (P35) — "o vídeo de afiliada caiu por causa das minhas campanhas de GMV Max / ROI alvo alto?" ✅ ligado ao GMV Max · ⏳ o alvo em si não está provado.**

O vídeo de afiliada **é canal de mídia, não canal orgânico**. Separando cada item por comissão de shop ads (Affiliate Orders API), por dia:

| vídeo de afiliada | 01/06–12/07 | 10/08–19/09 | Δ |
|---|---:|---:|---:|
| venda total | R$ 7.407 | R$ 3.720 | −49,8% |
| · puxada por anúncio | R$ 4.098 | R$ 1.533 | **−62,6%** |
| · orgânica | R$ 3.309 | R$ 2.187 | −33,9% |
| % da venda vinda de anúncio | 55,3% | 41,2% | |

- Os **cliques do canal caíram só −17,7%**: o tráfego continua chegando, o que encolheu é o anúncio que fechava a venda.
- **Contrafactual:** com a parte paga no nível anterior, o canal faria 66,5 peças/dia (vs 39,6) e a conversão daria **0,97%**, contra 1,00% real de antes. **A queda de conversão do canal é praticamente toda venda que o anúncio parou de puxar.**
- **r = +0,92** entre mídia de produto/dia e conversão semanal do canal (r = +0,84 com cliques).
- Contraprova interna: a **live de afiliada quase não usa anúncio** (6,9% → 3,5% da venda) e caiu bem menos (−28,9%).

**Sobre o ROI alvo (⏳ não provado):** a assinatura de estrangulamento por alvo é gasto caindo COM ROAS realizado subindo. Nas campanhas de produto o ROAS realizado ficou **estável em 5,4–7,1** enquanto o gasto caiu de R$ 2.072/dia para ~R$ 600/dia, e o CPA piorou (R$ 13,84 → R$ 15,10 por pedido). Isso é mais compatível com **campanha pausada/trocada** (a `[MARMORIZADA-CARD-PRINCIPAL]` encerrou em 11/08) do que com alvo alto mordendo. Um alvo de 12 no produto seria inalcançável (o painel entrega ~6) e faria a campanha morrer de fome — cenário possível, mas a API não expõe o alvo (P34), então fica ⏳.

⚠️ **Não basta voltar a gastar:** R$ 15,10 por pedido do painel = R$ 13,49 por peça, contra ~R$ 8 de contribuição bruta (P19) — **1,7× o que a peça devolve**, e o pedido do painel é a lente otimista. Se for testar, medir contribuição, não GMV.

**Correção 21/09 (P35) — eu errei duas vezes na leitura de mídia; o dono estava certo.**

O dono apontou dois IDs: `1873253065502882` (teste para baixar CAC) e `1871604934635057` (CAC alto, ROI baixo). Conferido campanha a campanha, ele está certo nos dois.

| campaign_id | campanha | janela | CPA | ROAS |
|---|---|---|---:|---:|
| 1837899752347697 | `[GMV-MAX][MARMORIZADA-CARD-PRINCIPAL]` (a do hero) | 01/06→11/08 | **14,60 → 18,19 → 22,14** (jun/jul/ago) | 6,3 |
| 1871604934635057 | `[MARMORIZADA-CARD-PRINCIPAL]-VENDA LIQUIDAS` | 24/07→11/08 | 14,52 | 7,0 |
| 1873253065502882 | `Product GMV Max_Receita bruta` | 11/08→20/09 | **14,28 → 13,00** (ago/set) | 7,2 → 7,4 |

**Erro 1 — Simpson.** Eu disse "o CPA piorou (13,84 → 15,10)". Isso é o AGREGADO das campanhas de produto. Campanha a campanha o CAC caiu: a nova é a mais barata do portfólio. O agregado subiu porque a verba migrou para campanhas pequenas e caras criadas em setembro: `WIDE LEG's` R$ 18,94 · `MOM 16/09` R$ 24,95 · `BAGGY R.B` R$ 37,73 — 32% do gasto de produto de setembro. **Nunca comparar CPA agregado quando o mix de campanha muda.**

**Erro 2 — régua errada.** Eu comparei a mídia com "contribuição ~R$ 8/peça" (média da operação inteira, que inclui live de afiliada). A régua certa é a por canal (`Regua de Midia por Contribuicao`, ago/26): **teto R$ 25,16/peça no card de produto** e **R$ 14,11 no vídeo de afiliada**. A `Product GMV Max` roda a **R$ 12,24/peça** — dentro dos dois. **A mídia de produto paga**; quem estoura é `BAGGY R.B` (R$ 33,99/peça) e `BAGGY 27.07` (R$ 28,24/peça).

**Consequência prática:** em ago+set, R$ 6.546 foram para campanhas acima do teto (CPA médio 22,19) e compraram 295 pedidos. No CPA da campanha boa comprariam 482 — **+187 pedidos com a mesma verba**.

**E cai a recomendação de pausar a `Product GMV Max`:** ela é a mais eficiente. O salto de cliques do vídeo do vendedor em 10/08 coincide com ela, mas o painel atribui 30 pedidos/dia à campanha enquanto a API de produto vê quase nenhum pedido na superfície de vídeo do vendedor — é atribuição cruzada (clique conta na superfície, pedido conta em outra), não tráfego inútil. Ver [[reference_video_afiliada_e_canal_de_midia]].

## P36 · "O ROI alvo alto puxa o vídeo para baixo, e o ticket do vídeo é maior que o da live" — ✅ CONFIRMADA (21/09/2026)

Hipótese do dono, testada na janela **10/08–19/09** com `ads_campanha` (painel do GMV Max) e o extrato de afiliada. **Ele está certo, e o efeito é mensurável.**

**1. O ticket do vídeo é maior mesmo.** No extrato de afiliada: **R$ 93,87/peça no vídeo contra R$ 80,72 na live** (na base de junho era R$ 96,19 × R$ 79,02). Pelos números do painel, por motor: produto R$ 86,74 × live R$ 75,44.

**2. Com CPV fixo (R$ 45,40), ticket maior vira contribuição desproporcional:**

| por peça | Produto (vídeo e card) | Live |
|---|---:|---:|
| preço | R$ 86,74 | R$ 75,44 |
| contribuição antes da mídia | R$ 16,05 | R$ 8,04 |
| mídia | R$ 13,60 | R$ 7,34 |
| **contribuição depois da mídia** | **R$ 2,44** | **R$ 0,70** |
| R$ de contribuição por R$ de mídia | R$ 0,18 | R$ 0,10 |
| ROAS real | 6,38 | 10,28 |
| **ROI de empate** | **5,41** | **9,38** |
| **ROI para ganhar R$ 3/peça** | **6,65** | **14,96** |

**3. Por que o alvo único de 12 estrangula o vídeo:** a ROI 12 a mídia do produto teria que caber em **R$ 7,23/peça**, quando a peça custa **R$ 13,60** hoje. A campanha não acha entrega no alvo e definha — e é justamente o motor de ticket maior e maior contribuição. Na live acontece o inverso: 12 é **baixo** (ela empata em 9,38 e só ganha R$ 3/peça em 14,96), então ela gasta devolvendo R$ 0,70/peça.

**Alvos coerentes: ~6,5–7 no produto e ~15 na live** — quase o inverso de um 12 para todos. Isso fecha o circuito com o adendo anterior: mídia de produto ↓ → venda puxada por anúncio no vídeo de afiliada ↓ 62,6% → conversão do canal ↓ → conversão da loja ↓ (r = +0,92).

⚠️ **Lente:** os níveis vêm do painel (atribuição otimista) — tratar como ponto de partida de teste, não como verdade. A **ordem** entre os motores é robusta: depende de preço e CPV, não de atribuição. Confirma e atualiza o P23 ([[reference_regua_midia_contribuicao]]) com dados de setembro, e responde o ⏳ que ficou no P34.

## P37 · O gargalo da queda é CONCENTRAÇÃO EM CREATOR, não mídia nem conversão da loja (21/09/2026)

Aberto por creator (Affiliate Orders API, base de comissão, cancelado fora), **base 01/06–12/07 × hoje 10/08–19/09**:

| creator | R$/dia base | R$/dia hoje | perda | % da queda da afiliada |
|---|---:|---:|---:|---:|
| @tacianemoraisofc | 5.407 | 922 | **4.484** | **86,5%** |
| @adv.dayane | 1.381 | 352 | 1.029 | 19,9% |
| @alinecavanellas | 685 | 164 | 521 | 10,0% |

- **@tacianemoraisofc era 42,5% de TODA a venda de afiliada** e caiu −82,9%. As três maiores eram 59,0%.
- **Não foi a mídia que a derrubou:** o orgânico dela caiu −78,1% e a parte puxada por anúncio −88,4% — **as duas pernas juntas**. Postagem: 31 vídeos (jun) · 39 (jul) · 24 (ago) · **9** (set até 21).
- **Ela é 80,6% da queda da venda puxada por anúncio.** Ou seja: o que eu havia lido como "a mídia de produto parou de puxar venda no vídeo de afiliada" (adendo anterior) é, em grande parte, **o sumiço do criativo que a mídia amplificava**. A mídia caiu ATRÁS dela. Isso reordena as causas, sem apagar a régua do P36 — que continua válida como regra de alocação.
- **A base não morreu:** 155 creators cresceram, +R$ 3.691/dia (@amandadjehdian +1.592, @thami.brambilla +489).
- Na live de afiliada o padrão é outro: creators que venderam 55 → 36 (−35%), mas **quem ficou vende +8,5%** — é problema de base, não de performance. No vídeo, a base ficou igual (114 → 112) e a venda por creator caiu −49%.

**Ação:** conversa com a creator antes de qualquer mexida em mídia; e tratar concentração como risco (nenhuma creator acima de 20% da venda de afiliada).

**Lição de método (registrada em memória):** eu respondi "todos os canais caíram" quando o dono perguntou se a queda era geral, e só abri por canal depois que ele insistiu — e mesmo assim parei no canal, sem descer para creator. **Para diagnóstico de queda: sempre descer até a menor unidade com nome (creator, campanha, SKU) antes de concluir.** A concentração transforma um evento individual em "tendência" falsa.

## P38 · Criativo de vídeo: portfólio de poucos acertos, e o anúncio é o multiplicador (21/09/2026)

Relatório `Relatorio Criativos de Video_2026-09-21` ([planilha](https://docs.google.com/spreadsheets/d/1wrvjRvNwQOlTfF4lGg30PcTi7R7Dz_O-ZnQPTWxGeL4/edit)), janela 22/08–21/09 × 23/07–21/08. Alcance da shop_videos API, venda do extrato de afiliada casada por `content_id`.

**✅ O vídeo VOLTOU a crescer:** venda R$ 93.514 → **R$ 117.754 (+25,9%)**, views +34,4%, peças +28,3%. A parte puxada por anúncio subiu +26,7% e a orgânica +25,4%. Corrige a leitura de que o canal seguia caindo — a queda era da janela anterior e estava concentrada em uma creator (P37).

**As cinco verdades medidas:**
1. **Só 2,5% dos vídeos vendem** (267 de 10.498 ativos na janela).
2. **Os 20 maiores fazem 53,2% da venda**; o maior sozinho, 14%.
3. **Vídeo com venda por anúncio faz R$ 857 em média contra R$ 154 sem — 5,6×** (views 14.696 × 2.055). ⚠️ Mistura efeito do anúncio com seleção (o GMV Max escolhe o que já converte): é **teto**, não retorno medido. **Só 40,8% dos vídeos que vendem têm apoio de anúncio.**
4. **A faixa que converte é 5 mil a 100 mil views:** R$ 49,60 por mil views (5–20 mil) e R$ 34,17 (20–100 mil), contra **R$ 8,34 acima de 100 mil**. Viral traz alcance que não compra.
5. **#corridarhode: 281 vídeos, 55.061 views, R$ 1.288 = 1,1% da venda de vídeo.** A corrida entrega POSTAGEM, não venda — confirma e estende o P30/P32. Repetir só com briefing de criativo e prêmio por venda.

**Hooks dos campeões** (frequência nos 40 maiores vs catálogo): #wideleg, #jeans, calça, #modafeminina, #calcajeans, "perfeita".

⛔ **Sem dado:** retenção/watch time (só TikTok Studio) e **custo de mídia por criativo** (a API do GMV Max não abre custo por vídeo; só raspando a tela do Seller Center). Sem isso, o multiplicador do anúncio fica sem denominador.

**Adendo 21/09 (P38) — legenda com frase vende 60% mais por view, e o plano de impulsionamento.**

Comparação limpa (só vídeos SEM anúncio, medida por R$ a cada mil views, o que controla alcance):

| legenda | vídeos | R$ por 1.000 views |
|---|---:|---:|
| com frase escrita | 87 | **R$ 95,60** |
| só hashtag | 71 | R$ 59,89 |

⚠️ Na média simples por vídeo o resultado se INVERTE (só hashtag R$ 536 × com frase R$ 364) — porque os vídeos de hashtag têm mais alcance. **A régua certa é por mil views**, senão a conclusão sai ao contrário.

**Entregas ligadas a isso (21/09):**
- `Relatorio Plano de Impulsionamento de Criativos_2026-09-21` ([planilha](https://docs.google.com/spreadsheets/d/1fyhzSbkrj2q5w7lytrWcrmQdBgbLdRkybaJGT9hhI38/edit)): **56 vídeos** que já vendem no orgânico, com 2 mil a 100 mil views e ≥70% de venda orgânica. Juntos: R$ 26.151 em 444.711 views = **R$ 58,80 por mil views, 2,7× a média de vídeo (R$ 21,61)**. Onda 1 (tier A) = 12 vídeos, R$ 184/dia; lista inteira R$ 886/dia. **Regra de corte: pausar acima de R$ 14,11 POR PEÇA em 3 dias; escalar abaixo de R$ 9,88.** Aba de acompanhamento com a decisão calculada por fórmula.
- `Briefing de Criativo Rhode Jeans_2026-09-21.docx` (Drive `1ewFGgzw7Oc3-8_jwQMFNHc0871RZISQ5`): material para as creators, com as 5 regras medidas (frase na legenda, faixa de 5–100 mil views, caimento/medida real, produto hero, constância).
