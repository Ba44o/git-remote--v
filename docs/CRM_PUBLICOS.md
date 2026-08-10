# CRM TikTok Shop — Mapa de Clusters e Públicos (Rhode)

> 2026-08-10. Desenho de segmentação para a aba CRM do Seller Center.
> **Base:** tabela `cliente` (22.012 clientes, pedidos 01/04 → 16/07/26), `pedidos_sku`
> (31.057 pedidos válidos), `devolucoes` (5.993), `extrato_pedidos` (creator de origem).
> Todos os números abaixo são medidos. Onde é aposta, está marcado **[APOSTA]**.
> ⚠️ A tabela `cliente` está defasada (última compra 16/07 vs hoje 10/08) — rodar
> `coletar_clientes.py --inicio 2026-04-01` antes de ativar qualquer público.

---

## 1. Premissas testadas (antes de desenhar)

### P1 — "O problema de AOV é ticket baixo" → ❌ **REFUTADA**
O ticket unitário está correto: 70,3% dos clientes compram na faixa R$60–89, que é o preço
do hero. O problema não é preço, é **quantidade por pedido**.

| Peças/pedido | Pedidos | % | Ticket | % do GMV |
|---|---|---|---|---|
| 1 | 28.511 | **91,8%** | R$ 77,72 | 84,5% |
| 2 | 2.090 | 6,7% | R$ 147,48 | 11,8% |
| 3 | 343 | 1,1% | R$ 198,23 | 2,6% |
| 4+ | 113 | 0,4% | R$ 261,29 | 1,1% |

**Attach rate = 8,2% · 1,10 peças/pedido.** AOV só sobe por attach, não por preço.
Corolário: o par co-comprado real é **calça + calça em outra lavagem** (203x e 182x nos
pedidos multi-produto), não calça + top. Bata Tomara-que-caia aparece só 49x+31x.

### P2 — "Recompra é um ciclo de 60–90 dias" → ❌ **REFUTADA**
Medido nos 2.295 clientes com exatamente 2 pedidos (intervalo exato):

| p10 | p25 | **p50** | p75 | p90 |
|---|---|---|---|---|
| 1d | 4d | **10d** | 28d | 51d |

**41,8% recompram em ≤7 dias · 77,4% em ≤30 dias.** Isso não é ciclo de lealdade, é o
comportamento *"provou, serviu, quero outra lavagem"*. **A janela de CRM é D+0 a D+30 pós-entrega.**
Consequência dura: dos 18.956 clientes de 1 pedido, **14.563 (66% da base) já estão fora da
janela** — reativá-los exige motivo novo (novidade/preço), não lembrete.

### P3 — "Devolução é ruído operacional" → ❌ **REFUTADA**
5.993 devoluções abr–jul, R$ 470.182 reembolsados. Motivo #1:

| Motivo | Qtd | % | Valor |
|---|---|---|---|
| **Item doesn't fit (não serviu)** | 4.406 | **73,5%** | **R$ 346.327** |
| Tecido/estilo fora do esperado | 303 | 5,1% | R$ 23.995 |
| Item com defeito | 247 | 4,1% | R$ 18.991 |
| Não precisa mais | 224 | 3,7% | R$ 18.209 |
| Cor/estampa fora do esperado | 203 | 3,4% | R$ 16.171 |

≈ **R$ 99k/mês evaporando por tamanho errado**, em 16,7% dos pedidos. 95,5% são
`RETURN_AND_REFUND` — ou seja, viram **dinheiro de volta, não troca**. Esse é o maior
público único de CRM da Rhode, e hoje ninguém fala com ele.
Confirma [[project_perda_produto_modelagem]] e dá destino ao [[project_size_finder]].

