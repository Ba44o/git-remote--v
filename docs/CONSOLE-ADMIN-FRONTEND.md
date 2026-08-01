# Console interno · admin.html — UI/UX & Frontend

> URL de produção: **creators.rhodejeans.com.br/admin.html**
> Redesenho aprovado em **13/07/2026** (skill `/ui` · direção decidida pelo dono)
> Escopo canônico: ferramenta interna (ver `feedback_dominios_rhode` — o creator-facing vive em `creators.rhodejeans.com.br/hub|bio|academia`, com estética própria; o console interno usa esta linguagem de dashboard)

---

## 1. Contexto e problema resolvido

**Antes** (versão pré-redesenho):
- Navegação em **abas horizontais** no topo (`.tabs-nav > .tab`) — 10 abas do Creators + switcher "Creators/Conciliação" (`.modnav`) num pill separado.
- Cada tela interna (`admin.html`, `dash-live.html`, `conciliacao.html`) tinha seu próprio topbar/nav — nenhum shell compartilhado.
- Tema claro fixo com **parchment** (`#f5f5f7`).
- `.main` limitado a `max-width:1400px` — em telas 1920+ ficava com espaço morto grande nos lados.

**Depois**:
- **Sidebar fixa** à esquerda (250px) com IA agrupada por área de trabalho.
- Item ativo em Rhode red sutil; seções em JetBrains Mono UPPERCASE.
- **Tema escuro** como default, com toggle claro/escuro persistente.
- Content full-width com padding responsivo (32/48px em telas 1600+).
- Shell reaplicável nas outras telas internas (`conciliacao.html` já migrado).

**Trade-off aceito**: preservar 100% da lógica JS existente (10 painéis + 297KB de CSS antigo). O redesenho é uma **cirurgia estrutural** — troca navegação + injeta tokens novos + tema dark, mantém o resto funcionando. Nenhuma reescrita de conteúdo.

---

## 2. Arquivos envolvidos

```
rhode-vercel/public/
├── admin.html                 ← alvo deste doc (297KB · 5019 linhas · inclui CSS + JS)
├── conciliacao.html           ← já migrado pro mesmo shell (Fase 1)
├── dash-live.html             ← ainda com layout antigo (Fase 2 pendente)
└── bio-admin.html             ← Bio Rhode (linkado como workspace na sidebar)

.claude/skills/ui/
├── SKILL.md                   ← guia canônico do redesenho
└── references/
    ├── tokens.css             ← tokens v2 (fonte da verdade das cores/espaçamentos)
    ├── componentes.md         ← receitas de shell/KPI/tabela/filtros
    └── checklist.md           ← 20 checagens antes de dizer "pronto"
```

---

## 3. Design tokens (v2 · aprovados 13/07/26)

Adicionados coexistindo com os tokens antigos do admin — NÃO substituo os antigos (senão eu quebro os 297KB de CSS específico das 10 abas). O **tema dark** apenas sobrescreve as variáveis "canvas/parchment/ink/hairline" quando `[data-theme="dark"]` está no `<html>`.

### 3.1 Novos tokens (adicionados dentro do `:root`)

```css
/* Espaçamento (escala 4/8/12/16/24/32/48) */
--sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-6:24px; --sp-8:32px; --sp-12:48px;

/* Raios / motion */
--r-input:10px; --r-card:14px; --r-pill:99px;
--focus:0 0 0 3px rgba(254,44,85,.20);
--ease:all .16s ease;

/* Shell */
--side-w:250px;
--side-bg:#ffffff;
--side-active:rgba(254,44,85,.08);
--divider:#eef0f3;

/* Shadows / grid */
--shadow-sm:0 1px 2px rgba(16,24,40,.06);
--shadow-md:0 6px 22px rgba(16,24,40,.08);
--chart-grid:rgba(16,24,40,.07);
```

### 3.2 Tokens antigos preservados

```css
--rhode-red:#FE2C55 (acento — CTA, item ativo, alertas de queda)
--rhode-red-hover:#e8264c
--canvas:#ffffff   → dark: #151922 (superfície dos cards)
--parchment:#f5f5f7 → dark: #0b0d12 (bg do body/app)
--pearl:#fafafc    → dark: #1c212c (hover suave, second surface)
--ink:#1d1d1f     → dark: #f2f4f7 (texto principal)
--ink-48:#7a7a7a  → dark: #8a93a3 (labels, meta)
--hairline:#e0e0e0 → dark: #242a35 (borders sutis)
--green:#00796b   → dark: #3ddc97 (delta up · KPI good)
--orange:#c05e00  → dark: #f5a524 (atenção · alerts)
```

