# Launch Video Recorder

Grava vídeos de lançamento em mp4 (estilo Anthropic) de qualquer página do ecossistema Rhode, pronto pra disparar no WhatsApp, postar em redes sociais ou anexar em email.

Não precisa de editor de vídeo, motion designer ou produção externa. Stack: **Playwright** (browser headless + recording) + **ffmpeg-static** (conversão webm → mp4).

## Setup (uma vez só)

```bash
cd "/Users/user/Documents/VS Claude Teste/tools/onboarding-recorder"
npm install                            # já está instalado
npx playwright install chromium        # browser engine (~150 MB)
```

Sem dependências de sistema. `ffmpeg` vem via npm (`ffmpeg-static`).

## Uso típico

```bash
# Tour completo do hub em 1:1 (1080×1080) — formato WhatsApp chat / Instagram
node record.js --mode=tour --aspect=1x1 --duration=55

# Onboarding modal em 9:16 (1080×1920) — formato WhatsApp Status / Reels
node record.js --mode=onboarding --aspect=9x16 --duration=38

# Outra página do mesmo domínio
node record.js --page=dash-live --mode=tour --aspect=1x1 --duration=45

# URL custom completa
node record.js --url=https://exemplo.com/qq?demo=tour --aspect=1x1 --duration=40
```

Output:
- `out/{name}-{stamp}.mp4` — vídeo final
- `~/Desktop/{name}-{stamp}.mp4` — cópia auto pro Desktop (desabilita com `--desktop=false`)
- `out/raw/page@xxx.webm` — gravação bruta do Playwright (apagar depois)

## Flags

| Flag | Default | Valores | Descrição |
|---|---|---|---|
| `--mode` | `tour` | `tour`, `onboarding`, ou qualquer `?demo=xxx` que a página suporte | Modo demo no app |
| `--aspect` | `1x1` | `1x1`, `9x16`, `16x9` | Formato do vídeo (1080×1080 / 1080×1920 / 1920×1080) |
| `--page` | `hub` | qualquer `/{page}.html` no domínio | Página a gravar |
| `--style` | — | `anthropic` (só onboarding) | Variação visual cream/serif |
| `--duration` | `55` | segundos | Tempo de gravação útil |
| `--name` | `{page}-{mode}-{aspect}` | string | Prefix do filename |
| `--base` | `https://creators.rhodejeans.com.br` | URL base | Pra outro domínio |
| `--url` | — | URL completa | Override total (ignora `--page`/`--mode`/etc) |
| `--headless` | `true` | `true`/`false` | `false` abre browser visível pra debug |
| `--desktop` | `true` | `true`/`false` | Copia mp4 final pro `~/Desktop` |

## Como funciona

1. **Playwright** abre Chromium headless no aspect escolhido (sem cursor real, sem scrollbar)
2. Navega pra URL com `?demo=tour` (cache buster `&_={timestamp}` automático contra CDN)
3. Aguarda o `body.tour-mode` ou `.onb-overlay.on` aparecer (sinal de boot pronto)
4. Grava `waitForTimeout(duration)` — todo o motion + autopilot do app roda nesse tempo
5. **ffmpeg-static** converte webm → mp4 (h264 + AAC silencioso, faststart) escalando pra resolução exata

A duração real do mp4 é `--duration + ~3-5s` (o tempo de page.goto entra na gravação).

## Recursos do app que o recorder espera encontrar

Pra gravar uma página NOVA, ela precisa ter implementado:

- Handler `?demo=tour` (ou `?demo=<modo>` custom) no JS de boot
- Classe `body.tour-mode` quando o tour está ativo
- (Opcional) `.onb-overlay.on` se for um modal demo

Sem isso, o recorder grava só a página normal (com loading screen, auth flow, etc).

## Validar antes de entregar

Sempre confira frames antes de mandar pro usuário/cliente:

```bash
FFMPEG=$(node -p "require('ffmpeg-static')")
OUT=$(ls -t out/*.mp4 | head -1)
for t in 3 10 20 30 45; do
  "$FFMPEG" -ss $t -i "$OUT" -vframes 1 -y "out/check-${t}s.png" 2>/dev/null
done
```

Abre os PNGs com Preview e verifica:
- Modal/loader não trava o vídeo
- Cursor fantasma está visível e navegando
- Dados sensíveis (handles, cupons, IDs) estão anonimizados
- Sininho de notif, botão Suporte, gn-name escondidos
- Stagger das cards está fluindo (não tudo de uma vez)

## Limites WhatsApp/Status

| Plataforma | Limite | Como caber |
|---|---|---|
| WhatsApp Status | 16 MB / 90s | Aspect 9:16, duration ≤ 60s, evitar motion complexo |
| WhatsApp Chat | 100 MB / 16 min | Qualquer aspect, qualquer duration razoável |
| Instagram Reels | 250 MB / 90s | Aspect 9:16 |
| Instagram Feed | 4 GB / 60s | Aspect 1:1 ideal |
| LinkedIn | 5 GB / 10 min | Aspect 1:1 ou 16:9 |

Pra cortar tamanho: baixar `--crf` (mais qualidade = maior) ou reduzir `--duration`.

## Pegadinhas

- **CDN cache** — Vercel cacheia o HTML (`x-vercel-cache: HIT`). O recorder adiciona `&_={timestamp}` automaticamente. Se for URL custom (`--url=`), garanta que você adicionou cache buster.
- **Headless render diferente de browser real** — fontes, scroll behavior podem variar. Use `--headless=false` se algo estiver estranho.
- **Cursor fantasma é responsabilidade do app** — esse recorder NÃO sobrepõe cursor próprio. O cursor visto nos vídeos é injetado pelo `startHubTour()` / `startDemoAutopilot()` na própria página.

## Estender pra outras páginas

1. Implemente `?demo=tour` na página alvo (template em `rhode-vercel/public/hub.html`, buscar `demoMode==='tour'`)
2. Copie o bloco CSS "MOTION pra ?demo=tour" do hub.html pro CSS da página
3. Deploy
4. `node record.js --page=novapage --mode=tour --aspect=1x1`

Veja a memória [pattern_launch_video.md](/Users/user/.claude/projects/-Users-user-Documents-VS-Claude-Teste/memory/pattern_launch_video.md) pro processo completo.

## Troubleshooting

| Sintoma | Causa provável | Fix |
|---|---|---|
| Mp4 mostra só loading screen | Boot falhou (pageerror no console) | Verificar Console; provavelmente TDZ — mover `let _foo` pro topo do script |
| Modal/cursor não aparece | App não implementou `?demo=tour` ou `body.tour-mode` | Implementar no app primeiro |
| Versão antiga sendo gravada | CDN cache | Recorder já adiciona buster; se `--url` custom, adicione `?_=${Date.now()}` |
| Vídeo trava 5s no início | page.goto demora | Normal — chamar `--duration=45` resulta em mp4 ~50s |
| Cupom/handle vaza no vídeo | MutationObserver não cobriu render assíncrono | Reforçar `maskHandlesInDOM` no app + checar patterns |
| Áudio: "vídeo sem som" | Algumas plataformas exigem áudio | Já adicionamos `anullsrc` AAC silencioso. Se ainda der, verificar codec do player |