### P4 — "Cliente trazido por creator vale mais" → ❌ **REFUTADA**
| Origem | Clientes | LTV | AOV | Volta % |
|---|---|---|---|---|
| **(loja / sem afiliada)** | 4.775 (21,7%) | **R$ 110,68** | R$ 85,15 | **18,8%** |
| tacianetorress | 4.318 | R$ 101,55 | R$ 87,72 | 12,7% |
| alinecavanellas | 709 | **R$ 124,70** | **R$ 102,09** | 15,7% |
| adv.dayane | 1.421 | R$ 104,59 | R$ 84,44 | 16,4% |
| natmarquesvi | 1.928 | R$ 100,06 | R$ 82,79 | 14,3% |
| amandadjehdian | 325 | R$ 84,02 | R$ 80,32 | 4,6% |
| laianenovaisss | 512 | R$ 94,34 | R$ 87,34 | 6,4% |

O cliente da **loja direta retém melhor que qualquer afiliada** (18,8% vs 4,6–16,4%).
A afiliada é motor de **aquisição**, não de retenção — e a retenção é justamente o que
o CRM controla. `alinecavanellas` é a exceção (LTV e AOV mais altos da base): vale
estudar o que ela vende (parece vender combo, AOV R$102 vs R$82 da média).

---

## 2. Mapa completo de dimensões de cluster

Legenda: ✅ temos o dado hoje · 🔶 dá pra construir (falta ETL) · 🔷 provavelmente nativo do
TikTok CRM (a confirmar na tela) · ❌ não temos e não dá.

### A. Demográfico e geográfico
| Dimensão | Status | Nota |
|---|---|---|
| UF (27) | ✅ | SP 7.242 (33%), MG 3.044, RJ 2.055 |
| Cidade | ✅ | no `cliente` |
| Região / clima | 🔶 | derivado da UF — separa calça pesada (Sul/Sudeste) de shorts/saia (N/NE) |
| LTV por UF | ✅ | MT R$114,13 e ES R$105,80 acima de SP R$103,92 |
| Faixa etária / gênero | 🔷 | Orders API não entrega; o TikTok tem |
| Renda / classe | ❌ | proxy fraco por CEP |

### B. Comportamento de compra (RFM)
| Dimensão | Status | Buckets medidos |
|---|---|---|
| **Recência** | ✅ | 0-30: 1.172 · 31-60: 5.688 · 61-90: 5.411 · 91+: 9.741 |
| **Frequência** | ✅ | 1x: 18.956 (86,1%) · 2x: 2.295 · 3-4x: 641 · 5x+: 120 |
| **Valor (ticket)** | ✅ | <60: 383 · 60-89: 15.470 · 90-119: 4.494 · 120-179: 1.313 · 180+: 352 |
| LTV acumulado | ✅ | média R$104,45 |
| Janela de recompra | ✅ | mediana 10d — define o *timing* de todo disparo |
| Mono vs multi-item | ✅ | 91,8% mono |

### C. Cesta / produto — **a dimensão mais valiosa, e a que falta**
| Dimensão | Status | Nota |
|---|---|---|
| Modelo comprado (Wide Leg / Mom / Baggy / shorts / saia / bata) | 🔶 | está em `pedidos_sku`, **não ligado ao cliente** |
| Cor / lavagem (marmorizada, stone…) | 🔶 | idem — é o eixo do cross-sell real |
| **Tamanho comprado (36–46)** | 🔶 | idem — é o eixo da devolução |
| Hero vs esteira | 🔶 | REF516/525/527 vs REF588/562/587/549/551/550/529 |
| Gap de catálogo (comprou calça, nunca comprou top) | 🔶 | derivado |
| Preço cheio vs campanha/liquidação | 🔶 | via `data` do pedido vs janela de campanha |

> 🛑 **Bloqueio #1:** a tabela `cliente` guarda `cpf_hash` mas **não guarda o que a pessoa
> comprou**. Sem isso, nenhum cluster de produto/tamanho/cor existe. Fix: `coletar_clientes.py`
> já lê `order_id` — basta gravar `cliente_pedido (cpf_hash, order_id)` e cruzar com
> `pedidos_sku` e `devolucoes`. ~½ dia. **Destrava os públicos 2, 7 e 10.**