### 3.3 Sobrescrita do tema dark (`:root[data-theme="dark"]`)

Redefine as variáveis "canvas/parchment/pearl/ink/hairline/divider-soft/green/gold/orange/cyan" pra valores do sistema dark. Como o CSS antigo já usa essas variáveis (`background:var(--canvas)`), o dark "vira" automaticamente sem precisar reescrever.

**Regra ouro**: use tokens dinâmicos (`var(--canvas)`, `var(--ink)`). Nunca `background:#fff`, nunca `color:#000`. Se encontrar CSS antigo com hex hardcoded, adicione um override `:root[data-theme="dark"] .seletor { ... }`.

---

## 4. Tipografia (mantida da marca)

- **Corpo/UI**: Inter (300/400/500/600/700) — `letter-spacing:-0.011em`
- **Eyebrow/label/meta**: JetBrains Mono (400/500) — `letter-spacing:.14-.18em; text-transform:uppercase`
- Carregada via Google Fonts (`<link rel="stylesheet">` no `<head>`).

Essa dupla é a **assinatura da marca no interno** — mantenha.

---

## 5. Arquitetura de informação (IA)

Sidebar unificada com **5 áreas** — segue o princípio da skill `/ui`: cada item vai a um **workspace**, não a uma página órfã.

```
Rhode. CONSOLE

── CREATORS ──
  ◧ Dashboard         (ativo por default)
  ☰ Ranking
  ⚠ Alertas
  ↗ Evolução
  ✦ Analista IA
  ⚙ Operação
  ✉ Comunicação
  ○ Comportamento
  ▤ Triagem

── VENDAS & GMV ──
  ▤ Conciliação →     (link pra conciliacao.html)

── LIVES ──
  ◔ Dashboard Lives → (link pra dash-live.html)

── BIO ──
  ✧ Bio Rhode →       (link pra bio-admin.html)

Sair ↩
```

**Regras de IA aplicadas**:
- As 9 abas do Creators (era 10, `Evento 13/04` foi removido em 2026-07-15 — evento pontual passado) viram items diretos na sidebar. Não há sub-menu porque cada aba é um workspace autônomo dentro do console de Creators.
- Cross-workspace (Conciliação, Lives, Bio) são **links** que trocam de HTML — cada um mantém sua própria lógica JS pesada. Na Fase 2 vão herdar o mesmo shell (já feito em conciliacao.html).
- **Breadcrumb no topbar**: `Creators › <aba ativa>` (atualiza dinamicamente via `TAB_LABELS[id]`).
- **Sair** fica no `.side-foot` — sempre acessível, longe dos botões de nav.

---

## 6. Shell (estrutura HTML)

```html
<div id="adm-app">            <!-- container geral (display:none até login) -->
  <div class="app">           <!-- grid: sidebar | content -->
    <div class="side-backdrop"><!-- overlay mobile (display:none default) --></div>
    <aside class="side">      <!-- sidebar fixa (250px) -->
      <div class="side-brand">Rhode<span class="adot">.</span><small>Console</small></div>
      <nav class="side-nav">
        <div class="side-sec">Creators</div>
        <button class="side-item on" data-sid="dashboard" onclick="tab('dashboard',this)">
          <span class="side-ico">◧</span> Dashboard
        </button>
        <!-- ... -->
      </nav>
      <div class="side-foot">
        <button class="side-btn" onclick="admLogout()">Sair ↩</button>
      </div>
    </aside>
    <main class="content">    <!-- conteúdo scrollável -->
      <header class="topbar">
        <button class="side-open-btn" onclick="openSide()">☰</button>  <!-- mobile only -->
        <div class="crumbs"><span>Creators</span><span class="sep">›</span><b id="crumbActive">Dashboard</b></div>
        <div class="tright">
          <span class="tstatus" id="st"></span>
          <button class="tbtn" onclick="syncAll()">↻ Sincronizar</button>
          <button class="theme-toggle" onclick="toggleTheme()"></button>
        </div>
      </header>
      <div class="pbar-wrap">   <!-- filtro de período (sticky top:56px) -->
        <span class="pbar-label">Período</span>
        <div class="prange">…</div>
      </div>
      <div class="tabs-nav" style="display:none">
        <!-- 9 botões .tab legado, invisíveis mas presentes pro tab() sincronizar -->
      </div>
      <!-- 9 painéis .panel (só o ativo tem .on) -->
      <div class="panel on" id="panel-dashboard">…</div>
      <div class="panel" id="panel-ranking">…</div>
      …
    </main>
  </div>
</div>
```

