# Referência — Live Commerce no TikTok Shop

> Levantamento da documentação pública disponível em **03/08/2026**. Fontes separadas
> por autoridade, porque a maior parte do que circula como "benchmark de live" é
> conteúdo de blog de ferramenta, não dado do TikTok.
>
> Complementa: `docs/PLAYBOOK_LIVE_CTA.md` (o nosso roteiro, com o dado da Rhode) e
> o módulo "Live que vende" em `rhode-vercel/public/academia.html`.

---

## 0. Hierarquia das fontes — leia antes de citar qualquer número

| Nível | O que é | Como tratar |
|---|---|---|
| **A · Oficial TikTok** | Seller University, TikTok Ads Help Center, Newsroom | Regra. Vale como norma e como mecânica de produto. |
| **B · Guia oficial BR** | "Guia de métricas para lives de sellers" (PDF, Seller Center BR) | Regra local. Onde conflita com A, prevalece o que estiver na SUA conta. |
| **C · Painel de vendedores** | Dashboardly, Kalodata, FastMoss | Direcional. Amostra US, denominador diferente do nosso. |
| **D · Blog de agência** | Arcos Scale, BlackFrame, TTS Vibes, etc. | Prática, não evidência. Útil pra tática, nunca pra número. |

⚠️ **Alerta de circularidade.** Quase todo "benchmark de live do TikTok" que aparece
no Google em 2026 (7,8% de conversão, curva de CVR por minuto, tabela por tipo de
host) tem uma única origem: **Dashboardly, abril/2026** — que é justamente o
concorrente que a gente já mapeou em `docs/COMPETITIVE_DASHBOARDLY.md`. O TTS Vibes
republica sem dizer que é blog de fornecedor. A metodologia deles é declarada
(reporte oficial do TikTok + terceiros + telemetria do próprio painel de merchants +
Kalodata/FastMoss), então **não é inventado** — mas é painel US, e o denominador
("todos os espectadores da live") **não é o mesmo** que o nosso `CTOR (SKU orders)`.
Nunca comparar os dois lado a lado.

---

## 1. Estrutura oficial da live (TikTok Seller University)

Arco de **1 hora**, pensado pra **repetir em loop** — a documentação é explícita:
"repeat key elements like product demos, bundling, and interaction in a loop", porque
"viewers join at different times".

| Bloco | Duração oficial | O que fazer |
|---|---|---|
| Abertura | 5 min | Receber pelo nome, apresentar o tema do evento, pedir compartilhamento |
| Aquecimento | 5–10 min | Visão geral dos produtos, promoção/sorteio/desconto exclusivo |
| Demo de produto | **5 min por produto** | Mostrar como comprar, **fixar o card**, explicar benefícios, citar venda em tempo real |
| Interação | 10 min+ | Responder dúvidas, recapitular benefícios, pedir opinião |
| Combos | 5–10 min | Agrupar itens relacionados, oferta por tempo limitado |
| Encore | 5 min | Repescar os mais vendidos com desconto por tempo limitado |
| Despedida | — | Agradecer, pedir feedback |

Frases de interação que a própria documentação sugere: *"Who's ready for a shoutout?
Drop a comment"*, *"Click the shopping bag to order now"*, e chamar pelo nome.

**Frequência e duração:** "The longer and more frequently you go LIVE, the more
opportunities you have to gain traffic and sales." Sem mínimo/máximo oficial.
O guia BR recomenda **2h30–3h**. A prática de agência BR converge em **2–4h**.

---

## 2. Mecânica do card fixado ⚠️

Documentação oficial (LIVE Product List Pin + TikTok LIVE Shopping):

- **"Pin product card every 30 seconds. Otherwise it will disappear and less people
  will click on the product."**
- **Um produto fixado por vez** — fixar o B desfixa o A.
- Existe **LIVE Product List Pin**: com mais de 2 produtos no showcase, dá pra fixar
  vários de uma vez.