### D. Engajamento e relacionamento (majoritariamente nativo TikTok)
| Dimensão | Status |
|---|---|
| Seguidor da loja vs não-seguidor | 🔷 |
| Viewer de live (assistiu / comentou / add-to-cart / comprou) | 🔷 parcial — `live_attr` tem views/pedidos por sala, não por pessoa |
| Assistiu vídeo do creator | 🔷 |
| **Carrinho abandonado / checkout não concluído** | 🔷 |
| **Pedido criado e não pago** (~15% de vazamento) | 🔶 status na Orders API |
| Abriu / respondeu mensagem da loja | 🔷 |
| Clicou em cupom e não usou | 🔷 |

### E. Origem e atribuição
| Dimensão | Status | Nota |
|---|---|---|
| Creator de origem (1º pedido) | ✅ | 596 origens, 23 com 100+ clientes |
| Canal do 1º pedido (live/vídeo afiliada, live/card loja, vitrine) | 🔶 | `content_type` no `extrato_pedidos` |
| Trazido por mídia paga (GMV Max) vs orgânico | 🔶 | |
| Cliente de campanha (6.6, liquidação) | 🔶 | por data |

### F. Pós-venda e risco
| Dimensão | Status | Nota |
|---|---|---|
| **Devolveu — e por qual motivo** | 🔶 | `devolucoes.return_reason`, falta o elo com o cliente |
| Troca vs reembolso | ✅ | 95,5% vira reembolso |
| Cancelou / não pagou | 🔶 | |
| Avaliação deixada (5★ vs ≤3★) | 🔷 | |

### G. Derivados (modelo, não filtro)
Propensão a recompra (janela p50=10d) · risco de churn (recência > 28d) · **score de
risco de tamanho** (modelo × cor × tamanho → prob. de não servir) · valor esperado 12m.

---

## 2-bis. O que a tela do CRM confirma (visto em 10/08, `seller-br.tiktok.com/crm`)

**Caminho:** Marketing → Clientes → *Criar segmento para clientes da loja*.
Estado atual: **Padrão 6 · Personalizado 0** (nenhum segmento próprio criado ainda).

### Catálogo COMPLETO das condições nativas (19 condições, 4 famílias)

| Família | Condições |
|---|---|
| **Dados demográficos** (3) | Idade · Gênero · Região |
| **Comportamento de compra** (8) | Navegaram nos produtos da loja · Salvaram nos favoritos · **Adicionaram ao carrinho** · Avaliaram os produtos · **Fizeram pedidos** · **Valor do pagamento** · **Data do primeiro pedido** · **Data do último pedido** |
| **Engajamento** (5) | Assistiram vídeos com produtos à venda · Curtiram vídeos com produtos · **Produtos clicados em vídeos** · Assistiram transmissões ao vivo · **Clicaram em produtos na LIVE** |
| **Desempenho de divulgação histórico** (3) | Leram suas mensagens · Clicaram nas suas mensagens · **Cancelaram a assinatura** |

**Leitura:** o **RFM inteiro é nativo** (`Fizeram pedidos` = frequência · `Valor do pagamento` = valor ·
`Data do último pedido` = recência · `Data do primeiro pedido` = coorte). Tudo que desenhei em
P1/P3/P4/P5/P6 é construível hoje, sem ETL nosso.

**O que NÃO existe** (confirma a camada 2): SKU/modelo/cor/tamanho comprado · motivo de devolução ·
creator de origem · **e não há "seguidor da loja"** — o Engajamento é todo sobre **vídeo e live**,
que por sinal é melhor: é intenção, não vaidade.

**🎯 Descoberta que vale sozinha:** existe `Clicaram em produtos na LIVE` e `Produtos clicados em
vídeos`. Cruzado com `Fizeram pedidos = 0`, isso **endereça diretamente o vazamento já medido no
ledger**: *"compra após clique 2,33% → 2,80% = +R$35,4k/mês, 94.461 cliques sem compra"*
(P9 · 03/08). Até hoje esse público era inalcançável. **Agora dá pra mandar mensagem pra ele.**

### Restrições de projeto que a tela impõe
1. **Canal = IM.** A URL traz `plan_channel=im` e as abas são *"Criar planos de chat"* / *"Gerenciar
   planos de divulgação"*. A ativação é **mensagem direta dentro do TikTok** →
   **resolve o bloqueio #3** (não ter e-mail/telefone). O CRM fala com a cliente sem PII nossa.
