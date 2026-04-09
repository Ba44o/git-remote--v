"""
Skill: Criação de Conteúdo
===========================
Ferramentas para gerar briefs criativos e calendários de conteúdo
alinhados com a identidade Rhode Jeans (brandbook).
"""
import json
from anthropic import beta_tool


# Identidade Rhode Jeans — extraída do brandbook
IDENTIDADE = {
    "cores": {
        "rose_escuro": "#B5294E",
        "carvao": "#1A1A1A",
        "off_white": "#F7F4F1",
        "bege": "#EDE8E3",
        "dourado": "#C9A882",
    },
    "personalidade": ["Direta", "Carismática", "Confiante", "Acolhedora", "Autêntica"],
    "tom_de_voz": "Direto, empoderador, sem filtros",
    "posicionamento": "Transição de custo-benefício → premium (ticket R$99+)",
    "referencias_visuais": ["Cotih", "LV Store", "CICE"],
}

# Briefs base por SKU (pode ser expandido conforme campanhas evoluem)
BRIEFS_BASE = {
    "REF516": {
        "conceito": "A calça que define sua silhueta",
        "angulos": ["perfil frontal cintura alta", "silhueta lateral completa", "detalhe cintura"],
        "hook": "POV: você finalmente encontrou a calça que faz sua silhueta",
        "cta": "Link na bio | Frete grátis acima de R$99",
        "cenario": "Ambiente neutro ou natureza, luz natural suave",
    },
    "REF549": {
        "conceito": "Cada peça é única como você",
        "angulos": ["close no padrão marborizado", "detalhe do tecido", "look completo"],
        "hook": "Essa estampa não existe igual em lugar nenhum 😱",
        "cta": "Garanta a sua antes de esgotar",
        "cenario": "Urbano ou industrial, luz dramática",
    },
    "REF551": {
        "conceito": "Wide leg que funciona no dia a dia",
        "angulos": ["look casual", "transição dia/noite", "styling minimalista"],
        "hook": "3 looks diferentes, 1 calça. Deixa eu te mostrar",
        "cta": "Disponível em todos os tamanhos",
        "cenario": "Café, rua, casa — ambientes cotidianos",
    },
    "REF562": {
        "conceito": "O neutro que completa qualquer look",
        "angulos": ["styling com tops claros", "close na cor chocolate", "monocromático bege"],
        "hook": "A cor que combina com TUDO no seu guarda-roupa",
        "cta": "Estoque limitado — não perde",
        "cenario": "Espaços bem iluminados, tons quentes",
    },
    "REF528": {
        "conceito": "O lado escuro do estilo",
        "angulos": ["look noturno", "contraste com blazer", "styling bold"],
        "hook": "Quando você quer ser elegante E fazer barulho",
        "cta": "A favorita que você ainda não descobriu",
        "cenario": "Ambiente escuro ou urbano, alto contraste",
    },
    "REF559": {
        "conceito": "Leveza com personalidade",
        "angulos": ["look de verão", "styling colorido", "outdoor / praia"],
        "hook": "Esse shorts mudou meu verão completo 🌸",
        "cta": "Perfeito pra essa estação",
        "cenario": "Outdoor, luz solar, ambiente vibrante",
    },
}


