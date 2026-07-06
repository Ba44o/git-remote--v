"""
Rhode Jeans — Entrypoint MENSAL do Relatório de Seeding (envio de amostras)
===========================================================================
Roda self-contained (local ou GitHub Actions Ubuntu). Todo dia 01 o cron gera o
relatório do MÊS QUE FECHOU (mês anterior).

Pipeline:
  1. (best-effort) renova o token TikTok — obter_token.py --refresh (Supabase/api_tokens + .env)
  2. coleta sample_applications FRESCO — agente_rhode/etl_sample_applications.py
  3. coleta vendas de afiliada p/ atribuição — coletar_vendas_seeding.py --mes <alvo>
  4. monta o template (6 abas + .md) — seeding_report.build_report(<alvo>)

Uso:
  python gerar_relatorio_seeding_mensal.py                 # mês anterior ao de hoje
  python gerar_relatorio_seeding_mensal.py --mes ""        # idem (assim o cron chama)
  python gerar_relatorio_seeding_mensal.py --mes 2026-06   # mês explícito
  python gerar_relatorio_seeding_mensal.py --skip-collect        # reusa CSVs já materializados
  python gerar_relatorio_seeding_mensal.py --no-token-refresh    # não rotaciona o token

Secrets no CI: SUPABASE_URL, SUPABASE_SERVICE_KEY, TIKTOK_APP_KEY, TIKTOK_APP_SECRET, TIKTOK_SHOP_CIPHER.
NÃO toca em agente_rhode/*.py (só importa/executa) — evita disparar o etl_sync.yml (ETL de produção).
"""
import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parent


def mes_anterior(hoje: date) -> str:
    y, m = hoje.year, hoje.month
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def _run(cmd, fatal=True, label=""):
    print(f"\n=== {label or ' '.join(cmd)} ===", flush=True)
    r = subprocess.run([sys.executable, *cmd], cwd=str(BASE))
    if r.returncode != 0:
        msg = f"[{'ERRO' if fatal else 'aviso'}] passo '{label}' saiu com código {r.returncode}"
        if fatal:
            print(msg, file=sys.stderr)
            sys.exit(r.returncode)
        print(msg)
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mes", default=None, help="mês-alvo AAAA-MM; vazio/ausente = mês anterior a hoje")
    ap.add_argument("--skip-collect", action="store_true", help="reusa warehouse/*.csv já materializados")
    ap.add_argument("--no-token-refresh", action="store_true", help="não tenta renovar o token TikTok")
    args = ap.parse_args()

    hoje = date.today()
    mes = args.mes.strip() if (args.mes and args.mes.strip()) else mes_anterior(hoje)
    # valida formato AAAA-MM
    try:
        y, m = int(mes[:4]), int(mes[5:7])
        assert len(mes) == 7 and mes[4] == "-" and 1 <= m <= 12
    except (ValueError, AssertionError):
        print(f"[ERRO] --mes inválido: {args.mes!r} (esperado AAAA-MM)", file=sys.stderr)
        sys.exit(2)

    exec_date = hoje.strftime("%Y-%m-%d")
    print(f"Relatório de Seeding mensal · mês-alvo: {mes} · execução: {exec_date}", flush=True)

    if not args.no_token_refresh:
        _run(["obter_token.py", "--refresh"], fatal=False, label="renovar token TikTok")

    if not args.skip_collect:
        _run(["agente_rhode/etl_sample_applications.py"], fatal=True, label="coletar sample_applications")
        _run(["coletar_vendas_seeding.py", "--mes", mes], fatal=True, label="coletar vendas (Affiliate Orders)")
    else:
        print("\n(--skip-collect: reusando warehouse/*.csv já materializados)")

    from seeding_report import build_report
    res = build_report(mes, exec_date=exec_date, base=BASE)

    print("\n=== RELATÓRIO GERADO ===")
    print("XLSX:", res["xlsx"])
    print("MD:  ", res["md"])
    dpe = f"{res['delta_enviadas_pct']:+.1f}%" if res["delta_enviadas_pct"] is not None else "sem base"
    print(f"Peças enviadas: {res['enviadas']} ({dpe} vs. {res['prev']}) · canceladas: {res['canceladas']}")
    if res["tem_vendas"]:
        print(f"Conversão: {res['conv_venderam']}/{res['creators_atingidas']} atingidas "
              f"({res['conv_taxa']:.1f}%) · GMV gerado: R$ {res['gmv_gerado']:,.2f}")
    else:
        print("Conversão/ROI: sem dado (vendas não coletadas)")


if __name__ == "__main__":
    main()
