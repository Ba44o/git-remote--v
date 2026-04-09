"""
Agente de Marketing Rhode Jeans
=================================
Orquestrador principal que coordena todos os "braços" especializados.

Arquitetura:
                    ┌─────────────────────┐
                    │  ORQUESTRADOR (main) │
                    └──────────┬──────────┘
                               │ decide qual fluxo usar
     ┌──────────────┬──────────┼──────────┬──────────────┐
     ▼              ▼          ▼          ▼              ▼
  [Skill:       [Skill:    [Skill:    [Skill:        [Skill:
 Análise]      Conteúdo]  Arquivos]  Creators]      Seeding]
     │              │          │          │              │
     └──────────────┴──────────┴──────────┴──────────────┘
                               │
             ┌─────────────────┴─────────────────┐
             ▼                                   ▼
    [Fluxo: Campanha SKU]           [Fluxo: Creators & Seeding]
    (análise → brief → calendário)  (prospecção → briefs → envios)

Uso:
    python main.py                          # modo interativo
    python main.py "analise o REF562"       # tarefa direta
"""
import sys
from pathlib import Path

import anthropic

# Importa todas as skills disponíveis
from skills.analisar_dados import analisar_sku, listar_skus_por_prioridade, resumo_negocio
from skills.criar_conteudo import (
    gerar_brief_criativo,
    gerar_calendario_conteudo,
    sugerir_hashtags,
)
from skills.ler_arquivos import ler_estrategia, listar_arquivos_projeto, ler_arquivo_por_nome
from skills.gestao_creators import (
    buscar_creators,
    adicionar_creator,
    gerar_mensagem_outreach,
    listar_todos_creators,
)
from skills.seeding import (
    registrar_envio,
    atualizar_status_seeding,
    listar_pendencias_followup,
    relatorio_seeding,
)

# Importa os fluxos
from fluxos.campanha_sku import executar_campanha
from fluxos.fluxo_creators import executar_fluxo_creators

client = anthropic.Anthropic()

# ── System Prompt do Orquestrador ────────────────────────────────────────────
SYSTEM = """Você é o Agente de Marketing da Rhode Jeans — marca de moda feminina especializada em Wide Leg.

Sua missão é coordenar análises estratégicas e criação de conteúdo de forma inteligente.

Contexto do negócio:
- GMV: R$684K/mês | 4.373 unidades | ticket R$170 | margem ~70%
- TikTok: 2M+ seguidores | +114% crescimento
- Problema principal: REF516 com 38.5% do GMV (meta: <25%)
- SKUs prioritários: REF549 (Azul Marborizado), REF551 (Wide Leg Clássica), REF562 (Chocolate)
- Oportunidade: REF528 com ativação zero

Identidade Rhode: Direta, Carismática, Confiante. Cores: Rose #B5294E, Carvão, Off-White, Bege.

Como trabalhar:
1. Sempre use as ferramentas para buscar dados antes de recomendar
2. Para campanhas completas, avise que pode executar o fluxo multi-agentes
3. Para gestão de creators: busque, filtre e gere outreach personalizado
4. Para seeding: registre envios, atualize status e monitore follow-ups
5. Seja estratégico e direto — sem rodeios

Fale sempre em português."""

# ── Todas as ferramentas disponíveis ─────────────────────────────────────────
TODAS_SKILLS = [
    # Análise
    analisar_sku,
    listar_skus_por_prioridade,
    resumo_negocio,
    # Conteúdo
    gerar_brief_criativo,
    gerar_calendario_conteudo,
    sugerir_hashtags,
    # Arquivos
    ler_estrategia,
    listar_arquivos_projeto,
    ler_arquivo_por_nome,
    # Creators
    buscar_creators,
    adicionar_creator,
    gerar_mensagem_outreach,
    listar_todos_creators,
    # Seeding
    registrar_envio,
    atualizar_status_seeding,
    listar_pendencias_followup,
    relatorio_seeding,
]


def executar_tarefa(tarefa: str) -> str:
    """
    Executa uma tarefa usando o orquestrador com todas as skills disponíveis.
    O Claude decide automaticamente quais ferramentas usar e em que ordem.
    """
    runner = client.beta.messages.tool_runner(
        model="claude-opus-4-6",
        max_tokens=4096,
        thinking={"type": "adaptive"},
        system=SYSTEM,
        tools=TODAS_SKILLS,
        messages=[{"role": "user", "content": tarefa}],
    )

    textos = []
    for message in runner:
        for block in message.content:
            if hasattr(block, "text"):
                textos.append(block.text)

    return "\n".join(textos)


def modo_interativo():
    """Loop de conversa interativa com o agente."""
    print("\n" + "=" * 60)
    print("  AGENTE RHODE JEANS — Marketing & Estratégia")
    print("=" * 60)
    print("Comandos especiais:")
    print("  /campanha REF562     → Fluxo completo de campanha (análise + brief + calendário)")
    print("  /creators REF549     → Fluxo de creators (prospecção + outreach + seeding)")
    print("  /seeding             → Relatório do pipeline de seeding")
    print("  /followup            → Lista pendências de follow-up com creators")
    print("  /skus                → Lista SKUs por prioridade")
    print("  /sair                → Encerra")
    print("=" * 60 + "\n")

    while True:
        try:
            entrada = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAté logo!")
            break

        if not entrada:
            continue

        if entrada.lower() in ("/sair", "sair", "exit", "quit"):
            print("Até logo!")
            break

        # Comando especial: fluxo completo de campanha
        if entrada.lower().startswith("/campanha"):
            partes = entrada.split()
            sku = partes[1].upper() if len(partes) > 1 else "REF562"
            resultado = executar_campanha(sku)
            for etapa, conteudo in resultado.items():
                print(f"\n## {etapa.upper()}")
                print(conteudo)
            print()
            continue

        # Comando especial: fluxo de creators
        if entrada.lower().startswith("/creators"):
            partes = entrada.split()
            sku = partes[1].upper() if len(partes) > 1 else "REF549"
            nicho = " ".join(partes[2:]) if len(partes) > 2 else "moda feminina"
            resultado = executar_fluxo_creators(sku, nicho)
            for etapa, conteudo in resultado.items():
                print(f"\n## {etapa.upper()}")
                print(conteudo)
            print()
            continue

        # Comando especial: relatório de seeding
        if entrada.lower() in ("/seeding", "seeding"):
            print(relatorio_seeding())
            print()
            continue

        # Comando especial: pendências de follow-up
        if entrada.lower() in ("/followup", "followup"):
            print(listar_pendencias_followup())
            print()
            continue

        # Comando especial: listar SKUs
        if entrada.lower() in ("/skus", "skus"):
            from skills.analisar_dados import listar_skus_por_prioridade as _listar
            print(_listar())
            print()
            continue

        # Tarefa livre para o orquestrador
        print("\nAgente: ", end="", flush=True)
        resposta = executar_tarefa(entrada)
        print(resposta)
        print()


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Tarefa passada como argumento: python main.py "analise o REF562"
        tarefa = " ".join(sys.argv[1:])
        print(f"\nTarefa: {tarefa}\n")
        print(executar_tarefa(tarefa))
    else:
        # Modo interativo
        modo_interativo()