@beta_tool
def gerar_brief_criativo(ref: str, formato: str = "TikTok", duracao_segundos: int = 30) -> str:
    """Gera um brief criativo detalhado para um produto Rhode Jeans.

    Args:
        ref: Referência do produto — REF516, REF549, REF551, REF562, REF528 ou REF559
        formato: Plataforma de destino — TikTok, Reels ou Story
        duracao_segundos: Duração do vídeo em segundos (15, 30 ou 60)
    """
    ref_upper = ref.upper()
    base = BRIEFS_BASE.get(
        ref_upper,
        {
            "conceito": f"Destaque o fit e acabamento premium da {ref}",
            "angulos": ["frente", "perfil", "detalhe do tecido"],
            "hook": "Essa peça precisa de uma legenda só pra ela",
            "cta": "Link na bio",
            "cenario": "Ambiente neutro com boa iluminação",
        },
    )

    brief = {
        "produto": ref_upper,
        "plataforma": formato,
        "duracao": f"{duracao_segundos}s",
        "conceito_central": base["conceito"],
        "hook_abertura": base["hook"],
        "angulos_obrigatorios": base["angulos"],
        "cenario_recomendado": base["cenario"],
        "cta_final": base["cta"],
        "identidade_visual": {
            "cores_destaque": [
                IDENTIDADE["cores"]["rose_escuro"],
                IDENTIDADE["cores"]["bege"],
                IDENTIDADE["cores"]["off_white"],
            ],
            "tom": IDENTIDADE["tom_de_voz"],
            "personalidade": IDENTIDADE["personalidade"][:3],
        },
        "estrutura_video": {
            "0-3s": "Hook forte — prende atenção imediata",
            f"3-{duracao_segundos - 5}s": "Demonstração do produto nos ângulos obrigatórios",
            f"{duracao_segundos - 5}-{duracao_segundos}s": "CTA + logo Rhode",
        },
    }

    return json.dumps(brief, ensure_ascii=False, indent=2)


@beta_tool
def gerar_calendario_conteudo(skus: str, dias: int = 30) -> str:
    """Gera um calendário de conteúdo TikTok para os próximos N dias.

    Args:
        skus: SKUs a incluir separados por vírgula — ex: "REF549,REF551,REF562"
        dias: Período do calendário em dias — 7, 14 ou 30
    """
    lista_skus = [s.strip().upper() for s in skus.split(",")]

    tipos_conteudo = [
        "Unboxing + primeiro uso",
        "3 looks com 1 peça",
        "Behind the scenes (equipe / processo)",
        "Depoimento de cliente",
        "Dueto com tendência viral",
        "Tutorial: como lavar e conservar",
        "Reestoque ou lançamento",
    ]

    semanas = dias // 7
    calendario = {}

    for semana in range(semanas):
        semana_label = f"Semana {semana + 1}"
        calendario[semana_label] = []
        for dia in range(7):
            idx_global = semana * 7 + dia
            sku = lista_skus[idx_global % len(lista_skus)]
            tipo = tipos_conteudo[dia % len(tipos_conteudo)]
            horario = "18h–20h" if dia < 5 else "12h–14h"
            calendario[semana_label].append({
                "dia": idx_global + 1,
                "sku": sku,
                "tipo_conteudo": tipo,
                "horario_ideal": horario,
                "formato": "TikTok 9:16 vertical",
            })

    return json.dumps(
        {
            "periodo_dias": dias,
            "skus_incluidos": lista_skus,
            "frequencia": "1 post/dia",
            "calendario": calendario,
        },
        ensure_ascii=False,
        indent=2,
    )


@beta_tool
def sugerir_hashtags(ref: str, quantidade: int = 10) -> str:
    """Sugere hashtags estratégicas para um produto Rhode Jeans no TikTok.

    Args:
        ref: Referência do produto
        quantidade: Número de hashtags a gerar (máximo 15)
    """
    hashtags_base = [
        "#RhodeJeans", "#WideLeg", "#ModaFeminina", "#TikTokShop",
        "#CalcaWideLeg", "#OOTDFeminino", "#LookDodia", "#ModaBrasileira",
        "#TikTokModa", "#Outfitinspo",
    ]

    hashtags_por_sku = {
        "REF516": ["#CinturaAlta", "#SilhuetaPerfeita", "#WideLegCinturaAlta"],
        "REF549": ["#EstampaMarmorizada", "#PecaUnica", "#ModaUnica"],
        "REF551": ["#LookCasual", "#StyleVersátil", "#CalcaCoringa"],
        "REF562": ["#TomChocolate", "#NeutroElegante", "#LookMinimalista"],
        "REF528": ["#PretoMarmorizado", "#LookBold", "#EstiloArrojado"],
        "REF559": ["#ShortsRosa", "#LookVerao", "#ModaPraia"],
    }

    especificas = hashtags_por_sku.get(ref.upper(), [])
    todas = (hashtags_base + especificas)[:quantidade]

    return json.dumps(
        {"produto": ref.upper(), "hashtags": todas, "dica": "Use 3-5 grandes + 5-7 de nicho"},
        ensure_ascii=False,
        indent=2,
    )
