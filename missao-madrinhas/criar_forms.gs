/**
 * Missão das Madrinhas — RhodeLovers
 * Cria os 2 Google Forms (A e B) exatamente conforme a spec, com todos os
 * textos, campos, validações e configurações. No fim, imprime no log:
 *   - URL de edição e URL pública de cada form
 *   - o link ENCURTADO do Form A (pra mensagem de abertura)
 *   - o entry.XXXXXXX do campo "Quem te convidou" (Form B)
 *   - o LINK PRÉ-PREENCHIDO BASE do Form B (só trocar TESTE pelo nome da madrinha)
 *
 * COMO RODAR:
 *   1. Abra https://script.google.com  → Novo projeto
 *   2. Cole este arquivo inteiro (substitui o Code.gs vazio)
 *   3. Edite a config LINK_DO_GRUPO abaixo com o link do grupo WhatsApp
 *   4. Menu ▶ Executar → função "criarMissaoMadrinhas"
 *   5. Autorize (é a sua conta criando os forms) e veja o resultado em
 *      "Execução" / "Registros de execução" (Ver → Logs)
 *
 * ⚠️ O QUE O SCRIPT NÃO FAZ (a API do Forms não permite — fazer manual):
 *   - Cor do tema (Índigo #1B3A5C), fonte "Básica" e o BANNER de cabeçalho.
 *     Abra cada form → paleta 🎨 → set cor + fonte + imagem do banner.
 */

// ===================== CONFIG — EDITE ANTES DE RODAR =====================
var LINK_DO_GRUPO = 'https://chat.whatsapp.com/COLE_AQUI_O_CONVITE'; // grupo WhatsApp RhodeLovers
// ========================================================================

