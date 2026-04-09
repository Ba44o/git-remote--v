"""
Skill: Gestão de Creators/Afiliados
=====================================
Ferramentas para buscar, filtrar e se comunicar com creators TikTok
para o programa de afiliados da Rhode Jeans.

Tiers:
  nano  → 1K–50K seguidores  | engajamento > 6%
  micro → 50K–200K           | engajamento > 4%
  mid   → 200K–1M            | engajamento > 3%
  macro → 1M+                | engajamento > 2%
"""
import json
from pathlib import Path
from anthropic import beta_tool

DATA_FILE = Path(__file__).parent.parent / "data" / "creators.json"


def _carregar() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def _salvar(dados: dict) -> None:
    DATA_FILE.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


@beta_tool
def buscar_creators(
    nicho: str = "",
    tier: str = "",
    min_engajamento: float = 0.0,
    min_seguidores: int = 0,
    max_seguidores: int = 10_000_000,
) -> str:
    """Busca creators no banco de dados filtrados por nicho, tier e métricas.

    Args:
        nicho: Palavra-chave do nicho — ex: "wide leg", "moda feminina", "tiktokshop"
        tier: Filtrar por tier — nano, micro, mid ou macro (deixe vazio para todos)
        min_engajamento: Taxa de engajamento mínima em % — ex: 4.0
        min_seguidores: Mínimo de seguidores — ex: 50000
        max_seguidores: Máximo de seguidores — ex: 500000
    """
    dados = _carregar()
    resultado = []

    for c in dados["creators"]:
        if c["status"] != "ativo":
            continue
        if tier and c["tier"] != tier:
            continue
        if c["taxa_engajamento"] < min_engajamento:
            continue
        if not (min_seguidores <= c["seguidores"] <= max_seguidores):
            continue
        if nicho and not any(nicho.lower() in n.lower() for n in c["nicho"]):
            continue

        resultado.append({
            "id": c["id"],
            "nome": c["nome"],
            "perfil": c["perfil_tiktok"],
            "seguidores": c["seguidores"],
            "engajamento": f"{c['taxa_engajamento']}%",
            "tier": c["tier"],
            "nicho": c["nicho"],
            "cidade": c["cidade"],
            "skus_ja_recebidos": c["skus_enviados"],
            "observacoes": c.get("observacoes", ""),
        })

    if not resultado:
        return json.dumps({"encontrados": 0, "mensagem": "Nenhum creator encontrado com esses filtros."})

    return json.dumps({"encontrados": len(resultado), "creators": resultado}, ensure_ascii=False, indent=2)


@beta_tool
def adicionar_creator(
    nome: str,
    perfil_tiktok: str,
    seguidores: int,
    taxa_engajamento: float,
    nicho: str,
    cidade: str = "",
    observacoes: str = "",
) -> str:
    """Adiciona um novo creator ao banco de dados da Rhode Jeans.

    Args:
        nome: Nome completo do creator
        perfil_tiktok: @ do TikTok — ex: @nomecreator
        seguidores: Número de seguidores atual
        taxa_engajamento: Taxa de engajamento média em % — ex: 5.2
        nicho: Nichos separados por vírgula — ex: "moda feminina, ootd, wide leg"
        cidade: Cidade do creator
        observacoes: Notas internas sobre o creator
    """
    dados = _carregar()

    # Verifica duplicata
    for c in dados["creators"]:
        if c["perfil_tiktok"].lower() == perfil_tiktok.lower():
            return json.dumps({"erro": f"Creator {perfil_tiktok} já existe no banco."})

    # Define tier automaticamente
    if seguidores < 50_000:
        tier = "nano"
    elif seguidores < 200_000:
        tier = "micro"
    elif seguidores < 1_000_000:
        tier = "mid"
    else:
        tier = "macro"

    novo_id = f"c{len(dados['creators']) + 1:03d}"
    novo = {
        "id": novo_id,
        "nome": nome,
        "perfil_tiktok": perfil_tiktok,
        "seguidores": seguidores,
        "taxa_engajamento": taxa_engajamento,
        "nicho": [n.strip() for n in nicho.split(",")],
        "tier": tier,
        "cidade": cidade,
        "status": "ativo",
        "skus_enviados": [],
        "observacoes": observacoes,
    }

    dados["creators"].append(novo)
    _salvar(dados)

    return json.dumps(
        {"sucesso": True, "id": novo_id, "tier_atribuido": tier, "creator": novo},
        ensure_ascii=False,
        indent=2,
    )


@beta_tool
def gerar_mensagem_outreach(creator_id: str, sku: str) -> str:
    """Gera uma mensagem personalizada de outreach para convidar um creator para seeding.

    Args:
        creator_id: ID do creator — ex: c001
        sku: SKU do produto a enviar — ex: REF549
    """
    dados = _carregar()
    creator = next((c for c in dados["creators"] if c["id"] == creator_id), None)

    if not creator:
        return json.dumps({"erro": f"Creator {creator_id} não encontrado."})

    briefings_sku = {
        "REF516": ("Wide Leg Cintura Alta", "define a silhueta com perfeição"),
        "REF549": ("Azul Marborizado", "tem estampa única — nenhuma igual à outra"),
        "REF551": ("Wide Leg Clássica", "funciona em qualquer look do dia a dia"),
        "REF562": ("Chocolate", "é o neutro que combina com tudo no guarda-roupa"),
        "REF528": ("Preta Marborizada", "é elegante e faz barulho ao mesmo tempo"),
        "REF559": ("Shorts Rosa Bebê", "traz leveza e personalidade pra qualquer look"),
    }

    sku_upper = sku.upper()
    nome_produto, gancho = briefings_sku.get(sku_upper, (sku_upper, "tem o fit Rhode"))

    primeiro_nome = creator["nome"].split()[0]

    mensagem = f"""Oi, {primeiro_nome}! 👋

Sou da Rhode Jeans — a marca de Wide Leg que tá bombando no TikTok Shop 🚀

Vi seu conteúdo de {creator['nicho'][0]} e achei que você ia amar nossa {nome_produto} ({sku_upper}) — que {gancho}.

A gente queria te enviar uma peça pra você experimentar e, se curtir, criar um conteúdo autêntico do seu jeito. Sem roteiro engessado — só você mostrando o look real.

Temos 2M+ seguidores e nossos creators têm uma ótima taxa de conversão no TikTok Shop 🛍️

Topa? Me responde aqui que te mando os detalhes do envio 🌹

— Equipe Rhode Jeans"""

    return json.dumps(
        {
            "creator": creator["nome"],
            "perfil": creator["perfil_tiktok"],
            "produto": f"{sku_upper} — {nome_produto}",
            "mensagem": mensagem,
        },
        ensure_ascii=False,
        indent=2,
    )


@beta_tool
def listar_todos_creators() -> str:
    """Lista todos os creators cadastrados com resumo de status e métricas."""
    dados = _carregar()

    resumo = []
    for c in dados["creators"]:
        resumo.append({
            "id": c["id"],
            "nome": c["nome"],
            "perfil": c["perfil_tiktok"],
            "tier": c["tier"],
            "seguidores": c["seguidores"],
            "engajamento": f"{c['taxa_engajamento']}%",
            "status": c["status"],
            "skus_enviados": c["skus_enviados"],
        })

    por_tier = {}
    for c in resumo:
        t = c["tier"]
        por_tier.setdefault(t, []).append(c)

    return json.dumps(
        {"total": len(resumo), "por_tier": por_tier},
        ensure_ascii=False,
        indent=2,
    )
