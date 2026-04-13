// Rhode Jeans — Lembrete automático para WAITING_VIDEO
// Segurança: muda estado WAITING_VIDEO → WAITING_VIDEO_REMINDED após envio.
// Nunca envia duas vezes para a mesma pessoa na mesma sessão.

const SB_URL  = 'https://ivzpykuluxcxefhyzfsf.supabase.co';
const SB_SVC  = process.env.SUPABASE_SERVICE_KEY || '';
const ZAPI    = 'https://api.z-api.io/instances/3F173410FA03D317C69AAAE399BC1248/token/23F1D0021AF2CC2A39C7AFE3';
const CLIENT_TOKEN = 'F92b6dc75c19f490188eea81fcc29b6aaS';

const WAITING_VIDEO  = 'WAITING_VIDEO';
const REMINDED       = 'WAITING_VIDEO_REMINDED';

const SB_H = {
  'apikey':        SB_SVC,
  'Authorization': `Bearer ${SB_SVC}`,
  'Content-Type':  'application/json',
};

function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

async function zapiSend(phone, message) {
  const r = await fetch(`${ZAPI}/send-text`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json', 'Client-Token': CLIENT_TOKEN },
    body:    JSON.stringify({ phone, message }),
  });
  return r.ok;
}

async function markReminded(phone) {
  await fetch(`${SB_URL}/rest/v1/bot_sessions?phone=eq.${encodeURIComponent(phone)}`, {
    method:  'PATCH',
    headers: { ...SB_H, 'Prefer': 'return=minimal' },
    body:    JSON.stringify({ session_id: REMINDED }),
  });
}

async function getCreatorName(phone) {
  // Tenta buscar nome amigável em eventos_creators
  const digits = phone.replace(/^55/, '');
  const r = await fetch(
    `${SB_URL}/rest/v1/eventos_creators?whatsapp=ilike.%25${digits}%25&select=nome&limit=1`,
    { headers: SB_H }
  );
  const rows = await r.json();
  const nome = rows?.[0]?.nome;
  return nome ? nome.split(' ')[0] : null;
}

export default async function handler(req, res) {
  // Permite disparo manual (POST) e automático (GET via cron Vercel)
  if (!['GET', 'POST'].includes(req.method)) {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  if (!SB_SVC) {
    return res.status(500).json({ error: 'SUPABASE_SERVICE_KEY não configurada' });
  }

  // 1. Busca apenas WAITING_VIDEO (não REMINDED — evita duplo disparo)
  const sbRes = await fetch(
    `${SB_URL}/rest/v1/bot_sessions?session_id=eq.${WAITING_VIDEO}`,
    { headers: SB_H }
  );
  const sessions = await sbRes.json();

  if (!Array.isArray(sessions) || sessions.length === 0) {
    console.log('[reminder] Nenhuma sessão WAITING_VIDEO encontrada.');
    return res.status(200).json({ ok: true, sent: 0, skipped: 0 });
  }

  let sent = 0, errors = 0;

  for (const session of sessions) {
    const phone = session.phone;
    if (!phone) continue;

    try {
      // 2. Busca nome da creator para personalizar (opcional — não bloqueia se falhar)
      const nome = await getCreatorName(phone).catch(() => null);
      const saudacao = nome ? `Oi, ${nome}! 🤍` : 'Oi! 🤍';

      const msg = `${saudacao}\n\nVocê tá na reta final da *Missão Extra Rhode* — é só mandar seu vídeo aqui nessa conversa pra garantir sua surpresa! 🎬\n\n_Qualquer dúvida, é só responder aqui._`;

      // 3. Envia lembrete
      const ok = await zapiSend(phone, msg);

      if (ok) {
        // 4. SOMENTE após envio confirmado, muda estado → nunca fica em estado inconsistente
        await markReminded(phone);
        sent++;
        console.log(`[reminder] ✓ ${phone.slice(-4)}****`);
      } else {
        errors++;
        console.error(`[reminder] ✗ falha zapi para ${phone.slice(-4)}****`);
      }

      // Pausa entre envios para não flood no Z-API
      await delay(1200);

    } catch (e) {
      errors++;
      console.error(`[reminder] erro ${phone.slice(-4)}****: ${e.message}`);
    }
  }

  console.log(`[reminder] Concluído: ${sent} enviados, ${errors} erros de ${sessions.length} sessões`);
  return res.status(200).json({
    ok:      true,
    total:   sessions.length,
    sent,
    errors,
  });
}
