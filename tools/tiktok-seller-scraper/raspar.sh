#!/bin/bash
# Raspa a tabela de criativos do TikTok Seller direto da aba logada do Chrome.
#
# PRÉ-REQUISITO (cai toda vez que o Chrome reinicia — sempre reconferir):
#   Chrome > menu Ver > Desenvolvedor > "Permitir o JavaScript dos Eventos da Apple" (✓)
#
# Uso:
#   ./raspar.sh saida.json          -> raspa a página atual da tabela
#   ./raspar.sh saida.json next     -> vira p/ a próxima página de criativos e raspa
#
# Dica p/ múltiplas janelas de data: ajuste o filtro de data no dashboard,
# rode com um nome por janela (ex: jul_p1.json, jul_p2.json, jun_p1.json...)
# e cruze depois pelo "ID da publicação" (col 1), que é a chave estável.

set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${1:-saida.json}"
MODE="${2:-}"

run_scrape() {
  osascript <<EOF
set scrapeJS to read (POSIX file "$DIR/scraper.js") as «class utf8»
tell application "Google Chrome"
	repeat with w in windows
		repeat with t in tabs of w
			if (URL of t) contains "seller-br.tiktok.com" then
				return (execute t javascript scrapeJS)
			end if
		end repeat
	end repeat
end tell
return "NO_TAB"
EOF
}

run_next_and_scrape() {
  osascript <<EOF
set clickJS to read (POSIX file "$DIR/click_next.js") as «class utf8»
set scrapeJS to read (POSIX file "$DIR/scraper.js") as «class utf8»
tell application "Google Chrome"
	repeat with w in windows
		repeat with t in tabs of w
			if (URL of t) contains "seller-br.tiktok.com" then
				execute t javascript clickJS
				delay 5
				return (execute t javascript scrapeJS)
			end if
		end repeat
	end repeat
end tell
return "NO_TAB"
EOF
}

if [ "$MODE" = "next" ]; then
  run_next_and_scrape > "$OUT"
else
  run_scrape > "$OUT"
fi

python3 - "$OUT" <<'PY'
import json,sys
try:
    d=json.load(open(sys.argv[1]))
    print("OK  linhas=%d  colunas=%d" % (len(d["rows"]), len(d["headers"])))
    print("URL:", d["url"][:120])
    if d["rows"]: print("1a linha:", d["rows"][0][0][:50])
except Exception as e:
    print("FALHOU:", open(sys.argv[1]).read()[:200])
PY
