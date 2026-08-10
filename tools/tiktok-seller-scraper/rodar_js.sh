#!/bin/bash
# Executa um arquivo JS (read-only) na aba já logada do Chrome cuja URL contém $2.
# PRÉ-REQUISITO: Chrome > Ver > Desenvolvedor > "Permitir o JavaScript dos Eventos da Apple" (✓)
# Uso: ./rodar_js.sh caminho/do.js "trecho-da-url" [saida.json]
set -euo pipefail
JSFILE="$1"; FILTRO="${2:-tiktok.com}"; OUT="${3:-}"
RES=$(osascript <<EOF
set jsCode to read (POSIX file "$JSFILE") as «class utf8»
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
[ "$RES" = "NO_TAB" ] && { echo "NO_TAB: nenhuma aba com \"$FILTRO\"." >&2; exit 2; }
[ -z "$RES" ] && { echo "VAZIO: confira Ver > Desenvolvedor > 'Permitir o JavaScript dos Eventos da Apple'." >&2; exit 3; }
if [ -n "$OUT" ]; then printf '%s' "$RES" > "$OUT"; echo "✓ $OUT"; else printf '%s' "$RES"; fi
