/*!
 * Rhode Size Finder — motor de recomendação de tamanho de calça.
 *
 * Função pura / stateless: entra medida do corpo (ou peso + altura), sai o
 * tamanho + metadados de caimento. Sem estado, sem UI acoplada — serve tanto
 * o webview do link da bio quanto o "modo operador" usado na live.
 *
 * Prosa em PT-BR, identificadores em inglês. Modelagem no MVP: Wide Leg.
 * Arquitetura preparada pra multi-modelagem (ver CHARTS + recommendAll).
 *
 * UMD: no browser expõe `window.RhodeSizeFinder`; no Node/endpoint expõe
 * `module.exports`. Mesmo arquivo é a fonte de verdade nos dois lados.
 */
(function (root, factory) {
  var api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.RhodeSizeFinder = api;
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // ── 1. Dados — a grade ────────────────────────────────────────────
  // Valores = circunferência da PEÇA (não do corpo), em cm.
  // `fit` = constantes de caimento POR modelagem (podem variar por corte).
  // `sizes` sempre ordenado crescente por `size`.
  var CHARTS = {
    wide_leg: {
      label: 'Wide Leg',
      fit: { hipEaseMin: 2, soltaStep: 1 },
      sizes: [
        { size: 36, waist: 68, hip: 100, length: 110 },
        // ⚠️ Pendência #1: waist 74 está fora da progressão (68→72→76→80→84→88).
        // Provável typo (deveria ser 72). Manter o valor oficial até confirmação;
        // se confirmado o erro, trocar só esta linha.
        { size: 38, waist: 74, hip: 104, length: 110 },
        { size: 40, waist: 76, hip: 108, length: 110 },
        { size: 42, waist: 80, hip: 112, length: 110 },
        { size: 44, waist: 84, hip: 116, length: 110 },
        { size: 46, waist: 88, hip: 120, length: 110 }
      ]
    }
    // Pendência #2: mom / baggy / chocolate — adicionar aqui quando as grades
    // chegarem, cada uma com sua própria `sizes` e seu próprio `fit`.
  };

  var DEFAULT_MODEL = 'wide_leg';

  // ── 9. Validação de input — ranges de sanidade ────────────────────
  var RANGES = {
    waistCm:  [45, 130],
    hipCm:    [45, 170],
    weightKg: [35, 180],
    heightCm: [130, 210]
  };
  var UNIT = { weightKg: 'kg', heightCm: 'cm', waistCm: 'cm', hipCm: 'cm' };

  // ── Helpers de número ─────────────────────────────────────────────
  // Aceita vírgula OU ponto como separador decimal (seção 9).
  function parseNum(v) {
    if (v === null || v === undefined) return null;
    if (typeof v === 'number') return isFinite(v) ? v : null;
    var s = String(v).trim();
    if (!s) return null;
    s = s.replace(',', '.');
    var n = parseFloat(s);
    return isFinite(n) ? n : null;
  }
  function round1(n) { return Math.round(n * 10) / 10; }
  function clamp(n, lo, hi) { return Math.max(lo, Math.min(hi, n)); }
  function inRange(field, v) { var r = RANGES[field]; return v >= r[0] && v <= r[1]; }
  // Formata número pra texto PT-BR (ponto → vírgula).
  function fmt(n) { return String(n).replace('.', ','); }

  function inputError(field, message) {
    return { error: { type: 'input', field: field, message: message } };
  }
  function rangeMsg(label, field) {
    var r = RANGES[field];
    return 'Valor de ' + label + ' fora do intervalo esperado (' +
           r[0] + '–' + r[1] + ' ' + UNIT[field] + ').';
  }

  // ── 3. Helpers de grade ───────────────────────────────────────────
  // Cintura da peça é o teto: precisa ser >= cintura do corpo pra fechar.
  function sizeByWaist(chart, bw) {
    var sizes = chart.sizes;
    for (var i = 0; i < sizes.length; i++) {
      if (sizes[i].waist >= bw) return { obj: sizes[i], index: i, over: false };
    }
    return { obj: sizes[sizes.length - 1], index: sizes.length - 1, over: true };
  }
  // Quadril da peça deve ser um pouco maior que o do corpo (folga hipEaseMin).
  function sizeByHip(chart, bh, fit) {
    var sizes = chart.sizes;
    var need = bh + fit.hipEaseMin;
    for (var i = 0; i < sizes.length; i++) {
      if (sizes[i].hip >= need) return { obj: sizes[i], index: i, over: false };
    }
    return { obj: sizes[sizes.length - 1], index: sizes.length - 1, over: true };
  }

  function populatedModels() {
    return Object.keys(CHARTS).filter(function (m) {
      return CHARTS[m].sizes && CHARTS[m].sizes.length;
    });
  }

  // ── 6. Mensagens (texto exibível) a partir das flags ──────────────
  // `flags` são chaves estáveis pra máquina; `messages` são pra tela.
  function buildMessages(f, ctx) {
    var m = [];
    var rec = ctx.rec, prev = ctx.prev;
    if (f.cantClose) {
      var top = ctx.sizes[ctx.sizes.length - 1];
      m.push({ level: 'hard', text:
        'Sua cintura (' + fmt(ctx.bw) + ' cm) passa da maior peça da grade ' +
        '(tamanho ' + top.size + ', cintura ' + top.waist + ' cm). Não temos um ' +
        'tamanho que feche com folga — fala com a gente pra ver outra modelagem ou peça sob medida.' });
    }
    if (f.looseAtMin) {
      m.push({ level: 'warn', text:
        'Sua cintura (' + fmt(ctx.bw) + ' cm) fica abaixo da nossa menor peça: o ' +
        rec.size + ' (cintura ' + rec.waist + ' cm) vai sobrar ~' + fmt(ctx.waistEase) +
        ' cm. Fecha, mas um cinto ajuda no caimento.' });
    }
    if (f.betweenSizes) {
      if (prev) {
        m.push({ level: 'info', text:
          'Você tá entre tamanhos: o ' + prev.size + ' (cintura ' + prev.waist + ') não fecha e o ' +
          rec.size + ' (cintura ' + rec.waist + ') sobra ~' + fmt(ctx.waistEase) + ' cm. ' +
          'Indicamos o ' + rec.size + '; cinto ajusta se quiser mais no corpo.' });
      } else {
        m.push({ level: 'info', text:
          'O ' + rec.size + ' (cintura ' + rec.waist + ') sobra ~' + fmt(ctx.waistEase) +
          ' cm na sua cintura. Fecha bem; cinto ajusta se quiser mais no corpo.' });
      }
    }
    if (f.pear) {
      m.push({ level: 'info', text:
        'Seu quadril pediu o ' + rec.size + ' (pra não apertar), então a cintura fica um ' +
        'pouco folgada nesse tamanho — é normal na ' + ctx.label + '. Um cinto resolve se incomodar.' });
    }
    if (f.hipTight) {
      m.push({ level: 'warn', text:
        'O quadril (' + fmt(ctx.bh) + ' cm) fica justo no ' + rec.size + ' (quadril da peça ' +
        rec.hip + ' cm, folga de só ' + fmt(ctx.hipEase) + ' cm). Se quiser mais conforto, ' +
        'peça a versão "solta" (um número acima).' });
    }
    if (f.hipUnknown) {
      m.push({ level: 'info', text:
        'Recomendamos só pela cintura. Se puder medir o quadril também, a gente confirma o caimento.' });
    }
    if (f.maxed) {
      m.push({ level: 'info', text:
        'O ' + rec.size + ' já é o maior tamanho da grade — não dá pra subir mais pro caimento "solta".' });
    }
    return m;
  }

  // Resumo curto pra tela (seção 8).
  function buildSummary(f, ctx) {
    if (f.cantClose) return 'Sem tamanho viável na grade ' + ctx.label + ' — recomendamos consultar.';
    var waistPart;
    if (ctx.preference === 'solta') waistPart = 'Um número acima, mais solta na cintura';
    else if (f.looseAtMin) waistPart = 'Cintura folgada (abaixo da grade)';
    else waistPart = 'No corpo na cintura';

    var hipPart;
    if (f.hipUnknown) hipPart = 'sem medida de quadril';
    else if (f.pear) hipPart = 'com o quadril definindo o tamanho';
    else if (f.hipTight) hipPart = 'com o quadril justo';
    else hipPart = 'com folga confortável no quadril';

    return waistPart + ', ' + hipPart;
  }

  // ── 4. Modo A — por medidas (principal) ───────────────────────────
  function recommend(waistCm, hipCm, preference, model) {
    model = model || DEFAULT_MODEL;
    var chart = CHARTS[model];
    if (!chart || !chart.sizes || !chart.sizes.length) {
      return inputError('model', 'Modelagem "' + model + '" não tem grade cadastrada.');
    }
    preference = (preference === 'solta') ? 'solta' : 'corpo';
    var fit = chart.fit;
    var sizes = chart.sizes;
    var lastIndex = sizes.length - 1;

    // --- validação de input ---
    var bw = parseNum(waistCm);
    if (bw === null) return inputError('waistCm', 'Informe a cintura (cm) — é o único campo obrigatório.');
    if (!inRange('waistCm', bw)) return inputError('waistCm', rangeMsg('cintura', 'waistCm'));

    var hipUnknown = true, bh = null;
    var rawHip = parseNum(hipCm);
    if (rawHip !== null) {
      if (!inRange('hipCm', rawHip)) return inputError('hipCm', rangeMsg('quadril', 'hipCm'));
      bh = rawHip; hipUnknown = false;
    }

    // --- seleção do tamanho ---
    var w = sizeByWaist(chart, bw);
    var baseIndex = w.index;
    var cantClose = bw > sizes[lastIndex].waist; // cintura passa da maior peça

    var hipDriven = false, hipOver = false;
    if (!hipUnknown) {
      var h = sizeByHip(chart, bh, fit);
      hipOver = h.over;
      if (h.index > baseIndex) { baseIndex = h.index; hipDriven = true; }
    }

    var recIndex = baseIndex;
    var maxed = false;
    if (preference === 'solta') {
      if (recIndex < lastIndex) recIndex += fit.soltaStep;
      else maxed = true;
    }
    if (recIndex > lastIndex) recIndex = lastIndex; // guard p/ soltaStep > 1

    var rec = sizes[recIndex];
    var prev = recIndex > 0 ? sizes[recIndex - 1] : null;

    var waistEase = round1(rec.waist - bw);
    var hipEase = hipUnknown ? null : round1(rec.hip - bh);

    // ── 6. Flags / edge cases ──
    var f = {
      cantClose:    cantClose,
      looseAtMin:   (rec.size === sizes[0].size && waistEase > 5 && !cantClose),
      betweenSizes: (!cantClose && waistEase >= 4 && waistEase <= 9 && preference !== 'solta'),
      pear:         hipDriven,
      hipTight:     (!hipUnknown && hipEase < fit.hipEaseMin && !hipOver),
      hipUnknown:   hipUnknown,
      maxed:        maxed
    };
    var flagOrder = ['cantClose', 'looseAtMin', 'betweenSizes', 'pear', 'hipTight', 'hipUnknown', 'maxed'];
    var flags = flagOrder.filter(function (k) { return f[k]; });

    // ── 7. Confiança ──
    var confidence;
    if (f.cantClose || hipOver) confidence = 'consultar';
    else if (f.pear || f.betweenSizes || f.hipUnknown || f.hipTight) confidence = 'media';
    else confidence = 'alta';

    var ctx = {
      rec: rec, prev: prev, sizes: sizes, label: chart.label,
      bw: bw, bh: bh, waistEase: waistEase, hipEase: hipEase,
      preference: preference
    };

    var recommendedSize = f.cantClose ? null : rec.size;

    // ── 8. Contrato de saída ──
    return {
      mode: 'medidas',
      model: model,
      recommendedSize: recommendedSize,
      fit: {
        waistEaseCm: f.cantClose ? null : waistEase,
        hipEaseCm: hipEase,
        preference: preference
      },
      confidence: confidence,
      flags: flags,
      messages: buildMessages(f, ctx),
      summary: buildSummary(f, ctx),
      garment: f.cantClose ? null
        : { size: rec.size, waist: rec.waist, hip: rec.hip, length: rec.length },
      input: { waistCm: bw, hipCm: hipUnknown ? null : bh, preference: preference }
    };
  }

  // ── 5. Modo B — rápido (peso + altura) ────────────────────────────
  function quickEstimate(weightKg, heightCm, preference, model) {
    model = model || DEFAULT_MODEL;
    preference = (preference === 'solta') ? 'solta' : 'corpo';

    var wkg = parseNum(weightKg);
    if (wkg === null) return inputError('weightKg', 'Informe o peso (kg).');
    if (!inRange('weightKg', wkg)) return inputError('weightKg', rangeMsg('peso', 'weightKg'));

    var hcm = parseNum(heightCm);
    if (hcm === null) return inputError('heightCm', 'Informe a altura (cm).');
    if (!inRange('heightCm', hcm)) return inputError('heightCm', rangeMsg('altura', 'heightCm'));

    var hM = hcm / 100;
    var bmi = wkg / (hM * hM);

    // Heurística de placeholder — NÃO é modelo calibrado (ver seção 5).
    var estWaist = Math.round(70 + (bmi - 21) * 2.3);
    estWaist = clamp(estWaist, 55, 100);
    var estHip = estWaist + 24;

    // Reaproveita o Modo A rodando sobre valores estimados, com margem ±3.
    var found = {};
    [-3, 0, 3].forEach(function (d) {
      var r = recommend(estWaist + d, estHip + d, preference, model);
      if (r && !r.error && r.recommendedSize != null) found[r.recommendedSize] = true;
    });
    var keys = Object.keys(found).map(Number).sort(function (a, b) { return a - b; });
    var range = keys.length ? [keys[0], keys[keys.length - 1]] : [null, null];

    return {
      mode: 'rapido',
      model: model,
      recommendedRange: range,
      confidence: 'estimativa',
      estimated: { waistCm: estWaist, hipCm: estHip, bmi: round1(bmi) },
      input: { weightKg: wkg, heightCm: hcm, preference: preference },
      note: 'Estimativa por peso/altura. Recomendar medir a cintura pra confirmar.'
    };
  }

  // ── 10. Multi-modelagem ───────────────────────────────────────────
  // Roda o recommend em todas as modelagens populadas → array pra UI mostrar
  // "Wide Leg 38 · Mom 36 · Baggy 38".
  function recommendAll(waistCm, hipCm, preference) {
    return populatedModels().map(function (m) {
      return recommend(waistCm, hipCm, preference, m);
    });
  }

  return {
    version: '1.0.0',
    CHARTS: CHARTS,
    RANGES: RANGES,
    DEFAULT_MODEL: DEFAULT_MODEL,
    recommend: recommend,
    quickEstimate: quickEstimate,
    recommendAll: recommendAll,
    populatedModels: populatedModels,
    parseNum: parseNum
  };
}));