### 6.1 CSS do grid

```css
.app{
  display:grid;
  grid-template-columns:var(--side-w) 1fr;
  min-height:100vh;
  background:var(--parchment);
}
```

**Bug corrigido durante o desenvolvimento**: `.side-backdrop` estava com `display:none` só dentro do `@media(max-width:900px)`. No desktop ele ficava com `display:block` default e ocupava a **coluna 1** do grid — empurrando `.side` pra coluna 2 e `.content` pra linha 2. **Fix**: `.side-backdrop{display:none}` como regra global (fora do media query). Só ativa `display:block` quando `.on` (via `openSide()`).

### 6.2 Sidebar

```css
.side{
  position:sticky; top:0; height:100vh;
  background:var(--side-bg);
  border-right:1px solid var(--hairline);
  display:flex; flex-direction:column;
  padding:var(--sp-4) var(--sp-3); gap:2px;
  overflow-y:auto; z-index:50;
}
.side-item{
  display:flex; align-items:center; gap:10px;
  padding:9px var(--sp-3);
  border-radius:var(--r-input);
  color:var(--ink-48);
  font-family:'Inter',sans-serif; font-size:13.5px; font-weight:500;
  transition:var(--ease);
}
.side-item:hover{ background:var(--divider); color:var(--ink); }
.side-item.on{ background:var(--side-active); color:var(--rhode-red); font-weight:600; }
.side-sec{
  font-family:'JetBrains Mono',monospace;
  font-size:10px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--ink-48); padding:var(--sp-4) var(--sp-3) var(--sp-1);
}
```

### 6.3 Topbar

```css
.topbar{
  position:sticky; top:0; z-index:40;
  height:56px;
  display:flex; align-items:center; justify-content:space-between;
  padding:0 var(--sp-6);
  background:var(--parchment);
  border-bottom:1px solid var(--hairline);
  backdrop-filter:saturate(180%) blur(20px);
}
.crumbs{ font-size:13px; color:var(--ink-48); }
.crumbs b{ color:var(--ink); font-weight:600; }
.theme-toggle{
  width:34px; height:34px; border-radius:var(--r-pill);
  background:var(--card); border:1px solid var(--hairline);
}
:root[data-theme="dark"] .theme-toggle::before{ content:'☀'; }
:root:not([data-theme="dark"]) .theme-toggle::before{ content:'☾'; }
```

O `pbar-wrap` (filtro de período) fica **sticky abaixo do topbar** (`top:56px`) — ao rolar o content, o filtro permanece visível junto com o topbar.

### 6.4 Responsivo (mobile off-canvas)

```css
@media(max-width:900px){
  .app{ grid-template-columns:1fr; }              /* single column */
  .side{
    position:fixed; left:-100%; top:0;
    height:100vh; width:var(--side-w);
    box-shadow:var(--shadow-md);
    transition:left .2s; z-index:55;
  }
  .side.open{ left:0; }
  .side-open-btn{ display:inline-flex; }           /* hamburger visível */
}
```

Handlers JS: `openSide()` adiciona `.open` na sidebar e `.on` no backdrop; `closeSide()` remove. `closeSide()` também é chamado dentro de `tab()` — quando o usuário navega no mobile, a sidebar fecha sozinha.

---

## 7. Tema dark/light

### 7.1 Aplicação anti-FOUC

Um `<script>` inline no `<head>` — antes de qualquer CSS/render — aplica o tema:

```html
<script>
(function(){
  try { var t = localStorage.getItem('rhode-theme') || 'dark';
        document.documentElement.setAttribute('data-theme', t); }
  catch(e) { document.documentElement.setAttribute('data-theme', 'dark'); }
})();
</script>
```

