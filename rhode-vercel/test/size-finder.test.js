/*
 * Testes do motor Rhode Size Finder — zero dependência.
 * Rodar: node rhode-vercel/test/size-finder.test.js
 *
 * Valida os exemplos do contrato (seção 8), as flags/edge-cases (seção 6),
 * a confiança (seção 7), o Modo B (seção 5) e a validação de input (seção 9).
 */
var assert = require('assert');
var SF = require('../public/size-finder.js');

var passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); passed++; console.log('  ✓ ' + name); }
  catch (e) { failed++; console.log('  ✗ ' + name + '\n      ' + e.message); }
}

console.log('\nRhode Size Finder — suite\n');

// ── Modo A — exemplo do contrato (seção 8) ────────────────────────
test('Modo A exemplo: cintura 70, quadril 98, corpo → 38 / betweenSizes / media', function () {
  var r = SF.recommend(70, 98, 'corpo');
  assert.strictEqual(r.recommendedSize, 38);
  assert.strictEqual(r.confidence, 'media');
  assert.deepStrictEqual(r.flags, ['betweenSizes']);
  assert.strictEqual(r.fit.waistEaseCm, 4);
  assert.strictEqual(r.fit.hipEaseCm, 6);
  assert.deepStrictEqual(r.garment, { size: 38, waist: 74, hip: 104, length: 110 });
  assert.strictEqual(r.summary, 'No corpo na cintura, com folga confortável no quadril');
  assert.strictEqual(r.messages.length, 1);
  assert.strictEqual(r.messages[0].level, 'info');
});

// ── Modo B — exemplo do contrato (seção 8) ────────────────────────
test('Modo B exemplo: 62kg / 165cm → range [38,42] / estWaist 74 / estHip 98 / bmi 22.8', function () {
  var r = SF.quickEstimate(62, 165, 'corpo');
  assert.strictEqual(r.mode, 'rapido');
  assert.deepStrictEqual(r.recommendedRange, [38, 42]);
  assert.strictEqual(r.confidence, 'estimativa');
  assert.strictEqual(r.estimated.waistCm, 74);
  assert.strictEqual(r.estimated.hipCm, 98);
  assert.strictEqual(r.estimated.bmi, 22.8);
});

// ── Helpers (seção 3) ─────────────────────────────────────────────
test('sizeByWaist: menor peça que fecha (72 → 38)', function () {
  assert.strictEqual(SF.recommend(72).recommendedSize, 38); // waist>=72 → 38 (waist 74)
  assert.strictEqual(SF.recommend(68).recommendedSize, 36); // exato no 36
});

// ── Flag cantClose (seção 6) ──────────────────────────────────────
test('cantClose: cintura 90 > 88 → recommendedSize null / consultar / garment null', function () {
  var r = SF.recommend(90, null, 'corpo');
  assert.strictEqual(r.recommendedSize, null);
  assert.strictEqual(r.confidence, 'consultar');
  assert.strictEqual(r.garment, null);
  assert.ok(r.flags.indexOf('cantClose') === 0);
  assert.strictEqual(r.fit.waistEaseCm, null);
  assert.strictEqual(r.messages[0].level, 'hard');
});

// ── Flag looseAtMin (seção 6) ─────────────────────────────────────
test('looseAtMin: cintura 60 → 36 sobra >5 cm, flag looseAtMin', function () {
  var r = SF.recommend(60, null, 'corpo');
  assert.strictEqual(r.recommendedSize, 36);
  assert.ok(r.flags.indexOf('looseAtMin') !== -1);
});

// ── Flag pear / hipDriven (seção 6) ───────────────────────────────
test('pear: cintura 70 (pede 38) + quadril 118 força 46 → pear / consultar(hipOver)', function () {
  var r = SF.recommend(70, 118, 'corpo');
  assert.strictEqual(r.recommendedSize, 46);
  assert.ok(r.flags.indexOf('pear') !== -1);
  // quadril 118 + folga 2 = 120 = maior peça, ainda fecha (não é hipOver)
  assert.strictEqual(r.confidence, 'media');
});

test('pear moderado: cintura 70 + quadril 110 → quadril força tamanho maior que a cintura', function () {
  var r = SF.recommend(70, 110, 'corpo');
  // cintura 70 pediria 38; quadril 110+2=112 → 42
  assert.strictEqual(r.recommendedSize, 42);
  assert.ok(r.flags.indexOf('pear') !== -1);
  assert.strictEqual(r.confidence, 'media');
});

// ── hipOver → consultar (seção 7) ─────────────────────────────────
test('hipOver: quadril 120 estoura a grade → consultar', function () {
  var r = SF.recommend(74, 120, 'corpo'); // 120+2=122 > 120
  assert.strictEqual(r.confidence, 'consultar');
});

