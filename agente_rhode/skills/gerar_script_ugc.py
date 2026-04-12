"""
Skill: Gerador de Script UGC
==============================
Gera scripts UGC personalizados para creators da Rhode Jeans
com base nos padrões extraídos de 194 vídeos de alta performance.

Integra com o orquestrador via tool_use do Anthropic SDK.
"""
import json
from pathlib import Path

# ── Padrões extraídos da análise de 194 vídeos validados ─────────────────────
# Fonte: /App/ugc-transcriber/analises/relatorio_padroes.json

PADROES_MARCA = {
    "hook_universal": "[Chamada íntima para 'amigas'] + [Emoção forte: paixão, surpresa ou descoberta] + [Referência ao problema/desejo específico OU validação social]",
    "estrutura_universal": "Hook emocional (0-5s) → Apresentação com contexto real (5-15s) → Prova no corpo com medidas (15-40s) → Ancoragem de valor vs marca cara (40-55s) → Benefícios emocionais (55-65s) → CTA suave carrinho laranja (65-75s)",
    "gatilhos_emocionais": [
        "Pertencimento: uso de 'amigas', tom confessional, compartilhando um segredo",
        "Inteligência de consumo: ancoragem Zara/R$200+ vs preço real abaixo de R$100",
        "Validação corporal: como a calça transforma a silhueta (bumbum, cintura)",
        "Urgência suave: 'vê se ainda tem o seu tamanho', 'corre que tá em promoção'",
        "Surpresa e descoberta: arco 'não acreditava → experimentei → fiquei chocada'",
    ],
    "padroes_por_produto": {
        "Wide Leg Marmorizada": {
            "hooks_top": [
                "Declaração de paixão — 'Eu sou simplesmente apaixonada por essa calça'",
                "Viralização — 'A calça mais viralizada do TikTok realmente vale cada centavo'",
                "Problema corporal — 'Amigas do popotão grandão com dificuldade de achar calça boa'",
                "Urgência — 'Amigas, para tudo. Olha o que eu descobri. Eu juro que nunca vi nada igual'",
                "Uso repetido — 'Eu tô usando essa calça pela quinta vez na semana'",
            ],
            "insights": [
                "Comparação com Zara é o maior motor de conversão desse SKU",
                "Especificidade corporal (altura + peso + quadril) elimina medo de não servir",
                "Reação genuína de surpresa supera review descritivo",
            ],
        },
        "Wide Leg Rosa Bebê": {
            "hooks_top": [
                "Surpresa pessoal — 'Eu não imaginava que eu precisava de uma calça rosa até eu ter uma'",
                "Quebra de objeção — 'Ah, eu só compro calça de grife. Amiga, para. Pega a referência aqui'",
                "Descoberta — 'Só compro calça direto da fábrica depois que descobri essa loja'",
                "Momento especial — 'Hoje é meu aniversário e vou estrear essa calça rosa'",
                "Validação social — 'Comprei a calça rosa viralizada do TikTok. Vamos levar comigo?'",
            ],
            "insights": [
                "'Direto da fábrica' justifica preço baixo + qualidade alta",
                "Ancoragem Zara + preço real < R$100 cria efeito de 'hackeando o sistema de moda'",
                "Medidas reais + reações de terceiros = prova social mais poderosa",
            ],
        },
        "Wide Leg Azul Médio": {
            "hooks_top": [
                "GRWM — 'Tô me arrumando pra sair e queria mostrar esse look'",
                "Revelação emocional — 'Esse jeans, eu sou apaixonada'",
                "Ocasião prática — 'Preciso de um look prático pra resolver coisas na rua'",
            ],
            "insights": [
                "GRWM esconde o conteúdo publicitário e aumenta autenticidade",
                "Benefício emocional supera funcional: 'me sinto arrumada sem esforço'",
                "CTA com escassez implícita mantém tom autêntico",
            ],
        },
    },
    "ctas_validados": [
        "Vou deixar o link aqui no carrinho laranja. Vê se ainda tem o seu tamanho.",
        "Corre que tá com promoção — link no carrinho laranja.",
        "Depois volta aqui pra me agradecer. Link tá no carrinho.",
        "Garanta a sua antes de acabar — carrinho laranja aqui embaixo.",
        "Confere se ainda tem da sua numeração. Link no carrinho.",
    ],
}

FORMATOS = {
    "30s": "Vídeo curto: hook direto + prova rápida no corpo + CTA",
    "60s": "Vídeo completo: hook + apresentação + prova + ancoragem de valor + CTA",
    "90s": "Narrativa completa: comparação de marcas + múltiplos benefícios + CTA",
    "live": "Live TikTok Shop: abertura + demonstração ao vivo + Q&A + CTAs repetidos",
    "brief": "Brief criativo: orientações para a creator gravar sem script fixo",
}

PRODUTOS = [
    "Wide Leg Marmorizada", "Wide Leg Rosa Bebê", "Wide Leg Azul Médio",
    "Wide Leg Preta", "Wide Leg Branca", "Wide Leg Chocolate",
    "Wide Leg Amarelo Manteiga", "Wide Leg Stone Used", "Wide Leg Sky Used",
    "Wide Leg Preta Marmorizada",
]


# ── Tool definitions para o orquestrador ────────────────────────────────────

