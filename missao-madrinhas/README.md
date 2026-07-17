# Missão das Madrinhas — RhodeLovers (handoff pro Nathan)

Pacote pronto pra subir os **2 formulários** + o **link único por madrinha** + a **apuração automática**.
Baseado na spec do Notion. Ferramenta: **Google Forms** (link pré-preenchido + tela de confirmação com o link do grupo).

**Missão vai até 22/07/2026.** Prêmio: **Look em Dobro** (2 Rhodebox). Regras: convidada mulher que vem pra ficar · quem ganhou Rhodebox nos últimos 60 dias dá a vez · empate = sorteio.

## URLs de produção (forms já criados ✅)

| Item | Link |
|---|---|
| **/vira-madrinha** — página self-service da madrinha (cadastra + gera o link) → **entrada da campanha** | https://creators.rhodejeans.com.br/vira-madrinha |
| **/madrinhas** — página bonita da convidada (posta no Form B) | https://creators.rhodejeans.com.br/madrinhas?madrinha=NOME |
| **Form A** — Quero ser madrinha (backend do /vira-madrinha) | https://forms.gle/QziBTXCEVPo67SzH7 |
| Form A — editar | https://docs.google.com/forms/d/1tybjueq7EHXbZrZINziRf3-qqqpS86PCzvS8hDzGQyc/edit |
| **Form B** — Bem-vinda à RhodeLovers (público) | https://docs.google.com/forms/d/e/1FAIpQLSe3F8u27dRYFyrC0LkUkxSh_pmN7YxqqtOnXGs44esC1l41lg/viewform |
| Form B — editar | https://docs.google.com/forms/d/1sMJYSQUjdujdicF0339xIQg-NzZCFd99O7s2xU1kSIQ/edit |
| Campo "Quem te convidou" | `entry.302021428` |
| Link pré-preenchido **base** (já na planilha, célula C4) | `...viewform?usp=pp_url&entry.302021428=TESTE` |

## Arquivos desta pasta

| Arquivo | Pra que serve |
|---|---|
| `criar_forms.gs` | Google Apps Script que **cria os 2 forms inteiros** (textos, campos, validações, configs) e imprime o `entry.XXXXXXX` + o **link pré-preenchido base** do Form B. Automatiza os itens 1–3 do checklist. |
| `Missao_Madrinhas_Controle.xlsx` | Planilha de controle: aba **Gerador de Links** (nome → link único + mensagem de WhatsApp) e aba **Placar e Apuração** (conta convidadas válidas por madrinha, com ranking e gráfico). |
| `banner_rhodelovers.html` / `banner_rhodelovers_1600x400.png` | Banner de **referência** no padrão da spec (charcoal + RHODELOVERS + órbita amarela). Rascunho — **Bianca finaliza no Canva com os masters**. O PNG está em 2× (3200×800), mesma proporção do 1600×400. |
| `mensagens.md` | **Kit de mensagens** da campanha pra WhatsApp: abertura (com o link do Form A), entrega do link único, lembretes e anúncio do resultado (com versão de empate/sorteio). |
| `preview.html` / `preview_convidada.html` | Prévias visuais aprovadas (visão geral e a página da convidada). Abrem no navegador. |
| `cadastro_preview.html` / `vira_madrinha_preview.html` | Prévias das páginas HTML reais (convidada e madrinha). As versões que vão pro ar ficam em `rhode-vercel/public/madrinhas.html` e `vira-madrinha.html`. |
| `deploy_madrinhas.sh` | Deploy seguro na Vercel (isola o `hub.html`, sobe só as páginas da campanha). Rode: `bash missao-madrinhas/deploy_madrinhas.sh`. |

### Arquitetura das páginas (HTML bonito + backend Google)
`vira-madrinha.html` e `madrinhas.html` são páginas próprias (visual aprovado, fundo off-white) que **postam nos Google Forms por baixo** (`fetch` `no-cors` → `.../formResponse`), então tudo cai na planilha/placar. Backend = Forms + Sheets, front = HTML.
- **/vira-madrinha** → posta no **Form A** (`entry.623921980` nome · `entry.354940634` WhatsApp) → mostra o link `‎/madrinhas?madrinha=NOME` + botão de compartilhar.
- **/madrinhas** → posta no **Form B** (`entry.302021428` quem convidou · `766889621` nome · `1780347753` WhatsApp · `1888004738` @social) → mostra o gate com o grupo.

---

## Passo a passo (ordem recomendada)

### 1) Rodar o script que cria os 2 forms
1. Abra **script.google.com** → **Novo projeto**.
2. Apague o `Code.gs` vazio e **cole todo o `criar_forms.gs`**.
3. No topo, edite `LINK_DO_GRUPO` com o convite do grupo WhatsApp da RhodeLovers.
4. **▶ Executar** → função `criarMissaoMadrinhas` → autorize (é a sua conta criando os forms).
5. Abra **Ver → Registros de execução (Logs)**. Ele imprime:
   - URLs de edição e públicas dos 2 forms;
   - o **link curto do Form A** (pra mensagem de abertura);
   - o **`entry.XXXXXXX`** do campo "Quem te convidou";
   - o **LINK PRÉ-PREENCHIDO BASE** do Form B (termina em `=TESTE`).

> ⚠️ O que o script **não** faz (a API do Forms não deixa): cor do tema, fonte e banner.
> Abra cada form → paleta 🎨 → **cor Índigo `#1B3A5C`**, **fonte "Básica"**, **banner 1600×400** (o da Bianca). Fundo claro.

