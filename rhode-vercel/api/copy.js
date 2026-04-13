// ─── INTELIGÊNCIA DA MARCA ────────────────────────────────────────────────────
// Extraída de 27 vídeos UGC validados (Marmorizada: 47 análises, Rosa Bebê: 31)
// Fonte: /analises/relatorio_padroes.json — gerado por analisar_padroes.py

const PADROES_MARCA = {
  hook_universal: `[Chamada íntima para 'amigas'] + [Emoção forte: paixão, surpresa ou descoberta] + [Referência ao problema/desejo específico OU validação social (viralização/uso repetido)]`,
  estrutura_universal: `Hook emocional/chamada íntima (0-5s) → Apresentação do produto com contexto real de uso (5-15s) → Prova no corpo com detalhes visuais: caimento, frente, costas, lavagem, costura (15-30s) → Dados de identificação corporal: tamanho, altura, peso, medidas (30-40s) → Ancoragem de valor: comparação com marca cara + revelação do preço real abaixo de R$100 + justificativa 'direto da fábrica' (40-55s) → Benefícios emocionais e funcionais: empina bumbum, modela cintura, versatilidade (55-65s) → CTA suave com urgência implícita direcionando ao carrinho laranja (65-75s)`,
  gatilhos_emocionais: [
    "Pertencimento e intimidade: uso constante de 'amigas', tom confessional — cria confiança e reduz percepção de publicidade",
    "Inteligência de consumo: ancoragem com Zara/grifes de R$200+ versus preço real abaixo de R$100 — compradora se sente esperta, não barata",
    "Validação corporal: foco em como a calça transforma a silhueta (empina bumbum, modela cintura) — conecta ao produto uma elevação de autoconfiança",
    "Escassez e urgência suave: 'vê se ainda tem o seu tamanho', 'corre que tá em promoção' — urgência que mantém tom de amiga, sem parecer vendedor",
    "Surpresa e descoberta: arco 'eu não acreditava → experimentei → fiquei chocada' — ativa curiosidade e desejo de replicar a experiência"
  ],
  vocabulario: {
    usar: ["amigas","apaixonada","para tudo","perfeita","carrinho laranja","viralizada","empina o bumbum","modela a cintura","menos de 100 reais","direto da fábrica","qualidade de Zara","caimento","100% algodão","não desbota","garante a sua","vê se ainda tem o seu tamanho","depois volta aqui pra me agradecer","versátil","combina com tudo","eu uso toda semana","todo mundo pergunta"],
    evitar: ["baratinha","compre agora","oferta imperdível","link na bio","cupom de desconto","publi/publicidade","fast fashion","básica/simples demais","produto bom pelo preço","não é de marca mas..."]
  },
  ctas_validados: [
    "Vou deixar o link aqui no carrinho laranja. Vê se ainda tem o seu tamanho e depois volta aqui pra me agradecer.",
    "Clica aqui, já vê se tem o seu tamanho, garante a sua, depois você volta aqui e me agradece, que você vai me agradecer muito.",
    "Corre que tá com promoção — link no carrinho laranja.",
    "Amiga, clica aqui no carrinho laranja e vai ser feliz.",
    "Garante a sua antes de acabar — carrinho laranja aqui embaixo.",
    "Não perde tempo que na hora que a promoção acabar vai tá outro valor."
  ],
  por_produto: {
    "Wide Leg Marmorizada": {
      videos: 47,
      hooks_top: [
        "Declaração de paixão/obsessão — 'Eu sou simplesmente apaixonada por essa calça'",
        "Referência à viralização — 'A calça mais viralizada do TikTok realmente vale cada centavo e custa menos de 100 reais'",
        "Problema corporal direto — 'Amigas do popotão grandão com dificuldade de achar calça que fique boa na cintura e no bumbum, essa é a solução'",
        "Comando de urgência — 'Amigas, para tudo. Olha o que eu descobri. Eu juro que nunca vi nada igual'",
        "Uso repetido como prova — 'Eu tô usando essa calça pela quinta vez na semana e ela tá simplesmente perfeita'"
      ],
      insights: [
        "Comparação com Zara é o maior motor de conversão — praticamente todos os vídeos top fazem isso",
        "Especificidade corporal (altura + peso + quadril) elimina o medo de não servir — é a maior barreira do e-commerce de moda",
        "Formato 'ceticismo → prova no corpo → reação genuína de surpresa' supera qualquer review descritivo",
        "Volume de vendas (28-40 mil itens) usado como prova social coletiva",
        "Falta de elastano posicionada como positivo: jeans premium, caimento elegante"
      ],
      prova_social: ["'Coisa de calça que você paga em mais de 200'", "'Já foram vendidas quase 40 mil calças dessa. Não é à toa, né?'", "'Parece que eu paguei uns 300 reais nela. Não tô brincando.'"],
      ctas_exatos: ["'Vê se ainda tem o seu tamanho aqui, depois você volta, você vai me agradecer muito, amiga, porque ela tá a menos de 80 reais e ela é perfeita'", "'Clica aqui, ó, já vê se tem o seu tamanho, garante a sua, depois você volta aqui e me agradece'"]
    },
    "Wide Leg Rosa Bebê": {
      videos: 31,
      hooks_top: [
        "Surpresa pessoal — 'Eu não imaginava que eu precisava de uma calça rosa até eu ter uma'",
        "Quebra de objeção direta — 'Ah, eu só compro calça de grife. Amiga, para. Pega a referência aqui'",
        "Descoberta de bastidor — 'Eu só compro calça direto da fábrica depois que descobri essa loja aqui no carrinho'",
        "Momento especial — 'Hoje é meu aniversário e vou estrear essa calça rosa que comprei aqui no carrinho laranja'",
        "Validação social — 'Comprei a calça rosa viralizada do TikTok. Vamos levar comigo?'"
      ],
      insights: [
        "'Fabricante/direto da fábrica' justifica preço baixo + qualidade alta — cria sensação de acesso exclusivo",
        "Ancoragem Zara + preço < R$100 cria efeito de 'hackeando o sistema de moda'",
        "A cor rosa precisa quebrar objeção de 'não combina' — mostrar 2-3 looks é obrigatório",
        "Prova social mais forte: medidas corporais reais + relato de lavagens sem desbotar + reações de terceiros ('todo mundo pergunta')",
        "Compra múltipla ('comprei todas as cores') é a prova de satisfação mais poderosa"
      ],
      prova_social: ["'Toda vez que saio com essa calça rosa na rua, me perguntam aonde comprei e ninguém acredita que foi no TikTok Shop'", "'Já usei muitas vezes, já lavei ela milhares de vezes e não desbota'", "'Essa calça aqui já virou meu uniforme. Eu uso ela toda semana.'"],
      ctas_exatos: ["'Eu vou deixar o linkzinho aqui nesse carrinho laranja pra você garantir a sua também'", "'Clica nesse carrinho aqui e pega a sua. Depois volta e me agradece'"]
    },
    "Wide Leg Azul Médio": {
      videos: 1,
      hooks_top: [
        "GRWM íntimo — 'Amigas, eu tô me arrumando pra sair e queria mostrar esse look'",
        "Revelação emocional — 'Esse jeans, eu sou apaixonada'",
        "Ocasião prática — 'Preciso de um look prático pra resolver coisas na rua'",
        "Contextualização real — 'Tá uma bagunça aqui, mas enfim... olha só o que eu tô usando'"
      ],
      insights: [
        "Formato GRWM esconde o conteúdo publicitário e aumenta autenticidade",
        "Benefício emocional supera funcional: 'eu sinto que estou arrumada, sem muito esforço'",
        "CTA com escassez implícita ('se ainda tiver em stock') mantém tom autêntico"
      ],
      prova_social: ["'Gente, eu sou apaixonada nele'", "'Olha só como ele modela o bumbum, empina o bumbum'", "'Eu coloco ele porque eu sinto que eu estou arrumada, sem muito esforço'"],
      ctas_exatos: ["'Eu vou deixar o link pra vocês aqui. Se ainda tiver em stock, já garante a sua. Beijo!'"]
    }
  }
};

