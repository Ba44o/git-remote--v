"""
Skill: Análise de Dados
========================
Ferramentas para análise de SKUs e métricas de negócio da Rhode Jeans.
Cada @beta_tool vira uma ferramenta que o Claude pode chamar automaticamente.
"""
import json
from anthropic import beta_tool


# Base de dados dos SKUs (em produção: conectar ao ERP Bling ou API Magazord)
DADOS_SKUS = {
    "REF516": {
        "nome": "Wide Leg Cintura Alta",
        "gmv_pct": 38.5,
        "status": "herói",
        "prioridade": "reduzir dependência",
        "meta": "< 25% do GMV",
        "estoque": "alto",
        "observacao": "SKU dominante — diversificar portfólio é urgente",
    },
    "REF549": {
        "nome": "Azul Marborizado",
        "gmv_pct": 15.0,
        "status": "crescimento",
        "prioridade": "alta",
        "tier": "Tier 1 + Tier 2",
        "observacao": "Principal foco de crescimento",
    },
    "REF551": {
        "nome": "Wide Leg Clássica",
        "gmv_pct": 12.0,
        "status": "crescimento",
        "prioridade": "alta",
        "estoque": 1256,
        "observacao": "Estoque alto — ativar creators é prioridade",
    },
    "REF562": {
        "nome": "Chocolate",
        "gmv_pct": 8.0,
        "status": "foco",
        "prioridade": "urgente",
        "gargalo": "tráfego + estoque",
        "observacao": "Precisa de criativos e tráfego pago",
    },
    "REF528": {
        "nome": "Preta Marborizada",
        "gmv_pct": 0.5,
        "status": "inativo",
        "prioridade": "ativação zero",
        "observacao": "Grande oportunidade inexplorada",
    },
    "REF559": {
        "nome": "Shorts Rosa Bebê",
        "gmv_pct": 5.0,
        "status": "foco",
        "prioridade": "média",
        "gargalo": "volume de criativos",
        "observacao": "Precisa de mais conteúdo TikTok",
    },
}


@beta_tool
def analisar_sku(ref: str) -> str:
    """Analisa o desempenho, status e prioridade de um SKU específico da Rhode Jeans.

    Args:
        ref: Referência do SKU — REF516, REF549, REF551, REF562, REF528 ou REF559
    """
    ref_upper = ref.upper()
    if ref_upper in DADOS_SKUS:
        return json.dumps(DADOS_SKUS[ref_upper], ensure_ascii=False, indent=2)

    disponiveis = ", ".join(DADOS_SKUS.keys())
    return f"SKU '{ref}' não encontrado. Disponíveis: {disponiveis}"


@beta_tool
def listar_skus_por_prioridade() -> str:
    """Lista todos os SKUs ordenados por prioridade estratégica (do mais urgente ao menos urgente)."""
    ordem = ["REF562", "REF528", "REF549", "REF551", "REF559", "REF516"]
    resultado = []
    for i, ref in enumerate(ordem, 1):
        sku = DADOS_SKUS[ref]
        resultado.append({
            "posição": i,
            "ref": ref,
            "nome": sku["nome"],
            "prioridade": sku["prioridade"],
            "gmv_pct": f"{sku['gmv_pct']}%",
        })
    return json.dumps(resultado, ensure_ascii=False, indent=2)


@beta_tool
def resumo_negocio() -> str:
    """Retorna métricas consolidadas do negócio Rhode Jeans — GMV, crescimento, equipe, canais."""
    dados = {
        "gmv_mensal": "R$ 684K",
        "unidades_vendidas": 4373,
        "ticket_medio": "R$ 170",
        "margem_bruta": "~70%",
        "seguidores_tiktok": "2M+",
        "crescimento_tiktok": "+114%",
        "recorde_wide_leg_marmorizada": "60K unidades vendidas",
        "tamanho_equipe": "8-10 pessoas (embalo, marketing, lives)",
        "erp": "Bling",
        "ecommerce": "Magazord",
        "sku_problema": "REF516 com 38.5% do GMV (meta: <25%)",
        "oportunidade_imediata": "REF528 com ativação zero",
        "meta_diversificacao": "Reduzir REF516 abaixo de 25% do GMV",
    }
    return json.dumps(dados, ensure_ascii=False, indent=2)
