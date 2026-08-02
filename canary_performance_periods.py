#!/usr/bin/env python3
"""
CANARY do performance_periods — falha ALTO quando o ranking/hub congela.

PORQUÊ ESTE ARQUIVO EXISTE (RUNBOOK #18): o `performance_periods` congelou em
silêncio duas vezes (13/07 e 02/08/26) — a guarda de cobertura do
`build_performance_forward` pulava o mês quando a janela deslizante `--dias 21`
deixava de alcançar o dia 1º. O daily reportava **success todo dia** enquanto
junho ia pro hub com 59% dos pedidos de fora. Exit code verde não é dado certo:
este canary mede o DADO contra uma fonte independente, não o status do job.

Roda no fim do `refresh_performance_diario.sh` e **derruba o run** (exit 1) —
é de propósito: cron vermelho é o único aviso que ninguém ignora.

3 checagens:
  1. REGRESSÃO DE JANELA (estrutural, sem rede) — o passo do extrato voltou pro
     `--dias`? A janela cobre o dia 1º do mês corrente E do anterior?
  2. COBERTURA (dado) — pedidos no `performance_periods` vs `affiliate_creator_product`
     (pipeline independente, `etl_creator_product --dias 90`, janela larga o
     bastante pra cobrir mês fechado). Congelamento derruba o ratio.
  3. FONTE VIVA — se a própria referência estiver parada, o ratio infla e
     esconderia o problema. Detecta e avisa em vez de dar OK falso.

Uso:
  python3 canary_performance_periods.py           # exit 1 se FAIL
  python3 canary_performance_periods.py --quiet   # só o veredito
"""
import os, sys, json, re, argparse, collections, urllib.request
from datetime import datetime, timezone, date

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from agente_rhode.etl_v2 import HANDLE_ALIASES
except Exception:
    HANDLE_ALIASES = {"NATMARQUESSS": "NATMARQUESVI"}

RAIZ = os.path.dirname(os.path.abspath(__file__))
DAILY_SH = os.path.join(RAIZ, "refresh_performance_diario.sh")
SB_URL = os.environ["SUPABASE_URL"].rstrip("/")
SBH = {"apikey": os.environ["SUPABASE_SERVICE_KEY"],
       "Authorization": "Bearer " + os.environ["SUPABASE_SERVICE_KEY"]}

# Calibrado no estado saudável de 02/08/26: jun 0,949 · jul 0,955 (o `pedidos` do
# product-level conta o mesmo pedido 1x por SKU, então o ratio saudável fica < 1).
# Estado quebrado do mesmo dia: jul 0,857 · jun 0,385 — os dois disparam.
RATIO_FAIL = 0.90
RATIO_WARN = 0.93
FONTE_MORTA = 1.50   # pp muito acima da referência = referência parada, não pp saudável
FORWARD_FROM = "2026-06"   # espelha coletar_extrato.py (Jan–Mai vêm do export, congelados)

falhas, avisos = [], []


def pageall(path):
    """PostgREST paginado. order= explícito na query (senão o offset pula linha —
    ver [[reference_pg_paginacao_order]] / RUNBOOK #17)."""
    out, off = [], 0
    while True:
        req = urllib.request.Request(f"{SB_URL}/rest/v1/{path}&limit=1000&offset={off}", headers=SBH)
        r = json.load(urllib.request.urlopen(req, timeout=90))
        out += r
        off += 1000
        if len(r) < 1000:
            return out


def norm(h):
    u = (h or "").strip().upper()
    return HANDLE_ALIASES.get(u, u)


def chave(h):
    """Handle sem pontuação. O mesmo handle aparece com e sem ponto/underscore
    dependendo da fonte (export vs API de afiliadas) — comparar cru geraria
    falso 'ausente'. A divisão em si é reportada por check_identidades()."""
    return re.sub(r"[^A-Z0-9]", "", norm(h))


def meses_vigiados(hoje):
    """Mês corrente + anterior — exatamente os dois que o forward mantém vivos."""
    cur = f"{hoje.year:04d}-{hoje.month:02d}"
    ant = (date(hoje.year - 1, 12, 1) if hoje.month == 1
           else date(hoje.year, hoje.month - 1, 1))
    return [p for p in (f"{ant.year:04d}-{ant.month:02d}", cur) if p >= FORWARD_FROM]


def check_janela(hoje, quiet):
    """1. A janela do daily ainda ancora no 1º do mês anterior?"""
    if not os.path.exists(DAILY_SH):
        avisos.append(f"não achei {DAILY_SH} — checagem de janela pulada")
        return
    txt = open(DAILY_SH, encoding="utf-8").read()
    chamadas = re.findall(r"^\s*python3 coletar_extrato\.py(.*)$", txt, re.M)
    if not chamadas:
        falhas.append("refresh_performance_diario.sh não chama mais coletar_extrato.py "
                      "— o performance_periods parou de ser alimentado")
        return
    for args in chamadas:
        if "--dias" in args:
            falhas.append(
                "REGRESSÃO: coletar_extrato.py voltou a rodar com `--dias` (janela deslizante). "
                "A partir do dia 22 ela não alcança o dia 1º, a guarda de cobertura pula o mês "
                "e o ranking/hub congela em silêncio. Ancorar no 1º do mês anterior (RUNBOOK #18).")
    ini = date(hoje.year - 1, 12, 1) if hoje.month == 1 else date(hoje.year, hoje.month - 1, 1)
    for per in meses_vigiados(hoje):
        if date.fromisoformat(f"{per}-01") < ini:
            falhas.append(f"janela do daily começa em {ini} e NÃO cobre o dia 1º de {per} "
                          f"— a guarda de cobertura vai pular esse mês")
    if not quiet:
        print(f"  janela do daily: {ini} → {hoje}  (cobre {', '.join(meses_vigiados(hoje))})")


