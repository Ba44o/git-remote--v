# Bio Rhode — Manual de Operação (1 página)

Página: **bio.rhodejeans.com.br** · Admin: **bio.rhodejeans.com.br/admin** (senha: ADMIN_PASS)

> Todo o CMS é visual. Nunca precisa editar código pra mudar bloco, cor, hero ou live.

---

## 🎯 Antes de cada live/drop — trocar o hero (2 min)

1. Abre `/admin` → painel **🎯 Hero (card do topo)**
2. Edita **Estado normal** (a campanha do momento):
   - **Kicker**: chip pequeno, ex `Agora na Rhode`
   - **Título**: peça/tema, ex `Wide Leg Marmorizada de volta`
   - **Descrição**: 1 linha de gatilho, ex `A queridinha voltou pro estoque — e vai rápido.`
   - **CTA**: `Ver na lojinha →`
   - **URL**: link do Showcase / TikTok Shop / lojinha
   - **Cor de fundo/texto**: opcional (paleta cai do preset se deixar padrão)
3. **Salvar hero**
4. Testa em [bio.rhodejeans.com.br](https://bio.rhodejeans.com.br) com hard-reload (`Cmd+Shift+R`)

---

## 🔴 Durante a live — ligar/desligar modo AO VIVO (1 clique)

**No começo da live:**
1. `/admin` → **🎯 Hero** → liga o toggle **🔴 Modo AO VIVO**
2. Confere se `live_url` aponta pra `tiktok.com/@rhodejeans/live` (já vem preenchido)
3. **Salvar hero**

O hero vira vermelho pulsante com "🔴 AO VIVO AGORA → Entrar na live" pra todos os visitantes. Se alguém do time quiser testar sem tocar no admin, abre com `?live=1` no fim da URL.

**Ao terminar a live:**
1. **Desliga** o toggle 🔴 → **Salvar hero**
2. Hero volta pra campanha normal automaticamente

⚠️ **Não esquecer de desligar** — hero vermelho fora do ar mata a credibilidade.

---

## 📦 Adicionar/editar/reordenar blocos

- **Adicionar**: `/admin` → botão `+ Novo bloco`
- **Editar**: clica no ✎ do bloco
- **Reordenar**: setas ↑ ↓ (troca posição com vizinho)
- **Ativar/desativar**: toggle Ativo dentro do editor
- **Agendar** (aparece/some sozinho): campos `starts_at` / `ends_at` no editor — perfeito pra campanhas com data (6.6, Black Friday)

**Convenções úteis:**
- **Seção**: string livre. Blocos consecutivos com mesma seção viram agrupados sob divisor. Ex: `Comprar`, `Pra você que cria`
- **WhatsApp com mensagem**: preenche o campo `Mensagem WhatsApp` — o cliente abre o chat com mensagem já digitada. Ex:
  - SAC: `Oi Rhode! Preciso de ajuda com meu pedido. Nº: `
  - Lovers: `Oi! Quero entrar pro grupo das Rhode Lovers 💛`
  - Mensagens diferentes = você sabe de onde veio no atendimento
- **Chip (rodapé)**: preset `Chip` transforma o bloco em pill pequeno no rodapé — usa pra marketplaces (ML, Shopee, Shein), política de trocas

---

## 📊 O que olhar toda semana (5 min de checagem)

`/admin` → painel **📊 Analytics** (janela: últimos 30d)

**Cards headline:**
- **Views** — quantas pessoas abriram o bio
- **Cliques** — quantos toques em blocos/hero
- **CTR médio** — cliques ÷ views

**Sinais pra ler:**
- **CTR médio < 30%** → hero ou primeiros 2 blocos não estão engajando. Troca copy/URL.
- **Bloco com 0 cliques em 7 dias** → mata ou muda. Espaço no bio é caro.
- **Views subindo, cliques planos** → problema de copy, não de tráfego.
- **Views caindo** → problema na origem (post/live/perfil), não no bio.

**Chart de views/dia:** picos batem com posts/lives. Vale correlacionar.

---

## 🎨 Mudar aparência (paleta, fonte, imagem de fundo)

`/admin` → painel **🎨 Aparência**

- **Presets rápidos**: Rhode padrão, Warm blush, Índigo denim, Grafite, Amanhecer, Preto&Branco, Verde denim
- **Fundo**: cor sólida / gradient / **imagem** (upload até 3MB → Supabase Storage)
- **Overlay**: se usar imagem, escurece pra manter texto legível
- **Tipografia**: 15 fontes Google (Montserrat, Playfair, Space Grotesk, Bebas Neue, Fraunces, Outfit…)
- **Cor de destaque**: aplica em ícones do logo, chips, botões de destaque
- **Tagline**: texto sob o logo

---

## 🔗 UTMs multi-plataforma

Cada canal usa um `?src=` diferente na URL do bio:

- **TikTok bio** → `bio.rhodejeans.com.br?src=tiktok` (default se omitir)
- **Instagram bio** → `bio.rhodejeans.com.br?src=ig`
- **YouTube descrição** → `?src=yt`
- **Newsletter** → `?src=email`

Todo link externo (site, lojinha, marketplaces) recebe `utm_source=<src>&utm_medium=bio_link&utm_campaign=bio_rhode` automaticamente. **Não é adicionado** em `wa.me/*` nem `tiktok.com/*` (evita quebrar deep link). O `src` também vai pro tracking interno, dá pra segmentar CTR por canal.

---

## ⚠️ Operação (não é código)

**Deep link do SAC abre o WhatsApp com mensagem pronta — mas quem segura a máquina é quem responde.**

Antes de divulgar o botão SAC em live/story:
1. Definir **macro de resposta** pro atendente (primeira mensagem em <5 min)
2. Definir **SLA** (resposta útil em <30 min no horário comercial, <2h fora)
3. Ter alguém de plantão **durante e 2h depois** de live/drop

Botão de ajuda que demora a responder queima mais que não ter botão.

---

## 🆘 Emergência (algo tá quebrado)

Ver [RUNBOOK.md](../RUNBOOK.md) pra cenários numerados. Se não estiver lá:

- **Bio não carrega** → verifica `bio.rhodejeans.com.br/admin` (se admin abre, é problema no fetch da tabela — abre o console)
- **Hero vermelho fora do ar** → alguém esqueceu de desligar. Vai no admin → Hero → desliga `Modo AO VIVO` → salva
- **Bloco não aparece** → confere `ativo=true` + `starts_at ≤ agora ≤ ends_at`
- **Cache velho** → visitantes veem versão antiga por até 6h (cache local do browser). Emergência: pede pra atualizar com `Cmd+Shift+R`