2. **Mínimo de 3 condições** por segmento ("utilize pelo menos 3 condições"). Todo público
   precisa ser expresso como **≥3 filtros nativos** — não adianta desenhar segmento de 1 eixo.
3. **Tamanho estimado** aparece antes de salvar → dá pra **validar nossa contagem contra a do
   TikTok**. Divergência grande = a base deles conta gente que a Orders API não vê (e vice-versa).
4. **A segmentação roda sobre o dado do TikTok, não sobre o nosso.** Não há como filtrar por
   SKU/lavagem/tamanho comprado, motivo de devolução ou creator de origem.

### ⚠️ Ressalva do algoritmo
Tooltip da tela: *"Os resultados dos segmentos são refinados usando nosso algoritmo."*
O segmento **não é filtro literal** — o TikTok refina/expande. **Não esperar que o "Tamanho
estimado" bata com a nossa contagem do Supabase.** Nossos números = business case (quanto vale o
público); o número deles = alcance. Divergência não é bug, é base diferente.

### ⛔ Restrição dura: a janela só tem 3 valores
O seletor de período é **rádio de 3 opções**: `Nos últimos 7 dias` · `Nos últimos 30 dias` ·
`Nos últimos 90 dias`. **Não há faixa customizada nem data inicial/final.**

**Isso não atrapalha — confirma.** A janela de recompra medida é p50 = **10d** e p75 = **28d**:
- `últimos 7 dias` captura **41,8%** das recompras
- `últimos 30 dias` captura **77,4%** ← **é a janela de trabalho**
- `últimos 90 dias` captura **~100%** (p90 = 51d)

**O que a restrição mata:** segmentos de *reativação por faixa* ("entre 60 e 90 dias", "mais de
90 dias"). Só é possível construí-los se a ferramenta aceitar **negação/exclusão** (`últimos 90`
MENOS `últimos 30`) — **a confirmar**. Se não aceitar, **S6 e S7 caem** — e eram justamente os
de menor retorno na minha própria ordenação. A ferramenta é desenhada para a **janela quente**,
que é exatamente onde o dado disse que está o dinheiro.

### Receitas de segmento (revisadas para 7/30/90 · ≥3 condições cada)

| # | Segmento | Condições nativas | Nosso tamanho | Viável? |
|---|---|---|---|---|
| **S2** ⭐ | **Clicou na LIVE e não comprou** | `Clicaram produtos na LIVE: 30d` + `Fizeram pedidos = 0` + `Assistiram lives: 30d` | ordem de 94k cliques | ✅ |
| **S1** | **Serviu? → 2ª lavagem** | `Fizeram pedidos = 1` + `Data do último pedido: 30d` + `Não cancelaram assinatura` | 4.761 | ✅ (30d = 77,4% da janela) |
| **S4** | Comprou múltiplo e sumiu | `Fizeram pedidos = 1` + `Valor do pagamento ≥ R$120` + `Último pedido: 90d` | 1.381 · R$226k | ✅ |
| **S5** | VIP → candidata a afiliada | `Fizeram pedidos ≥ 3: 90d` + `Avaliaram os produtos` + `Clicaram nas mensagens` | 761 · LTV R$330 | ✅ |
| **S8** | Intenção sem compra (topo) | `Navegaram: 30d` + `Salvaram nos favoritos` + `Fizeram pedidos = 0` | — | ✅ |
| **S9** | Leitura demográfica (não é campanha) | `Idade` × `Gênero` × `Região` | — | ✅ |
| **S3** | Carrinho abandonado | — | — | ⚠️ **já existe plano automatizado rodando** (ver abaixo) |
| **S6** | Recorrente em risco (60–90d) | `Fizeram pedidos = 2` + `Último pedido: 90d` **NÃO** `30d` | 647 | ❓ depende de negação |
| **S7** | Base fria (>90d) | `Fizeram pedidos = 1` + **NÃO** `Último pedido: 90d` | 14.563 | ❓ depende de negação |

