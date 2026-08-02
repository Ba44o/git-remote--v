#!/usr/bin/env python3
"""
Testes do canary do performance_periods (RUNBOOK #18).

PORQUÊ EXISTE: canary que nunca disparou não protege nada — só dá sensação de
segurança, que é exatamente o que o cron verde já dava enquanto o hub servia
dado pela metade. Estes testes provam que ele dispara nos modos de falha reais
e NÃO dispara no estado saudável.

O limiar é o ponto sensível: o ratio real de julho ANTES do fix era 0,858 e o
saudável é 0,955 — perto o bastante pra um limiar mal calibrado errar os dois
lados. Por isso os casos de fronteira usam os números REAIS medidos em 02/08/26,
não valores redondos inventados.

READ-ONLY: nada é escrito no Supabase. Os modos de falha são simulados por
monkeypatch do `pageall` e por uma cópia temporária do shell script.

Uso:  python3 tests/test_canary_performance_periods.py
"""
import os, sys, io, importlib, contextlib, tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
os.chdir(RAIZ)

resultados = []


def carrega():
    """Recarrega o módulo do zero — `falhas`/`avisos` são globais e vazam entre runs."""
    for m in list(sys.modules):
        if m.startswith("canary_performance_periods"):
            del sys.modules[m]
    return importlib.import_module("canary_performance_periods")


def roda(nome, esperado, prep=None):
    c = carrega()
    if prep:
        prep(c)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = c.main()
    ok = rc == esperado
    resultados.append(ok)
    print(f"{'✓' if ok else '✗'} {nome}  (exit {rc}, esperado {esperado})")
    if not ok:
        print("   " + buf.getvalue().replace("\n", "\n   "))
    else:
        for l in buf.getvalue().splitlines():
            if "❌" in l:
                print(f"     └ {l.strip()[:130]}")
    return ok


def trunca_julho(alvo):
    """Simula o performance_periods de julho com exatamente `alvo` pedidos."""
    def prep(c):
        orig = c.pageall

        def fake(path, _orig=orig, _alvo=alvo):
            rows = _orig(path)
            if "performance_periods" in path and "periodo=eq.2026-07" in path:
                out, tot = [], 0
                for r in rows:
                    if tot >= _alvo:
                        break
                    r = dict(r)
                    r["pedidos"] = min(r["pedidos"], _alvo - tot)
                    tot += r["pedidos"]
                    out.append(r)
                assert tot == _alvo, f"esperava {_alvo}, montei {tot}"
                return out
            return rows
        c.pageall = fake
    return prep


def zera(tabela, filtro=""):
    def prep(c):
        orig = c.pageall
        c.pageall = lambda p, _o=orig: ([] if (tabela in p and filtro in p) else _o(p))
    return prep


def regride_janela(c):
    """Alguém reverte o passo [14] pro `--dias 21` — a regressão que causou o bug."""
    txt = open(os.path.join(RAIZ, "refresh_performance_diario.sh"), encoding="utf-8").read()
    txt = txt.replace('python3 coletar_extrato.py --inicio "$EXTRATO_INI" --fim "$EXTRATO_FIM"',
                      "python3 coletar_extrato.py --dias 21")
    f = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False, encoding="utf-8")
    f.write(txt); f.close()
    c.DAILY_SH = f.name


print("═══ Modos de falha ═══")
roda("estado real de hoje (pós-fix) — não pode disparar", 0)
roda("daily regrediu pro --dias 21 (janela deslizante)", 1, regride_janela)
roda("performance_periods de julho vazia", 1, zera("performance_periods", "eq.2026-07"))
roda("fonte independente (acp) vazia — não pode dar OK falso", 1, zera("affiliate_creator_product"))

print("\n═══ Calibragem do limiar (números reais de 02/08/26) ═══")
roda("4539 ped = julho REAL antes do fix (ratio 0,858)", 1, trunca_julho(4539))
roda("4763 ped = exatamente no limiar 0,900",            1, trunca_julho(4763))
roda("4900 ped = degradação leve aceitável (0,926)",     0, trunca_julho(4900))
roda("5056 ped = julho REAL depois do fix (0,955)",      0, trunca_julho(5056))

print(f"\n═══ {sum(resultados)}/{len(resultados)} corretos ═══")
sys.exit(0 if all(resultados) else 1)
