"""
Fluxo: Creators & Seeding
===========================
Workflow que encadeia 3 agentes para montar e executar
uma estratégia completa de creators para um SKU.

  [Agente de Prospecção] → [Agente de Briefs] → [Agente de Seeding]
           ↓                        ↓                     ↓
   Lista de creators         Brief + outreach        Plano de envios
   filtrados por fit         personalizados          + alertas follow-up
"""
import sys
from pathlib import Path

import anthropic

sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.gestao_creators import buscar_creators, gerar_mensagem_outreach, listar_todos_creators
from skills.seeding import relatorio_seeding, listar_pendencias_followup
from skills.criar_conteudo import gerar_brief_criativo, sugerir_hashtags
from skills.analisar_dados import analisar_sku

client = anthropic.Anthropic()


def _executar_agente(nome: str, system: str, tools: list, tarefa: str) -> str:
    """Executa um agente especializado e retorna o texto da resposta final."""
    print(f"  → {nome}...")

    runner = client.beta.messages.tool_runner(
        model="claude-opus-4-6",
        max_tokens=2048,
        thinking={"type": "adaptive"},
        system=system,
        tools=tools,
        messages=[{"role": "user", "content": tarefa}],
    )

    textos = []
    for message in runner:
        for block in message.content:
            if hasattr(block, "text"):
                textos.append(block.text)

    return "\n".join(textos)


def executar_fluxo_creators(sku: str, nicho: str = "moda feminina") -> dict[str, str]:
    """
    Executa o fluxo completo de creators para um SKU.

    Etapas:
    1. Prospecção — identifica os creators com melhor fit
    2. Briefs     — gera briefs e mensagens de outreach personalizadas
    3. Seeding    — monta plano de envio e lista pendências de follow-up

    Args:
        sku: SKU alvo — ex: REF549
        nicho: Nicho para filtrar creators — ex: "wide leg"
    """
    print(f"\n🎯 Fluxo de Creators para {sku}")
    print("=" * 50)

    resultados = {}

    # ── Etapa 1: Prospecção ───────────────────────────────────────────────────
    resultados["prospeccao"] = _executar_agente(
        nome="Agente de Prospecção",
        system=(
            "Você é um talent manager especialista em influencer marketing para moda feminina no TikTok. "
            "Sua missão é identificar os creators com maior potencial de conversão para a Rhode Jeans. "
            "Priorize engajamento real e fit de nicho acima de volume de seguidores."
        ),
        tools=[buscar_creators, listar_todos_creators, analisar_sku],
        tarefa=(
            f"Analise o {sku} e encontre os melhores creators para uma campanha de seeding. "
            f"Busque por nicho '{nicho}' e filtre por taxa de engajamento mínima de 4%. "
            "Liste os top 3 creators recomendados com justificativa para cada escolha."
        ),
    )

    # ── Etapa 2: Briefs & Outreach ────────────────────────────────────────────
    resultados["briefs"] = _executar_agente(
        nome="Agente de Briefs",
        system=(
            "Você é um diretor criativo e copywriter especialista em TikTok Shop e moda feminina. "
            "Crie briefs claros para creators e mensagens de outreach que convertam. "
            "Tom: próximo, direto, empoderador — nunca corporativo."
        ),
        tools=[gerar_brief_criativo, sugerir_hashtags, gerar_mensagem_outreach],
        tarefa=(
            f"Com base nessa seleção de creators:\n\n{resultados['prospeccao']}\n\n"
            f"Para o {sku}:\n"
            "1. Gere o brief criativo para os creators usarem\n"
            "2. Gere mensagens de outreach personalizadas para os top 2 creators (use os IDs c001 a c005)\n"
            "3. Sugira as hashtags que os creators devem usar no post"
        ),
    )

    # ── Etapa 3: Plano de Seeding ─────────────────────────────────────────────
    resultados["seeding"] = _executar_agente(
        nome="Agente de Seeding",
        system=(
            "Você é um operations manager especialista em programas de seeding e afiliados. "
            "Monte planos de envio realistas e crie alertas de follow-up proativos. "
            "Seja preciso com prazos e status."
        ),
        tools=[relatorio_seeding, listar_pendencias_followup],
        tarefa=(
            f"Com base na seleção de creators e briefs:\n\n{resultados['briefs'][:600]}...\n\n"
            "1. Verifique o status atual do pipeline de seeding (relatório geral)\n"
            "2. Liste as pendências de follow-up que precisam de ação imediata\n"
            "3. Monte um plano de ação: quais envios fazer primeiro e por quê\n"
            "4. Dê um checklist executável para a equipe de embalo"
        ),
    )

    print("\n✅ Fluxo de creators concluído!\n")
    return resultados


if __name__ == "__main__":
    resultado = executar_fluxo_creators("REF549", nicho="wide leg")

    print("\n" + "=" * 60)
    print("RESULTADO — FLUXO DE CREATORS")
    print("=" * 60)

    for etapa, conteudo in resultado.items():
        print(f"\n## {etapa.upper()}")
        print("-" * 40)
        print(conteudo)
