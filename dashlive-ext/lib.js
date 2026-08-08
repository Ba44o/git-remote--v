"use strict";
/* DashLive — funções puras (parsing, benchmark, detecção de perfil de CTR).
   Fica separado do content.js por dois motivos: dá pra testar em Node sem DOM
   (tests/test_dashlive_lib.mjs) e o content.js fica só com UI + leitura da página.
   Carregado como content_script antes do content.js. Sem imports, sem rede. */
(() => {
  const L = {};

  /* ============ parsing pt-BR ============
     Casos reais da tela do Seller Center: "R$ 1.234,56" · "9.519" · "2,52%" · "28,4%".
     A regra que decide tudo: quem é o ÚLTIMO separador manda. Se vier só ponto com
     3 dígitos depois, é milhar ("9.519" = 9519) — exceto em percentual, onde
     "2.52%" é decimal de origem en-US e virar 252 destruiria a leitura. */
  // O Seller Center abrevia número grande: "R$ 2,8 mil", "1,4 mil", às vezes "12,5 mi".
  // Sem tratar isso o painel lê R$ 2,80 no lugar de R$ 2.800 — e não dá nenhum sinal
  // de que errou, porque 2,80 é um número perfeitamente válido.
  L.SUFIXOS = [
    [/\d\s*(bi|bilh(?:ão|ões))\b/i, 1e9],
    [/\d\s*(mi|milh(?:ão|ões)|M)\b/, 1e6],
    [/\d\s*(mil|k)\b/i, 1e3],
  ];
  L.parseNumberPtBR = function (raw, type) {
    if (raw == null) return null;
    const bruto = String(raw);
    let mult = 1;
    for (const [rx, m] of L.SUFIXOS) if (rx.test(bruto)) { mult = m; break; }
    let s = bruto.replace(/[^\d.,-]/g, "");
    const neg = /^-/.test(s);
    s = s.replace(/-/g, "");
    if (!s) return null;
    const hasC = s.includes(","), hasD = s.includes(".");
    if (hasC && hasD) {
      // o separador mais à direita é o decimal; o outro é milhar
      s = s.lastIndexOf(",") > s.lastIndexOf(".")
        ? s.replace(/\./g, "").replace(",", ".")
        : s.replace(/,/g, "");
    } else if (hasC) {
      s = s.replace(",", ".");                       // "28,4" → 28.4
    } else if (hasD) {
      const p = s.split(".");
      if (p.length > 2) s = p.join("");              // "1.234.567" → milhar repetido
      else if (p[1] && p[1].length === 3 && type !== "pct") s = p.join(""); // "9.519" → 9519
    }
    let n = parseFloat(s);
    if (isNaN(n)) return null;
    // "2,8 mil": o 2,8 é decimal de verdade, não milhar — multiplica depois de parsear.
    if (mult > 1) n = n * mult;
    if (type === "int") n = Math.round(n);
    return neg ? -n : n;
  };
  // Valor abreviado perde precisão (R$ 2,8 mil = qualquer coisa entre 2.750 e 2.849).
  // Quem consome usa isso pra avisar que o número é aproximado, não pra corrigir.
  L.ehAbreviado = raw => raw != null && L.SUFIXOS.some(([rx]) => rx.test(String(raw)));

  /* ============ benchmarks ============
     Fonte única: benchmarks.js, gerado de `lives` por gerar_benchmarks_live.py.
     O fallback abaixo só existe pra extensão não quebrar se o arquivo faltar —
     está marcado como stale pra aparecer no painel, não pra passar por dado fresco. */
  L.FALLBACK = {
    gerado_em: null, fonte: "fallback embutido (benchmarks.js ausente)", stale: true,
    perfis: {
      views: {
        janela: { de: "2026-03", ate: "2026-05", lives: 108 },
        ctr: { v: 22.43 }, co: { v: 2.54 }, convView: { v: 0.57 },
        ticket: { v: 81.88 }, gmvPerLive: { v: 3703.21 }, views: { v: 8283 }, peakViewers: { v: 180 },
      },
      impressoes: {
        janela: { de: "2026-06", ate: "2026-07", lives: 93 },
        ctr: { v: 6.58 }, co: { v: 2.85 }, convView: { v: 0.19 },
        ticket: { v: 85.45 }, gmvPerLive: { v: 3379.79 }, views: { v: 5648 }, peakViewers: null,
      },
    },
  };

  L.getBenchmarkSource = function (scope) {
    const g = (scope || (typeof self !== "undefined" ? self : globalThis));
    return (g && g.DASHLIVE_BENCHMARKS) || L.FALLBACK;
  };

  /* Achata o perfil escolhido em { ctr, co, convView, ticket, gmvPerLive, views, peakViewers }. */
  L.resolveBenchmarks = function (src, profile) {
    const p = (src && src.perfis && src.perfis[profile]) || null;
    if (!p) return null;
    const val = k => (p[k] && p[k].v != null ? p[k].v : null);
    return {
      profile,
      ctr: val("ctr"), co: val("co"), convView: val("convView"),
      ticket: val("ticket"), gmvPerLive: val("gmvPerLive"),
      views: val("views"), peakViewers: val("peakViewers"),
      janela: p.janela || null,
      identidade: p.identidade || null,
      geradoEm: src.gerado_em || null,
      stale: !!src.stale,
    };
  };

  /* ============ detecção do perfil de CTR (R11) ============
     `lives.ctr` mudou de denominador entre schemas do export, e a tela ao vivo segue
     um dos dois. Comparar 6,5% real contra bench de 22,4% pintaria a live de vermelho
     a noite inteira — por isso o perfil é detectado, não presumido.

     Via 1 (exata): com cliques calibrados, reproduz os dois quocientes e vê qual bate.
     Via 2 (magnitude): sem cliques, escolhe o bench mais próximo em escala log.
       Só decide se um for claramente mais perto — empate devolve null e o painel
       segue no último perfil conhecido em vez de chutar. */
  L.detectCtrProfile = function (r, src) {
    const S = src || L.getBenchmarkSource();
    const perfis = (S && S.perfis) || {};
    const ctr = r && r.ctr;
    if (ctr == null || !(ctr > 0)) return { profile: null, method: "sem-ctr", confident: false };

    if (r.clicks > 0) {
      const cand = [
        { profile: "views", den: r.views },
        { profile: "impressoes", den: r.impressions },
      ].filter(c => c.den > 0 && perfis[c.profile])
       .map(c => ({ profile: c.profile, erro: Math.abs(100 * r.clicks / c.den - ctr) }))
       .sort((a, b) => a.erro - b.erro);
      // 0,5 p.p. absorve arredondamento da tela sem aceitar o denominador errado
      // (os dois quocientes vivem em ordens de grandeza distintas: ~22% vs ~6%).
      if (cand.length && cand[0].erro <= 0.5) {
        return { profile: cand[0].profile, method: "identidade", confident: true, erro: +cand[0].erro.toFixed(3) };
      }
    }

    const dists = Object.keys(perfis)
      .filter(k => perfis[k] && perfis[k].ctr && perfis[k].ctr.v > 0)
      .map(k => ({ profile: k, d: Math.abs(Math.log(ctr / perfis[k].ctr.v)) }))
      .sort((a, b) => a.d - b.d);
    if (!dists.length) return { profile: null, method: "sem-bench", confident: false };
    if (dists.length === 1) return { profile: dists[0].profile, method: "magnitude", confident: false };
    // 0,5 em log ≈ 1,65× de folga. Calibrado contra 75 lives reais (tests/): abaixo
    // disso a via magnitude começa a escolher a régua errada em vez de admitir dúvida.
    // Ela nunca vira `confident` — uma live de CTR genuinamente ruim é indistinguível
    // de uma live medida no outro denominador, e só os cliques desempatam.
    const ambiguo = dists[1].d - dists[0].d < 0.5;
    return {
      profile: ambiguo ? null : dists[0].profile,
      method: ambiguo ? "ambiguo" : "magnitude",
      confident: false,
    };
  };

  /* ============ reconhecimento de rótulo (auto-mapeamento) ============
     A calibração manual existe porque o TikTok ofusca as CLASSES — mas os RÓTULOS
     são texto em português e estáveis ("GMV atribuído", "Cliques no produto").
     Dá pra reconhecer a maioria sozinho e deixar o clique só pro que sobrar.

     `evita` é tão importante quanto `aceita`: "Itens atribuídos" mora ao lado de
     "GMV atribuído" e não é pedido — casar errado ali estraga o ticket em silêncio. */
  L.normalizarRotulo = t => String(t == null ? "" : t)
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")   // tira acento
    .toLowerCase()
    .replace(/[.…:%()$>]/g, " ")
    .replace(/\s+/g, " ")
    .trim();

  // `perfilCtr`: alguns rótulos já DIZEM o denominador. "CTR por LIVE" é cliques
  // sobre visualizações da live — com isso a régua sai do próprio nome do campo,
  // sem depender de calibrar os cliques pra fechar a conta.
  L.ALIASES = [
    { key:"gmv",         aceita:["gmv atribuido","gmv da live","gmv total","gmv r","gmv","receita atribuida","receita da live"], evita:["por hora","medio","gmv max","meta","hora"] },
    // "SKU" fica de fora de propósito: pedido de SKU conta por SKU, pedido conta por
    // compra. O bench de ticket é GMV ÷ PEDIDOS — misturar os dois desloca o ticket
    // sem avisar. Fora que na tabela de produtos essa coluna é por linha, não total.
    { key:"orders",      aceita:["pedidos atribuidos","total de pedidos","pedidos","numero de pedidos"], evita:["itens","item","produtos vendidos","por hora","valor","taxa","porcentagem","ctor","sku","%"] },
    { key:"liveViewers", aceita:["espectadores atuais","espectadores ativos","espectadores ao vivo","espectadores agora","espectadores no momento","audiencia ao vivo"], evita:["total","acumulad","duracao","medi"] },
    { key:"viewers",     aceita:["visualizacoes","total de espectadores","espectadores totais","views","visualizacoes da live"], evita:["duracao","medi","por hora","ativos","1 min","min","taxa","porcentagem"] },
    { key:"clicks",      aceita:["cliques no produto","cliques em produto","cliques nos produtos","product clicks","total de cliques"], evita:["porcentagem","taxa","por hora","ctr"] },
    { key:"ctr",         aceita:["ctr por live"], evita:[], perfilCtr:"views" },
    { key:"ctr",         aceita:["porcentagem de cliques no produto","porcentagem de cliques","taxa de cliques no produto","taxa de cliques","ctr"], evita:["compra","pedido","conversao","por hora"] },
    { key:"co",          aceita:["taxa de compra apos clique","compra apos clique","taxa de conversao apos clique","conversao apos clique"], evita:["visualizacao","view"] },
    // "Taxa de pedidos (SKU)" NÃO é o CO: é pedido sobre VISUALIZAÇÃO, ou seja, a
    // conversão por visualização (CTR × CO). Confirmado na tela de 08/08/26 —
    // 0,34% × 581 views = 1,98 ≈ os 2 itens vendidos. Tratar como CO derrubaria
    // o painel pra vermelho, que é o mesmo erro do R10 por outro caminho.
    { key:"convView",    aceita:["taxa de pedidos sku","taxa de pedidos","taxa de conversao por visualizacao","conversao por visualizacao"], evita:["clique","click"] },
    { key:"impressions", aceita:["impressoes da live","impressoes do produto","impressoes de produto","impressoes","exibicoes do produto"], evita:["por hora","gpm","taxa"] },
    { key:"comments",    aceita:["comentarios","total de comentarios"], evita:["taxa","porcentagem"] },
    { key:"err",         aceita:["taxa de entrada","err","entry rate"], evita:["saida"] },
  ];

  // Qual perfil de CTR o próprio rótulo revela (null quando o nome não diz).
  L.perfilPeloRotulo = function (texto) {
    const t = L.normalizarRotulo(texto);
    for (const a of L.ALIASES) {
      if (!a.perfilCtr) continue;
      if (a.aceita.some(x => t === x || t.includes(x))) return a.perfilCtr;
    }
    return null;
  };

  // CO não aparece em toda tela. Quando a página dá a conversão por visualização
  // (ex: "Taxa de pedidos (SKU)") e o CTR, o CO sai da identidade CTR × CO = convView.
  // É derivação legítima — o inverso do erro R10, que chamava o CO de convView.
  L.deriveCO = (convView, ctr) => (convView == null || !(ctr > 0) ? null : convView * 100 / ctr);

  /* Devolve a métrica que o rótulo representa, ou null.
     Casa por igualdade, depois por conter, e por fim por PREFIXO — porque a tela
     trunca com reticências ("Porcentagem d…") e às vezes o corte chega ao texto. */
  L.metricaDoRotulo = function (texto) {
    const t = L.normalizarRotulo(texto);
    if (!t || t.length < 3) return null;
    const bloqueado = a => (a.evita || []).some(e => t.includes(e));
    for (const a of L.ALIASES) if (!bloqueado(a) && a.aceita.some(x => t === x)) return a.key;
    // Alias curto ("err", "ctr", "views") só vale por igualdade: por "conter", QUALQUER
    // rótulo com essas 3 letras casaria — foi assim que "ERR" capturou o contador de
    // comentários e virou 6.475%.
    for (const a of L.ALIASES) if (!bloqueado(a) && a.aceita.some(x => x.length >= 6 && t.includes(x))) return a.key;
    for (const a of L.ALIASES) {
      if (bloqueado(a)) continue;
      // prefixo só vale com 8+ caracteres: abaixo disso "taxa de" casaria com tudo
      if (a.aceita.some(x => x.length >= 8 && t.length >= 8 && (x.startsWith(t) || t.startsWith(x)))) return a.key;
    }
    return null;
  };

  /* ============ derivados ============ */
  // Conversão por visualização é o PRODUTO das duas etapas (view→clique→pedido).
  // O build antigo tratava o CO como se fosse essa conversão e dividia por CTR — R10.
  L.deriveConvView = (ctr, co) => (ctr == null || co == null ? null : ctr * co / 100);
  L.computeGpm = (gmv, impressions) => (gmv == null || !(impressions > 0) ? null : gmv / impressions * 1000);
  L.grade = (ratio, warnAt, badAt) => (ratio >= warnAt ? "good" : ratio >= badAt ? "warn" : "bad");

  if (typeof module !== "undefined" && module.exports) module.exports = L;
  else (typeof self !== "undefined" ? self : globalThis).DashLiveLib = L;
})();
