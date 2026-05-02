/**
 * Rhode Jeans — Análise Cognitiva de Lives (IA)
 * POST /api/analyze
 * Body: { kpis, periodo, tendencia, contexto }
 * Resposta: JSON com score, dimensoes, resumo, diagnostico, recomendacoes, projecao
 */

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { kpis, periodo, tendencia, contexto } = req.body || {};
  if (!kpis) return res.status(400).json({ error: 'kpis obrigatório' });

  const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY;
  if (!ANTHROPIC_KEY) return res.status(500).json({ error: 'ANTHROPIC_API_KEY não configurada' });

  const prompt = `Você é um analista sênior de e-commerce e TikTok Shop especializado em live commerce.
Analise os KPIs de lives da Rhode Jeans (marca de moda feminina, especializada em Wide Leg jeans, vendas via TikTok Shop).

DADOS DO PERÍODO: ${periodo || 'histórico completo'}

KPIs ATUAIS:
${JSON.stringify(kpis, null, 2)}

TENDÊNCIA MENSAL (últimos meses, mais recente primeiro):
${tendencia ? JSON.stringify(tendencia, null, 2) : 'não disponível'}

CONTEXTO ADICIONAL:
${contexto || 'Operação de live commerce no TikTok Shop Brasil. Lives são a principal alavanca de GMV. Meta de longo prazo: R$200k/mês em GMV de lives.'}

BENCHMARKS DO SETOR (TikTok Shop Brasil, moda feminina):
- CTR saudável: ≥ 20%
- CTOR bom: ≥ 3% | médio: 2–3% | gargalo: < 2%
- R$/Viewer eficiente: ≥ R$0,80 | médio: R$0,40–0,80 | baixo: < R$0,40
- Duração ideal: 6h+ (correlação 0,79 com GMV)
- Impr./Viewer: multiplicador de engajamento — quanto maior, melhor a curadoria de produto

Retorne APENAS um JSON válido (sem markdown, sem explicação fora do JSON) com esta estrutura exata:
{
  "score_geral": <número 0-100>,
  "grade": <"A","B","C","D" ou "F">,
  "headline": <string curta (max 12 palavras) descrevendo a situação geral>,
  "dimensoes": [
    {
      "nome": <"Alcance"|"Engajamento"|"Conversão"|"Receita"|"Eficiência"|"Consistência">,
      "score": <número 0-100>,
      "status": <"excelente"|"bom"|"médio"|"atenção"|"crítico">,
      "avaliacao": <string 1-2 frases concisas com dado específico>
    }
  ],
  "resumo_executivo": <string 3-4 frases. Tom direto, executivo. Mencionar número concreto.>,
  "diagnostico": [
    {
      "tipo": <"critico"|"alerta"|"positivo">,
      "titulo": <string curta>,
      "descricao": <string 1-2 frases com dado concreto>,
      "impacto": <string — ex: "R$X/mês se corrigido" ou "representa Y% do GMV">
    }
  ],
  "recomendacoes": [
    {
      "prioridade": <1,2,3...>,
      "titulo": <string ação clara>,
      "impacto_estimado": <string ex: "+R$15k/mês">,
      "como": <string 1-3 frases táticas concretas>,
      "prazo": <"imediato"|"7 dias"|"30 dias"|"90 dias">
    }
  ],
  "projecao": {
    "pessimista": { "gmv_mensal": <número>, "descricao": <string curta> },
    "base":        { "gmv_mensal": <número>, "descricao": <string curta> },
    "otimista":    { "gmv_mensal": <número>, "descricao": <string curta> }
  },
  "insight_ia": <string — 1 insight não óbvio, contraditório ou surpreendente que os dados revelam>
}`;

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
        max_tokens: 2000,
        messages: [{ role: 'user', content: prompt }],
      }),
    });

    if (!resp.ok) {
      const err = await resp.text();
      return res.status(502).json({ error: 'Erro Claude API', detail: err.slice(0, 300) });
    }

    const data = await resp.json();
    const raw  = data.content?.[0]?.text || '';

    // Extrai JSON mesmo que venha com backticks
    const jsonMatch = raw.match(/\{[\s\S]*\}/);
    if (!jsonMatch) return res.status(502).json({ error: 'Resposta inválida da IA', raw: raw.slice(0, 500) });

    const analysis = JSON.parse(jsonMatch[0]);
    return res.status(200).json(analysis);

  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
