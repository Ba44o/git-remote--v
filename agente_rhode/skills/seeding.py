"""
Skill: Seeding — Gestão de Envios para Creators
=================================================
Rastreia todo o pipeline de seeding: desde a seleção do creator
até o post publicado (ou follow-up por falta de conteúdo).

Pipeline de status:
  selecionado → enviado → entregue → postou
                                   ↘ nao_postou → followup_enviado
"""
import json
from datetime import date, timedelta
from pathlib import Path
from anthropic import beta_tool

DATA_SEEDING = Path(__file__).parent.parent / "data" / "seeding.json"
DATA_CREATORS = Path(__file__).parent.parent / "data" / "creators.json"

STATUS_VALIDOS = ["selecionado", "enviado", "entregue", "postou", "nao_postou", "followup_enviado"]


def _carregar_seeding() -> dict:
    return json.loads(DATA_SEEDING.read_text(encoding="utf-8"))


def _salvar_seeding(dados: dict) -> None:
    DATA_SEEDING.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def _carregar_creators() -> dict:
    return json.loads(DATA_CREATORS.read_text(encoding="utf-8"))


@beta_tool
def registrar_envio(creator_id: str, sku: str, data_envio: str = "") -> str:
    """Registra o envio de um produto para um creator no pipeline de seeding.

    Args:
        creator_id: ID do creator — ex: c001
        sku: SKU enviado — ex: REF549
        data_envio: Data do envio no formato YYYY-MM-DD (deixe vazio para hoje)
    """
    creators_data = _carregar_creators()
    creator = next((c for c in creators_data["creators"] if c["id"] == creator_id), None)
    if not creator:
        return json.dumps({"erro": f"Creator {creator_id} não encontrado."})

    dados = _carregar_seeding()
    envio_id = f"s{len(dados['envios']) + 1:03d}"
    data = data_envio or date.today().isoformat()
    prazo_post = (date.fromisoformat(data) + timedelta(days=14)).isoformat()

    envio = {
        "id": envio_id,
        "creator_id": creator_id,
        "creator_nome": creator["nome"],
        "creator_perfil": creator["perfil_tiktok"],
        "sku": sku.upper(),
        "status": "enviado",
        "data_envio": data,
        "prazo_esperado_post": prazo_post,
        "data_entrega": None,
        "data_post": None,
        "link_post": None,
        "followup_enviado": False,
        "notas": "",
    }

    dados["envios"].append(envio)
    _salvar_seeding(dados)

    # Atualiza lista de SKUs enviados no creator
    for c in creators_data["creators"]:
        if c["id"] == creator_id and sku.upper() not in c["skus_enviados"]:
            c["skus_enviados"].append(sku.upper())
    DATA_CREATORS.write_text(json.dumps(creators_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return json.dumps(
        {"sucesso": True, "id": envio_id, "prazo_post": prazo_post, "envio": envio},
        ensure_ascii=False,
        indent=2,
    )


@beta_tool
def atualizar_status_seeding(envio_id: str, novo_status: str, link_post: str = "", notas: str = "") -> str:
    """Atualiza o status de um envio no pipeline de seeding.

    Args:
        envio_id: ID do envio — ex: s001
        novo_status: Novo status — selecionado | enviado | entregue | postou | nao_postou | followup_enviado
        link_post: URL do post TikTok (somente quando status = postou)
        notas: Observações adicionais
    """
    if novo_status not in STATUS_VALIDOS:
        return json.dumps({"erro": f"Status inválido. Use: {', '.join(STATUS_VALIDOS)}"})

    dados = _carregar_seeding()
    envio = next((e for e in dados["envios"] if e["id"] == envio_id), None)
    if not envio:
        return json.dumps({"erro": f"Envio {envio_id} não encontrado."})

    envio["status"] = novo_status
    if notas:
        envio["notas"] = notas
    if link_post:
        envio["link_post"] = link_post
    if novo_status == "entregue":
        envio["data_entrega"] = date.today().isoformat()
    if novo_status == "postou":
        envio["data_post"] = date.today().isoformat()
    if novo_status == "followup_enviado":
        envio["followup_enviado"] = True

    _salvar_seeding(dados)
    return json.dumps({"sucesso": True, "envio": envio}, ensure_ascii=False, indent=2)


@beta_tool
def listar_pendencias_followup() -> str:
    """Lista todos os envios que estão com prazo vencido sem post e precisam de follow-up."""
    dados = _carregar_seeding()
    hoje = date.today()
    pendentes = []

    for e in dados["envios"]:
        if e["status"] in ("postou", "followup_enviado"):
            continue
        prazo = date.fromisoformat(e["prazo_esperado_post"])
        dias_atraso = (hoje - prazo).days

        if dias_atraso >= 0:
            pendentes.append({
                "id": e["id"],
                "creator": e["creator_nome"],
                "perfil": e["creator_perfil"],
                "sku": e["sku"],
                "status_atual": e["status"],
                "prazo_era": e["prazo_esperado_post"],
                "dias_em_atraso": dias_atraso,
                "followup_ja_enviado": e["followup_enviado"],
            })

    pendentes.sort(key=lambda x: x["dias_em_atraso"], reverse=True)

    if not pendentes:
        return json.dumps({"mensagem": "Nenhuma pendência de follow-up! Tudo em dia ✅"})

    return json.dumps(
        {"total_pendentes": len(pendentes), "pendencias": pendentes},
        ensure_ascii=False,
        indent=2,
    )


@beta_tool
def relatorio_seeding() -> str:
    """Retorna relatório completo do pipeline de seeding — quantos em cada status, conversão de posts."""
    dados = _carregar_seeding()
    envios = dados["envios"]

    if not envios:
        return json.dumps({"mensagem": "Nenhum envio registrado ainda. Use registrar_envio para começar."})

    contagem = {s: 0 for s in STATUS_VALIDOS}
    por_sku: dict[str, dict] = {}

    for e in envios:
        contagem[e["status"]] = contagem.get(e["status"], 0) + 1
        sku = e["sku"]
        if sku not in por_sku:
            por_sku[sku] = {"enviados": 0, "postaram": 0}
        por_sku[sku]["enviados"] += 1
        if e["status"] == "postou":
            por_sku[sku]["postaram"] += 1

    total = len(envios)
    postaram = contagem.get("postou", 0)
    taxa_conversao = round((postaram / total) * 100, 1) if total else 0

    for sku, stats in por_sku.items():
        stats["taxa_conversao"] = (
            f"{round((stats['postaram'] / stats['enviados']) * 100, 1)}%"
            if stats["enviados"] else "0%"
        )

    return json.dumps(
        {
            "total_envios": total,
            "taxa_conversao_geral": f"{taxa_conversao}%",
            "por_status": contagem,
            "por_sku": por_sku,
        },
        ensure_ascii=False,
        indent=2,
    )
