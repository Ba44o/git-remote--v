// ══════════════════════════════════════════════════════════════
// Rhode Jeans — Data Bridge v2
// Google Apps Script Web App
//
// Endpoints (GET):
//   ?action=all              → creators do período atual (sync_ready)
//   ?action=kpis             → KPIs + Δ% vs período anterior
//   ?action=periods          → lista de períodos disponíveis
//   ?action=trends&id=HANDLE → histórico de 1 creator
//   ?creator_id=X&gmail=Y&whatsapp=Z → cadastro (legado)
//   (sem parâmetros)         → health check
//
// Setup:
//   script.google.com → cole este código → Deploy → New deployment
//   Execute as: Me | Who has access: Anyone
// ══════════════════════════════════════════════════════════════

const SPREADSHEET_ID = '1hiyu1y9G7NeiBKnwV6FNlYRjVqTCRP3jY--I0Lv0Mh0';
const ADMIN_EMAIL    = 'humbertobasso9@gmail.com';

// Nomes das abas
const TAB_SYNC_READY     = 'sync_ready';
const TAB_RAW_IMPORTS    = 'raw_imports';
const TAB_PERIOD_SUMMARY = 'period_summary';
const TAB_MASTER         = 'creators_master';

// Colunas de cadastro
const COL_CREATOR_ID = 'creator_id';
const COL_GMAIL      = 'gmail';
const COL_WHATSAPP   = 'whatsapp';


// ══════════════════════════════════════════════════════════════
// ENTRY POINTS
// ══════════════════════════════════════════════════════════════

function doGet(e) {
  const p = e && e.parameter ? e.parameter : {};
  const action = p.action || '';

  try {
    if (action === 'all')      return actionAll();
    if (action === 'kpis')     return actionKpis();
    if (action === 'periods')  return actionPeriods();
    if (action === 'trends')   return actionTrends(p.id || '');
    if (action === 'insights') return actionInsights();
    if (p.creator_id)          return actionRegister(p);
    return respond({ status: 'ok', message: 'Rhode Bridge v2 ativo.', version: 2 });
  } catch(err) {
    return respond({ status: 'error', message: err.toString() });
  }
}

function doPost(e) {
  try {
    let creator_id, gmail, whatsapp;
    if (e.postData && e.postData.type === 'application/json') {
      const body = JSON.parse(e.postData.contents);
      creator_id = (body.creator_id || '').trim().toLowerCase();
      gmail      = (body.gmail      || '').trim().toLowerCase();
      whatsapp   = (body.whatsapp   || '').trim().replace(/\D/g, '');
    } else {
      creator_id = (e.parameter.creator_id || '').trim().toLowerCase();
      gmail      = (e.parameter.gmail      || '').trim().toLowerCase();
      whatsapp   = (e.parameter.whatsapp   || '').trim().replace(/\D/g, '');
    }
    return registerCreator(creator_id, gmail, whatsapp);
  } catch(err) {
    return respond({ status: 'error', message: err.toString() });
  }
}


// ══════════════════════════════════════════════════════════════
// ACTIONS
// ══════════════════════════════════════════════════════════════

// action=all → creators do período mais recente
function actionAll() {
  const rows = sheetToObjects(TAB_SYNC_READY);
  const creators = rows
    .filter(r => r['creator_id'])
    .map(r => ({
      nome:      r['creator_id'],
      gmv:       parseNum(r['gmv_bruto']),
      reimb:     parseNum(r['reembolso']),
      liq:       parseNum(r['gmv_liquido']),
      ped:       parseInt(r['pedidos'])    || 0,
      aov:       parseNum(r['aov']),
      vids:      parseInt(r['videos'])     || 0,
      lives:     parseInt(r['lives'])      || 0,
      comm:      parseNum(r['comissao']),
      amostras:  parseInt(r['amostras'])   || 0,
      tier:      r['tier'] || 'Ferro',
      periodo:   r['periodo'] || '',
      refPct:    parseNum(r['refund_pct']),
    }));

  const periodo = creators.length ? creators[0].periodo : '';
  return respond({ status: 'ok', total: creators.length, periodo, synced: new Date().toISOString(), creators });
}


