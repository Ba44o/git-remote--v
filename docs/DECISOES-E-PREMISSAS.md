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