**Higiene do canal (transversal):** toda campanha exclui `Cancelaram a assinatura` e prioriza quem
`Leu`/`Clicou`. IM é canal de confiança — queimou, não volta. Teto sugerido: **1 mensagem por
cliente a cada 14 dias** [APOSTA, calibrar pela taxa de descadastro].

---

## 2-ter. Planos automatizados — o que JÁ roda (e o que está desligado)

Aba *Gerenciar planos de divulgação* → **Modelos de planos automatizados**, *sem limite de cota*.

| Plano | Status | Leitura |
|---|---|---|
| Recuperar carrinhos abandonados | 🟢 desde **14/01/2026** | ~7 meses no ar, **nunca medido** |
| Recuperar finalizações de compra incompletas | 🟢 desde **14/01/2026** | é o **vazamento de pagamento (~15%)** — já tem plano! |
| Agradecimento pós-compra | 🟢 desde **14/01/2026** | **veículo natural do S1** — ver ressalva de timing |
| Receber lembretes sobre reduções de preço | 🟢 desde **10/08/2026** (hoje) | recém-ligado |
| **Promover eventos de LIVE** | 🔴 **DESLIGADO** | gera visita à LIVE |
| **Lembrete para iniciar LIVE** | 🔴 **DESLIGADO** — marcado pelo TikTok como **"Conversão alta"** | avisa cliente quando a LIVE começa |

### 🚨 O achado com ação hoje
**Os dois únicos planos desligados são justamente os de LIVE** — e a live é motor central da Rhode
([[reference_shop_lives_api]], painel de lives, 65 lives em julho). Um deles o próprio TikTok
rotula **"Conversão alta"**. Ligar custa **um clique** e não consome cota.

É o mesmo público do **S2**: quem assiste/clica na live e não compra. Ordem de grandeza já medida
no ledger: **94.461 cliques sem compra** e a alavanca "compra após clique 2,33%→2,80%" avaliada em
**+R$35,4k/mês** (P9 · 03/08). Antes não havia como falar com essas pessoas. Agora há — e o canal
já está construído, só desligado.

### ⚠️ Ressalva sobre o "Agradecimento pós-compra"
Ele dispara **na compra**, não na **entrega**. Com recompra mediana de **10 dias**, a mensagem
certa ("serviu? leva a outra lavagem") precisa chegar **depois que a peça chegou no corpo**.
Verificar se o plano aceita **atraso configurável**. Se não aceitar, o S1 tem que ser um plano
**manual** por segmento, não esse automatizado.

### Antes de criar qualquer coisa nova
Os 4 planos ligados rodam há ~7 meses e **ninguém olhou o resultado**. Primeiro passo não é criar
— é **medir**: taxa de leitura, clique, descadastro e pedidos atribuídos de cada um. Se o de
carrinho já converte, o S3 não precisa existir.

### Consequência: arquitetura de ativação em 2 camadas
| Camada | Onde vive | Como ativa | Públicos |
|---|---|---|---|
| **1 — Nativa (CRM/IM)** | segmento no Seller Center | plano de chat | P1, P6, P9, P11, P12 + demografia |
| **2 — Nossa (dado próprio)** | Supabase (`cliente` + `pedidos_sku` + `devolucoes`) | insert na embalagem · creator · Hub · custom audience de ads · fluxo de troca | **P2 (não serviu)**, P7 (lavagem), P10 (risco de tamanho), P4 (VIP→afiliada), P8 |

> ⚠️ Ler junto: **o público de maior valor (P2, ~R$99k/mês) é de camada 2** — o CRM nativo
> não o alcança. A aba resolve alcance e entrega; ela **não** resolve inteligência de produto.

### Ganho inesperado: Idade e Gênero
Nunca tivemos essas duas dimensões ([[reference_cliente_dados_ltv]]: Orders API dá CPF, nome e
endereço, e só). Vale um segmento exploratório só para **ler a demografia real da compradora**
do Wide Leg — insumo direto para casting de creator e para a copy da Academia.

---

## 3. Os públicos (desenho)

Ordenados por R$ na mesa, não por elegância.

