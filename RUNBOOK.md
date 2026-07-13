# Rhode Hub — Runbook de Debug

> **Como usar:** quando algo quebra em produção, leia daqui. Cada cenário tem sintoma → diagnóstico em ordem → fix conhecido. Sem necessidade de "puxar contexto" do nada.
>
> **Última atualização:** 2026-05-02

---

## 🚨 "Algo está errado e eu não sei o quê"

**Bateria de sanity checks (rodar nessa ordem):**

```bash
# 1. ETL/dados batem com exports?
cd "/Users/user/Documents/VS Claude Teste"
python3 audit_data.py

# 2. Último deploy está saudável?
cd rhode-vercel
npx vercel ls | head -3
# (verifica se há deploy READY recente)

# 3. APIs respondem?
curl -sI https://creators.rhodejeans.com.br/hub.html | head -1   # 200 OK?
curl -sI https://creators.rhodejeans.com.br/admin.html | head -1 # 200 OK?

# 4. Supabase responde e tem dados?
curl -sI "https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1/performance_periods?select=periodo&limit=1" \
  -H "apikey: $SB_KEY" -H "Prefer: count=exact" | grep -i content-range
# Esperado: content-range: 0-0/6870

# 5. Último ETL run no GitHub
gh run list --workflow=etl_sync.yml --limit 3   # (se gh CLI disponível)
# OU verifica em github.com/Ba44o/git-remote--v/actions
```

Se algum falhar → ir para o cenário específico abaixo.

---

## 1. Dados do admin/hub estão errados

### Sintomas comuns
- "Top creator de abril com R$ 325" (real é R$ 132k)
- "GMV total muito menor que o esperado"
- "Mirella aparecendo com gmv_liquido negativo"
- "Creators que não existem mais aparecendo"

### Diagnóstico

```bash
# Audit completo
python3 audit_data.py

# Audit só do período suspeito
python3 audit_data.py --periodo 2026-04
```

**O que olhar no output:**
- `Faltando` > 0 → creators no export mas não no Supabase (sync não rodou ou falhou)
- `Extra` > 0 → creators no Supabase mas não no export (fantasmas — DELETE não rodou)
- `Divergentes` > 0 → valores numéricos diferentes (bug no parsing ou no sync)

### Fixes conhecidos

**Caso A — TikTok renomeou um header.** Sintoma: `gmv_bruto = 0` em massa.
1. Ler headers do export mais recente:
   ```bash
   python3 -c "
   import openpyxl
   wb=openpyxl.load_workbook('dados/creators/exports/[FILENAME].xlsx', read_only=True)
   ws=wb.active
   for c in range(1,ws.max_column+1): print(c, repr(ws.cell(1,c).value))
   "
   ```
2. Comparar com `COLUMN_ALIASES` em `agente_rhode/etl_v2.py`
3. Adicionar o novo nome normalizado ao dict (ver exemplo "ao criador" vs "a afiliados")
4. Reprocessar:
   ```bash
   rm warehouse/raw_imports.csv
   python3 agente_rhode/etl_v2.py --dir dados/creators/exports
   SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python3 agente_rhode/sync_supabase.py
   ```

**Caso B — Múltiplos snapshots do mesmo mês.** Sintoma: linhas duplicadas, contagem maior do que o export.
- O `pick_canonical_per_period` em `etl_v2.py` deveria filtrar. Se não filtrou:
- Verificar se o nome do arquivo tem padrão `YYYYMMDD-YYYYMMDD` (regex em `detect_period`)
- Forçar reprocessamento limpo: `rm warehouse/raw_imports.csv && python3 agente_rhode/etl_v2.py ...`

**Caso C — Creators fantasma.** Sintoma: audit reporta "Extra" > 0.
- Causa: `sync_supabase.py` está fazendo upsert sem delete prévio (regressão).
- Verificar se a função `sync_performance_periods` tem o bloco `# DELETE-then-UPSERT por período`
- Se sumiu, restaurar do git e rerodar sync.

**Caso D — Admin trunca em 1000.** Sintoma: contagens batem com `min(real, 1000)`.
- Verificar se `admin.html` usa `sbGetPaged()` em vez de `sbGet()` direto
- `grep -n "sbGetPaged\|sbGet(" rhode-vercel/public/admin.html`

---

