const SB_URL = 'https://ivzpykuluxcxefhyzfsf.supabase.co';
const SB_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2enB5a3VsdXhjeGVmaHl6ZnNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3Mzc5MzYsImV4cCI6MjA5MTMxMzkzNn0.4_ZShB2t3yCg8ag7-LPWvzHXVrTmj0N4iKWp_tEZb9g';
const SB_SERVICE = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2enB5a3VsdXhjeGVmaHl6ZnNmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTczNzkzNiwiZXhwIjoyMDkxMzEzOTM2fQ.qlHnvGOnGSMwniuS_YYKQaQa-gD_F5asDQTIT2B42hk';
const ZAPI    = 'https://api.z-api.io/instances/3F173410FA03D317C69AAAE399BC1248/token/23F1D0021AF2CC2A39C7AFE3';
const CLIENT_TOKEN = 'F92b6dc75c19f490188eea81fcc29b6aaS';
const HUB_URL = 'https://creators.rhodejeans.com.br/hub.html';

const SBH  = { 'apikey': SB_KEY,     'Authorization': `Bearer ${SB_KEY}`,     'Content-Type': 'application/json' };
const SBSH = { 'apikey': SB_SERVICE, 'Authorization': `Bearer ${SB_SERVICE}`, 'Content-Type': 'application/json' };

function normalizePhone(phone) {
  const digits = (phone || '').replace(/\D/g, '');
  if (digits.startsWith('55')) return digits;
  return '55' + digits;
}

function generateToken() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let t = '';
  for (let i = 0; i < 24; i++) t += chars[Math.floor(Math.random() * chars.length)];
  return t;
}

async function sbGet(path) {
  const r = await fetch(`${SB_URL}/rest/v1/${path}`, { headers: SBH });
  return r.ok ? r.json() : [];
}

async function sbPatch(path, body) {
  await fetch(`${SB_URL}/rest/v1/${path}`, {
    method: 'PATCH',
    headers: { ...SBSH, 'Prefer': 'return=minimal' },
    body: JSON.stringify(body)
  });
}

async function zapiSend(phone, message) {
  await fetch(`${ZAPI}/send-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Client-Token': CLIENT_TOKEN },
    body: JSON.stringify({ phone, message })
  });
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { handle, whatsapp } = req.body || {};
  if (!handle || !whatsapp) {
    return res.status(400).json({ error: 'Informe seu @ do TikTok e WhatsApp.' });
  }

  const cleanHandle = handle.trim().replace(/^[@.]+/, '').toLowerCase();
  const phone = normalizePhone(whatsapp);
  const digits = phone.replace(/^55/, '');

  // ── 1. Busca em affiliates (handle + whatsapp)
  let found = null;
  let table = null;

  const affRows = await sbGet(
    `affiliates?or=(affiliate_id.ilike.${encodeURIComponent(cleanHandle)},tiktok_handle.ilike.${encodeURIComponent(cleanHandle)})&limit=10`
  );

  if (affRows?.length) {
    // Valida que o WhatsApp bate
    found = affRows.find(r => {
      const w = (r.whatsapp || r.phone || '').replace(/\D/g, '');
      return w.includes(digits) || digits.includes(w.slice(-8));
    });
    if (found) table = 'affiliates';
  }

  // ── 2. Se não achou em affiliates, busca em eventos_creators
  if (!found) {
    const evRows = await sbGet(
      `eventos_creators?handle=ilike.${encodeURIComponent(cleanHandle)}&limit=10`
    );
    if (evRows?.length) {
      found = evRows.find(r => {
        const w = (r.whatsapp || '').replace(/\D/g, '');
        return w.includes(digits) || digits.includes(w.slice(-8));
      });
      if (found) table = 'eventos_creators';
    }
  }

  if (!found) {
    return res.status(404).json({
      error: 'Não encontramos esse @ com esse WhatsApp na nossa base. Verifique os dados ou faça o cadastro.'
    });
  }

  // ── 3. Recupera ou gera token
  let token = found.access_token;
  if (!token) {
    token = generateToken();
    await sbPatch(`${table}?id=eq.${found.id}`, { access_token: token });
  }

  // ── 4. Envia link via WhatsApp
  const nome = (found.nome || found.name || cleanHandle).split(' ')[0];
  const link = `${HUB_URL}?token=${token}`;

  await zapiSend(phone,
    `Olá, ${nome}! 🤍\n\nAqui está seu link de acesso ao *Creator Hub Rhode Jeans*:\n${link}\n\n_Este link é exclusivo para você. Não compartilhe._`
  );

  return res.status(200).json({ ok: true });
}
