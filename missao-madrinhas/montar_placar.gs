/**
 * Missão das Madrinhas — PLACAR + FEED (robusto, sem fórmula).
 *
 * Lê as respostas direto do Form B (form.getResponses) e GRAVA VALORES em duas abas:
 *   • "Placar"     — ranking madrinha × convidadas (pra você olhar na planilha)
 *   • "Feed_Dash"  — Data + Madrinha (sem telefone/nome), fonte do dash visual
 * Sem QUERY/FILTER/referência de aba → nada de #ERROR! nem problema de locale.
 * Instala um gatilho onFormSubmit: a cada nova convidada, atualiza sozinho.
 *
 * RODAR (1x): ▶ Executar → "montarPlacar" → autorizar. Depois é automático.
 */

var FORM_B_ID = '1sMJYSQUjdujdicF0339xIQg-NzZCFd99O7s2xU1kSIQ'; // Form B (id de edição)

function montarPlacar()      { construir_(true);  }   // manual: monta tudo + instala gatilho
function onNovaConvidada()   { construir_(false); }   // gatilho: só atualiza os dados

function construir_(instalarGatilho) {
  var form = FormApp.openById(FORM_B_ID);

  // planilha de respostas (usa a existente ou cria)
  var ss;
  try { ss = SpreadsheetApp.openById(form.getDestinationId()); }
  catch (e) {
    ss = SpreadsheetApp.create('Missão das Madrinhas — Respostas (Form B)');
    form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());
    SpreadsheetApp.flush(); Utilities.sleep(1500);
    ss = SpreadsheetApp.openById(ss.getId());
  }
  var tz = ss.getSpreadsheetTimeZone() || 'America/Sao_Paulo';

  // lê as respostas: [{ts, madrinha}]
  var dados = [];
  form.getResponses().forEach(function (r) {
    var quem = '';
    r.getItemResponses().forEach(function (ir) {
      if (String(ir.getItem().getTitle()).toLowerCase().indexOf('convidou') >= 0)
        quem = String(ir.getResponse()).trim();
    });
    if (quem) dados.push({ ts: r.getTimestamp(), quem: quem });
  });

  montarFeed_(ss, tz, dados);
  montarPlacarTab_(ss, dados);
  if (instalarGatilho) instalarGatilho_(form);

  Logger.log('✅ Placar + Feed_Dash atualizados (' + dados.length + ' registros). ' + ss.getUrl());
  return ss.getUrl();
}

/** Aba Feed_Dash: Data + Madrinha (sem PII) — fonte do dash. */
function montarFeed_(ss, tz, dados) {
  var feed = ss.getSheetByName('Feed_Dash') || ss.insertSheet('Feed_Dash');
  feed.clear();
  var rows = [['Data', 'Madrinha']];
  dados.slice().sort(function (a, b) { return b.ts - a.ts; }).forEach(function (d) {
    rows.push([Utilities.formatDate(d.ts, tz, 'dd/MM/yyyy HH:mm:ss'), d.quem]);
  });
  feed.getRange(1, 1, rows.length, 2).setValues(rows);
  feed.getRange('A1:B1').setFontWeight('bold');
}

/** Aba Placar: ranking madrinha × convidadas (valores + formatação). */
function montarPlacarTab_(ss, dados) {
  var map = {};
  dados.forEach(function (d) { map[d.quem] = (map[d.quem] || 0) + 1; });
  var arr = Object.keys(map).map(function (k) { return [k, map[k]]; })
    .sort(function (a, b) { return b[1] - a[1] || String(a[0]).localeCompare(b[0]); });
  var total = dados.length, ativas = arr.length;

  var pl = ss.getSheetByName('Placar') || ss.insertSheet('Placar', 0);
  pl.clear(); pl.clearConditionalFormatRules();
  ss.setActiveSheet(pl); ss.moveActiveSheet(1);

  pl.getRange('A1').setValue('🏆 PLACAR — Missão das Madrinhas').setFontSize(16).setFontWeight('bold');
  pl.getRange('A2').setValue('Atualiza a cada nova convidada. Válida na apuração (22/07) = registrou E está no grupo no dia.')
    .setFontColor('#666666').setFontSize(9);
  pl.getRange('D1').setValue('Total convidadas').setFontColor('#666666').setFontWeight('bold');
  pl.getRange('D2').setValue(total).setFontSize(20).setFontWeight('bold');
  pl.getRange('F1').setValue('Madrinhas ativas').setFontColor('#666666').setFontWeight('bold');
  pl.getRange('F2').setValue(ativas).setFontSize(20).setFontWeight('bold');

  pl.getRange('A4:B4').setValues([['Madrinha', 'Convidadas']])
    .setFontWeight('bold').setBackground('#1B3A5C').setFontColor('#FFFFFF');
  if (arr.length) pl.getRange(5, 1, arr.length, 2).setValues(arr);

  pl.setColumnWidth(1, 260); pl.setColumnWidth(2, 120);
  pl.setColumnWidth(3, 24); pl.setColumnWidth(4, 130); pl.setColumnWidth(6, 130);
  pl.setFrozenRows(4);
  if (arr.length) {
    var rule = SpreadsheetApp.newConditionalFormatRule()
      .setGradientMinpoint('#FFFFFF').setGradientMaxpoint('#F2D413')
      .setRanges([pl.getRange(5, 2, arr.length, 1)]).build();
    pl.setConditionalFormatRules([rule]);
  }
}

/** Instala o gatilho onFormSubmit uma única vez. */
function instalarGatilho_(form) {
  var jaTem = ScriptApp.getProjectTriggers().some(function (t) {
    return t.getHandlerFunction() === 'onNovaConvidada';
  });
  if (!jaTem) ScriptApp.newTrigger('onNovaConvidada').forForm(form).onFormSubmit().create();
}