## 1b. Hub aparece com dados da Taci pra outra pessoa

### Sintoma
- "Abri /hub.html e parece a tela da Taci"
- Hub boota com nome/dados da Taci mesmo a creator não sendo ela

### Causa
- Visita anterior a `?demo=tour` OU ao preview link `?token=TACI-PREVIEW-2026`
  gravou esse token em `localStorage.rhode_creator_token`
- Próximas visitas a /hub.html sem query string puxam o token cacheado
- `validateToken('TACI-PREVIEW-2026')` retorna o row da Taci (é token real
  no Supabase), então o hub boota como Taci

### Fix (já aplicado em 2026-05-14, commit 025ec80)
- `readToken()` em hub.html sanitiza: se o localStorage tem token que casa
  `^TACI-PREVIEW`, limpa e retorna null (força ir pra /acesso.html)
- `?demo=tour` agora usa `removeItem(TOKEN_KEY)` em vez de `setItem`

### Se voltar a acontecer
- Confirmar que [hub.html:1994-2009](rhode-vercel/public/hub.html#L1994-L2009) ainda tem o `PREVIEW_TOKEN_RE` e o branch que limpa
- Verificar se algum outro endpoint está gravando `rhode_creator_token` direto sem ir pelo `readToken`
- Pra mitigação imediata da creator afetada: pedir pra abrir devtools → Application → Local Storage → limpar `rhode_creator_token`. Ou abrir em aba anônima.

---

## 2. Creator não consegue acessar o hub

### Sintomas
- "@nataliacosta digitou o @ e diz 'handle não encontrado'"
- "PIN dela não funciona"
- "Diz que está bloqueada"

### Diagnóstico

```bash
# Existe na base?
SB_KEY="..."
curl -s "https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1/affiliates?or=(affiliate_id.ilike.NATALIACOSTA,tiktok_handle.ilike.NATALIACOSTA)&limit=2" \
  -H "apikey: $SB_KEY" | python3 -m json.tool

# Existe em eventos_creators (alternativa)?
curl -s "https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1/eventos_creators?handle=ilike.NATALIACOSTA&limit=2" \
  -H "apikey: $SB_KEY" | python3 -m json.tool
```

### Fixes

**Caso A — Não existe em nenhuma tabela.**
- Creator não foi importada ainda. Soluções:
  1. Adicionar manualmente em `affiliates` (com handle + phone se conhecido)
  2. Esperar próximo ETL se ela já está vendendo no TikTok
  3. Se for caso de erro no TikTok ou afiliada antiga, pedir info pra Rhode

**Caso B — Existe mas sem `phone`.**
- O fluxo de auto-cadastro de phone deveria cobrir. Se ela diz que dá erro:
- Verificar se `acesso.html` tem o `submitFirstAccess()` (não `submitWpp+submitCreate` separados)
- Confirmar que `get-hub.js` tem o bloco `if (!storedW) { sbPatch(...) }`

**Caso C — PIN não funciona (existe pin_acesso, mas dela não bate).**
- Resetar para ela criar de novo:
  ```bash
  curl -X PATCH "https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1/affiliates?affiliate_id=eq.NATALIACOSTA" \
    -H "apikey: $SB_SVC_KEY" -H "Authorization: Bearer $SB_SVC_KEY" \
    -H "Content-Type: application/json" -H "Prefer: return=minimal" \
    -d '{"pin_acesso": null, "access_token": null}'
  ```
- Ela faz primeiro acesso de novo.

**Caso D — Bloqueada pelo rate limit local.**
- Pedir pra ela limpar localStorage do navegador OU abrir em aba anônima
- Limit é 5 tentativas / 5min por handle

---

## 3. Disparo Z-API não chegou na creator

### Diagnóstico

```bash
# Phone formatado certo?
echo "11999998888" | python3 -c "
import sys
p = ''.join(c for c in sys.stdin.read().strip() if c.isdigit())
print('Esperado: 55 + DDD + 9 + número (12-13 dígitos)')
print(f'Phone: {p} ({len(p)} dígitos)')
print(f'Com 55: {p if p.startswith(\"55\") else \"55\"+p}')
"

# Z-API conectado?
curl -s "https://api.z-api.io/instances/3F173410FA03D317C69AAAE399BC1248/token/23F1D0021AF2CC2A39C7AFE3/connection-status" \
  -H "Client-Token: F92b6dc75c19f490188eea81fcc29b6aaS"
# Esperado: { "connected": true }
```

### Fixes

**Caso A — Z-API desconectado.**
- Re-escanear QR no painel do Z-API (z-api.io)

**Caso B — Phone mal formatado.**
- `disparar_hub.py` faz normalize. Verificar se o phone na base tem 55 prefix ou não
- Padrão correto: `5511999998888` (13 dígitos)

**Caso C — Mensagem entregue mas creator diz que não recebeu.**
- Verificar no Z-API dashboard se mensagem foi marcada como `delivered` / `read`
- Pode ter caído no spam do WhatsApp se conta Z-API for nova

**Caso D — Disparo segmentado (admin → Comunicação) volta com 0 alvos.**
- `affiliates.phone` é **sempre NULL** — nunca foi populada. Não filtre por ela.
- A fonte de phone é `eventos_creators.whatsapp` (tabela compartilhada por evento + cadastro.html + acesso.html).
- Validar:
  ```bash
  curl -s "https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1/eventos_creators?select=count&whatsapp=not.is.null" \
    -H "apikey: <SB_ANON>" -H "Prefer: count=exact" -I | grep content-range
  # Esperado: content-range: 0-0/N (onde N ~= 200 mai/2026)
  ```
- Se o N estiver caindo: `cadastro.html` pode estar quebrado no front (POST falhando) ou validação de schema rejeitando inserts.

---

## 4. Hub mostra GMV diferente do que a creator vê no painel TikTok

### Diagnóstico

```bash
# 1. Audit interno bate?
python3 audit_data.py --periodo 2026-04

# 2. Quando foi o último export baixado?
ls -lt dados/creators/exports/Transaction_Analysis_Creator_List_*.xlsx | head -3

# 3. TikTok faz updates retroativos?
# Pode ter pedido cancelado depois do export. Confirmar baixando NOVO export e rodando ETL.
```

### Fixes

**Caso A — Audit interno está limpo.** Significa: o export que baixamos bate com nosso DB. Se o painel da TikTok mostra outro número, é porque o TikTok atualizou retroativamente desde o último export.
- Solução: baixar export novo + commit + push (GitHub Actions roda ETL automático)

**Caso B — Audit reporta divergência.** Ver Cenário 1 acima.

---

## 5a. Painel mostra dados antigos mesmo após sync rodar

### Sintoma
- ETL rodou, Supabase tem dados novos (audit confirma)
- Mas admin/hub no navegador mostra dados antigos

### Diagnóstico

```bash
# Hash do servido vs local
curl -s "https://creators.rhodejeans.com.br/admin.html" | shasum | cut -c1-12
shasum "/Users/user/Documents/VS Claude Teste/rhode-vercel/public/admin.html" | cut -c1-12
# Iguais → deploy OK, é cache do browser
# Diferentes → deploy não propagou ou rollback automático

# Headers de cache
curl -sI "https://creators.rhodejeans.com.br/admin.html" | grep -iE "cache-control|age|x-vercel-cache"
# Se "x-vercel-cache: HIT" e "age" > 60 → CDN está servindo antigo
```

### Fixes

**Caso A — Hashes batem, problema é cache do browser.**
- Pedir hard refresh (Cmd+Shift+R / Ctrl+Shift+R)
- Ou aba anônima

**Caso B — CDN está cacheando agressivamente.**
- Verificar `vercel.json` tem o header `Cache-Control: no-cache, no-store, must-revalidate` para arquivos HTML
- Se faltar, adicionar:
  ```json
  "headers": [
    {
      "source": "/(admin|hub|acesso|cadastro|index)\\.html",
      "headers": [
        { "key": "Cache-Control", "value": "no-cache, no-store, must-revalidate" }
      ]
    }
  ]
  ```
- Deploy novo (`npx vercel --prod`) — o header só ativa em deploy novo

---

## 5. Deploy quebrou / página em branco

### Diagnóstico

```bash
cd rhode-vercel

# Logs do último deploy
npx vercel logs --output raw | head -50

# Está apontando pro deploy certo?
npx vercel ls | head -5

# Console do navegador: erro de JS?
# (DevTools → Console)
```

### Fixes

**Caso A — JS error em runtime.**
- Geralmente é uma variable não definida ou função inexistente
- Ler erro do console, identificar arquivo+linha
- Fix local + `npx vercel --prod`

**Caso B — Deploy falhou no build.**
- `npx vercel logs` mostra erro
- Geralmente é typo no `vercel.json` ou path errado em `functions:`

**Caso C — Rollback urgente.**
```bash
# Lista deploys recentes
npx vercel ls

# Promove um deploy específico
npx vercel promote <deployment-url>
```

---

## 6. ETL falhou no GitHub Actions

### Diagnóstico

1. Abrir `github.com/Ba44o/git-remote--v/actions`
2. Clicar no run que falhou
3. Olhar a step que deu vermelho

### Fixes por step

**`Rodar ETL v2` falhou:**
- Geralmente é o sanity check abortando — quer dizer `gmv_bruto = 0` em massa
- Caso A do Cenário 1 (TikTok renomeou header)

**`Sincronizar com Supabase` falhou:**
- Verificar `SUPABASE_URL` e `SUPABASE_SERVICE_KEY` nas secrets do GitHub
- Se expirou: regenerar no Supabase dashboard e atualizar secret

**`Setup credentials` falhou:**
- `GCP_CREDENTIALS` secret expirou ou está malformatada
- Regenerar service account JSON no GCP e atualizar secret

---

## 7. Tier de uma creator está errado

### Diagnóstico

```bash
SB_KEY="..."

# GMV acumulado lifetime
curl -s "https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1/performance_periods?affiliate_id=eq.PSI.MIRELLARODRIGUES&select=periodo,gmv_liquido&order=periodo.asc" \
  -H "apikey: $SB_KEY" | python3 -c "
import sys,json
rows=json.loads(sys.stdin.read())
total=sum(float(r['gmv_liquido'] or 0) for r in rows)
print(f'GMV acumulado: R\$ {total:,.2f}')
print('Tier esperado:')
if total >= 500_000: print('  Black')
elif total >= 150_000: print('  Diamond')
elif total >= 80_000: print('  Gold')
elif total >= 50_000: print('  Silver')
elif total >= 20_000: print('  Bronze')
else: print('  Iniciante')
"
```

### Fixes

**Caso A — Cálculo bate, hub mostra outro tier.**
- Cache do navegador. Pedir Cmd+Shift+R
- Verificar se `TIERS` em `hub.html` ainda é Bronze 20k / Silver 50k / Gold 80k / Diamond 150k / Black 500k

**Caso B — Cálculo no Supabase não bate com a expectativa.**
- Algum período pode estar vazio ou com dados errados → ver Cenário 1

---

## 8. Cron Vercel não rodou

### Cron jobs ativos

Conferir em `vercel.json`:
```
- cron-recovery (3x: 14/04 15h, 15/04 15h)
- cron-reminder (6x: 13/04 15h/17h/19h/21h, 14/04 15h/19h)
- cron-tier-milestones (diário 12h UTC)
```

### Diagnóstico

```bash
cd rhode-vercel
npx vercel inspect <production-url> | grep -i cron
# OU dashboard.vercel.com → projeto → Cron Jobs
```

### Fixes

**Caso A — Cron não está aparecendo no dashboard.**
- Push novo deploy. Crons só são registrados em deploys novos
- Verificar `vercel.json` está válido (`npx vercel build --debug`)

**Caso B — Cron rodou mas API retornou erro.**
- Logs em `dashboard.vercel.com → projeto → Logs → [função do cron]`
- Geralmente é env var faltando ou Supabase indisponível

---

## 9. Hub: hero aparece mas o detalhe abaixo dá "ERRO AO CARREGAR"

### Sintoma
O topo do Painel (GMV/tier no hero) renderiza, mas a seção `#perf-main` logo
abaixo mostra "ERRO AO CARREGAR / Tente recarregar a página". Pode afetar TODA
creator com dados (não só uma).

### Causa
`loadPerf()` tem um `try/catch` que envolve hero + render + chamadas auxiliares
(`renderPerf`, `loadLeaderboard`, `loadTarefasRhode`, `loadFlashSales`). O hero
é renderizado ANTES; se QUALQUER linha depois lançar, o catch sobrescreve o
`#perf-main` com "ERRO AO CARREGAR". Como o catch era silencioso, o erro real
ficava escondido. **Já aconteceu (jun/2026):** `loadTarefasRhode(affId)` com
`affId` indefinido (removido numa migração pro proxy) → `ReferenceError`. Fix:
commit que removeu o arg morto + `console.error` no catch.

### Diagnóstico
```
# 1. Abre o hub com um token e olha o CONSOLE do browser (F12) — agora o catch loga "loadPerf falhou: ..."
# 2. Reproduz local sem deploy:
cd rhode-vercel && vercel dev --listen 3010
# Playwright: carrega hub.html?token=TACI-PREVIEW-2026 e checa textContent('#perf-main') NÃO contém "ERRO AO CARREGAR"
```

### Fix conhecido
- Achar a linha que lança dentro do `try` do `loadPerf` (variável indefinida,
  função renomeada, shape de dado). Corrigir.
- **Lição:** smoke test do hub tem que checar o conteúdo do `#perf-main`, não só
  o hero (que renderiza antes do erro). E nunca deixar catch silencioso —
  sempre `console.error(e)`.

---

## 10. Hub: painel mostra "Mês atual · 05/26" (mês anterior rotulado como atual)

### Sintoma
No início de um mês novo, a creator abre o painel e vê o **mês anterior**
rotulado como "Mês atual" (ex: dia 9 de junho mostrando "05/26"). Parece que
"a API parou de atualizar".

### Causa
**Não é a API.** O `getFilteredView()` do filtro `month` pegava `_perfHistory[0]`
(o último período **com dados**) e o rotulava "Mês atual". Quem ainda não vendeu
no mês corrente não tem linha do mês → cai no mês anterior. No dia 9, ~960 de
~1000 creators estão nessa situação (normal — nem todas venderam ainda).

### Diagnóstico (descartar antes de "consertar a coleta")
1. **Cron rodou?** API pública: `/repos/Ba44o/git-remote--v/actions/workflows/{id}/runs`
   (workflow `daily-collect.yml`). Event `schedule` + success = ok. GitHub atrasa 2-3h.
2. **Banco tem o mês?** `performance_periods?periodo=eq.AAAA-MM&order=gmv_bruto.desc`
   — top creators presentes? Se sim, dado existe.
3. **Proxy devolve?** `curl -X POST .../api/get-hub -d '{"token":"...","action":"perf"}'`
   — o 1º período da lista é o mês corrente? Se sim, é **cache do navegador**
   (Cmd+Shift+R) ou a creator simplesmente não vendeu no mês (estado-zero, correto).

### Fix conhecido
- Frontend já corrigido: `month` ancorado em `currentMonthStr()` (mês do
  calendário). Sem linha do mês → estado-zero honesto ("ainda não registrou
  vendas em Junho/2026"), deltas −100% suprimidos, histórico/comissões intactos.
- **Lição:** "Mês atual" tem que significar o mês do **calendário**, não o último
  período com dados. Validar estado-zero com `validate-empty-month.js` (intercepta
  a resposta `perf` p/ simular creator sem venda no mês).

---

## 🛠️ Comandos úteis (cheatsheet)

```bash
# Audit completo
python3 audit_data.py

# Reprocessar ETL do zero (perde nada — exports são fonte)
rm warehouse/raw_imports.csv
python3 agente_rhode/etl_v2.py --dir dados/creators/exports

# Sync Supabase (após ETL)
SUPABASE_URL='https://ivzpykuluxcxefhyzfsf.supabase.co' \
SUPABASE_SERVICE_KEY='...' \
python3 agente_rhode/sync_supabase.py

# Deploy hub/admin
cd rhode-vercel && npx vercel --prod

# Disparar workflow manualmente no GitHub
# (Actions → ETL v2 → Run workflow)

# Resetar PIN de uma creator
curl -X PATCH "https://...supabase.co/rest/v1/affiliates?affiliate_id=eq.HANDLE" \
  -H "apikey: $SB_SVC_KEY" -H "Authorization: Bearer $SB_SVC_KEY" \
  -H "Content-Type: application/json" -H "Prefer: return=minimal" \
  -d '{"pin_acesso": null, "access_token": null}'
```

---

## 11. Cron do Relatório Mensal de Seeding falhou (dia 01)

### Sintoma
Dia 01 passou e as **abas de seeding do mês** (`AAAA-MM · Resumo/Detalhe/Itens/Segmentos` + linha
nova em `KPIs (histórico)`) não apareceram no Google Sheet do projeto (`1hiyu1y9…Lv0Mh0`). Workflow:
`.github/workflows/monthly-seeding-report.yml` (cron `0 12 1 * *` = 09h BRT). Passos: coleta via
`gerar_relatorio_seeding_mensal.py` (ROOT) → entrega via `sync_seeding_to_sheets.py` (ROOT).

### Rodar manualmente (a forma normal de recuperar)
1. GitHub → **Actions** → **"Rhode — Relatório mensal de Seeding (dia 01)"** → **Run workflow**.
2. Input `mes`: **deixe vazio** para o mês anterior a hoje, OU informe `AAAA-MM` (ex.: `2026-06`)
   para reprocessar um mês específico. É o `workflow_dispatch` com input `mes`.
3. Equivale a rodar localmente (coleta + entrega no Sheets):
   ```bash
   python gerar_relatorio_seeding_mensal.py --mes 2026-06     # coleta + monta .xlsx (mês explícito)
   python sync_seeding_to_sheets.py        --mes 2026-06      # entrega: escreve as abas no Sheet do projeto
   # sem --mes = mês anterior a hoje; --skip-collect no 1º reusa warehouse/*.csv (não rebusca API)
   ```

### Diagnóstico (onde olhar o log)
- Actions → run vermelho → abrir a step que falhou. Ordem dos passos internos do entrypoint:
  `renovar token TikTok` (best-effort) → `coletar sample_applications` → `coletar vendas (Affiliate Orders)` → build.

### Fixes por causa
**Token TikTok inválido/expirado** (passo de coleta retorna `code != 0`, ex. 105002/erro de auth):
- O `refresh_token` na tabela `api_tokens` (Supabase) pode ter expirado. Renovar: `python obter_token.py --refresh`
  local; se o refresh também expirou, refazer o fluxo de `auth_code` no browser (ver `obter_token.py`) e re-salvar.
- Confirmar secrets no repo: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `TIKTOK_APP_KEY`, `TIKTOK_APP_SECRET`,
  `TIKTOK_SHOP_CIPHER`. Sem eles o token não resolve (token_store lê `api_tokens` e cai pro env).

**`coletar sample_applications` abortou** ("Nenhum pedido de amostra retornado"):
- Token morto (acima), ou a API renomeou campos de `sample_applications`. Rodar o ETL isolado pra ver o erro:
  `python agente_rhode/etl_sample_applications.py`. **NÃO editar `agente_rhode/*.py` num commit avulso** — isso
  dispara o `etl_sync.yml` (reescreve `performance_periods` em prod). Só importa/executa.

**`coletar vendas (Affiliate Orders)` abortou** (`RuntimeError: affiliate_orders falhou na página N`):
- Timeout do servidor TikTok (code 36009007) estourou os 5 retries, ou token expirou. Reexecutar (o dispatch
  recolhe do zero). O CSV parcial NÃO é gravado se a coleta abortar (não gera dado inconsistente).

**Entrega no Google Sheets falhou** (passo "Entregar no Google Sheets do projeto"):
- `credentials.json` vazio/malformado → conferir o secret `GCP_CREDENTIALS` no repo (mesmo do `etl_sync.yml`).
- `403 ... storage quota exceeded` ao **criar** Sheet → o SA não tem cota; o script **reusa** o Sheet existente
  (`SPREADSHEET_ID` fixo em `sync_seeding_to_sheets.py`). Nunca usar `client.create`. Se o ID do Sheet mudar, atualizar a constante.
- `403`/`PermissionError` ao escrever → o SA `rhode-etl-936@creators-rhode.iam.gserviceaccount.com` perdeu acesso de Editor ao
  Sheet do projeto → recompartilhar. As abas de seeding são recriadas a cada run (idempotente; só tocam abas de seeding).

**Rodou mas conversão/GMV gerado ficou "sem dado":**
- Faltou `warehouse/raw_vendas_seeding_<AAAA-MM>.csv` (coleta de vendas falhou mas o build seguiu). Rodar
  `python coletar_vendas_seeding.py --mes AAAA-MM` e depois `--skip-collect` no entrypoint.
- ROI (lucro÷custo) é **sempre "sem dado"** de propósito enquanto não houver COGS/frete real — isso é esperado, não é bug.

**Números divergem levemente de uma execução pra outra no MESMO dia:**
- Esperado. A janela de atribuição termina em "hoje" e os pedidos de afiliada do dia ainda estão entrando →
  o `GMV gerado` cresce ao longo do dia. As contagens (enviadas/atingidas/conversão) são estáveis.

---

## 12. Creator VENDE mas não aparece no hub (nem no admin)

### Sintoma
- "A @fulana nem aparece no meu painel do hub" — mas ela está vendendo de verdade
  (você vê no TikTok / na conciliação / no seeding).

### Causa
O hub lê **`affiliates`** (identidade/login) + **`performance_periods`** (números).
Esses dois vêm do **Creator List export** (até maio) e do **forward-fill** da API
(`coletar_extrato.py`, jun+). Creator **100%-nova** (só começou a vender de junho pra
cá, nunca entrou num export) **não tem linha em `affiliates`**. O forward tinha uma
trava de FK (`performance_periods.affiliate_id → affiliates`) que **filtrava fora**
quem não estava em `affiliates` → invisível no hub. Ela existe só no pipeline da API
de afiliadas (`affiliate_perf` / `affiliate_creator_product`), que usa o **handle**
(ex.: `suzane.ganga`), não o id normalizado do export (ex.: `SUZANEDIAN`).

### Diagnóstico
```bash
SB="https://ivzpykuluxcxefhyzfsf.supabase.co"; K="<service_key do .env>"
H=(-H "apikey: $K" -H "Authorization: Bearer $K")   # SEM o Bearer, RLS devolve 0 linhas!
HANDLE="suzane.ganga"; ID=$(echo "$HANDLE" | tr a-z A-Z)
# Está na API (vende)?  → deve ter linhas
curl -s "$SB/rest/v1/affiliate_creator_product?creator=eq.$HANDLE&select=data,gmv,pedidos" "${H[@]}"
# Está no hub (affiliates + perf)?  → provavelmente VAZIO = a causa
curl -s "$SB/rest/v1/affiliates?affiliate_id=ilike.$ID&select=affiliate_id" "${H[@]}"
curl -s "$SB/rest/v1/performance_periods?affiliate_id=ilike.$ID&select=periodo,gmv_liquido" "${H[@]}"
```

### Fix (aplicado 13/07/26)
- `coletar_extrato.py` agora **auto-cadastra** a identidade mínima da creator nova em
  `affiliates` antes de escrever o `performance_periods` (não filtra mais fora). O
  próximo daily resolve sozinho. Onboarding manual imediato (RUNBOOK cenário 2, Caso A):
  ```bash
  # 1) identidade (affiliate_id = HANDLE em UPPERCASE, casa com o forward .upper())
  curl -X POST "$SB/rest/v1/affiliates?on_conflict=affiliate_id" "${H[@]}" \
    -H "Content-Type: application/json" -H "Prefer: resolution=merge-duplicates,return=minimal" \
    -d "[{\"affiliate_id\":\"$ID\",\"tiktok_handle\":\"$HANDLE\"}]"
  # 2) números: rodar coletar_extrato.py --inicio <1º-do-mês-inicial> --fim <hoje>  (janela
  #    FULL do mês — corrige mês passado inteiro).
  ```
- **Guarda de cobertura (13/07/26):** `build_performance_forward` só escreve um mês se a
  janela o cobre INTEIRO (`window_start <= dia 1`). Assim o daily `--dias 21` NÃO encolhe
  mais mês passado (pula junho, escreve só o mês corrente); mês passado só muda via backfill
  full-window. Se o hub voltar a subnotificar um mês fechado: rodar o backfill daquele mês.
- **Lição:** `performance_periods` cobre menos creators que `affiliate_perf`/`extrato_resumo`
  → provável FK-filter mordendo (ou perf subnotificado). Sempre validar recompute
  full-window contra `affiliate_creator_product` (fonte independente) antes de gravar.

---

## 📞 Quando me chamar

Diga:
> "Tem um problema: [sintoma]"

Eu vou:
1. Ler RUNBOOK.md
2. Identificar o cenário (1-8 acima)
3. Rodar a bateria de diagnóstico do cenário
4. Reportar o que encontrei
5. Aplicar fix conhecido (ou abrir investigação se for novo)
6. Atualizar este arquivo se descobrir algo que ainda não está aqui