// ── Flag hipTight (seção 6) — quirk documentado ───────────────────
// A flag existe no motor (fiel à spec), mas a lógica de seleção a torna
// estruturalmente inalcançável: sempre que uma peça cobre o quadril sem
// estourar a grade (não hipOver), a folga é >= hipEaseMin por construção
// (sizeByHip pega a menor peça com hip >= bh + min). Quando o quadril NÃO
// cabe, cai em hipOver → consultar, não hipTight. Registrado pra revisão
// futura (pendência: recalibrar hipEaseMin ou a regra da flag).
test('hipTight nunca dispara no domínio válido (varredura) — vira hipOver/consultar', function () {
  var everTight = false;
  for (var bw = 45; bw <= 130; bw += 1) {
    for (var bh = 45; bh <= 170; bh += 1) {
      var r = SF.recommend(bw, bh, 'corpo');
      if (!r.error && r.flags.indexOf('hipTight') !== -1) everTight = true;
    }
  }
  assert.strictEqual(everTight, false, 'hipTight disparou — a lógica mudou; revisar a spec');
});

test('quadril no limite da grade → consultar via hipOver (não hipTight)', function () {
  var r = SF.recommend(88, 119, 'corpo'); // 119+2=121 > 120 (maior hip) → hipOver
  assert.strictEqual(r.confidence, 'consultar');
  assert.strictEqual(r.flags.indexOf('hipTight'), -1);
});

// ── Flag hipUnknown (seção 6) ─────────────────────────────────────
test('hipUnknown: sem quadril → flag hipUnknown / media / hipEaseCm null', function () {
  var r = SF.recommend(74, null, 'corpo');
  assert.ok(r.flags.indexOf('hipUnknown') !== -1);
  assert.strictEqual(r.confidence, 'media');
  assert.strictEqual(r.fit.hipEaseCm, null);
  assert.strictEqual(r.input.hipCm, null);
});

// ── Preferência solta + maxed (seção 4/6) ─────────────────────────
test('solta: sobe um número (cintura 74 → 38 vira 40)', function () {
  var r = SF.recommend(74, null, 'solta');
  assert.strictEqual(r.recommendedSize, 40);
  assert.strictEqual(r.fit.preference, 'solta');
  // solta desliga betweenSizes
  assert.strictEqual(r.flags.indexOf('betweenSizes'), -1);
});

test('maxed: solta já no 46 não sobe mais', function () {
  var r = SF.recommend(88, null, 'solta');
  assert.strictEqual(r.recommendedSize, 46);
  assert.ok(r.flags.indexOf('maxed') !== -1);
});

// ── Confiança alta (seção 7) ──────────────────────────────────────
test('alta: cintura exata + quadril folgado, sem flags de risco', function () {
  var r = SF.recommend(76, 100, 'corpo'); // 76 → 40 (hip 108); quadril 100 folga 8
  assert.strictEqual(r.recommendedSize, 40);
  assert.strictEqual(r.confidence, 'alta');
  assert.deepStrictEqual(r.flags, []);
});

// ── Validação de input (seção 9) ──────────────────────────────────
test('input: vírgula decimal aceita (70,5)', function () {
  var r = SF.recommend('70,5', '98,0', 'corpo');
  assert.ok(!r.error);
  assert.strictEqual(r.input.waistCm, 70.5);
});

test('input: cintura fora do range (200) → erro de input, não recomenda', function () {
  var r = SF.recommend(200, null, 'corpo');
  assert.ok(r.error);
  assert.strictEqual(r.error.type, 'input');
  assert.strictEqual(r.error.field, 'waistCm');
});

test('input: cintura ausente → erro (único campo obrigatório do Modo A)', function () {
  var r = SF.recommend('', null, 'corpo');
  assert.ok(r.error);
  assert.strictEqual(r.error.field, 'waistCm');
});

test('input Modo B: peso fora do range → erro', function () {
  var r = SF.quickEstimate(300, 165, 'corpo');
  assert.ok(r.error);
  assert.strictEqual(r.error.field, 'weightKg');
});

// ── Multi-modelagem (seção 10) ────────────────────────────────────
test('recommendAll: só wide_leg populado hoje → array de 1', function () {
  var arr = SF.recommendAll(74, 98, 'corpo');
  assert.strictEqual(arr.length, 1);
  assert.strictEqual(arr[0].model, 'wide_leg');
  assert.deepStrictEqual(SF.populatedModels(), ['wide_leg']);
});

// ── Comprimento fixo (seção 8) ────────────────────────────────────
test('length constante = 110 em todos os tamanhos', function () {
  SF.CHARTS.wide_leg.sizes.forEach(function (s) { assert.strictEqual(s.length, 110); });
});

console.log('\n' + passed + ' passaram, ' + failed + ' falharam.\n');
process.exit(failed ? 1 : 0);