Isso **evita o flash branco** que acontece quando o browser renderiza claro por 100ms antes do CSS de dark aplicar.

### 7.2 Toggle

```js
function toggleTheme(){
  const cur = document.documentElement.getAttribute('data-theme')==='dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', cur);
  try { localStorage.setItem('rhode-theme', cur); } catch(e) {}
}
```

O ícone (`☀`/`☾`) é aplicado via CSS `::before` no `.theme-toggle`, condicional ao `[data-theme]`.

### 7.3 Padrão pra novos elementos

- **Sempre use var()** — `background:var(--canvas)`, `color:var(--ink)`, `border-color:var(--hairline)`.
- **Cores semânticas via token**: `var(--rhode-red)` (down/erro), `var(--green)` (up), `var(--gold)`/`var(--orange)` (atenção).
- **Se herdar CSS legado com hex fixo** (`#fff`, `#000`, `rgba(0,0,0,.06)`) — adicione um bloco `:root[data-theme="dark"] .seu-seletor { ... }` para sobrescrever. Ver bloco de overrides do `#sd-root` como exemplo (linhas 82-110 do admin.html).

---

## 8. Sistema de navegação — `tab(id, elBtn)`

Ponto sensível: **existem duas definições** de `tab()` no arquivo:
1. Linha 1990 — versão base (redirect pra render de ranking/alertas/evolução).
2. Linha 3207 — versão redefinida com renders adicionais (`renderAnalista`, `loadComunicacaoInit`, `loadComportamento`, `loadTriagem`, `startVIPRefresh`). Por JS hoisting, **essa segunda ganha**.

A `tab()` da linha 3207 foi patchada durante o redesenho pra sincronizar a sidebar:

```js
function tab(id, elBtn){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));
  document.querySelectorAll('.side-item[data-sid]').forEach(t=>t.classList.remove('on'));
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('on'));

  const sideBtn = document.querySelector(`.side-item[data-sid="${id}"]`);
  if (sideBtn) sideBtn.classList.add('on');
  const tabBtn = document.querySelector(`.tab[onclick*="'${id}'"]`);
  if (tabBtn) tabBtn.classList.add('on');
  el(`panel-${id}`).classList.add('on');

  const crumb = el('crumbActive');
  if (crumb) crumb.textContent = TAB_LABELS[id] || id;
  closeSide();

  if (id==='ranking') renderRankingPage(1);
  else if (id==='alertas') renderAlertas();
  else if (id==='evolucao') renderEvolucao();
  else if (id==='analista') renderAnalista();
  // ... loads condicionais por painel
}
```

**Bug já resolvido**: antes o reset só removia `.tab.on` (não `.side-item.on`), o que fazia os cliques **acumularem** items ativos na sidebar. Fix: adicionar o `forEach(t=>t.classList.remove('on'))` sobre `.side-item[data-sid]`.

**Se adicionar uma aba nova**:
1. Novo item na sidebar: `<button class="side-item" data-sid="XXX" onclick="tab('XXX',this)"><span class="side-ico">◆</span> Nome</button>`
2. Novo `.tab` (invisível) no `.tabs-nav`: `<button class="tab" onclick="tab('XXX',this)">Nome</button>`
3. Novo `<div class="panel" id="panel-XXX">…</div>`
4. Adicionar `XXX: 'Nome'` em `TAB_LABELS` (pra crumb funcionar).
5. Se precisa de render lazy, adicionar `else if (id==='XXX') renderXXX();` na `tab()`.

---

## 9. Componentes de conteúdo

### 9.1 Cards de KPI (padrão do painel)

```html
<div class="kgrid">
  <div class="kcard">
    <div class="klabel">GMV LÍQUIDO</div>
    <div class="kval">R$ 484K</div>
    <div class="ksub">margem 55% − com. − custo</div>
    <div class="kdelta up">↑ 12.3%</div>
  </div>
</div>
```

```css
.kgrid{ display:grid; grid-template-columns:repeat(6,1fr); gap:12px; margin-bottom:24px; }
.kcard{
  background:var(--canvas);
  border:1px solid rgba(0,0,0,0.05);
  border-radius:14px; padding:20px;
}
.klabel{
  font-family:'JetBrains Mono',monospace;
  font-size:10px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--ink-48); font-weight:500;
}
.kval{ font-size:30px; font-weight:700; letter-spacing:-.022em; }
.kdelta.up{ color:var(--green); }
.kdelta.dn{ color:var(--rhode-red); }
```