// action=kpis → KPIs do período atual + Δ% vs anterior
function actionKpis() {
  const rows = sheetToObjects(TAB_PERIOD_SUMMARY);
  if (!rows.length) return respond({ status: 'ok', periods: [], current: null, previous: null });

  // Ordena por período
  const sorted = rows.sort((a, b) => a.periodo < b.periodo ? -1 : 1);
  const current  = sorted[sorted.length - 1];
  const previous = sorted.length > 1 ? sorted[sorted.length - 2] : null;

  function kpiObj(r) {
    if (!r) return null;
    return {
      periodo:             r['periodo'],
      periodo_inicio:      r['periodo_inicio'],
      periodo_fim:         r['periodo_fim'],
      gmv_bruto:           parseNum(r['gmv_bruto_total']),
      gmv_liquido:         parseNum(r['gmv_liquido_total']),
      gmv_liquido_proj:    parseNum(r['gmv_liquido_projetado']),
      reembolso:           parseNum(r['reembolso_total']),
      pedidos:             parseInt(r['pedidos_total'])   || 0,
      creators_ativas:     parseInt(r['creators_ativas']) || 0,
      creators_total:      parseInt(r['creators_total'])  || 0,
      videos:              parseInt(r['videos_total'])    || 0,
      lives:               parseInt(r['lives_total'])     || 0,
      comissao:            parseNum(r['comissao_total']),
      aov_medio:           parseNum(r['aov_medio']),
      refund_rate:         parseNum(r['refund_rate_pct']),
      dias_cobertos:       parseInt(r['dias_cobertos'])   || 0,
      dias_mes:            parseInt(r['dias_mes'])        || 0,
      periodo_parcial:     r['periodo_parcial'] === 'True' || r['periodo_parcial'] === true,
    };
  }

  const cur = kpiObj(current);
  const prv = kpiObj(previous);

  // Calcula deltas
  function delta(curVal, prvVal) {
    if (!prv || !prvVal || prvVal === 0) return null;
    return parseFloat(((curVal - prvVal) / Math.abs(prvVal) * 100).toFixed(1));
  }

  const deltas = prv ? {
    gmv_bruto:       delta(cur.gmv_bruto,      prv.gmv_bruto),
    gmv_liquido:     delta(cur.gmv_liquido,    prv.gmv_liquido),
    pedidos:         delta(cur.pedidos,        prv.pedidos),
    creators_ativas: delta(cur.creators_ativas, prv.creators_ativas),
    comissao:        delta(cur.comissao,       prv.comissao),
    aov_medio:       delta(cur.aov_medio,      prv.aov_medio),
    refund_rate:     delta(cur.refund_rate,    prv.refund_rate),
  } : null;

  const all_periods = sorted.map(r => r['periodo']);

  return respond({ status: 'ok', current: cur, previous: prv, deltas, all_periods });
}


// action=periods → lista de períodos com KPIs completos para tabela de evolução
function actionPeriods() {
  const rows = sheetToObjects(TAB_PERIOD_SUMMARY);
  const periods = rows
    .sort((a, b) => a.periodo < b.periodo ? -1 : 1)
    .map(r => ({
      periodo:          r['periodo'],
      periodo_inicio:   r['periodo_inicio'],
      periodo_fim:      r['periodo_fim'],
      gmv_bruto:        parseNum(r['gmv_bruto_total']),
      gmv_liquido:      parseNum(r['gmv_liquido_total']),
      gmv_liquido_proj: parseNum(r['gmv_liquido_projetado']),
      reembolso:        parseNum(r['reembolso_total']),
      pedidos:          parseInt(r['pedidos_total'])   || 0,
      creators_ativas:  parseInt(r['creators_ativas']) || 0,
      creators_total:   parseInt(r['creators_total'])  || 0,
      videos:           parseInt(r['videos_total'])    || 0,
      lives:            parseInt(r['lives_total'])     || 0,
      comissao:         parseNum(r['comissao_total']),
      aov_medio:        parseNum(r['aov_medio']),
      refund_rate:      parseNum(r['refund_rate_pct']),
      gmv_delta_pct:    parseNum(r['gmv_liquido_total_delta_pct']),
      dias_cobertos:    parseInt(r['dias_cobertos'])   || 0,
      dias_mes:         parseInt(r['dias_mes'])        || 0,
      periodo_parcial:  r['periodo_parcial'] === 'True' || r['periodo_parcial'] === true,
    }));
  return respond({ status: 'ok', total: periods.length, periods });
}


// action=trends&id=HANDLE → histórico mensal de 1 creator
function actionTrends(creatorId) {
  if (!creatorId) return respond({ status: 'error', message: 'id obrigatório' });
  const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');
  const rows = sheetToObjects(TAB_RAW_IMPORTS);

  const history = rows
    .filter(r => norm(r['creator_id'] || '') === norm(creatorId))
    .sort((a, b) => a.periodo < b.periodo ? -1 : 1)
    .map(r => ({
      periodo:  r['periodo'],
      gmv:      parseNum(r['gmv_bruto']),
      liq:      parseNum(r['gmv_liquido']),
      reimb:    parseNum(r['reembolso']),
      pedidos:  parseInt(r['pedidos'])  || 0,
      aov:      parseNum(r['aov']),
      vids:     parseInt(r['videos'])   || 0,
      lives:    parseInt(r['lives'])    || 0,
      comm:     parseNum(r['comissao_calculada'] || r['comissao']),
      refPct:   parseNum(r['refund_pct']),
      tier:     r['tier'] || 'Ferro',
    }));

  if (!history.length) return respond({ status: 'not_found', id: creatorId });

  // Calcula crescimento total
  const first = history[0].liq, last = history[history.length - 1].liq;
  const growth = first > 0 ? parseFloat(((last - first) / first * 100).toFixed(1)) : null;

  return respond({
    status: 'ok',
    creator_id: creatorId,
    periodos: history.length,
    growth_pct: growth,
    history,
  });
}