function criarMissaoMadrinhas() {
  var out = [];
  out.push('===== MISSÃO DAS MADRINHAS — FORMS CRIADOS =====');

  // ----------------------------------------------------------------------
  // FORM A — "Quero ser madrinha 💛"
  // ----------------------------------------------------------------------
  var formA = FormApp.create('Quero ser madrinha 💛');
  formA.setTitle('Quero ser madrinha 💛');
  formA.setDescription(
    'A missão do Dia do Amigo: traga amigas pra RhodeLovers até 22/07. ' +
    'Quem trouxer mais, ganha o LOOK EM DOBRO — duas Rhodebox: uma pra você e ' +
    'uma pra quem você escolher (ou as duas pra você, a gente não julga 👀). ' +
    'Preencha aqui e receba o SEU link de convite no WhatsApp. ' +
    'Regras: vale convidada mulher que vem pra ficar de verdade · ' +
    'quem ganhou Rhodebox nos últimos 60 dias dá a vez · empate = sorteio.'
  );

  aplicarConfigsPadrao_(formA);

  formA.addTextItem()
    .setTitle('Seu nome completo')
    .setRequired(true);

  var telA = formA.addTextItem()
    .setTitle('Seu WhatsApp (com DDD)')
    .setRequired(true);
  telA.setValidation(validacaoTelefone_());

  formA.setConfirmationMessage(
    'Prontinho, madrinha! 💛 Em instantes o SEU link de convite chega no seu ' +
    'WhatsApp. Regra de ouro: convida quem realmente curte jeans e vem pra ' +
    'ficar — é assim que a comunidade cresce do jeito certo. Boa missão! 👑'
  );

  var urlAedit = formA.getEditUrl();
  var urlApub = formA.getPublishedUrl();
  var urlAcurto = '';
  try { urlAcurto = formA.shortenFormUrl(urlApub); } catch (e) { urlAcurto = urlApub; }

  // ----------------------------------------------------------------------
  // FORM B — "Bem-vinda à RhodeLovers ✨" (o que a convidada abre)
  // ----------------------------------------------------------------------
  var formB = FormApp.create('Bem-vinda à RhodeLovers ✨');
  formB.setTitle('Bem-vinda à RhodeLovers ✨');
  formB.setDescription(
    'Você foi convidada por uma RhodeLover pra entrar no grupo mais especial ' +
    'da Rhode Jeans — onde tudo acontece primeiro: lançamentos, condições ' +
    'exclusivas, sorteios e bastidores. Preenche aqui embaixo (30 segundos) ' +
    'e o link do grupo aparece na hora.'
  );

  aplicarConfigsPadrao_(formB);

  // >>> Campo 1: é ESTE que o link único pré-preenche <<<
  var quemConvidou = formB.addTextItem()
    .setTitle('Quem te convidou')
    .setHelpText('(preenchido automaticamente pelo seu link de convite)')
    .setRequired(true);

  formB.addTextItem()
    .setTitle('Seu nome completo')
    .setRequired(true);

  var telB = formB.addTextItem()
    .setTitle('Seu WhatsApp (com DDD)')
    .setRequired(true);
  telB.setValidation(validacaoTelefone_());

  formB.addTextItem()
    .setTitle('Seu @ do Instagram ou TikTok')
    .setRequired(false); // opcional

  // A TELA DE CONFIRMAÇÃO É O GATE: o link do grupo só existe aqui.
  formB.setConfirmationMessage(
    'Prontinho! Agora sim: seu lugar na RhodeLovers tá te esperando 💛 ' +
    'Entra por aqui 👉 ' + LINK_DO_GRUPO + ' — te vejo lá dentro!'
  );

  // Gera o LINK PRÉ-PREENCHIDO BASE (equivale a "Gerar link pré-preenchido" no menu ⋮)
  var respostaTeste = formB.createResponse()
    .withItemResponse(quemConvidou.createResponse('TESTE'));
  var linkPreenchido = respostaTeste.toPrefilledUrl();

  // Extrai o entry.XXXXXXX do link
  var entryId = 'entry.(não identificado)';
  var m = linkPreenchido.match(/entry\.\d+/);
  if (m) { entryId = m[0]; }

  var urlBedit = formB.getEditUrl();
  var urlBpub = formB.getPublishedUrl();

  // ----------------------------------------------------------------------
  // RESULTADO
  // ----------------------------------------------------------------------
  out.push('');
  out.push('--- FORM A — Quero ser madrinha 💛 ---');
  out.push('Editar : ' + urlAedit);
  out.push('Público: ' + urlApub);
  out.push('CURTO (usar na mensagem de abertura): ' + urlAcurto);
  out.push('');
  out.push('--- FORM B — Bem-vinda à RhodeLovers ✨ ---');
  out.push('Editar : ' + urlBedit);
  out.push('Público: ' + urlBpub);
  out.push('');
  out.push('>>> entry do campo "Quem te convidou": ' + entryId);
  out.push('>>> LINK PRÉ-PREENCHIDO BASE (troque TESTE pelo nome da madrinha):');
  out.push(linkPreenchido);
  out.push('');
  out.push('PRÓXIMOS PASSOS MANUAIS (a API não faz):');
  out.push('1. Em cada form: 🎨 → cor Índigo #1B3A5C, fonte "Básica", banner 1600×400 (Bianca).');
  out.push('2. Confira que LINK_DO_GRUPO foi preenchido na config (Form B).');
  out.push('3. Cole o link base acima na aba "Gerador de Links" da planilha de controle.');
  out.push('4. Form B → aba Respostas → "Vincular a Planilhas" pra apuração automática.');
  out.push('================================================');

  var texto = out.join('\n');
  Logger.log(texto);
  return texto; // aparece também no retorno da execução
}

/** Configurações comuns aos 2 forms (com try/catch p/ variações de conta). */
function aplicarConfigsPadrao_(form) {
  // NÃO exigir login Google (mata conversão)
  try { form.setRequireLogin(false); } catch (e) {}
  // Não coletar e-mail (reforça o "sem login")
  try { form.setCollectEmail(false); } catch (e) {}
  // Não limitar a 1 resposta (duplicata se resolve na apuração)
  try { form.setLimitOneResponsePerUser(false); } catch (e) {}
  // Desativar "enviar outra resposta" na confirmação
  try { form.setShowLinkToRespondAgain(false); } catch (e) {}
  // Sem edição depois de enviar
  try { form.setAllowResponseEdits(false); } catch (e) {}
}

/** Validação leve de telefone: aceita (11) 99999-9999, 11999999999, etc. */
function validacaoTelefone_() {
  return FormApp.createTextValidation()
    .setHelpText('Digite o número com DDD. Ex: (11) 99999-9999')
    .requireTextMatchesPattern('\\(?\\d{2}\\)?[\\s.\\-]?\\d{4,5}[\\s.\\-]?\\d{4}')
    .build();
}