⚠️ **Conflito com o guia BR.** O PDF do Seller Center BR trata o card como algo que
*permanece* ("Tempo com card fixado = % do tempo da live em que o produto ficou
fixado" · "fixe o card enquanto fala do produto e remova quando mudar de item"), o
que contradiz o auto-sumiço em 30s. Pode ser diferença de versão de UI ou de mercado.

**Instrução segura sob as duas leituras:** o operador **re-fixa o card a cada bloco**
e trata o card como algo que some — nunca assume que ficou. Confirmar o comportamento
real na conta antes de escrever regra definitiva.

---

## 3. Compliance — o que derruba a live

### Top 5 violações em LIVE (documento oficial)

| # | Violação | Proibido | No lugar |
|---|---|---|---|
| 1 | Promoção irrelevante | Falar de produto ou assunto sem relação com o que está listado | Conteúdo preso ao produto listado |
| 2 | Replay na sala | Áudio/vídeo pré-gravado, conteúdo em loop | Conteúdo único, produto físico na mão |
| 3 | Produção ruim | Imagem borrada, mal iluminada, ruído de fundo | Alta resolução, luz adequada, microfone |
| 4 | Funcionalidade enganosa | "cura", "emagrece rápido", promessa sem base | Só o que dá pra sustentar |
| 5 | Descrição vaga | Omitir o que a compradora precisa pra decidir | Preço, uso, benefício, depoimento |

### Requisitos de qualidade (oficial)

- **Conteúdo estático ou animado não pode passar de 50% da tela.** Imagem parada,
  screenshot, scroll de imagem, gravação de tela e slideshow são proibidos acima disso.
- **Screenshot da página do produto (PDP) é explicitamente proibido.**
- **Fala em tempo real obrigatória** — verbal ou libras.
- Rosto visível / presença humana. Conteúdo parado e repetitivo conta como baixa qualidade.

### 🚨 Voz de IA banida (julho/2026)

O TikTok Shop passou a **proibir voz gerada por IA, áudio gravado e locução em loop**
em lives de venda. Libras segue permitida como alternativa à fala. Violações passam a
afetar o **Account Health Rating** (0–1.000, janela móvel de 180 dias).

### Penalidades

Advertência (perde alcance / comentários desativados) → suspensão de live de 24–48h →
7–30 dias → restrição de comissão → remoção de conta. Categorias proibidas = suspensão
imediata.

### Redirecionamento para fora

Proibido levar a audiência pra fora da plataforma: QR code, link externo. A orientação
oficial é **evitar mencionar outras redes sociais e outros e-commerces**.

---

## 4. LIVE GMV Max (TikTok Ads Help — oficial)

- **O que otimiza:** ROI total da sala = GMV total da liveroom ÷ investimento.
- **Dois criativos, alocados automaticamente pelo sistema:**
  - **Video-to-LIVE** — usa vídeos da conta conectada como anúncio pra puxar gente pra sala
  - **LIVE-to-LIVE** — usa a própria transmissão em andamento como anúncio
- **Regra de convivência:** com uma campanha LIVE GMV Max ativa na conta primária,
  **os LIVE Shopping Ads da conta oficial são pausados automaticamente** — de qualquer
  ad account. Precisam ser religados na mão depois.
- **Fase de aprendizado:** ~**40 conversões** pra sair. Orçamento sugerido da campanha
  = **40 × o CPA histórico**.
- **Não mexer no ROI toda hora** — o GMV Max reotimiza diariamente e alteração
  frequente interrompe o aprendizado. Alvo sugerido: **10–15% acima do break-even**
  nas duas primeiras semanas.
- **Biblioteca de vídeo autorizada** (volume + qualidade) é o fator que mais acelera
  o aprendizado do sistema.
- Gestão de budget deve ser **dinâmica, atrelada ao GPM**: GPM forte → sobe diária;
  GPM fraco → desce, ou trava um alvo de ROAS mínimo.

---

## 5. Prática de mercado (BR + agências) — nível D, tática

Convergência entre as fontes brasileiras:

- **Blocos de venda de 15–20 min** por produto: gancho (problema) → demonstração
  (prova visual) → prova social → CTA com gatilho. Depois repete com o próximo item.
- **Moderador é ferramenta de venda, não de banimento**: quebra objeção em tempo real
  (tamanho, pagamento, prazo), fixa comentário com regra da oferta, cria pressão de
  estoque. O apresentador fica livre pra demonstrar. (Oficial: até **20 moderadores**.)
- **Teaser obrigatório** (oficial): 1 vídeo no dia anterior + reforço 2h antes,
  menos de 30s, com sticker de contagem regressiva.
- **Dois celulares**: um filma, outro acompanha comentário (oficial).
- **Otimização ao vivo**: audiência caindo → oferta relâmpago; produto esquentando →
  mais tempo de tela e urgência; oferta sem resposta → troca na hora.
- **Ancoragem antes do preço** e venda de transformação, não de especificação.
- **Escassez real, nunca inventada** — as próprias agências alertam que escassez falsa
  queima credibilidade.
- **Reaproveitar a live**: cortar os picos em vídeo curto pro feed.

---

## 6. Benchmarks que circulam — e o que fazer com eles

Origem única: **Dashboardly, abril/2026** (painel US). Denominador = *todos os
espectadores da live*, não cliques.

| Janela da live | CVR | AOV |
|---|---|---|
| 0–5 min | 2,1% | US$ 29 |
| 5–15 min | 5,4% | US$ 31 |
| 15–30 min | 7,8% | US$ 29 |
| **30–60 min** | **9,2%** | US$ 26 |
| 60–120 min | 8,1% | US$ 24 |

Outras da mesma fonte: live = 26% do GMV do TikTok Shop US (era 14% em 2024);
co-host (marca + creator) converte melhor que marca sozinha; devolução de live
8–12% vs 20–30% do e-commerce estático (McKinsey 2025).

**Como usar:** só como **formato de curva**, não como meta. Duas leituras sobrevivem
ao teste de denominador:
1. A conversão **sobe** ao longo da primeira hora e cai depois de ~2h.
2. O **ticket cai** conforme a live avança (comprador tardio empilha item barato).

Ambas apontam pro mesmo lugar: live curta demais nunca chega na janela boa.

---

## 7. O que isso muda no nosso roteiro

| Achado | Fonte | Status |
|---|---|---|
| Card some em ~30s — re-fixar a cada bloco | A (conflita com B) | ⚠️ corrigido no módulo, comportamento a confirmar na conta |
| Voz IA / áudio gravado banidos | A (jul/26) | ✅ adicionado ao módulo |
| Screenshot de PDP proibido; estático ≤50% da tela | A | ✅ adicionado — risco real ao mostrar tabela de medidas |
| Não mencionar outras redes / link externo | A | ✅ adicionado |
| Duração: nossa mediana 1,8h vs 2h30–3h recomendado | A + B + nosso dado | ⏳ maior alavanca não testada |
| Encore (repescar campeãs no fim) | A | ⏳ não temos |
| Teaser 1 dia antes + 2h antes | A | ⏳ não temos |
| Moderador como quebrador de objeção | B + D | ⏳ papel não definido |
| Combos/bundles como bloco próprio | A | parcial (temos "segunda peça") |

**A duração é o achado mais forte**, porque três fontes independentes convergem:
o TikTok diz "mais tempo = mais tráfego", o guia BR pede 2h30–3h, o painel US mostra
a conversão subindo até 30–60 min — e **o nosso próprio dado** mostra as 16 melhores
lives com 130 min contra 84 min das 16 piores. Estamos rodando abaixo do mínimo
recomendado por todo mundo, inclusive por nós mesmos.

---

## Fontes

**Oficiais TikTok**
- [How to Structure LIVE Content and Tips on Script Design](https://seller-us.tiktok.com/university/essay?knowledge_id=4034166326036267&lang=en)
- [TikTok LIVE Shopping](https://seller-us.tiktok.com/university/essay?knowledge_id=6927759780628226&lang=en)
- [LIVE Product List Pin](https://seller-us.tiktok.com/university/essay?knowledge_id=6700885599471402&lang=en)
- [Do's & Don'ts for Top 5 Violations in LIVE](https://seller-us.tiktok.com/university/essay?knowledge_id=6700885598914346&default_language=en)
- [Requirements for High-Quality Videos and LIVEs](https://seller-us.tiktok.com/university/essay?knowledge_id=4581457528243969&lang=en)
- [Choose the perfect host for your livestream in 3 Steps](https://seller-us.tiktok.com/university/course?learning_id=34326864283438&content_id=34326864054062&lang=en)
- [About LIVE GMV Max](https://ads.tiktok.com/help/article/about-live-gmv-max?lang=en)
- [Best practices for setting a LIVE Shopping Ads budget](https://ads.tiktok.com/help/article/best-practices-for-setting-a-live-shopping-ads-budget)
- [Differences between LIVE Shopping Ads and LIVE GMV Max](https://ads.tiktok.com/help/article/differences-between-live-shopping-ads-and-live-gmv-max-campaigns?lang=en)
- [Best practices for Product GMV Max](https://ads.tiktok.com/help/article/best-practices-for-product-gmv-max?lang=en)

**Painel de vendedores (nível C)**
- [Dashboardly — TikTok Shop LIVE Shopping Statistics 2026](https://www.dashboardly.io/statistics/tiktok-shop-live-shopping-statistics)
- [TTS Vibes — TikTok Live Shopping Conversion Rate 2026](https://insights.ttsvibes.com/tiktok-live-shopping-conversion-rate)

**Prática (nível D)**
- [Arcos Scale — 10 estratégias avançadas para lives de vendas](https://blog.arcosscale.com.br/10-estrategias-avancadas-sucesso-lives-vendas-tiktok/)
- [BlackFrame Studios — Como fazer live commerce que vende](https://www.blackframestudios.com.br/blog/como-fazer-live-commerce-que-vende-tiktok-shop)
- [COMU — Live no TikTok Shop: boas práticas que vendem](https://comunidade.nossacomu.com.br/c/por-dentro-do-tiktok/live-no-tiktok-shop-as-boas-praticas-que-realmente-vendem)
- [TechTimes — TikTok Shop bans AI voices from live commerce (jul/2026)](https://www.techtimes.com/articles/320624/20260715/tiktok-shop-bans-ai-voices-live-commerce-streams-violations-now-dent-account-health-score.htm)