### 🥇 P1 — "Serviu?" — janela quente pós-entrega
**Quem:** comprou 1 peça, entrega concluída, D+3 a D+28.
**Tamanho:** 4.761 clientes em recência 0-30 (fluxo contínuo de ~1.400/semana).
**Por quê:** mediana de recompra = 10 dias e 41,8% em ≤7d. É o único momento em que a
cliente está com a peça no corpo e a opinião fresca.
**Ação:** mensagem única D+3 pós-entrega — *"serviu?"* — com dois caminhos:
não serviu → troca de tamanho (P2); serviu → **a mesma calça na outra lavagem** com desconto
progressivo na 2ª peça. Sem cupom genérico da loja.
**KPI:** attach rate 8,2% → **12%** e taxa de recompra em 30d.

### 🥈 P2 — "Não serviu" → troca, não reembolso
**Quem:** devolução com motivo `Item doesn't fit`.
**Tamanho:** 4.406 pedidos / R$ 346.327 em 3,5 meses (**≈ R$ 99k/mês**).
**Por quê:** 95,5% viram reembolso. Cada um é uma cliente que **queria** a peça e saiu com
dinheiro de volta e uma experiência ruim.
**Ação:** interceptar **antes** do reembolso concluir — oferta de troca de tamanho com frete
por conta da Rhode + [[project_size_finder]] no fluxo. Suprimir esse público de qualquer
campanha de venda enquanto a devolução está aberta.
**KPI:** % de devolução convertida em troca. **[APOSTA]** converter 30% ≈ R$ 30k/mês de GMV
retido — e mais importante, a cliente fica na base em vez de sair.

### 🥉 P3 — Compradora múltipla que sumiu
**Quem:** 1 pedido só, ticket ≥ R$120 (comprou 2+ peças de uma vez).
**Tamanho:** 1.381 clientes · R$ 226.234.
**Por quê:** já provaram que compram múltiplo — não precisam ser convencidas do combo.
**Ação:** lançamento/novidade em primeira mão, não desconto. É o público de teste de preço cheio.

### P4 — VIP → candidata a afiliada
**Quem:** 3+ pedidos. **Tamanho:** 761 clientes · LTV R$ 330,08 · R$ 251.192.
**Ação:** acesso antecipado e curadoria, **nunca desconto** (ela já compra). O pulo do gato:
essa é a candidata natural a **creator/afiliada** — compra recorrente, tem as peças, usa.
Cruzar com o Hub e a Copa Rhode Creators.

### P5 — Recorrente em risco
**Quem:** 2 pedidos, recência 61+ dias. **Tamanho:** 647 clientes · LTV ~R$170.
**Por quê:** já passaram do p90 (51d) da janela. Provaram valor e estão saindo.
**Ação:** janela curta de reativação com novidade + motivo. Se não voltar em 30d, migra pra P6.

### P6 — Base fria (1x fora da janela)
**Tamanho:** 14.563 clientes (66% da base).
**Por quê:** já passaram de 28d sem voltar. Propensão baixa.
**Ação:** **não gastar mensagem 1:1 aqui.** Usar como semente de *lookalike* em ads e como
público de campanha sazonal em massa (liquidação, coleção nova). Custo por toque tem que ser ~0.

### P7 — Cross-sell de lavagem (depende do bloqueio #1)
**Quem:** comprou o hero em UMA lavagem e nunca comprou outra.
**Por quê:** os pares reais são calça+calça (203x wide leg + wide leg; 182x). O catálogo já
prova qual é o segundo passo natural.
**Ação:** "sua Wide Leg em [outra lavagem]" — recomendação por cor, não por categoria.

### P8 — Órfãs da loja direta (o público esquecido)
**Tamanho:** 4.775 clientes (21,7%) · LTV R$ 110,68 · **volta 18,8%** (o melhor da base).
**Por quê:** chegaram sem afiliada, retêm melhor que qualquer creator, e não têm ninguém
falando com elas — não existe creator "dona" desse relacionamento.
**Ação:** é o público-alvo #1 do CRM próprio da marca (live da loja, card do vendedor, vitrine).

