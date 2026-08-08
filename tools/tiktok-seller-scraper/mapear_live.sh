#!/bin/bash
# Lê os pares rótulo→valor da tela de live commerce, na aba já logada do Chrome.
#
# PRÉ-REQUISITO (cai toda vez que o Chrome reinicia — sempre reconferir):
#   Chrome > menu Ver > Desenvolvedor > "Permitir o JavaScript dos Eventos da Apple" (✓)
#
# Uso:
#   ./mapear_live.sh                      -> primeira aba de live commerce que achar
#   ./mapear_live.sh "workbench/live"     -> aba cuja URL contém o trecho
#   ./mapear_live.sh "" saida.json        -> salva em arquivo
#
# Read-only: executa JS de leitura, não clica nem navega. Seguro com live no ar.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
FILTRO="${1:-tiktok.com}"
OUT="${2:-}"

RES=$(osascript <<EOF
set jsCode to read (POSIX file "$DIR/mapear_metricas_live.js") as «class utf8»
tell application "Google Chrome"
	repeat with w in windows
		repeat with t in tabs of w
			if (URL of t) contains "$FILTRO" then
				return (execute t javascript jsCode)
			end if
		end repeat
	end repeat
end tell
return "NO_TAB"
EOF
)

if [ "$RES" = "NO_TAB" ]; then
  echo "NO_TAB: nenhuma aba com \"$FILTRO\". Abra a tela no Chrome." >&2
  exit 2
fi
if [ -z "$RES" ]; then
  echo "VAZIO: o Chrome não devolveu nada — confira Ver > Desenvolvedor > 'Permitir o JavaScript dos Eventos da Apple'." >&2
  exit 3
fi

if [ -n "$OUT" ]; then printf '%s' "$RES" > "$OUT"; echo "✓ $OUT"; else printf '%s' "$RES"; fi