const FORMATOS = {
  hook:    "Gere 3 variações de hook de abertura (máximo 5 segundos cada). Cada hook deve parar o scroll imediatamente. Para cada um indique o tipo: Emocional, Problema/Identificação ou Prova Social.",
  "30s":   "Gere um roteiro completo de 30 segundos com: hook direto, prova rápida no corpo com as medidas da creator, ancoragem de preço, CTA suave.",
  "60s":   "Gere um roteiro completo de 60 segundos com: hook emocional (0-5s), apresentação com contexto de uso (5-15s), prova no corpo com medidas (15-30s), ancoragem de valor/preço (30-45s), benefícios emocionais (45-55s), CTA (55-60s).",
  "90s":   "Gere um roteiro de 90 segundos com narrativa completa: hook, contexto de vida real, comparação com marca cara, prova no corpo com medidas, múltiplos benefícios, reação de terceiros, CTA com urgência.",
  live:    "Gere um roteiro para live TikTok Shop com as seções: Abertura energética (chama quem entrou), Apresentação do produto ao vivo, Demonstração no corpo, Ancoragem de preço, Respostas a objeções frequentes, CTA repetido com urgência de estoque."
};

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { nome, altura, peso, quadril, cintura, tamanho, produto, tipo, contexto } = req.body || {};

  if (!nome || !produto || !tipo) {
    return res.status(400).json({ error: 'Campos obrigatórios: nome, produto, tipo' });
  }

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return res.status(500).json({ error: 'API key não configurada' });

  // Padrões específicos do produto ou fallback para os gerais
  const padrao = PADROES_MARCA.por_produto[produto];
  const ctx_produto = padrao
    ? `TOP HOOKS VALIDADOS (${padrao.videos} vídeos analisados):
${padrao.hooks_top.map(h => `- ${h}`).join('\n')}

INSIGHTS DE CONVERSÃO:
${padrao.insights.map(i => `- ${i}`).join('\n')}

PROVA SOCIAL QUE MAIS CONVERTE:
${padrao.prova_social.map(p => `- ${p}`).join('\n')}

CTAS EXATOS DOS VÍDEOS TOP:
${padrao.ctas_exatos.map(c => `- ${c}`).join('\n')}`
    : `Use os padrões gerais da marca. Enfatize: caimento, versatilidade, qualidade vs preço, medidas da creator.`;

  const perfil_medidas = [
    `Nome: ${nome}`,
    altura ? `Altura: ${altura}` : null,
    peso ? `Peso: ${peso}` : null,
    quadril ? `Quadril: ${quadril}` : null,
    cintura ? `Cintura: ${cintura}` : null,
    tamanho ? `Tamanho: ${tamanho}` : null,
  ].filter(Boolean).join(' | ');

  const prompt = `Você é O Roteirista da Rhode Jeans — especialista em UGC para TikTok Shop.
Você criou os scripts que geraram mais de 40.000 vendas da marca.

═══ INTELIGÊNCIA DA MARCA (27 vídeos validados) ═══

Estrutura que converte:
${PADROES_MARCA.estrutura_universal}

Gatilhos emocionais:
${PADROES_MARCA.gatilhos_emocionais.map(g => `- ${g}`).join('\n')}

Vocabulário obrigatório: ${PADROES_MARCA.vocabulario.usar.slice(0, 12).join(', ')}
Vocabulário PROIBIDO: ${PADROES_MARCA.vocabulario.evitar.slice(0, 8).join(', ')}

═══ PRODUTO: ${produto} ═══

${ctx_produto}

═══ CREATOR ═══

${perfil_medidas}
${contexto ? `Contexto adicional: ${contexto}` : ''}

═══ FORMATO SOLICITADO ═══

${FORMATOS[tipo] || FORMATOS['60s']}

═══ DIRETRIZES NÃO NEGOCIÁVEIS ═══

1. Falar como pessoa real, nunca como anúncio
2. Usar as medidas da creator para gerar identificação corporal
3. Ancorar com marca aspiracional ANTES de revelar o preço
4. CTA suave ("vê se ainda tem o seu tamanho") — nunca agressivo
5. Indicações de ação [entre colchetes] para guiar a gravação
6. Tom de "amiga contando um segredo", nunca de vendedora

═══ OUTPUT ═══

Retorne APENAS um JSON válido com esta estrutura:

{
  "titulo": "caption do vídeo até 150 caracteres com emoji",
  "hooks": [
    {"tipo": "Emocional / Paixão", "texto": "..."},
    {"tipo": "Problema / Identificação", "texto": "..."},
    {"tipo": "Prova Social / Curiosidade", "texto": "..."}
  ],
  "script": "script completo com [ações em colchetes] e marcações de tempo",
  "ctas": [
    {"tipo": "Urgência suave", "texto": "..."},
    {"tipo": "Afetivo / Amizade", "texto": "..."},
    {"tipo": "Escassez implícita", "texto": "..."}
  ],
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#tag8"],
  "notas_direcao": ["dica 1", "dica 2", "dica 3", "dica 4"]
}`;

  try {
    const r = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json'
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 1200,
        messages: [{ role: 'user', content: prompt }]
      })
    });

    const data = await r.json();
    if (!r.ok) {
      console.error('Anthropic error:', JSON.stringify(data));
      return res.status(500).json({ error: 'Erro na API de IA. Tente novamente.' });
    }

    let raw = data.content?.[0]?.text?.trim() || '';
    if (raw.startsWith('```')) {
      raw = raw.replace(/^```json?\n?/, '').replace(/\n?```$/, '').trim();
    }

    const result = JSON.parse(raw);
    return res.status(200).json(result);

  } catch (e) {
    console.error('copy handler error:', e.message);
    return res.status(500).json({ error: 'Erro interno. Tente novamente.' });
  }
}
