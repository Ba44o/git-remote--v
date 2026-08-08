#!/usr/bin/env python3
"""
Raspa o relatório de CRIATIVOS do TikTok Seller (GMV Max) em várias janelas de data,
navegando a aba logada do Chrome por URL. Tudo que importa está na querystring:

  reporting_type=video        -> abre o painel de criativos (SEM isso só vem a tabela de campanhas)
  campaign_start_date / _end  -> janela (epoch ms, BRT)
  sp_creative=...             -> filtro de status (item_delivery_status; '3' = Veiculado)
  creative_page_size          -> itens por página (50)
  creative_page               -> número da página

PRÉ-REQUISITO: Chrome > Ver > Desenvolvedor > "Permitir o JavaScript dos Eventos da Apple" (✓)
(cai a cada reinício do Chrome)

Uso:  python3 raspar_janelas.py
"""
import json, subprocess, sys, time, urllib.parse
from datetime import datetime, timezone, timedelta

BRT = timezone(timedelta(hours=-3))
HERE = "/Users/user/Documents/VS Claude Teste/tools/tiktok-seller-scraper"
OUT = "/Users/user/Documents/VS Claude Teste/dados/campanhas/tiktok/criativos"

CAMPAIGN_ID = "1837899752347697"
PRODUCT_ID = "1731763836201109087"
LABEL = ""  # prefixo dos arquivos de saída (vazio = campanha Marmorizada original)
# filtro de status dos criativos: in_field_values![...] -> '3' = Veiculado
STATUS_VEICULADO = "%5B%28%27field%21%27item_delivery_status%27%7Efilter_type%210%7Ein_field_values%21%5B%273%27%5D%29%5D_"

def ms(y, m, d, h=0, mi=0):
    return int(datetime(y, m, d, h, mi, tzinfo=BRT).timestamp() * 1000)

def build_url(start_ms, end_ms, page=1, page_size=50, sp_creative=STATUS_VEICULADO):
    return (
        "https://seller-br.tiktok.com/ads-creation/dashboard"
        f"?mpa=1&reporting_type=video&product_id={PRODUCT_ID}&activated_tab_id=1"
        f"&campaign_start_date={start_ms}&campaign_end_date={end_ms}"
        f"&shop_region=BR&sp_campaign_list_pgm=%5B%5D_&campaign_id={CAMPAIGN_ID}"
        f"&sp_creative={sp_creative}"
        f"&creative_page_size={page_size}&creative_page={page}"
    )

NAV = '''
tell application "Google Chrome"
	repeat with w in windows
		repeat with t in tabs of w
			if (URL of t) contains "seller-br.tiktok.com" then
				set URL of t to "{url}"
				return "ok"
			end if
		end repeat
	end repeat
end tell
return "NO_TAB"
'''

SCRAPE = '''
set scrapeJS to read (POSIX file "{here}/scraper.js") as «class utf8»
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
'''

def _osa(script):
    r = subprocess.run(["osascript", "-"], input=script, capture_output=True, text=True)
    return r.stdout.strip() or r.stderr.strip()

def _scrape_once():
    txt = _osa(SCRAPE.format(here=HERE))
    try:
        return json.loads(txt)
    except Exception:
        return {"erro": txt[:200], "rows": [], "headers": []}

def scrape(url, tentativas=14, intervalo=4):
    """Navega e fica tentando até o painel de CRIATIVOS renderizar de fato.
    O SPA é corrida: às vezes só a tabela de campanhas existe nos primeiros segundos."""
    _osa(NAV.format(url=url))
    time.sleep(6)
    ultimo = {"erro": "timeout", "rows": [], "headers": []}
    for _ in range(tentativas):
        d = _scrape_once()
        h = d.get("headers", [])
        if h and h[0] == "Criativo" and d.get("rows"):
            return d
        ultimo = d
        time.sleep(intervalo)
    return ultimo

def janela(nome, start_ms, end_ms, max_paginas=8):
    """Pagina até a página vir com menos que o page_size. Retorna nº total de linhas."""
    total = 0
    for page in range(1, max_paginas + 1):
        d = scrape(build_url(start_ms, end_ms, page=page))
        n = len(d.get("rows", []))
        cols = len(d.get("headers", []))
        heads = d.get("headers", [])
        if not heads or heads[0] != "Criativo" or not n:
            print(f"  {nome} p{page}: painel de criativos não renderizou (cols={cols}) — pulando")
            break
        prefix = f"{LABEL}_" if LABEL else ""
        path = f"{OUT}/{prefix}{nome}_p{page}.json"
        with open(path, "w") as f:
            json.dump(d, f)
        total += n
        print(f"  {nome} p{page}: {n} linhas -> {path.split('/')[-1]}")
        if n < 50:
            break
    return total

if __name__ == "__main__":
    # Uso: python3 raspar_janelas.py [campaign_id product_id label]
    if len(sys.argv) >= 4:
        CAMPAIGN_ID, PRODUCT_ID, LABEL = sys.argv[1], sys.argv[2], sys.argv[3]
        print(f"Campanha {CAMPAIGN_ID} / produto {PRODUCT_ID} / label '{LABEL}'\n")
    JANELAS = {
        "jun26": (ms(2026, 6, 1),  ms(2026, 6, 30, 23, 59)),
        "jul26": (ms(2026, 7, 1),  ms(2026, 7, 22, 23, 59)),
        "d90":   (ms(2026, 4, 23), ms(2026, 7, 22, 23, 59)),
    }
    for nome, (a, b) in JANELAS.items():
        ini = datetime.fromtimestamp(a/1000, BRT).strftime('%d/%m')
        fim = datetime.fromtimestamp(b/1000, BRT).strftime('%d/%m')
        print(f"[{nome}] {ini} -> {fim}")
        t = janela(nome, a, b)
        print(f"  TOTAL {nome}: {t} criativos\n")
