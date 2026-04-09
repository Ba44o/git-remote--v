"""
Fluxo: Campanha Completa por SKU
==================================
Workflow multi-etapas que encadeia 3 agentes especializados:

  [Agente Analista] → [Agente Criativo] → [Agente de Calendário]
         ↓                    ↓                      ↓
    Dados do SKU         Brief TikTok          Plano 30 dias

Cada etapa alimenta a próxima com contexto acumulado.
"""
import sys
from pathlib import Path

import anthropic

# Resolve imports relativos ao pacote raiz
sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.analisar_dados import analisar_sku, resumo_negocio, listar_skus_por_prioridade
from skills.criar_conteudo import gerar_brief_criativo, gerar_calendario_conteudo, sugerir_hashtags
from skills.ler_arquivos import ler_estrategia

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


def executar_campanha(sku: str) -> dict[str, str]:
    """
    Executa o fluxo completo de campanha para um SKU.

    Etapas:
    1. Analista  — levanta dados e contexto do SKU
    2. Criativo  — cria brief baseado nos dados
    3. Calendário — monta plano de 30 dias com o brief como base

    Returns:
        Dict com as saídas de cada etapa: analise, brief, calendario
    """
    print(f"\n🚀 Fluxo de campanha para {sku}")
    print("=" * 50)

    resultados = {}

    # ── Etapa 1: Análise ──────────────────────────────────────────────────────
    resultados["analise"] = _executar_agente(
        nome="Agente Analista",
        system=(
            "Você é um analista de dados de e-commerce especialista em moda feminina. "
            "Use as ferramentas para levantar dados concretos e identificar oportunidades. "
            "Seja objetivo e destaque os 3 pontos mais importantes."
        ),
        tools=[analisar_sku, resumo_negocio, ler_estrategia],
        tarefa=(
            f"Analise o {sku} no contexto atual da Rhode Jeans. "
            "Quais são os principais pontos de atenção, oportunidades e o que precisa ser feito?"
        ),
    )

    # ── Etapa 2: Brief Criativo ───────────────────────────────────────────────
    # Passa o contexto da análise para o agente criativo
    resultados["brief"] = _executar_agente(
        nome="Agente Criativo",
        system=(
            "Você é um diretor criativo especialista em TikTok Shop e moda feminina. "
            "Crie briefs impactantes alinhados com a identidade Rhode Jeans. "
            "Baseie suas escolhas nos dados fornecidos pelo analista."
        ),
        tools=[gerar_brief_criativo, sugerir_hashtags],
        tarefa=(
            f"Com base nessa análise:\n\n{resultados['analise']}\n\n"
            f"Crie um brief criativo completo para o {sku} no TikTok (30 segundos). "
            "Inclua hashtags estratégicas e explique as escolhas criativas."
        ),
    )

    # ── Etapa 3: Calendário ───────────────────────────────────────────────────
    # Passa análise + brief para montar o calendário
    resultados["calendario"] = _executar_agente(
        nome="Agente de Calendário",
        system=(
            "Você é um social media manager especialista em TikTok Shop. "
            "Monte calendários de conteúdo realistas e executáveis. "
            "Considere a capacidade de produção da equipe (8-10 pessoas)."
        ),
        tools=[gerar_calendario_conteudo, listar_skus_por_prioridade],
        tarefa=(
            f"Com base nessa análise e brief:\n\n"
            f"ANÁLISE: {resultados['analise'][:500]}...\n"
            f"BRIEF: {resultados['brief'][:500]}...\n\n"
            f"Monte um calendário de 30 dias para o TikTok focado no {sku}. "
            "Inclua os SKUs complementares conforme prioridade estratégica."
        ),
    )

    print("\n✅ Campanha concluída!\n")
    return resultados


if __name__ == "__main__":
    # Exemplo: campanha para o REF562 (urgente — gargalo de tráfego + estoque)
    resultado = executar_campanha("REF562")

    print("\n" + "=" * 60)
    print("RESULTADO FINAL DA CAMPANHA")
    print("=" * 60)

    for etapa, conteudo in resultado.items():
        print(f"\n## {etapa.upper()}")
        print("-" * 40)
        print(conteudo)