def gerar_script_ugc(
    produto: str,
    formato: str,
    nome_creator: str,
    altura: str,
    peso: str,
    quadril: str,
    tamanho: str,
    cintura: str = "",
    tom: str = "descontraído, como amiga",
    preco: str = "menos de R$100",
    destaque: str = "",
    info_extra: str = "",
    variacoes: int = 3,
) -> dict:
    """
    Gera script UGC personalizado para uma creator.

    Args:
        produto: nome do produto Rhode Jeans
        formato: 30s | 60s | 90s | live | brief
        nome_creator: nome da creator
        altura: ex '1,65m'
        peso: ex '65kg'
        quadril: ex '98cm'
        tamanho: PP | P | M | G | GG | XGG
        cintura: ex '70cm' (opcional)
        tom: tom de voz da creator
        preco: preço do produto
        destaque: destaque principal do produto (opcional)
        info_extra: contexto extra sobre a creator (opcional)
        variacoes: número de variações de hook e CTA a gerar (padrão 3)

    Returns:
        dict com hooks[], script, ctas[], hashtags, notas_direcao
    """
    import anthropic

    # Contexto do produto
    padrao = PADROES_MARCA["padroes_por_produto"].get(produto)
    ctx_produto = (
        f"TOP HOOKS VALIDADOS:\n" + "\n".join(f"- {h}" for h in padrao["hooks_top"]) +
        f"\n\nINSIGHTS:\n" + "\n".join(f"- {i}" for i in padrao["insights"])
        if padrao else "Use os padrões gerais da marca."
    )

    prompt = f"""Você é O Roteirista da Rhode Jeans — especialista em UGC para TikTok Shop.

## INTELIGÊNCIA DA MARCA (194 vídeos validados)

Estrutura: {PADROES_MARCA["estrutura_universal"]}

Gatilhos:
{chr(10).join(f"- {g}" for g in PADROES_MARCA["gatilhos_emocionais"])}

## PRODUTO: {produto}

{ctx_produto}

## CREATOR

Nome: {nome_creator} | Altura: {altura} | Peso: {peso} | Quadril: {quadril}{f" | Cintura: {cintura}" if cintura else ""} | Tamanho: {tamanho}
Tom: {tom}{f" | Contexto: {info_extra}" if info_extra else ""}

## PRODUTO

{produto} — Rhode Jeans | Preço: {preco}{f" | Destaque: {destaque}" if destaque else ""}

## FORMATO

{formato}: {FORMATOS.get(formato, formato)}

## DIRETRIZES (não negociáveis)

- Falar como pessoa real, nunca como anúncio
- Usar medidas da creator para criar identificação corporal
- Ancorar com marca aspiracional ANTES de revelar o preço
- CTA suave ("vê se ainda tem o seu tamanho") — nunca agressivo
- Ações entre [colchetes] para guiar a gravação
- Liberdade criativa total DENTRO dessas diretrizes

## OUTPUT (JSON)

Retorne APENAS um JSON válido com esta estrutura exata:

{{
  "titulo": "caption do vídeo até 150 caracteres com emoji",
  "hooks": [
    {{"tipo": "Emocional / Surpresa", "texto": "..."}},
    {{"tipo": "Problema / Identificação", "texto": "..."}},
    {{"tipo": "Prova Social / Curiosidade", "texto": "..."}}
  ],
  "script": "script completo com [ações em colchetes]",
  "ctas": [
    {{"tipo": "Urgência suave", "texto": "..."}},
    {{"tipo": "Afetivo / Amizade", "texto": "..."}},
    {{"tipo": "Curiosidade / Desafio", "texto": "..."}}
  ],
  "hashtags": ["#tag1", "#tag2", ...],
  "notas_direcao": ["dica 1", "dica 2", "dica 3", "dica 4"]
}}"""

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.content[0].text.strip()
    # Remove possíveis marcadores de código
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip().rstrip("`").strip()

    return json.loads(raw)


def salvar_script(resultado: dict, creator: str, produto: str, formato: str) -> str:
    """Salva o script gerado em relatorios/ugc/."""
    output_dir = Path(__file__).parent.parent.parent / "relatorios" / "ugc"
    output_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    nome = f"{ts}_{creator.replace(' ','_')}_{produto.replace(' ','_')}_{formato}.json"
    path = output_dir / nome

    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "creator": creator,
            "produto": produto,
            "formato": formato,
            "gerado_em": datetime.now().isoformat(),
            **resultado,
        }, f, indent=2, ensure_ascii=False)

    return str(path)


def formatar_script_para_leitura(resultado: dict) -> str:
    """Formata o script como texto legível para exibir no terminal."""
    linhas = []
    linhas.append(f"\n{'='*60}")
    linhas.append(f"TÍTULO: {resultado.get('titulo','')}")
    linhas.append(f"{'='*60}\n")

    linhas.append("── HOOKS ──────────────────────────────────")
    for i, h in enumerate(resultado.get("hooks", []), 1):
        linhas.append(f"\n[{i}] {h['tipo']}")
        linhas.append(f"    {h['texto']}")

    linhas.append(f"\n── SCRIPT COMPLETO ────────────────────────")
    linhas.append(resultado.get("script", ""))

    linhas.append(f"\n── CTAs ───────────────────────────────────")
    for i, c in enumerate(resultado.get("ctas", []), 1):
        linhas.append(f"\n[{i}] {c['tipo']}")
        linhas.append(f"    {c['texto']}")

    linhas.append(f"\n── HASHTAGS ───────────────────────────────")
    linhas.append(" ".join(resultado.get("hashtags", [])))

    linhas.append(f"\n── NOTAS DE DIREÇÃO ───────────────────────")
    for n in resultado.get("notas_direcao", []):
        linhas.append(f"  • {n}")

    linhas.append(f"\n{'='*60}")
    return "\n".join(linhas)