### 9.2 Cards do painel Seeding (`#sd-root .sd-kc`)

CSS escopado com prefixo `.sd-` (o painel Seeding é o padrão de referência mencionado na skill `/ui` — filtros temporais + lentes de ação + tabela densa).

```css
#sd-root .sd-kpis{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr));
  gap:12px;
}
#sd-root .sd-kc{
  background:#fff; border:1px solid var(--hairline);
  border-radius:14px; padding:18px 20px;
  display:flex; flex-direction:column; gap:6px;
  overflow:hidden;
}
#sd-root .sd-kc .l{
  font-size:10.5px; letter-spacing:.14em; text-transform:uppercase;
  color:var(--ink-48); font-weight:500;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;   /* não estoura */
}
#sd-root .sd-kc .v{
  font-size:26px; font-weight:700; letter-spacing:-.02em;
  font-variant-numeric:tabular-nums;
}
#sd-root .sd-kc .s{ /* subtitle */
  font-size:11px; color:var(--ink-48);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
}
#sd-root .sd-kc.alert{ border-color:#f3d3a0; background:#fffaf2; }  /* precisam de ação */
#sd-root .sd-kc.good .v{ color:#0a8a4f; }                            /* KPI positivo */
```

Como esse painel tinha muito `background:#fff` hardcoded, adicionei bloco grande de dark overrides (`admin.html` linhas 82-110). **Ao criar novo painel escopado, prefira usar `var(--canvas)` desde o início pra não precisar de overrides depois.**

### 9.3 Barra de filtros temporais (regra firme — `feedback_sempre_filtros_temporais`)

Sempre presente no topo do painel. Componentes:

- **Janela** (pills `.pbtn`): Tudo / 30d / 60d / 90d
- **Mês** (`<select>`)
- **Data** (`<input type="date">` de → até)
- **vs anterior** (checkbox `.prange-toggle`)

```html
<div class="pbar-wrap">
  <span class="pbar-label">Período</span>
  <div class="prange">
    <select id="prange-bucket" class="prange-select" onchange="onRangeChange()">
      <option value="mes_atual">Mês atual</option>
      <option value="mes_anterior">Mês anterior</option>
      <option value="last_3m">Últimos 3 meses</option>
      <option value="last_6m">Últimos 6 meses</option>
      <option value="ytd">YTD</option>
      <option value="custom">Personalizado…</option>
    </select>
    <div class="prange-custom" style="display:none">
      <select class="prange-from"></select>
      <span class="prange-sep">→</span>
      <select class="prange-to"></select>
    </div>
  </div>
  <label class="prange-toggle">
    <input type="checkbox" id="prange-compare" onchange="onCompareToggle()"> vs anterior
  </label>
</div>
```

### 9.4 Tabela densa

```css
.tbl{
  background:var(--canvas);
  border:1px solid var(--hairline);
  border-radius:var(--r-card);
  overflow:hidden;
}
.tbl th{
  font-family:'JetBrains Mono',monospace;
  font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--ink-48); font-weight:500;
  padding:12px 16px; text-align:left;
  border-bottom:1px solid var(--divider);
  position:sticky; top:0; background:var(--canvas);      /* sticky header */
}
.tbl td.num{ text-align:right; font-variant-numeric:tabular-nums; }
.tbl tr:hover td{ background:var(--pearl); }
```

Regras firmes:
- Números à direita com `tabular-nums`.
- Ordenação decrescente por padrão.
- Colunas completas (nada faltando "pra depois").
- Header sticky.

---

## 10. Estados obrigatórios (checklist antes de fechar tela)

Toda tela/componente **precisa ter**:

- [ ] **Hover** — feedback visual em `.side-item`, `.pbtn`, `.tab`, botões (`transition:.15s`).
- [ ] **Focus-visible** — ring vermelho (`:focus-visible { box-shadow:var(--focus); }`).
- [ ] **Disabled** — `opacity:.4; cursor:not-allowed`.
- [ ] **Loading** — skeleton com `--surface-2` pulsando, sem layout shift.
- [ ] **Empty** — mensagem clara ("Sem dado no período", "Nenhum resultado" — nunca área branca muda).
- [ ] **Erro** — texto em `--rhode-red`, mono 11px.