def check_cobertura(hoje, quiet):
    """2+3. performance_periods vs affiliate_creator_product (pipeline independente)."""
    meses = meses_vigiados(hoje)
    corte = min(meses) + "-01"
    acp = pageall(f"affiliate_creator_product?select=creator,data,pedidos,gmv&data=gte.{corte}&order=id")
    if not acp:
        falhas.append("affiliate_creator_product vazia na janela — sem fonte independente "
                      "pra validar o ranking (etl_creator_product quebrado?)")
        return
    for per in meses:
        pp = pageall(f"performance_periods?select=affiliate_id,pedidos,gmv_liquido&periodo=eq.{per}&order=affiliate_id")
        ref = collections.defaultdict(lambda: [0, 0.0])
        for r in acp:
            if r["data"].startswith(per):
                c = chave(r["creator"])
                ref[c][0] += int(r["pedidos"] or 0)
                ref[c][1] += float(r["gmv"] or 0)
        pped, rped = sum(r["pedidos"] for r in pp), sum(v[0] for v in ref.values())
        if not rped:
            avisos.append(f"{per}: referência sem pedidos — mês não validado")
            continue
        if not pp:
            falhas.append(f"{per}: ZERO creators no performance_periods, mas a referência tem "
                          f"{len(ref)} creators / {rped} pedidos")
            continue
        ratio = pped / rped
        ausentes = sorted(set(ref) - {chave(r["affiliate_id"]) for r in pp},
                          key=lambda c: -ref[c][1])
        graves = [c for c in ausentes if ref[c][1] >= 1000]
        if not quiet:
            print(f"  {per}: {len(pp)} creators / {pped} pedidos  ·  referência "
                  f"{len(ref)} / {rped}  ·  ratio {ratio:.3f}  ·  ausentes {len(ausentes)}")
        if ratio < RATIO_FAIL:
            falhas.append(f"{per}: ranking com {pped} pedidos contra {rped} da fonte independente "
                          f"(ratio {ratio:.3f} < {RATIO_FAIL}) — mês provavelmente CONGELADO. "
                          f"Fix: coletar_extrato.py --inicio {per}-01 --fim {hoje} (RUNBOOK #18)")
        elif ratio < RATIO_WARN:
            avisos.append(f"{per}: ratio {ratio:.3f} abaixo do saudável (~0,95) — vigiar")
        if ratio > FONTE_MORTA and per != meses[-1]:
            avisos.append(f"{per}: ratio {ratio:.3f} alto demais — a REFERÊNCIA pode estar parada "
                          f"(etl_creator_product), o que mascara congelamento do ranking")
        if graves:
            avisos.append(f"{per}: {len(graves)} creator(s) com GMV ≥ R$1.000 na fonte e ausentes "
                          f"do ranking: {', '.join(graves[:5])}")


def check_identidades(quiet):
    """4. A MESMA creator gravada sob 2 affiliate_id que só diferem na pontuação
    (ex.: .FAMILIAPIMENTEL do export × FAMILIAPIMENTEL do forward). O histórico
    dela racha no meio, o GMV acumulado não soma e o TIER sai errado. Não é
    congelamento — por isso AVISO, não FAIL: o conserto passa por HANDLE_ALIASES
    e mexe em tier creator-facing, então é decisão humana."""
    aff = pageall("affiliates?select=affiliate_id&order=affiliate_id")
    grupos = collections.defaultdict(list)
    for a in aff:
        grupos[chave(a["affiliate_id"])].append(a["affiliate_id"])
    # Grupo com >1 handle NÃO é problema por si: se o HANDLE_ALIASES já mapeia todos
    # pro mesmo canônico (ex.: NATMARQUESSS→NATMARQUESVI), o ETL consolida e o
    # performance_periods sai certo. Só alerta quem sobra sem alias — esses o ETL
    # trata como creators diferentes e o histórico racha de verdade.
    dup = {k: v for k, v in grupos.items()
           if len(v) > 1 and len({norm(h) for h in v}) > 1}
    if not quiet:
        print(f"  identidades: {len(aff)} em affiliates · {len(dup)} dividida(s) sem alias")
    for k, v in sorted(dup.items()):
        avisos.append(f"identidade dividida SEM alias — {' × '.join(sorted(v))}: mesma creator em "
                      f"linhas separadas, GMV acumulado não soma e o tier sai subestimado. "
                      f"Consolidar via HANDLE_ALIASES (mexe em tier creator-facing — decisão humana)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    hoje = datetime.now(tz=timezone.utc).date()
    if not a.quiet:
        print(f"═══ Canary performance_periods — {hoje} ═══")
    check_janela(hoje, a.quiet)
    check_cobertura(hoje, a.quiet)
    check_identidades(a.quiet)

    for w in avisos:
        print(f"  ⚠ AVISO: {w}")
    if falhas:
        print("\n" + "!" * 72)
        print("CANARY FALHOU — o ranking/hub está servindo dado incompleto às creators.")
        for f in falhas:
            print(f"  ❌ {f}")
        print("!" * 72)
        return 1
    print("✓ canary OK — performance_periods bate com a fonte independente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
