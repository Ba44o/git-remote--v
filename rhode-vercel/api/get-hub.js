const SB_URL = 'https://ivzpykuluxcxefhyzfsf.supabase.co';
const SB_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2enB5a3VsdXhjeGVmaHl6ZnNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3Mzc5MzYsImV4cCI6MjA5MTMxMzkzNn0.4_ZShB2t3yCg8ag7-LPWvzHXVrTmj0N4iKWp_tEZb9g';
const SB_SVC = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2enB5a3VsdXhjeGVmaHl6ZnNmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTczNzkzNiwiZXhwIjoyMDkxMzEzOTM2fQ.qlHnvGOnGSMwniuS_YYKQaQa-gD_F5asDQTIT2B42hk';

const SBH  = { 'apikey': SB_KEY,  'Authorization': `Bearer ${SB_KEY}`,  'Content-Type': 'application/json' };
const SBSH = { 'apikey': SB_SVC,  'Authorization': `Bearer ${SB_SVC}`,  'Content-Type': 'application/json' };

function normalizePhone(phone) {
  const digits = (phone || '').replace(/\D/g, '');
  return digits.startsWith('55') ? digits : '55' + digits;
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

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { handle, whatsapp, pin, new_pin } = req.body || {};
  if (!handle) return res.status(400).json({ error: 'Informe seu @ do TikTok.' });

  const cleanHandle = handle.trim().replace(/^[@.]+/, '').toLowerCase();

  // 1. Busca em eventos_creators
  let rows = await sbGet(
    `eventos_creators?handle=ilike.${encodeURIComponent(cleanHandle)}&select=id,handle,whatsapp,pin_acesso,access_token&limit=5`
  );
  let table = 'eventos_creators';

  // 2. Fallback: busca em affiliates
  if (!rows?.length) {
    const affRows = await sbGet(
      `affiliates?or=(affiliate_id.ilike.${encodeURIComponent(cleanHandle)},tiktok_handle.ilike.${encodeURIComponent(cleanHandle)})&select=affiliate_id,tiktok_handle,phone,pin_acesso,access_token&limit=5`
    );
    table = 'affiliates';
    // Normaliza para o mesmo formato interno
    rows = (affRows || []).map(r => ({
      ...r,
      id:       r.affiliate_id,   // chave primária em affiliates é affiliate_id
      whatsapp: r.phone || '',
      handle:   r.tiktok_handle || r.affiliate_id,
      _pk:      'affiliate_id',
    }));
  }

  if (!rows?.length) {
    return res.status(404).json({ error: 'Handle não encontrado na nossa base. Verifique seu @ ou fale com a Rhode.' });
  }

  const creator = { ...rows[0], _table: table };
  // pkClause: qual coluna usar no WHERE do PATCH
  const pkClause = creator._pk
    ? `${creator._pk}=eq.${creator.id}`
    : `id=eq.${creator.id}`;

  // ── MODO 1: Creator já tem PIN → valida e entra ──────────────────────────
  if (creator.pin_acesso) {
    if (!pin) return res.status(200).json({ step: 'enter_pin' });

    if (pin.trim() !== creator.pin_acesso) {
      // Delay anti brute-force: torna ataque automatizado 100x mais lento
      await new Promise(r => setTimeout(r, 1000));
      return res.status(401).json({ error: 'Código incorreto. Tente novamente.' });
    }

    // PIN correto → retorna token
    let token = creator.access_token;
    if (!token) {
      token = generateToken();
      await sbPatch(`${creator._table}?${pkClause}`, { access_token: token });
    }
    return res.status(200).json({ token });
  }

  // ── MODO 2: Primeiro acesso → verifica WhatsApp e cria PIN ───────────────
  if (!whatsapp) return res.status(200).json({ step: 'first_access' });

  // Valida WhatsApp
  const phone   = normalizePhone(whatsapp);
  const digits  = phone.replace(/^55/, '');
  const storedW = (creator.whatsapp || '').replace(/\D/g, '');

  if (storedW && !storedW.includes(digits) && !digits.includes(storedW.slice(-8))) {
    return res.status(401).json({ error: 'WhatsApp não confere com o cadastro. Verifique o número.' });
  }

  // Sem phone cadastrado → registra agora (auto-cadastro para afiliadas sem número na base)
  if (!storedW) {
    await sbPatch(`${creator._table}?${pkClause}`, { phone: phone, whatsapp: phone });
  }

  if (!new_pin) return res.status(200).json({ step: 'create_pin' });

  // Valida PIN: 4-6 dígitos
  if (!/^\d{4,6}$/.test(new_pin.trim())) {
    return res.status(400).json({ error: 'O código deve ter entre 4 e 6 números.' });
  }

  // Salva PIN e retorna token
  let token = creator.access_token || generateToken();
  await sbPatch(`${creator._table}?${pkClause}`, {
    pin_acesso:   new_pin.trim(),
    access_token: token
  });

  return res.status(200).json({ token });
}
