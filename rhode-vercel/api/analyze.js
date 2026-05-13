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

AMOSTRA DE LIVES (top ${Math.min(20, lives_amostra.length)} mais recentes):
${JSON.stringify(lives_amostra.slice(0, 20), null, 0)}

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

Sua tarefa: gerar análise estruturada em 4 blocos. Use SEMPRE números concretos das amostras, nunca vagueza (alguns, muitas). Quando citar lives específicas, use o título exato.

IMPORTANTE — REGRAS DE JSON:
- Retorne APENAS JSON válido. Sem markdown, sem cercas, sem texto fora.
- Dentro de strings, NÃO use aspas duplas. Use aspas simples ' se precisar citar algo.
- Não use vírgulas trailing antes de } ou ].
- Strings em uma única linha (sem quebra de linha dentro).
- Para listas vazias use [], para objetos vazios use null.

Estrutura exata (preencher todos os campos, nunca omitir):

{
  "score_geral": <0-100>,
  "grade": <"A"|"B"|"C"|"D"|"F">,
  "headline": <string max 12 palavras>,

  "dimensoes": [
    { "nome": <"Alcance"|"Engajamento"|"Conversão"|"Receita"|"Eficiência"|"Consistência">,
      "score": <0-100>,
      "status": <"excelente"|"bom"|"médio"|"atenção"|"crítico">,
      "avaliacao": <1 frase curta com dado específico> }
  ],

  "resumo_executivo": <2 frases. Tom direto. Cite 2 números concretos.>,

  "diagnostico_lives": {
    "top_3": [ // exatamente 3 lives

      { "titulo": <título exato da live>,
        "started_at": <ISO>,
        "gmv": <número>,
        "por_que": <1 frase curta: o que essa live tem de diferente. Compare com média do período.> }
    ],
    "bottom_3": [ // exatamente 3 lives

      { "titulo": <título>,
        "started_at": <ISO>,
        "gmv": <número>,
        "o_que_deu_errado": <1 frase curta: hipótese causal específica.> }
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

  "acoes_priorizadas": [ // exatamente 3 ações, ordenadas por prioridade
    { "prioridade": <1-3>,
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
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 5500,
        messages: [{ role: 'user', content: prompt }],
      }),
    });

    if (!resp.ok) {
      const err = await resp.text();
      return res.status(502).json({ error: 'Erro Claude API', detail: err.slice(0, 400) });
    }

    const data = await resp.json();
    const raw  = data.content?.[0]?.text || '';

    // Extract JSON (mesmo se vier com cercas/markdown)
    const jsonMatch = raw.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      return res.status(502).json({ error: 'Resposta inválida da IA', raw: raw.slice(0, 600) });
    }

    const tryParse = (s) => { try { return JSON.parse(s); } catch (e) { return null; } };

    let analysis = tryParse(jsonMatch[0]);

    if (!analysis) {
      // Tentativas de auto-fix em erros comuns de JSON do LLM:
      // 1) Trailing commas antes de } ou ]
      let fixed = jsonMatch[0].replace(/,(\s*[}\]])/g, '$1');
      analysis = tryParse(fixed);

      if (!analysis) {
        // 2) Aspas curvas dentro de strings (″ ‟ ’) → escapar como ' simples
        fixed = fixed.replace(/[""‟]/g, '"').replace(/['']/g, "'");
        analysis = tryParse(fixed);
      }

      if (!analysis) {
        // 3) Aspas duplas não-escapadas dentro de valores de string: troca por aspas simples.
        // Heurística: encontra valores delimitados por " e escapa aspas internas.
        // Padrão: "..." onde dentro tem outra " sem \ antes
        fixed = fixed.replace(/:\s*"((?:[^"\\]|\\.)*?)"(\s*[,}\]])/g, (m, val, tail) => {
          const safe = val.replace(/(?<!\\)"/g, "'");
          return ': "' + safe + '"' + tail;
        });
        analysis = tryParse(fixed);
      }
    }

    if (!analysis) {
      // Última tentativa: pega só o início válido (trunca no último } balanceado).
      let depth = 0, lastValid = -1;
      const s = jsonMatch[0];
      for (let i = 0; i < s.length; i++) {
        if (s[i] === '{') depth++;
        else if (s[i] === '}') { depth--; if (depth === 0) lastValid = i; }
      }
      if (lastValid > 0) analysis = tryParse(s.slice(0, lastValid + 1));
    }

    if (!analysis) {
      // Debug detalhado — tenta parse final pra capturar position do erro
      let parseErr = '';
      try { JSON.parse(jsonMatch[0]); } catch (e) { parseErr = e.message; }
      const m = parseErr.match(/position (\d+)/);
      const pos = m ? parseInt(m[1]) : 0;
      const snippet = pos ? jsonMatch[0].slice(Math.max(0, pos-80), pos+80) : '';
      return res.status(502).json({
        error: 'JSON inválido da IA — não foi possível auto-corrigir',
        parse_error: parseErr,
        error_position: pos,
        snippet_around_error: snippet,
        raw_length: raw.length,
        raw_tail: raw.slice(-500),
      });
    }

    return res.status(200).json(analysis);

  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}
