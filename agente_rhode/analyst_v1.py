"""
Rhode Jeans — Analyst v1
========================
Motor de análise cognitiva de performance de creators.

Módulos:
  1. Anomalias        — spikes de refund, crashes de GMV, inatividade súbita
  2. Oportunidades    — upgrade de tier, alto AOV + baixa frequência, recuperáveis
  3. Stars & At-Risk  — top consistentes, em declínio, novas apostas
  4. Cohorts          — novos, veteranos, recuperados, churned
  5. Projeções        — GMV mês completo, criadores ativos esperados
  6. Health Score     — 0-100, por período e geral
  7. Executive Brief  — texto executivo gerado por regras

Uso:
  python agente_rhode/analyst_v1.py --warehouse warehouse
  python agente_rhode/analyst_v1.py --warehouse warehouse --sync  (envia ao Sheets)

Output:
  warehouse/insights.json
"""

import json
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date
from calendar import monthrange

# ── Constantes ────────────────────────────────────────────────────────────────

TIER_THRESHOLDS = [
    ("Diamante", 60_000, 0.13),
    ("Ouro",     25_000, 0.11),
    ("Prata",     8_000, 0.09),
    ("Bronze",    2_000, 0.07),
    ("Ferro",         0, 0.05),
]

def calc_tier(gmv_liq: float) -> str:
    for name, threshold, _ in TIER_THRESHOLDS:
        if gmv_liq >= threshold:
            return name
    return "Ferro"

def next_tier(gmv_liq: float):
    """Retorna (próximo_tier, gmv_necessário, falta) ou None se já é Diamante."""
    for i, (name, threshold, _) in enumerate(TIER_THRESHOLDS):
        if gmv_liq >= threshold:
            if i == 0:
                return None  # já é Diamante
            next_name, next_thresh, _ = TIER_THRESHOLDS[i - 1]
            return next_name, next_thresh, round(next_thresh - gmv_liq, 2)
    return TIER_THRESHOLDS[-2][0], TIER_THRESHOLDS[-2][1], TIER_THRESHOLDS[-2][1]


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_warehouse(warehouse_dir: Path):
    raw     = pd.read_csv(warehouse_dir / "raw_imports.csv")
    summary = pd.read_csv(warehouse_dir / "period_summary.csv")
    master  = pd.read_csv(warehouse_dir / "creators_master.csv") if (warehouse_dir / "creators_master.csv").exists() else pd.DataFrame()
    return raw, summary, master


# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_pct_change(new_val, old_val) -> object:
    if old_val is None or old_val == 0:
        return None
    return round((new_val - old_val) / abs(old_val) * 100, 1)

def period_days(inicio_str, fim_str):
    try:
        ini = pd.to_datetime(inicio_str)
        fim = pd.to_datetime(fim_str)
        _, dias_mes = monthrange(ini.year, ini.month)
        dias_cob = (fim - ini).days + 1
        return dias_cob, dias_mes
    except Exception:
        return None, None

