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
Marca: Rhode Jeans (Wide Leg jeans, expansão pra Mom/Baggy em mai/26). Canal: TikTok Shop Brasil.
Meta de longo prazo: R$200k/mês em GMV de lives.

═══════════════════════════════════════════════════════════════
LENTE DE ANÁLISE — TESE PRINCIPAL (LER ANTES DE TUDO):
═══════════════════════════════════════════════════════════════
Em 205 lives analisadas, as correlações com GMV são:
  • Product clicks       r=+0,86  ← driver dominante
  • Views                r=+0,80
  • LIVE impressions     r=+0,79
  • New followers        r=+0,77
  • Duration             r=+0,57
  • SKU order rate       r=+0,56
  • CTR                  r=+0,40
  • Avg viewing duration r=+0,34

CONCLUSÃO DA LENTE:
GMV de live na Rhode é JOGO DE TOPO DE FUNIL, não de taxa de conversão.
O que separa uma live de R$12k de uma de R$3k é QUANTAS pessoas entraram
e clicaram, não quão bem converteu quem clicou. A taxa de conversão
(SKU order rate ~0,6%) é estável entre lives boas e ruins.

IMPLICAÇÃO PRO DIAGNÓSTICO:
- Otimizar CTOR de 2,8% pra 3,3% em 30 lives ≈ +R$13k/mês (margem)
- Dobrar Product clicks numa live ≈ dobrar o GMV direto (alavanca real)
- PRIORIZE recomendações de TRÁFEGO/CLIQUES sobre conversão fina
- Quando CTOR aparecer no diagnóstico, contextualize: "estável, não é gargalo"

BENCHMARKS INTERNOS DA RHODE (use estes, não chute):
- GMV/hora: abr/26 R$2.138 (modelo) · mar/26 R$1.115 · mai/26 R$1.232
- GMV/live: abr/26 R$6.233 · mar/26 R$3.550 · mai/26 R$3.165
- Best-in-class GMV/hora: COLEÇÃO DE INVERNO 1,9h → R$3.618/h
- Curva de duração:
  · <1h        → R$672 GMV/live  (LIXO operacional: quedas/testes)
  · 1-2h       → R$3.283 · R$1.766/h  (JOELHO de eficiência)
  · 2-3h       → R$3.607 · R$1.300/h  (platô — GMV/h não cresce mais)
  · 3-4h       → R$5.109 · R$1.302/h  (só vale a pena em datas-pico)
- Janela horária: manhã (≤11h) R$1.523/h · noite (19h+) R$1.370/h (pior)
- Dia semana: sex/sáb 3,2% CTOR · meio-de-semana 2,6-2,8%

PADRÕES DE TÍTULO OBSERVADOS:
- Convertem (CTOR 4-6%): "Lançamento", "Especial TikTok", "Coleção [tema]",
  "Presente Perfeito", "Super Live 11/11" → ÂNCORA CONCRETA
- Não convertem (CTOR <1,7%): "QUARTOU DE PROMO", "QUINTOU COM A RHODE",
  "OFERTAS ESPECIAIS PARA ELAS", "Garanta o seu" → PROMO GENÉRICA DE DIA

ALERTAS SEMÂNTICOS:
- Maio/26 vs Abril/26: ticket↑ (R$67→R$75) + viewing duration↑ + Show GPM↑
  MAS Views/live↓ (12.2k→6.7k) → engajamento e ticket saudáveis, TRÁFEGO CAIU.
  Esse é o problema a destravar, não conversão.
- Lives v2 (mai/26+) não têm coluna Viewers/Peak viewers (TikTok removeu).
  NUNCA cite Viewers ou R$/Viewer pra esse período.
═══════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════
PERÍODO ANALISADO: ${periodo || 'histórico completo'}
═══════════════════════════════════════════════════════════════

KPIs AGREGADOS:
${JSON.stringify(kpis, null, 2)}

TENDÊNCIA MENSAL (mais antigo → mais recente):
${tendencia ? JSON.stringify(tendencia, null, 2) : 'não disponível'}

AMOSTRA DE LIVES (${lives_amostra.length} lives — mix de top GMV, bottom e recentes):
${JSON.stringify(lives_amostra.slice(0, 25), null, 0)}

CORRELAÇÕES PEARSON (variável vs GMV, pré-calculadas):
${JSON.stringify(drivers_calc, null, 2)}

CONTEXTO:
${contexto || 'Lives diárias, principalmente 11h-16h, duração 2-4h.'}

═══════════════════════════════════════════════════════════════
BENCHMARKS SETOR (TikTok Shop BR moda feminina) — use só como contexto secundário,
prioridade são os benchmarks INTERNOS acima:
- CTR (cliques/impressões): ≥ 25% saudável
- SKU order rate (pedidos/impressões): ≥ 0,7% bom
- Ads ROAS: ≥ 3× bom | <2× ruim
═══════════════════════════════════════════════════════════════

Sua tarefa: gerar análise estruturada em 4 blocos.

REGRAS DE INTEGRIDADE NUMÉRICA (não-negociáveis):
- USE EXATAMENTE os números que recebeu acima. NÃO arredonde de forma estranha, NÃO some, NÃO infira valores.
- NÃO INVENTE quantidades: se kpis.n_lives = 49, NÃO escreva "28 lives em maio" ou qualquer número não presente nos dados.
- NÃO EXTRAPOLE: se um campo veio NULL (ex: viewers em lives v2), trate como "sem dado", nunca como zero.
- Top 3 / Bottom 3: escolha ESTRITAMENTE da lives_amostra que recebeu. Use título e GMV exatos.
- Se um número não está nos dados (ex: pico de viewers em mai/26), diga "não disponível" ao invés de chutar.

REGRAS DE JSON:
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

  "dimensoes": [ // exatamente 6 — nomes fixos abaixo, NÃO renomear:
    // Alcance     → Views/LIVE impressions vs abril (R$2.138/h modelo). DRIVER FORTE.
    // Engajamento → Product clicks + follow rate. DRIVER MAIS FORTE (r=0.86).
    // Conversão   → CTOR/SKU rate. ESTÁVEL ~0,6% — NÃO é gargalo, é margem.
    // Receita     → GMV/live e principalmente GMV/HORA vs R$2.138 (abr/26).
    // Eficiência  → Duração relativa ao joelho de 2h. Lives <60min penalizam.
    // Consistência → Variabilidade GMV entre lives (CV).
    { "nome": <"Alcance"|"Engajamento"|"Conversão"|"Receita"|"Eficiência"|"Consistência">,
      "score": <0-100>,
      "status": <"excelente"|"bom"|"médio"|"atenção"|"crítico">,
      "avaliacao": <1 frase curta com dado específico DO PERÍODO ANALISADO> }
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

  "acoes_priorizadas": [ // exatamente 3 ações, ordenadas. ATENÇÃO À HIERARQUIA:
    // P1 deve atacar TRÁFEGO/CLIQUES (driver dominante r=0.86, maior alavanca)
    // P2 deve atacar EFICIÊNCIA OPERACIONAL (duração, horário, lives <60min)
    // P3 pode atacar conversão/ticket/margem, mas reconheça que é margem, não alavanca
    // NUNCA recomende como P1 algo de CTOR/conversão fina — é margem
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
    "pessimista": { "gmv_mensal": <número>, "descricao": <MÁX 15 palavras> },
    "base":        { "gmv_mensal": <número>, "descricao": <MÁX 15 palavras> },
    "otimista":    { "gmv_mensal": <número>, "descricao": <MÁX 15 palavras> }
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
        max_tokens: 7000,
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