### 2) Configurar o gerador de links
1. Abra `Missao_Madrinhas_Controle.xlsx` → aba **Gerador de Links**.
2. Cole o **link pré-preenchido base** (aquele que termina em `=TESTE`) na **célula amarela** (C4). Não edite o `TESTE`.
3. **Apague os 3 exemplos** (Ana / Bruna / Carla) e digite o nome de cada madrinha na coluna **Nome da Madrinha**.
4. As colunas **Link Único** e **Mensagem pronta pro WhatsApp** se geram sozinhas.
   - O link troca o `TESTE` pelo nome dela (espaço → `%20`).
   - *(Opcional)* encurte no bit.ly e cole na coluna **Link Encurtado** — a mensagem passa a usar o encurtado.
5. Copie a coluna **Mensagem pronta** e cole no WhatsApp de cada madrinha.

### 3) Ligar a apuração
1. No **Form B** → aba **Respostas** → **Vincular a Planilhas** (o Google cria a planilha de respostas).
2. Conforme as convidadas preenchem, você tem duas opções de apuração:
   - **Simples:** cole as respostas na aba **Respostas Form B** do `.xlsx` → o **Placar** conta sozinho.
   - **Nativo (Sheets):** replique as fórmulas do Placar na planilha de respostas do Google (troque `,` por `;` e use `ENCODEURL` no gerador).
3. Na coluna **Saiu do grupo?** marque **"Sim"** pra quem entrou e depois saiu. **Válida = registrou E está no grupo no dia 22.**

### 4) Apuração (22/07, ~15 min)
- Abra a aba **Placar e Apuração**: ela já mostra **convidadas válidas por madrinha**, ranking e a **vencedora**.
- Aplique as regras: convidada mulher · madrinha **sem Rhodebox nos últimos 60 dias** · maior nº vence · **empate = sorteio** (mesma prática das lives).
- A **regra dos 30 dias é AVISO** na comunicação, **não** critério de corte (decisão 17/07). A apuração conta quem está no grupo no dia 22.
- Anúncio na bolinha às **19h** com o resultado.

---

## Textos prontos (já embutidos no script — aqui pra conferência/uso manual)

### FORM A — "Quero ser madrinha 💛"
**Descrição:**
> A missão do Dia do Amigo: traga amigas pra RhodeLovers até 22/07. Quem trouxer mais, ganha o LOOK EM DOBRO — duas Rhodebox: uma pra você e uma pra quem você escolher (ou as duas pra você, a gente não julga 👀). Preencha aqui e receba o SEU link de convite no WhatsApp. Regras: vale convidada mulher que vem pra ficar de verdade · quem ganhou Rhodebox nos últimos 60 dias dá a vez · empate = sorteio.

**Campos:** `Seu nome completo` (obrigatório) · `Seu WhatsApp (com DDD)` (obrigatório, validação de número).

**Confirmação:**
> Prontinho, madrinha! 💛 Em instantes o SEU link de convite chega no seu WhatsApp. Regra de ouro: convida quem realmente curte jeans e vem pra ficar — é assim que a comunidade cresce do jeito certo. Boa missão! 👑

**Mensagem de entrega do link (você responde no WhatsApp da madrinha):**
> Madrinha confirmada! 👑 Esse link é SÓ SEU — manda pras suas amigas: [link único]. Cada uma que entrar por ele conta pro seu placar. Missão vai até 22/07 💛

### FORM B — "Bem-vinda à RhodeLovers ✨" (o que a convidada abre)
**Descrição:**
> Você foi convidada por uma RhodeLover pra entrar no grupo mais especial da Rhode Jeans — onde tudo acontece primeiro: lançamentos, condições exclusivas, sorteios e bastidores. Preenche aqui embaixo (30 segundos) e o link do grupo aparece na hora.

**Campos:** `Quem te convidou` ⚠️ (obrigatório — **é este que o link único pré-preenche**) · `Seu nome completo` (obrigatório) · `Seu WhatsApp (com DDD)` (obrigatório) · `Seu @ do Instagram ou TikTok` (**opcional**).

**Confirmação (O GATE — o link do grupo só existe aqui):**
> Prontinho! Agora sim: seu lugar na RhodeLovers tá te esperando 💛 Entra por aqui 👉 [LINK DO GRUPO] — te vejo lá dentro!

---

## Config dos forms (o script já aplica)
- **Não** exigir login Google (mata conversão) · **não** coletar e-mail.
- **Não** limitar a 1 resposta (duplicata se resolve na apuração).
- **Desativar** "enviar outra resposta" na confirmação.
- Grupo WhatsApp: **"participantes podem adicionar" DESLIGADO** (Bianca monitora) — garante que ninguém entra sem passar pelo Form B → tracking 100% + consentimento.

## O padrão do link único
`.../viewform?usp=pp_url&entry.XXXXXXX=NOME%20DA%20MADRINHA`
O `entry.XXXXXXX` é **fixo** (o script te dá). Só o nome muda → gera em série na planilha. A apuração agrupa pela coluna **"Quem te convidou"**.

---

## Checklist de subida (Nathan)
- [ ] Rodar `criar_forms.gs` → Form A e Form B criados
- [ ] Aplicar tema (Índigo `#1B3A5C`, fonte "Básica", fundo claro) + **banner** nos 2 forms
- [ ] Preencher `LINK_DO_GRUPO` na confirmação do Form B
- [ ] Colar o link pré-preenchido base na planilha (aba Gerador de Links)
- [ ] Testar ponta a ponta com um nome de teste (madrinha → link → Form B → confirmação → placar)
- [ ] Colar o **link do Form A** na mensagem de abertura (`mensagens.md` → item 1) e disparar
- [ ] Agendar/preparar as demais mensagens do kit (entrega do link, lembretes, resultado 22/07)