def fmt_brl(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def creator_series(raw: pd.DataFrame, creator_id: str) -> pd.DataFrame:
    return raw[raw["creator_id"] == creator_id].sort_values("periodo").reset_index(drop=True)


# ── Módulo 1: Anomalias ───────────────────────────────────────────────────────

def detect_anomalias(raw: pd.DataFrame, periods) -> list[dict]:
    if len(periods) < 2:
        return []

    cur_p  = periods[-1]
    prev_p = periods[-2]

    agg = {c: "sum" for c in ["gmv_bruto","gmv_liquido","reembolso","pedidos","videos","lives"] if c in raw.columns}
    agg.update({c: "mean" for c in ["refund_pct","aov"] if c in raw.columns})
    def _agg(df):
        return df.groupby("creator_id").agg(agg)

    cur  = _agg(raw[raw["periodo"] == cur_p])
    prev = _agg(raw[raw["periodo"] == prev_p])

    anomalias = []

    common = cur.index.intersection(prev.index)
    for cid in common:
        c = cur.loc[cid]
        p = prev.loc[cid]

        # Spike de refund (>2× e acima de 20%)
        if p["refund_pct"] > 0 and c["refund_pct"] > 20 and c["refund_pct"] > p["refund_pct"] * 2:
            anomalias.append({
                "tipo": "refund_spike",
                "creator": str(cid),
                "valor_atual": round(float(c["refund_pct"]), 1),
                "valor_anterior": round(float(p["refund_pct"]), 1),
                "delta_pct": safe_pct_change(c["refund_pct"], p["refund_pct"]),
                "severidade": "critica" if c["refund_pct"] > 40 else "alta",
                "gmv_em_risco": round(float(c["reembolso"]), 2),
                "acao": f"Refund saltou de {p['refund_pct']:.1f}% → {c['refund_pct']:.1f}%. Investigar produto/cliente recorrente.",
            })

        # Crash de GMV (queda >40% entre quem tinha vendas)
        if p["gmv_liquido"] > 500 and c["gmv_liquido"] < p["gmv_liquido"] * 0.6:
            delta = safe_pct_change(c["gmv_liquido"], p["gmv_liquido"])
            anomalias.append({
                "tipo": "gmv_crash",
                "creator": str(cid),
                "valor_atual": round(float(c["gmv_liquido"]), 2),
                "valor_anterior": round(float(p["gmv_liquido"]), 2),
                "delta_pct": delta,
                "severidade": "alta" if (delta or 0) < -60 else "media",
                "acao": f"GMV caiu {abs(delta or 0):.0f}%. Verificar frequência de conteúdo e qualidade.",
            })

        # Inatividade súbita (tinha GMV, zerou)
        if p["gmv_bruto"] > 300 and c["gmv_bruto"] == 0:
            anomalias.append({
                "tipo": "inatividade_subita",
                "creator": str(cid),
                "valor_atual": 0,
                "valor_anterior": round(float(p["gmv_liquido"]), 2),
                "delta_pct": -100.0,
                "severidade": "media",
                "acao": f"Parou de gerar GMV. Último período: {fmt_brl(p['gmv_liquido'])}. Reativar com amostra ou campanha.",
            })

    # AOV outlier estatístico (>3σ no período atual, mínimo 10 pedidos)
    ativas_cur = cur[cur["pedidos"] >= 10].copy()
    if len(ativas_cur) > 10:
        mean_aov = ativas_cur["aov"].mean()
        std_aov  = ativas_cur["aov"].std()
        outliers = ativas_cur[ativas_cur["aov"] > mean_aov + 3 * std_aov]
        for cid, row in outliers.iterrows():
            anomalias.append({
                "tipo": "aov_outlier",
                "creator": str(cid),
                "valor_atual": round(float(row["aov"]), 2),
                "valor_anterior": round(mean_aov, 2),
                "delta_pct": safe_pct_change(row["aov"], mean_aov),
                "severidade": "info",
                "acao": f"AOV {fmt_brl(row['aov'])} vs média {fmt_brl(mean_aov)}. Investigar produto premium ou erro de dados.",
            })

    # Ordena por severidade
    ordem = {"critica": 0, "alta": 1, "media": 2, "info": 3}
    anomalias.sort(key=lambda x: ordem.get(x["severidade"], 9))
    return anomalias


# ── Módulo 2: Oportunidades ───────────────────────────────────────────────────

def detect_oportunidades(raw: pd.DataFrame, periods) -> list[dict]:
    cur_p = periods[-1]
    cur   = raw[raw["periodo"] == cur_p]
    ativas = cur[cur["gmv_liquido"] > 0]

    opps = []

    for _, row in ativas.iterrows():
        gmv = float(row["gmv_liquido"])
        cid = str(row["creator_id"])

        # Próximo de upgrade de tier (dentro de 15%)
        nt = next_tier(gmv)
        if nt:
            next_name, next_thresh, falta = nt
            pct_faltando = falta / next_thresh * 100
            if pct_faltando <= 15:
                opps.append({
                    "tipo": "tier_upgrade",
                    "creator": cid,
                    "gmv_atual": round(gmv, 2),
                    "tier_atual": calc_tier(gmv),
                    "tier_alvo": next_name,
                    "gmv_faltando": round(falta, 2),
                    "pct_faltando": round(pct_faltando, 1),
                    "prioridade": "alta" if pct_faltando <= 5 else "media",
                    "acao": f"Faltam {fmt_brl(falta)} para {next_name}. Incentivar com meta de conteúdo.",
                })

        # Alto AOV + baixa frequência de conteúdo (potencial de escala)
        aov = float(row.get("aov", 0))
        conteudos = int(row.get("videos", 0)) + int(row.get("lives", 0))
        if aov > 80 and conteudos < 5 and gmv > 500:
            opps.append({
                "tipo": "escala_conteudo",
                "creator": cid,
                "gmv_atual": round(gmv, 2),
                "aov": round(aov, 2),
                "conteudos": conteudos,
                "prioridade": "alta" if aov > 100 else "media",
                "acao": f"AOV alto ({fmt_brl(aov)}) com apenas {conteudos} conteúdo(s). Dobrar frequência = ~2× GMV.",
            })

        # Só live, zero vídeos
        vids  = int(row.get("videos", 0))
        lives = int(row.get("lives", 0))
        if lives > 3 and vids == 0 and gmv > 1000:
            opps.append({
                "tipo": "sem_videos",
                "creator": cid,
                "gmv_atual": round(gmv, 2),
                "lives": lives,
                "prioridade": "media",
                "acao": f"Só faz lives ({lives}). Vídeos evergreen têm descoberta orgânica constante.",
            })

    # Remove duplicatas por creator (mantém prioridade mais alta)
    seen = {}
    for o in sorted(opps, key=lambda x: 0 if x["prioridade"] == "alta" else 1):
        seen.setdefault(o["creator"], o)
    return list(seen.values())


# ── Módulo 3: Stars & At-Risk ─────────────────────────────────────────────────

def detect_stars_and_risk(raw: pd.DataFrame, periods) :
    if len(periods) < 2:
        return {"stars": [], "em_risco": [], "novos_destaques": []}

    pivot = raw.pivot_table(
        index="creator_id", columns="periodo", values="gmv_liquido", fill_value=0
    )
    cols = [p for p in periods if p in pivot.columns]
    pivot = pivot[cols]

    stars, em_risco, novos_destaques = [], [], []

    for cid, row in pivot.iterrows():
        vals = list(row)
        # Stars: crescimento positivo nos últimos 3 períodos disponíveis
        recent = vals[-3:] if len(vals) >= 3 else vals
        if len(recent) >= 2 and all(recent[i+1] > recent[i] * 1.05 for i in range(len(recent)-1)) and recent[-1] > 1000:
            growth = safe_pct_change(recent[-1], recent[0])
            stars.append({
                "creator": str(cid),
                "gmv_atual": round(recent[-1], 2),
                "crescimento_pct": growth,
                "tier": calc_tier(recent[-1]),
                "tendencia": [round(v, 2) for v in recent],
            })

        # Em risco: tinha GMV, caindo 2+ meses seguidos
        if len(vals) >= 3 and vals[-3] > 500:
            if vals[-2] < vals[-3] * 0.85 and vals[-1] < vals[-2] * 0.85:
                queda = safe_pct_change(vals[-1], vals[-3])
                em_risco.append({
                    "creator": str(cid),
                    "gmv_pico": round(max(vals), 2),
                    "gmv_atual": round(vals[-1], 2),
                    "queda_total_pct": queda,
                    "tier": calc_tier(vals[-1]),
                    "tendencia": [round(v, 2) for v in vals[-3:]],
                })

        # Novos destaques: apareceu no último período com GMV > 2000
        if vals[-1] > 2000 and sum(1 for v in vals[:-1] if v > 0) == 0:
            novos_destaques.append({
                "creator": str(cid),
                "gmv_estreia": round(vals[-1], 2),
                "tier": calc_tier(vals[-1]),
                "acao": "Primeira aparição com GMV relevante. Priorizar onboarding e amostra.",
            })

    # Ordena
    stars.sort(key=lambda x: -(x["crescimento_pct"] or 0))
    em_risco.sort(key=lambda x: x["queda_total_pct"] or 0)
    novos_destaques.sort(key=lambda x: -x["gmv_estreia"])

    return {
        "stars":          stars[:20],
        "em_risco":       em_risco[:20],
        "novos_destaques": novos_destaques[:10],
    }


# ── Módulo 4: Cohorts ─────────────────────────────────────────────────────────

def build_cohorts(raw: pd.DataFrame, periods) :
    cur_p  = periods[-1]
    prev_p = periods[-2] if len(periods) >= 2 else None

    cur_ids  = set(raw[(raw["periodo"] == cur_p)  & (raw["gmv_bruto"] > 0)]["creator_id"])
    prev_ids = set(raw[(raw["periodo"] == prev_p) & (raw["gmv_bruto"] > 0)]["creator_id"]) if prev_p else set()
    all_ids  = set(raw["creator_id"])

    novos       = cur_ids - prev_ids              # ativas agora, não eram antes
    recorrentes = cur_ids & prev_ids              # ativas nos dois períodos
    churned     = prev_ids - cur_ids              # eram ativas, sumiram
    dormentes   = all_ids - cur_ids - prev_ids    # nunca ativas nos últimos 2

    cur_data = raw[raw["periodo"] == cur_p].set_index("creator_id")

    def gmv_sum(ids):
        common = [i for i in ids if i in cur_data.index]
        return round(float(cur_data.loc[common, "gmv_liquido"].sum()), 2) if common else 0

    return {
        "novos":       {"count": len(novos),       "gmv": gmv_sum(novos)},
        "recorrentes": {"count": len(recorrentes), "gmv": gmv_sum(recorrentes)},
        "churned":     {"count": len(churned),     "gmv": 0},
        "dormentes":   {"count": len(dormentes),   "gmv": 0},
        "retencao_pct": round(len(recorrentes) / max(len(prev_ids), 1) * 100, 1) if prev_ids else None,
    }


# ── Módulo 5: Projeções ───────────────────────────────────────────────────────

def build_projecoes(raw: pd.DataFrame, summary: pd.DataFrame) :
    last_sum = summary.sort_values("periodo").iloc[-1]

    dias_cob  = int(last_sum.get("dias_cobertos", 0) or 0)
    dias_mes  = int(last_sum.get("dias_mes", 30) or 30)
    is_parcial = bool(last_sum.get("periodo_parcial", False))

    gmv_liq_atual = float(last_sum.get("gmv_liquido_total", 0))
    gmv_proj      = float(last_sum.get("gmv_liquido_projetado", gmv_liq_atual))

    pedidos_proj = None
    if is_parcial and dias_cob > 0:
        pedidos_atual = int(last_sum.get("pedidos_total", 0))
        pedidos_proj  = round(pedidos_atual / dias_cob * dias_mes)

    # Projeção de crescimento baseada na média dos 2 últimos meses completos
    completos = summary[~summary["periodo_parcial"].astype(str).isin(["True"])] if "periodo_parcial" in summary else summary
    if len(completos) >= 2:
        sorted_c = completos.sort_values("periodo")
        growth_rates = sorted_c["gmv_liquido_total"].pct_change().dropna()
        avg_growth = float(growth_rates.mean()) if len(growth_rates) else 0
        gmv_proximo = round(gmv_proj * (1 + avg_growth), 2)
    else:
        avg_growth = None
        gmv_proximo = None

    return {
        "periodo_atual":        str(last_sum["periodo"]),
        "is_parcial":           is_parcial,
        "dias_cobertos":        dias_cob,
        "dias_mes":             dias_mes,
        "gmv_atual":            round(gmv_liq_atual, 2),
        "gmv_projetado_mes":    round(gmv_proj, 2),
        "pedidos_projetados":   pedidos_proj,
        "crescimento_medio_pct": round(avg_growth * 100, 1) if avg_growth is not None else None,
        "gmv_proximo_periodo":  gmv_proximo,
    }


# ── Módulo 6: Health Score ────────────────────────────────────────────────────

def calc_health_score(summary: pd.DataFrame, anomalias, opps) :
    last = summary.sort_values("periodo").iloc[-1]

    score = 100.0
    fatores = []

    # Refund rate (peso 30)
    ref = float(last.get("refund_rate_pct", 0))
    if ref > 25:
        pen = min(30, (ref - 25) * 2)
        score -= pen
        fatores.append({"fator": "Refund rate", "valor": f"{ref:.1f}%", "impacto": -round(pen, 1), "status": "ruim"})
    elif ref > 15:
        pen = (ref - 15) * 1
        score -= pen
        fatores.append({"fator": "Refund rate", "valor": f"{ref:.1f}%", "impacto": -round(pen, 1), "status": "alerta"})
    else:
        fatores.append({"fator": "Refund rate", "valor": f"{ref:.1f}%", "impacto": 0, "status": "ok"})

    # Concentração top 10 (peso 20) — calculado indiretamente
    crit_anomalias = [a for a in anomalias if a["severidade"] in ("critica", "alta")]
    if len(crit_anomalias) > 5:
        pen = min(20, len(crit_anomalias) * 2)
        score -= pen
        fatores.append({"fator": "Anomalias críticas", "valor": str(len(crit_anomalias)), "impacto": -round(pen, 1), "status": "ruim"})

    # Crescimento (peso 20)
    delta_gmv = float(last.get("gmv_liquido_total_delta_pct", 0) or 0)
    if delta_gmv < -15:
        pen = min(20, abs(delta_gmv) * 0.5)
        score -= pen
        fatores.append({"fator": "GMV vs período ant.", "valor": f"{delta_gmv:.1f}%", "impacto": -round(pen, 1), "status": "ruim"})
    elif delta_gmv > 10:
        bonus = min(5, delta_gmv * 0.2)
        score = min(100, score + bonus)
        fatores.append({"fator": "GMV vs período ant.", "valor": f"+{delta_gmv:.1f}%", "impacto": round(bonus, 1), "status": "ok"})
    else:
        fatores.append({"fator": "GMV vs período ant.", "valor": f"{delta_gmv:.1f}%", "impacto": 0, "status": "neutro"})

    score = max(0, min(100, round(score, 1)))
    label = "Excelente" if score >= 80 else "Saudável" if score >= 60 else "Atenção" if score >= 40 else "Crítico"
    color = "#16a34a" if score >= 80 else "#2563eb" if score >= 60 else "#ea580c" if score >= 40 else "#dc2626"

    return {"score": score, "label": label, "color": color, "fatores": fatores}


# ── Módulo 7: Executive Brief ─────────────────────────────────────────────────

def build_executive_brief(
    summary: pd.DataFrame,
    anomalias,
    opps,
    stars_risk: dict,
    cohorts: dict,
    projecoes: dict,
    health: dict,
) :
    last = summary.sort_values("periodo").iloc[-1]
    periodo = str(last["periodo"])
    gmv_liq = float(last.get("gmv_liquido_total", 0))
    ref_rate = float(last.get("refund_rate_pct", 0))
    ativas   = int(last.get("creators_ativas", 0))
    delta    = float(last.get("gmv_liquido_total_delta_pct", 0) or 0)

    # Headline
    if health["score"] >= 80:
        headline = f"Operação saudável em {periodo} — GMV líquido {fmt_brl(gmv_liq)}, refund {ref_rate:.1f}%."
    elif health["score"] >= 60:
        headline = f"{periodo} estável com pontos de atenção — {len(anomalias)} anomalia(s) identificada(s)."
    else:
        headline = f"Período {periodo} requer ação imediata — {len([a for a in anomalias if a['severidade']=='critica'])} anomalia(s) crítica(s)."

    # Bullets
    bullets = []

    # GMV
    if projecoes["is_parcial"]:
        bullets.append(
            f"GMV atual ({projecoes['dias_cobertos']}d de {projecoes['dias_mes']}d): "
            f"{fmt_brl(gmv_liq)} → projeção mês completo: {fmt_brl(projecoes['gmv_projetado_mes'])}."
        )
    else:
        sinal = "+" if delta >= 0 else ""
        bullets.append(f"GMV líquido {fmt_brl(gmv_liq)} ({sinal}{delta:.1f}% vs período anterior).")

    # Refund
    if ref_rate > 20:
        bullets.append(f"⚠ Refund rate {ref_rate:.1f}% — acima do limite de 15%. {len([a for a in anomalias if a['tipo']=='refund_spike'])} creator(s) com spike crítico.")
    else:
        bullets.append(f"Refund rate {ref_rate:.1f}% — dentro do controle.")

    # Stars
    if stars_risk["stars"]:
        top = stars_risk["stars"][0]
        pct_str = f"+{top['crescimento_pct']:.0f}%" if top['crescimento_pct'] is not None else "crescimento"
        bullets.append(f"🚀 {len(stars_risk['stars'])} creator(s) em trajetória de crescimento. Destaque: {top['creator']} ({pct_str}).")

    # Em risco
    if stars_risk["em_risco"]:
        bullets.append(f"🔻 {len(stars_risk['em_risco'])} creator(s) em declínio consecutivo — requerem reativação.")

    # Oportunidades
    upgrades = [o for o in opps if o["tipo"] == "tier_upgrade"]
    if upgrades:
        bullets.append(f"💡 {len(upgrades)} creator(s) a menos de 15% de upgrade de tier — candidatas a meta de incentivo.")

    # Retenção
    if cohorts.get("retencao_pct") is not None:
        bullets.append(f"Retenção de creators ativas: {cohorts['retencao_pct']:.1f}% ({cohorts['recorrentes']['count']} recorrentes, {cohorts['churned']['count']} churned).")

    # Top 3 ações
    acoes = []
    criticas = [a for a in anomalias if a["severidade"] == "critica"]
    if criticas:
        acoes.append(f"URGENTE: contatar {criticas[0]['creator']} — {criticas[0]['acao']}")
    if stars_risk["em_risco"]:
        acoes.append(f"Campanha de reativação para {len(stars_risk['em_risco'])} creators em queda.")
    if upgrades:
        top_up = sorted(upgrades, key=lambda x: x["pct_faltando"])[0]
        acoes.append(f"Meta de tier: {top_up['creator']} falta apenas {fmt_brl(top_up['gmv_faltando'])} para {top_up['tier_alvo']}.")
    if not acoes:
        acoes.append("Manter cadência atual e monitorar refund semanalmente.")

    return {
        "headline":   headline,
        "bullets":    bullets,
        "acoes":      acoes[:3],
        "health_score": health["score"],
        "health_label": health["label"],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def run_analyst(warehouse_dir: Path) :
    print("\n" + "═" * 56)
    print("  Rhode Jeans — Analyst v1")
    print("═" * 56)

    raw, summary, master = load_warehouse(warehouse_dir)
    periods = sorted(raw["periodo"].unique())

    print(f"  Períodos: {periods}")
    print(f"  Creators: {raw['creator_id'].nunique()} | Registros: {len(raw)}")

    print("\n▶ Detectando anomalias...")
    anomalias = detect_anomalias(raw, periods)
    print(f"  {len(anomalias)} anomalia(s) — {len([a for a in anomalias if a['severidade']=='critica'])} crítica(s)")

    print("▶ Mapeando oportunidades...")
    opps = detect_oportunidades(raw, periods)
    print(f"  {len(opps)} oportunidade(s)")

    print("▶ Identificando stars & at-risk...")
    stars_risk = detect_stars_and_risk(raw, periods)
    print(f"  {len(stars_risk['stars'])} stars | {len(stars_risk['em_risco'])} at-risk | {len(stars_risk['novos_destaques'])} novos")

    print("▶ Construindo cohorts...")
    cohorts = build_cohorts(raw, periods)
    print(f"  Retenção: {cohorts.get('retencao_pct')}%")

    print("▶ Calculando projeções...")
    projecoes = build_projecoes(raw, summary)

    print("▶ Calculando health score...")
    health = calc_health_score(summary, anomalias, opps)
    print(f"  Health Score: {health['score']} ({health['label']})")

    print("▶ Gerando executive brief...")
    brief = build_executive_brief(summary, anomalias, opps, stars_risk, cohorts, projecoes, health)

    insights = {
        "generated_at":   date.today().isoformat(),
        "periodos":       periods,
        "periodo_atual":  periods[-1],
        "health":         health,
        "executive_brief": brief,
        "anomalias":      anomalias,
        "oportunidades":  opps,
        "stars":          stars_risk["stars"],
        "em_risco":       stars_risk["em_risco"],
        "novos_destaques": stars_risk["novos_destaques"],
        "cohorts":        cohorts,
        "projecoes":      projecoes,
    }

    out_path = warehouse_dir / "insights.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(insights, f, ensure_ascii=False, indent=2)

    print(f"\n✅ insights.json salvo em {out_path}")
    return insights


def main():
    parser = argparse.ArgumentParser(description="Rhode Analyst v1")
    parser.add_argument("--warehouse", default="warehouse")
    parser.add_argument("--sync", action="store_true", help="Enviar insights ao Google Sheets")
    args = parser.parse_args()

    insights = run_analyst(Path(args.warehouse))

    # Print resumo executivo
    print("\n── Executive Brief ──────────────────────────────────")
    print(f"  {insights['executive_brief']['headline']}")
    for b in insights["executive_brief"]["bullets"]:
        print(f"  • {b}")
    print("\n  AÇÕES:")
    for a in insights["executive_brief"]["acoes"]:
        print(f"  → {a}")
    print("─" * 56)

    if args.sync:
        print("\n▶ Sync ao Sheets não implementado neste release.")


if __name__ == "__main__":
    main()