---

## 11. Fluxo de dados (autenticação & chamadas)

### 11.1 Login

```js
async function admLogin(){
  const pass = document.getElementById('adm-pass').value;
  const r = await fetch('/api/get-hub', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ action:'admin_login', pass })
  });
  const d = await r.json();
  if (r.ok && d.token) {
    sessionStorage.setItem(ADM_TOKEN_KEY, d.token);
    enter();                       // esconde login, mostra #adm-app
  }
}
```

O `ADMIN_PASS` fica em env server-side. O `ADMIN_TOKEN` volta cifrado do server e é usado como bearer nas queries via `admProxy`.

### 11.2 Query autenticada

```js
async function admProxy(method, path, body, prefer, paged){
  const r = await fetch('/api/get-hub', {
    method:'POST',
    body: JSON.stringify({
      action:'admin_query', adminToken: admToken(),
      method, path, body, prefer, paged
    })
  });
  if (r.status === 401) { admLogout(); throw new Error('sessão expirada'); }
  return r.json();
}
```

O `/api/get-hub` faz proxy pra PostgREST do Supabase usando `service_role` (só o server tem a chave). Isso mantém a UI simples (sem RLS complexa no client) e o dado seguro.

---

## 12. Deploy & operação

### 12.1 Vercel

- Projeto: `rhode-vercel`
- Comando: `npx vercel --prod --yes --cwd rhode-vercel`
- Push em `main` também dispara deploy (integração com GitHub).
- **Limite Vercel Hobby: 12 Serverless Functions** — não criar rota nova sem consultar `reference_vercel_12_funcoes`.

### 12.2 Validação visual

O dono é perfeccionista (`feedback_perfeccionista_iterar`) — valide visualmente desde a v1. Use Playwright pra tirar screenshot pós-deploy:

```js
// scratchpad/check.mjs
import { chromium } from 'playwright';
const b = await chromium.launch();
const c = await b.newContext({ viewport:{ width:1440, height:900 } });
const p = await c.newPage();
await p.goto('https://creators.rhodejeans.com.br/admin.html');
// pra pular login sem senha:
await p.evaluate(() => {
  document.getElementById('adm-login').style.display='none';
  document.getElementById('adm-app').style.display='block';
});
await p.screenshot({ path:'admin.png' });
```

Introspecção pra debugar layout:
```js
const debug = await p.evaluate(() => {
  const app = document.querySelector('.app');
  const side = document.querySelector('.side');
  return {
    theme: document.documentElement.getAttribute('data-theme'),
    appCols: getComputedStyle(app).gridTemplateColumns,
    sideWidth: side.getBoundingClientRect().width,
  };
});
```

---

## 13. Histórico de decisões e bugs corrigidos

### 13.1 Bug: sidebar invertida no desktop

- **Sintoma**: sidebar (250px) aparecia à direita e content (250px) à esquerda em desktop; layout mobile ativo mesmo em 1440px.
- **Causa**: `.side-backdrop{display:none}` estava dentro de `@media(max-width:900px)`. No desktop o div ficava `display:block` (default do `<div>`) e ocupava a coluna 1 do grid.
- **Fix**: mover `.side-backdrop{display:none}` pra fora do media query (regra global).

### 13.2 Bug: múltiplos items ativos na sidebar

- **Sintoma**: cada click acumulava `.on` — Dashboard + Ranking + Alertas todos vermelhos.
- **Causa**: duas definições de `function tab()` no arquivo (linhas 1990 e 3207); a segunda (por hoisting JS) ganhava e só removia `.tab.on`, não sabia da sidebar.
- **Fix**: adicionar `document.querySelectorAll('.side-item[data-sid]').forEach(t=>t.classList.remove('on'))` na `tab()` da linha 3207.

### 13.3 Bug: painel Seeding com fundo branco no dark

- **Sintoma**: cards KPI, filtros, tabela do `#sd-root` renderizavam brancos em tema dark, quebrando contraste.
- **Causa**: CSS escopado do `#sd-root` (linhas 1071-1112) usa `background:#fff` hardcoded.
- **Fix**: bloco de overrides `[data-theme="dark"] #sd-root .* { !important }` (admin.html linhas 82-110). Semânticas dos segments (ativar/reativar/vendeubem/etc) usam tokens dark com `opacity:.14-.22` pra manter legibilidade.

