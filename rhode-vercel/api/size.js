/*
 * POST/GET /api/size — endpoint stateless do Rhode Size Finder.
 *
 * Wrapper fino sobre o motor puro (public/size-finder.js). Sem estado, sem DB,
 * sem segredo: dá pra chamar do webview do link da bio ou do modo operador da
 * live. A lógica mora no motor; aqui só normaliza input/output e faz CORS.
 *
 * Modo:
 *   - medidas (default): ?waistCm=&hipCm=&preference=corpo|solta[&model=][&all=1]
 *   - rapido: ?weightKg=&heightCm=&preference=  (ou mode=rapido)
 * Erro de input → HTTP 422 com { error: { type, field, message } }.
 */
var engine = require('../public/size-finder.js');

module.exports = async function handler(req, res) {
  // Stateless + dado público → CORS liberado (serve qualquer webview).
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  res.setHeader('Cache-Control', 'no-store');
  if (req.method === 'OPTIONS') return res.status(204).end();

  var q = (req.method === 'POST') ? (req.body || {}) : (req.query || {});
  var preference = (q.preference === 'solta') ? 'solta' : 'corpo';
  var model = q.model || undefined;

  var hasWeight = q.weightKg != null && q.weightKg !== '';
  var hasHeight = q.heightCm != null && q.heightCm !== '';
  var mode = q.mode || ((hasWeight && hasHeight) ? 'rapido' : 'medidas');
  var wantAll = q.all === '1' || q.all === 1 || q.all === true || q.all === 'true';

  var out;
  if (mode === 'rapido') {
    out = engine.quickEstimate(q.weightKg, q.heightCm, preference, model);
  } else if (wantAll) {
    out = { mode: 'medidas', preference: preference, results: engine.recommendAll(q.waistCm, q.hipCm, preference) };
  } else {
    out = engine.recommend(q.waistCm, q.hipCm, preference, model);
  }

  var status = (out && out.error) ? 422 : 200;
  return res.status(status).json(out);
};