// action=insights → lê insights.json da aba analyst_insights
function actionInsights() {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName('analyst_insights');
  if (!sheet) return respond({ status: 'not_found', message: 'Aba analyst_insights não encontrada. Execute o ETL com analyst_v1.' });
  const val = sheet.getRange(1, 1).getValue();
  if (!val) return respond({ status: 'empty' });
  try {
    const data = JSON.parse(val.toString());
    return respond({ status: 'ok', insights: data });
  } catch(e) {
    return respond({ status: 'error', message: 'JSON inválido na aba analyst_insights.' });
  }
}


// Cadastro de creator (legado — manter compatibilidade)
function actionRegister(p) {
  const creator_id = (p.creator_id || '').trim().toLowerCase();
  const gmail      = (p.gmail      || '').trim().toLowerCase();
  const whatsapp   = (p.whatsapp   || '').trim().replace(/\D/g, '');
  return registerCreator(creator_id, gmail, whatsapp);
}


// ══════════════════════════════════════════════════════════════
// REGISTRO
// ══════════════════════════════════════════════════════════════

function registerCreator(creator_id, gmail, whatsapp) {
  if (!creator_id || !gmail || !whatsapp) {
    return respond({ status: 'error', message: 'Campos obrigatórios faltando.' });
  }

  const sheet   = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(TAB_SYNC_READY);
  const data    = sheet.getDataRange().getValues();
  const headers = data[0].map(h => h.toString().toLowerCase().trim());

  const idxId       = headers.indexOf(COL_CREATOR_ID);
  const idxGmail    = ensureColumn(sheet, headers, COL_GMAIL);
  const idxWhatsapp = ensureColumn(sheet, headers, COL_WHATSAPP);

  if (idxId === -1) return respond({ status: 'error', message: 'Coluna creator_id não encontrada.' });

  const normalize = s => s.toLowerCase().replace(/[^a-z0-9]/g, '');
  let targetRow = -1;
  for (let i = 1; i < data.length; i++) {
    if (normalize(String(data[i][idxId])) === normalize(creator_id)) {
      targetRow = i + 1;
      break;
    }
  }

  if (targetRow === -1) return respond({ status: 'not_found' });

  const currentGmail = sheet.getRange(targetRow, idxGmail + 1).getValue().toString().trim();
  if (currentGmail) {
    notifyAdmin(creator_id, gmail, currentGmail);
    return respond({ status: 'duplicate' });
  }

  sheet.getRange(targetRow, idxGmail    + 1).setValue(gmail);
  sheet.getRange(targetRow, idxWhatsapp + 1).setValue(whatsapp);
  notifyAdminNew(creator_id, gmail, whatsapp);
  return respond({ status: 'ok' });
}


// ══════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════

function respond(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// Lê uma aba e retorna array de objetos {coluna: valor}
function sheetToObjects(tabName) {
  const sheet = SpreadsheetApp.openById(SPREADSHEET_ID).getSheetByName(tabName);
  if (!sheet) return [];
  const data = sheet.getDataRange().getValues();
  if (data.length < 2) return [];
  const headers = data[0].map(h => h.toString().toLowerCase().trim());
  return data.slice(1).map(row => {
    const obj = {};
    headers.forEach((h, i) => { obj[h] = row[i]; });
    return obj;
  });
}

// Converte número do Sheets (nativo, US "8055.55", ou PT-BR "8.055,55")
function parseNum(v) {
  if (!v && v !== 0) return 0;
  if (typeof v === 'number') return v;
  const s = String(v).replace(/R\$\s*/g, '').trim();
  if (!s || s === '-' || s === '') return 0;
  if (s.includes(',')) return parseFloat(s.replace(/\./g, '').replace(',', '.')) || 0;
  return parseFloat(s) || 0;
}

// Garante que coluna existe; retorna índice 0-based
function ensureColumn(sheet, headers, colName) {
  let idx = headers.indexOf(colName);
  if (idx === -1) {
    sheet.getRange(1, sheet.getLastColumn() + 1).setValue(colName);
    headers.push(colName);
    idx = headers.length - 1;
  }
  return idx;
}

function notifyAdmin(creator_id, newGmail, existingGmail) {
  MailApp.sendEmail(ADMIN_EMAIL,
    `[Rhode Hub] Tentativa de recadastro — ${creator_id}`,
    `Creator: ${creator_id}\nGmail tentado: ${newGmail}\nGmail cadastrado: ${existingGmail}\nhttps://docs.google.com/spreadsheets/d/${SPREADSHEET_ID}`
  );
}

function notifyAdminNew(creator_id, gmail, whatsapp) {
  MailApp.sendEmail(ADMIN_EMAIL,
    `[Rhode Hub] Nova creator — ${creator_id}`,
    `Handle: ${creator_id}\nGmail: ${gmail}\nWhatsApp: ${whatsapp}\nhttps://docs.google.com/spreadsheets/d/${SPREADSHEET_ID}`
  );
}
