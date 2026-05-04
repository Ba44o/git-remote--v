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
curl -sI https://dash.rhodejeans.com.br/admin.html | head -1     # 200 OK?

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
