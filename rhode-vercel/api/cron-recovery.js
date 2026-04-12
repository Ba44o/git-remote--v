const SB_URL = 'https://ivzpykuluxcxefhyzfsf.supabase.co';
const SB_SERVICE = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2enB5a3VsdXhjeGVmaHl6ZnNmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTczNzkzNiwiZXhwIjoyMDkxMzEzOTM2fQ.qlHnvGOnGSMwniuS_YYKQaQa-gD_F5asDQTIT2B42hk';
const ZAPI = 'https://api.z-api.io/instances/3F173410FA03D317C69AAAE399BC1248/token/23F1D0021AF2CC2A39C7AFE3';
const CLIENT_TOKEN = 'F92b6dc75c19f490188eea81fcc29b6aaS';
const SB_SH = { 'apikey': SB_SERVICE, 'Authorization': `Bearer ${SB_SERVICE}`, 'Content-Type': 'application/json' };

const RECOVERY_MSG = `Oi! 🤍 Sua Missão Secreta Rhode ainda está aberta.\n\nSó falta postar o vídeo no TikTok ou Reels e mandar o link aqui. Seu registro fica guardado e você faz parte da nossa seleção de conteúdos.\n\nManda o link quando publicar! 🎬`;

function normalizePhone(phone) {
  const digits = (phone || '').replace(/\D/g, '');
  if (digits.startsWith('55')) return digits;
  return '55' + digits;
}

async function zapiSend(phone, message) {
  try {
    await fetch(`${ZAPI}/send-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Client-Token': CLIENT_TOKEN },
      body: JSON.stringify({ phone, message })
    });
  } catch (e) {
    console.error(`zapiSend error for ${phone}:`, e.message);
  }
}

async function delay(ms) {
  return new Promise(r => setTimeout(r, ms));
}

export default async function handler(req, res) {
  // Verifica autorização do cron (Vercel envia automaticamente)
  const authHeader = req.headers.authorization;
  const cronSecret = process.env.CRON_SECRET;
  if (cronSecret && authHeader !== `Bearer ${cronSecret}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    // Busca creators que iniciaram a missão mas ainda não mandaram o vídeo
    const r = await fetch(
      `${SB_URL}/rest/v1/eventos_creators?missao_iniciada=eq.true&video_url=is.null&select=whatsapp,nome`,
      { headers: SB_SH }
    );
    const pending = r.ok ? await r.json() : [];

    console.log(`cron-recovery: ${pending.length} creators pendentes`);

    let sent = 0;
    for (const creator of pending) {
      if (!creator.whatsapp) continue;
      const phone = normalizePhone(creator.whatsapp);
      await zapiSend(phone, RECOVERY_MSG);
      sent++;
      await delay(1200); // respeita rate limit do Z-API
    }

    return res.status(200).json({ ok: true, sent, total: pending.length });
  } catch (e) {
    console.error('cron-recovery error:', e.message);
    return res.status(500).json({ error: e.message });
  }
}