### P9 — Geo/sazonal
SP (7.242) concentra 33% mas tem LTV médio; **MT (R$114,13) e ES (R$105,80) rendem mais por
cliente**. Ação: separar oferta por clima — peça pesada no Sul/Sudeste, shorts (740 peças) e
saia (279) no N/NE.

### P10 — Risco de tamanho (preventivo, depende do bloqueio #1)
**Quem:** cliente prestes a comprar um par modelo×tamanho com histórico alto de "não serviu"
(o 46 é o pior — [[project_perda_produto_modelagem]]).
**Ação:** não é mensagem, é **intervenção na pré-compra** (Size Finder + tabela de medidas no
card). Evita a devolução em vez de remediar.

### P11 e P12 — Topo de funil (✅ confirmados nativos — ver S2, S3, S8)
**P11 — intenção sem compra:** não existe filtro de "seguidor", e sim de **comportamento**:
navegou/favoritou/assistiu vídeo/assistiu live **e não comprou** (S2, S8). É melhor que seguidor —
é intenção medida, não vaidade. **S2 (clicou na LIVE e não comprou) é o maior público novo da lista.**
**P12 — carrinho abandonado / pedido não pago:** ~15% de vazamento em pagamento
([[project_meta10k_cascata]]). Recuperação de checkout é o dinheiro mais barato da lista —
a pessoa já decidiu comprar.

---

## 4. Visão full funnel

| Etapa | Público | Dimensão de cluster | Métrica |
|---|---|---|---|
| Topo | **S2 clicou na LIVE sem comprar** · S8 navegou/favoritou | engajamento (nativo) | 1ª compra |
| Meio | S3 carrinho abandonado | comportamento (nativo) | recuperação de checkout |
| Conversão | P10 risco de tamanho | produto × tamanho | taxa de devolução |
| **Pós D+0–30** | **P1 "serviu?" · P7 lavagem** | recência + cesta | **attach 8,2% → 12%** |
| **Recuperação** | **P2 não serviu · P5 em risco** | pós-venda | **R$99k/mês em jogo** |
| Lealdade | P4 VIP → afiliada | frequência | LTV R$330 |
| Massa | P6 base fria · P9 geo | RFM + geo | custo por toque ~0 |

**Onde está o dinheiro, em ordem:** (1) devolução por tamanho ~R$99k/mês · (2) attach de
8,2% · (3) recuperação de checkout · (4) reativação da base fria — que é a maior em volume
e a menor em retorno, e por isso vem por último.

---

## 5. Bloqueios e próximo passo

| # | Bloqueio | Fix | Esforço | Destrava |
|---|---|---|---|---|
| 1 | `cliente` não tem o que a pessoa comprou | tabela `cliente_pedido (cpf_hash, order_id)` + join `pedidos_sku`/`devolucoes` | ~½ dia | P2, P7, P10 |
| 2 | `cliente` defasada (16/07 vs hoje) | rodar `coletar_clientes.py --inicio 2026-04-01` | 1 pull | tudo |
| 3 | ~~Sem e-mail/telefone~~ | ✅ **RESOLVIDO**: o CRM entrega por **IM** (`plan_channel=im`), sem precisar de PII nossa | — | ativação camada 1 |
| 4 | ~~Falta o catálogo de condições~~ | ✅ **RESOLVIDO 10/08**: 19 condições mapeadas, 9 receitas escritas (§2-bis) | — | S1–S9 |
| 6 | Operadores de cada condição (faixa? contagem? janela?) e os 6 segmentos "Padrão" | ver ao montar o 1º segmento | 5 min | calibrar S1–S9 |
| 5 | LGPD para contato 1:1 | fase 2 do `docs/CRM_IMPLEMENTACAO.md` (base legal + retenção) | — | qualquer disparo |

**Veredito geral:** ✅ a aba CRM vale o esforço — mas o valor dela **não** está em reativar
os 14.563 inativos (é o instinto natural e é o pior retorno). Está em (a) interceptar a
devolução por tamanho e (b) ocupar a janela de 10 dias pós-entrega com a 2ª lavagem.