### 13.4 Bug: `.main` com espaço morto em telas grandes

- **Sintoma**: em 1920px, sidebar 250px + `.main{max-width:1400px; margin:0 auto}` deixava ~135px de espaço vazio em cada lado.
- **Fix**: `.main{max-width:none; padding:32px 32px 80px}` + `@media(min-width:1600px){ .main{ padding:32px 48px 80px } }`.

### 13.5 Card "Precisam de ação" mal-formatado

- **Sintoma**: subtítulo `ativar+reativar+aguard.+cancel.` estourava do card, layout confuso.
- **Fix**:
  - `.sd-kc{ display:flex; flex-direction:column; gap:6px; overflow:hidden }` — hierarquia coesa.
  - `.sd-kc .l/.s{ white-space:nowrap; overflow:hidden; text-overflow:ellipsis }` — texto longo corta com `…`.
  - Subtitle encurtado no JS pra `ativar · reativar · aguard.`.
  - Grid do container: `grid-template-columns:repeat(auto-fit,minmax(180px,1fr))` — respiro consistente.

---

## 14. Manutenção futura

### 14.1 Fase 2 — migrar as outras telas internas

- **`dash-live.html`** — ainda com layout antigo. Aplicar a mesma cirurgia:
  1. `<script>` inline setando `data-theme` no `<head>`.
  2. Injetar tokens v2 no `:root` (mesmo bloco da seção 3.1).
  3. Adicionar `:root[data-theme="dark"] { ... }` sobrescrevendo canvas/parchment/etc.
  4. Trocar `#app` (ou equivalente) pelo shell (`<div class="app"><aside class="side">...</aside><main class="content">…</main></div>`).
  5. Marcar `Dashboard Lives` como `.on` na sidebar; outros items são links.
  6. Adicionar `toggleTheme/openSide/closeSide/admLogout`.
- **`bio-admin.html`** — mesma coisa, marcar `Bio Rhode` como `.on`.

Depois disso, considerar extrair o shell em um `_console-shell.html` incluído via SSI/build (ou inline via script). Mas primeiro validar 3-4 telas manualmente.

### 14.2 Ideias de refino (não urgentes)

- **Deep-link por URL**: `/admin.html#ranking` já abrir na aba certa (hoje precisa clicar).
- **Sidebar colapsável**: ícone-only quando `--side-w:64px` (mais espaço pra tabelas).
- **Search global**: `Cmd+K` que filtra items da sidebar + creators/pedidos.
- **Preferência de tema por dispositivo**: `matchMedia('(prefers-color-scheme:dark)')` como fallback antes de default hard.

### 14.3 Como remover uma aba com segurança

Passos (exemplo: remover `Evento 13/04`, feito em 2026-07-15):

1. Remover `<button class="side-item" data-sid="evento" ...>` da sidebar.
2. Remover `<button class="tab" onclick="tab('evento',this)">` da `.tabs-nav`.
3. Opcional: deletar `<div class="panel" id="panel-evento">…</div>` e código relacionado (`loadEvento`, `startVIPRefresh`, `TAB_LABELS.evento`).

O painel fica órfão sem entrada de navegação — não quebra nada, só ocupa peso morto no HTML até a limpeza completa.

---

## 15. Referências cruzadas

- [`.claude/skills/ui/SKILL.md`](../.claude/skills/ui/SKILL.md) — guia canônico do redesenho
- [`.claude/skills/ui/references/tokens.css`](../.claude/skills/ui/references/tokens.css) — fonte da verdade dos tokens v2
- [`.claude/skills/ui/references/componentes.md`](../.claude/skills/ui/references/componentes.md) — receitas de shell/KPI/tabela
- [`.claude/skills/ui/references/checklist.md`](../.claude/skills/ui/references/checklist.md) — checklist de qualidade
- Protótipo aprovado (13/07): `https://claude.ai/code/artifact/252e03ac-1111-4203-8a33-b198b0817b6f`
- Memory: `project_ui_redesign_direction`, `reference_ui_prototipo_console`, `feedback_sempre_filtros_temporais`, `feedback_dominios_rhode`, `feedback_perfeccionista_iterar`, `reference_vercel_12_funcoes`
