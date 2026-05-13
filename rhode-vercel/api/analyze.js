/**
 * Rhode Jeans — Análise Cognitiva v2 (4 direções)
 *
 * POST /api/analyze
 * Body: { kpis, periodo, tendencia, lives_amostra, drivers_calc, contexto }
 *   • kpis: agregados do período (gmv, ctor, ctr, etc)
 *   • lives_amostra: top 50 lives do período (cru — title, started_at, métricas)
 *   • drivers_calc: correlações Pearson pré-computadas client-side
 *   • tendencia: array de meses
 *   • periodo: label
 *
 * Retorna JSON com 4 blocos:
 *   1. diagnostico_lives  (top/bottom 3 + outliers + padrão)
 *   2. drivers           (interpretação + benchmark + vs período anterior)
 *   3. acoes             (top 5 priorizadas + experimento A/B)
 *   4. projecao_30d      (cone pessimista/base/otimista) + resumo
 */

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const {
    kpis,
    lives_amostra = [],
    drivers_calc = [],
    tendencia,
    periodo,
    contexto,
  } = req.body || {};

  if (!kpis) return res.status(400).json({ error: 'kpis obrigatório' });

  const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY;
  if (!ANTHROPIC_KEY) return res.status(500).json({ error: 'ANTHROPIC_API_KEY não configurada' });

  const prompt = `Você é analista sênior de live commerce no TikTok Shop, especializado em moda feminina.
Marca: Rhode Jeans (Wide Leg jeans). Canal principal: TikTok Shop Brasil.
Meta de longo prazo: R$200k/mês em GMV de lives.

═══════════════════════════════════════════════════════════════
PERÍODO ANALISADO: ${periodo || 'histórico completo'}
═══════════════════════════════════════════════════════════════

KPIs AGREGADOS:
${JSON.stringify(kpis, null, 2)}

TENDÊNCIA MENSAL (mais antigo → mais recente):
${tendencia ? JSON.stringify(tendencia, null, 2) : 'não disponível'}

AMOSTRA DE LIVES (top ${lives_amostra.length} mais recentes do período):
${JSON.stringify(lives_amostra.slice(0, 50), null, 2)}

CORRELAÇÕES PEARSON (variável vs GMV, pré-calculadas):
${JSON.stringify(drivers_calc, null, 2)}

CONTEXTO:
${contexto || 'Lives diárias, principalmente 11h-16h, duração 2-4h.'}

═══════════════════════════════════════════════════════════════
BENCHMARKS DO SETOR (TikTok Shop BR · moda feminina):
- CTR saudável: ≥ 20%
- CTOR bom: ≥ 3% | médio: 2-3% | gargalo: <2%
- R$/Viewer eficiente: ≥ R$0,80 | médio: R$0,40-0,80 | baixo: <R$0,40
- Duração ideal: 6h+ (correlação 0,79 com GMV em estudos)
- Impr./Viewer: ≥ 5× (curadoria de produto saudável)
- Ads ROAS bom: ≥ 3× | aceitável: 2-3× | ruim: <2×
═══════════════════════════════════════════════════════════════

Sua tarefa: gerar análise estruturada em 4 blocos. Use SEMPRE números concretos das amostras, nunca vagueza ("alguns", "muitas"). Quando citar lives específicas, use o título exato.

Retorne APENAS JSON válido (sem markdown, sem texto fora):

{
  "score_geral": <0-100>,
  "grade": <"A"|"B"|"C"|"D"|"F">,
  "headline": <string max 12 palavras>,

  "dimensoes": [
    { "nome": <"Alcance"|"Engajamento"|"Conversão"|"Receita"|"Eficiência"|"Consistência">,
      "score": <0-100>,
      "status": <"excelente"|"bom"|"médio"|"atenção"|"crítico">,
      "avaliacao": <1-2 frases com dado específico> }
  ],

  "resumo_executivo": <3-4 frases. Tom direto. Cite 2+ números concretos.>,

  "diagnostico_lives": {
    "top_3": [
      { "titulo": <título exato da live>,
        "started_at": <ISO>,
        "gmv": <número>,
        "por_que": <1-2 frases: o que essa live tem de diferente. Compare com média do período.> }
    ],
    "bottom_3": [
      { "titulo": <título>,
        "started_at": <ISO>,
        "gmv": <número>,
        "o_que_deu_errado": <1-2 frases: hipótese causal específica.> }
    ],
    "outliers": [
      { "tipo": <"positivo"|"negativo">,
        "titulo": <título da live>,
        "metrica": <"GMV"|"CTOR"|"Duração"|"Viewers"|outra>,
        "valor": <string formatada>,
        "explicacao": <1 frase> }
    ],
    "padrao_emergente": <1 frase descrevendo um padrão recorrente. Ex: "Lives às 11h convertem 1,8× mais que às 15h">
  },

  "drivers": {
    "principais": [
      { "variavel": <"CTOR"|"CTR"|"Duração"|"Peak viewers"|outra>,
        "correlacao": <-1 a 1>,
        "interpretacao": <1 frase prática: o que isso significa pra próxima live> }
    ],
    "vs_periodo_anterior": [
      { "metrica": <"GMV total"|"GMV/live"|"CTOR"|outra>,
        "atual": <número>,
        "anterior": <número>,
        "delta_pct": <número>,
        "comentario": <1 frase> }
    ],
    "vs_melhor_historica": {
      "titulo_live": <título>,
      "gmv_referencia": <número>,
      "gap_pct": <quanto a média do período está abaixo dessa, em %>,
      "o_que_replicar": <1 frase>
    },
    "vs_benchmark": [
      { "kpi": <"CTR"|"CTOR"|"R$/Viewer"|"Duração"|"Impr./Viewer"|"Ticket">,
        "atual": <string formatada>,
        "benchmark": <string>,
        "status": <"acima"|"dentro"|"abaixo"|"crítico">,
        "gap": <string descritivo, ex: "30% abaixo do bench">  }
    ]
  },

  "acoes_priorizadas": [
    { "prioridade": <1-5>,
      "titulo": <ação clara e curta>,
      "impacto_rs": <string ex: "+R$15-25k/mês">,
      "hipotese": <1 frase: por que isso deve funcionar baseado nos dados>,
      "como": <2-3 frases táticas com passos concretos>,
      "prazo": <"imediato"|"7 dias"|"30 dias"|"90 dias">,
      "criterio_sucesso": <1 frase: como saber se deu certo> }
  ],

  "experimento_sugerido": {
    "nome": <string curto>,
    "hipotese": <1 frase clara: SE X ENTÃO Y porque Z>,
    "variavel_testada": <"horário"|"título"|"duração"|"produto destaque"|"investimento em ads"|outra>,
    "variante_a": <descrição do controle>,
    "variante_b": <descrição da variação>,
    "lives_minimas": <número — quantas lives precisam rodar pra ter sinal estatístico>,
    "metrica_alvo": <"GMV"|"CTOR"|"Orders">,
    "expectativa_lift_pct": <número — quanto a variante B deve melhorar>
  },

  "projecao_30d": {
    "pessimista": { "gmv_mensal": <número>, "descricao": <1 frase: condições assumidas> },
    "base":        { "gmv_mensal": <número>, "descricao": <1 frase> },
    "otimista":    { "gmv_mensal": <número>, "descricao": <1 frase: o que precisaria dar certo> }
  },

  "insight_ia": <1 frase com 1 insight não-óbvio que SÓ aparece olhando os dados juntos>
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
        max_tokens: 6000,
        messages: [{ role: 'user', content: prompt }],
      }),
    });

    if (!resp.ok) {
      const err = await resp.text();
      return res.status(502).json({ error: 'Erro Claude API', detail: err.slice(0, 400) });
    }

    const data = await resp.json();
    const raw  = data.content?.[0]?.text || '';

    // Extract JSON (mesmo se vier com cercas)
    const jsonMatch = raw.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return res.status(502).json({ error: 'Resposta inválida da IA', raw: raw.slice(0, 600) });
    }

    let analysis;
    try {
      analysis = JSON.parse(jsonMatch[0]);
    } catch (e) {
      return res.status(502).json({ error: 'JSON inválido da IA', detail: e.message, raw: raw.slice(0, 600) });
    }

    return res.status(200).json(analysis);

  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
