/**
 * Rhode Jeans — Analista Cognitivo de Creators (IA)
 * POST /api/analyst
 * Body: { mode: 'creator' | 'period', data: <object>, contexto?: string }
 * Resposta: JSON estruturado com diagnóstico, ações priorizadas e insights.
 */

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { mode, data, contexto } = req.body || {};
  if (!mode || !data) return res.status(400).json({ error: 'mode e data obrigatórios' });

  const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY;
  if (!ANTHROPIC_KEY) return res.status(500).json({ error: 'ANTHROPIC_API_KEY não configurada' });

  let prompt;

  if (mode === 'creator') {
    prompt = `Você é um analista de growth especializado em creator economy e TikTok Shop. Sua função: olhar para os dados de UMA creator da Rhode Jeans e produzir um diagnóstico operacional — o que ela é, do que é capaz, onde trava, e o que fazer com ela.

DADOS DA CREATOR:
${JSON.stringify(data, null, 2)}

CONTEXTO RHODE:
- Marca: Wide Leg jeans premium, ticket médio R$ 80–100
- Canal: TikTok Shop Brasil (vídeos curtos + lives)
- Programa de tiers (GMV acumulado): Bronze 20k · Silver 50k · Gold 80k · Diamond 150k · Black 500k
- Comissões: 10–12% conforme tier
- Operação: meta R$ 200k/mês em GMV de lives
${contexto ? '- Contexto adicional: ' + contexto : ''}

REGRAS DE ANÁLISE:
- Refund > 25% é crítico, > 15% atenção
- AOV abaixo de R$ 60 sinaliza ticket baixo (cupom errado, produto barato no carrinho)
- AOV acima de R$ 100 = mix premium, manter cadência
- Mais de 0 lives no período + 0 vídeos = live seller pura (alta GMV/sessão, baixa frequência)
- 0 lives + muitos vídeos = video creator (volume, baixo GMV/peça)
- 0 ambos no período = dormente
- Δ GMV período/período é a métrica de trajetória mais importante

Retorne APENAS JSON válido (sem markdown, sem texto fora do JSON):
{
  "perfil": {
    "tipo": <"live_seller" | "video_creator" | "hibrido" | "dormente">,
    "estagio": <"iniciante" | "em_crescimento" | "estabelecida" | "em_declinio">,
    "headline": <string 6-12 palavras descrevendo essa creator de forma específica>
  },
  "score_growth": <0-100>,
  "trajetoria": <"acelerando" | "estavel" | "desacelerando" | "instavel">,
  "forcas": [<3 strings com pontos fortes específicos baseados em números>],
  "riscos": [<2-3 strings com riscos, sempre com dado concreto>],
  "diagnostico": <string 3-4 frases. Tom analítico, direto. Cite números.>,
  "acoes": [
    {
      "prioridade": <1|2|3>,
      "acao": <string ação clara e específica para esta creator>,
      "razao": <string 1 frase>,
      "impacto_estimado": <string ex: "+R$ 5k/mês" ou "-15% refund">,
      "prazo": <"imediato" | "7d" | "30d">
    }
  ],
  "projecao_3m": {
    "gmv_estimado": <número absoluto em R$>,
    "premissa": <string curta — assumindo o quê>
  },
  "insight_nao_obvio": <string com 1 padrão escondido ou contraintuitivo nos dados>
}`;
  } else if (mode === 'period') {
    prompt = `Você é um analista de growth do programa de afiliadas Rhode Jeans (TikTok Shop, Wide Leg jeans). Analise a saúde geral do programa no período abaixo.

DADOS AGREGADOS DO PERÍODO:
${JSON.stringify(data, null, 2)}

CONTEXTO:
- Programa de tiers: Bronze 20k · Silver 50k · Gold 80k · Diamond 150k · Black 500k (GMV acumulado)
- Comissões: 10–12% conforme tier
${contexto ? '- Contexto adicional: ' + contexto : ''}

REGRAS:
- Concentração top 10 > 70% do GMV é dependência crítica
- Refund médio > 20% é problema sistêmico
- % de creators com 0 GMV > 60% indica programa inflado
- Crescimento MoM saudável: +10% ou mais

Retorne APENAS JSON válido:
{
  "score_geral": <0-100>,
  "grade": <"A" | "B" | "C" | "D" | "F">,
  "headline": <string max 14 palavras>,
  "dimensoes": [
    { "nome": <"Concentração" | "Saúde de Refund" | "Crescimento" | "Diversidade" | "Engajamento">, "score": <0-100>, "status": <"excelente" | "bom" | "medio" | "atencao" | "critico">, "avaliacao": <string 1-2 frases com número específico> }
  ],
  "resumo_executivo": <string 3-5 frases. Cite números do período. Tom direto.>,
  "diagnostico": [
    { "tipo": <"critico" | "alerta" | "positivo">, "titulo": <string>, "descricao": <string com dado>, "impacto": <string ex: "R$X potencial perdido"> }
  ],
  "recomendacoes": [
    { "prioridade": <1|2|3>, "titulo": <string ação clara>, "como": <string 1-3 frases táticas>, "impacto_estimado": <string>, "prazo": <"imediato" | "7d" | "30d" | "90d"> }
  ],
  "insight_nao_obvio": <string contraintuitivo escondido nos dados>
}`;
  } else {
    return res.status(400).json({ error: 'mode inválido (use "creator" ou "period")' });
  }

  try {
    const resp = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 2500,
        messages: [{ role: 'user', content: prompt }],
      }),
    });

    if (!resp.ok) {
      const err = await resp.text();
      return res.status(502).json({ error: 'Erro Claude API', detail: err.slice(0, 300) });
    }
    const result = await resp.json();
    const raw = result.content?.[0]?.text || '';
    const match = raw.match(/\{[\s\S]*\}/);
    if (!match) return res.status(502).json({ error: 'Resposta inválida', raw: raw.slice(0, 500) });
    return res.status(200).json(JSON.parse(match[0]));
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
