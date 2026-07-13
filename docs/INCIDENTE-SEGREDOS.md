# Incidente — segredos vivos no git (remediação)

> Segredos versionados num repo **público** (`Ba44o/git-remote--v`). Enquanto não
> **rotacionar**, o modelo de segurança está comprometido — purga/limpeza são só
> defesa-em-profundidade. Faça na ordem.

## Status (13/07/2026)

| Item | Estado |
|---|---|
| `service_role` Supabase hardcoded no tree | ✅ já em `process.env` (sync_catalogo/get-hub) |
| Z-API instance/token/client-token hardcoded (7 backends + docs) | ✅ movido pra `process.env` (commit `5516b0c`) |
| Anon key hardcoded (relay/request-access) | ⚪ mantido — anon é **público por design** (protegido por RLS) |
| **Rotacionar** service_role + Z-API | ⛔ **PENDENTE — mãos do Humberto** |
| Setar chaves novas no Vercel + GitHub secrets | ⛔ pendente |
| Repo privado | ⛔ pendente |
| Purgar segredos do **histórico** git | ⛔ pendente (script pronto) |

## 1. Rotacionar (mata as chaves vazadas — faça PRIMEIRO)

- **Supabase** → projeto `ivzpykuluxcxefhyzfsf` → Settings → API → `service_role` → **Roll**. Copiar a nova.
- **Z-API** → z-api.io → instância → **regenerar token** (ou desconectar/reconectar).

## 2. Repo privado (para o sangramento enquanto purga)

GitHub → repo → Settings → Danger Zone → **Change visibility → Private**.

## 3. Setar as chaves novas onde o app lê

- **Vercel** (projeto do hub) → Settings → Environment Variables:
  `SUPABASE_SERVICE_KEY` (nova), `ZAPI_INSTANCE`, `ZAPI_TOKEN`, `ZAPI_CLIENT_TOKEN` (novos).
- **GitHub → repo → Settings → Secrets and variables → Actions:** `SUPABASE_SERVICE_KEY` (nova).
- Conferir que o Vercel tem `SUPABASE_URL` setado **antes** de qualquer deploy que dependa de env
  (senão os proxies live caem — ver aviso em [[project_security_incident_secrets]]).

## 4. Deploy do código já sanado

`git push` do branch (commits `5516b0c` etc.) → Vercel redeploya. Testar: hub abre, disparo
WhatsApp funciona (usa os `ZAPI_*` do env agora).

## 5. Purgar o histórico (depois de rotacionar)

Rewrite de histórico → muda TODOS os SHAs → exige `--force` e re-clone por quem tiver o repo.
Rode numa cópia limpa. O arquivo de substituições fica **fora do repo** (contém os segredos):
scratchpad `purge-replacements.txt` (regenerável por `gen_purge_replacements.py`).

```bash
# instalar (uma vez): brew install git-filter-repo   OU   pip install git-filter-repo
cd "/Users/user/Documents/VS Claude Teste"
git filter-repo --replace-text /caminho/para/purge-replacements.txt
# reconfigurar o remote (filter-repo remove por segurança) e forçar:
git remote add origin https://github.com/Ba44o/git-remote--v.git
git push --force --all origin
git push --force --tags origin
```

## 6. Verificar

Procurar no histórico pelos valores antigos (pegue-os do `purge-replacements.txt`
no scratchpad — **não** cole os literais aqui, senão re-commita o segredo):

```bash
# ex.: git grep -l "<valor_antigo_zapi_token>" $(git rev-list --all) | head   → vazio = ok
```
E confirmar no GitHub que os commits antigos não mostram mais as chaves. Depois de
tudo, **rotacionar de novo não é preciso** — mas só torne o repo público se a purga
passou 100%.
