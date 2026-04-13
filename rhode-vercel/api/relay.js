const SB_URL = 'https://ivzpykuluxcxefhyzfsf.supabase.co';
const SB_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2enB5a3VsdXhjeGVmaHl6ZnNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU3Mzc5MzYsImV4cCI6MjA5MTMxMzkzNn0.4_ZShB2t3yCg8ag7-LPWvzHXVrTmj0N4iKWp_tEZb9g';
const SB_SERVICE = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2enB5a3VsdXhjeGVmaHl6ZnNmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTczNzkzNiwiZXhwIjoyMDkxMzEzOTM2fQ.qlHnvGOnGSMwniuS_YYKQaQa-gD_F5asDQTIT2B42hk';
const TYPEBOT_ID = 'rhode-miss-o-extra-ulvrj9s';
// ─── TROCAR AQUI quando mudar de número ──────────────────────────────────────
const ZAPI_INSTANCE  = '3F173410FA03D317C69AAAE399BC1248';
const ZAPI_TOKEN     = '23F1D0021AF2CC2A39C7AFE3';
const CLIENT_TOKEN   = 'F92b6dc75c19f490188eea81fcc29b6aaS';
// ─────────────────────────────────────────────────────────────────────────────
const ZAPI = `https://api.z-api.io/instances/${ZAPI_INSTANCE}/token/${ZAPI_TOKEN}`;
const HUB_URL = 'https://creators.rhodejeans.com.br/hub.html';
const TRIGGER = 'MISSAO';
const WAITING_VIDEO  = 'WAITING_VIDEO';           // aguardando vídeo (sem lembrete)
const WAITING_REMINDED = 'WAITING_VIDEO_REMINDED'; // aguardando vídeo (lembrete já enviado)

const SB_H = { 'apikey': SB_KEY, 'Authorization': `Bearer ${SB_KEY}`, 'Content-Type': 'application/json' };
const SB_SH = { 'apikey': SB_SERVICE, 'Authorization': `Bearer ${SB_SERVICE}`, 'Content-Type': 'application/json' };

function generateToken() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let t = '';
  for (let i = 0; i < 24; i++) t += chars[Math.floor(Math.random() * chars.length)];
  return t;
}

function normalizePhone(phone) {
  const digits = (phone || '').replace(/\D/g, '');
  if (digits.startsWith('55')) return digits;
  return '55' + digits;
}

async function sbPatch(path, body) {
  await fetch(`${SB_URL}/rest/v1/${path}`, {
    method: 'PATCH',
    headers: { ...SB_SH, 'Prefer': 'return=minimal' },
    body: JSON.stringify(body)
  });
}

async function sbGet(path) {
  const r = await fetch(`${SB_URL}/rest/v1/${path}`, { headers: SB_H });
  return r.ok ? r.json() : [];
}
async function sbPost(path, body, prefer = '') {
  const h = { ...SB_H, ...(prefer ? { 'Prefer': prefer } : {}) };
  await fetch(`${SB_URL}/rest/v1/${path}`, { method: 'POST', headers: h, body: JSON.stringify(body) });
}
async function sbDelete(path) {
  await fetch(`${SB_URL}/rest/v1/${path}`, { method: 'DELETE', headers: SB_H });
}

async function getSession(phone) {
  const rows = await sbGet(`bot_sessions?phone=eq.${encodeURIComponent(phone)}&limit=1`);
  return rows[0]?.session_id || null;
}
async function saveSession(phone, sessionId) {
  await sbPost('bot_sessions', { phone, session_id: sessionId }, 'resolution=merge-duplicates');
}
async function clearSession(phone) {
  await sbDelete(`bot_sessions?phone=eq.${encodeURIComponent(phone)}`);
}

async function markMissaoIniciada(phone) {
  const digits = normalizePhone(phone).replace(/^55/, '');
  await sbPatch(
    `eventos_creators?whatsapp=ilike.%25${digits}%25`,
    { missao_iniciada: true }
  );
}

async function saveVideoUrl(phone, videoUrl) {
  const digits = normalizePhone(phone).replace(/^55/, '');
  await sbPatch(
    `eventos_creators?whatsapp=ilike.%25${digits}%25`,
    { video_url: videoUrl, missao_extra: true }
  );
}

async function getOrCreateHubToken(phone) {
  const digits = normalizePhone(phone).replace(/^55/, '');
  const rows = await fetch(
    `${SB_URL}/rest/v1/eventos_creators?whatsapp=ilike.%25${digits}%25&limit=1`,
    { headers: SB_H }
  ).then(r => r.json());

  if (!rows?.length) return null;
  const row = rows[0];

  if (row.access_token) {
    await sbPatch(`eventos_creators?id=eq.${row.id}`, { hub_sent: true });
    return row.access_token;
  }

  const token = generateToken();
  await sbPatch(`eventos_creators?id=eq.${row.id}`, { access_token: token, hub_sent: true });
  return token;
}

async function typebotStart(phone) {
  const r = await fetch(`https://typebot.io/api/v1/typebots/${TYPEBOT_ID}/startChat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ isPreview: false, prefilledVariables: { Phone: phone } })
  });
  return r.json();
}
async function typebotContinue(sessionId, message) {
  const r = await fetch(`https://typebot.io/api/v1/sessions/${sessionId}/continueChat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  return r.json();
}

function parseMessages(data) {
  if (!data?.messages) return [];
  return data.messages
    .filter(m => m.type === 'text')
    .map(m => {
      const rich = m.content?.richText;
      if (!rich) return '';
      return rich
        .map(block => (block.children || []).map(c => c.text || '').join(''))
        .filter(Boolean)
        .join('\n');
    })
    .filter(Boolean);
}

async function zapiSend(phone, message) {
  const r = await fetch(`${ZAPI}/send-text`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Client-Token': CLIENT_TOKEN },
    body: JSON.stringify({ phone, message })
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data?.error) {
    console.error(`[zapi] falha ao enviar para ${phone.slice(-4)}****: ${JSON.stringify(data)}`);
    throw new Error(`zapi_send_failed: ${data?.error || r.status}`);
  }
  return data;
}

function delay(ms) {
  return new Promise(r => setTimeout(r, ms));
}

// Extrai URL de mídia do webhook Z-API (vários formatos possíveis)
function extractVideoUrl(body) {
  return body?.video?.url
    || body?.video?.videoUrl
    || body?.video?.mediaUrl
    || body?.image?.url
    || body?.image?.imageUrl
    || body?.document?.url
    || body?.audio?.url
    || body?.media?.url
    || body?.mediaUrl
    || null;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(200).json({ ok: true });

  const body = req.body;

  // Ignora mensagens enviadas por nós
  if (body?.fromMe) return res.status(200).json({ ok: true });

  // Aceita ReceivedCallback (texto) e callbacks de mídia do Z-API
  const validTypes = ['ReceivedCallback', 'VideoCallback', 'ImageCallback', 'DocumentCallback', 'AudioCallback'];
  if (!validTypes.includes(body?.type)) {
    return res.status(200).json({ ok: true });
  }

  const phone = normalizePhone(body?.phone);
  const message = (body?.text?.message || '').trim();
  const videoUrl = extractVideoUrl(body);

  if (!phone) return res.status(200).json({ ok: true });

  try {
    const sessionId = await getSession(phone);

    // ── Modo espera de vídeo ──────────────────────────────────────────
    if (sessionId === WAITING_VIDEO || sessionId === WAITING_REMINDED) {
      if (!videoUrl) {
        // Mandou texto em vez de vídeo — lembra ela
        await zapiSend(phone, 'Manda o vídeo aqui mesmo, direto nessa conversa. 🎬');
        return res.status(200).json({ ok: true });
      }

      // Vídeo recebido — salva, encerra, envia hub
      await saveVideoUrl(phone, videoUrl);
      await clearSession(phone);

      await zapiSend(phone, 'Missão registrada! ✅\n\nSeu conteúdo foi recebido e já está no nosso radar. Obrigada por fazer parte da Rhode. 🤍');
      await delay(1200);

      const token = await getOrCreateHubToken(phone);
      if (token) {
        await zapiSend(phone, `Aqui está seu painel exclusivo Rhode:\n${HUB_URL}?token=${token}\n\n_Suas métricas de vendas aparecem em até 2 dias após o evento._`);
      }

      return res.status(200).json({ ok: true });
    }

    // ── Fluxo Typebot ─────────────────────────────────────────────────
    if (!message) return res.status(200).json({ ok: true });

    let data;

    if (!sessionId) {
      // Só inicia se for a palavra-chave
      if (message.toUpperCase() !== TRIGGER) return res.status(200).json({ ok: true });

      data = await typebotStart(phone);
      if (!data?.sessionId) return res.status(200).json({ ok: true });

      await saveSession(phone, data.sessionId);
      await markMissaoIniciada(phone);
    } else {
      data = await typebotContinue(sessionId, message);
    }

    // Envia mensagens do Typebot via Z-API
    const msgs = parseMessages(data);
    for (const msg of msgs) {
      await zapiSend(phone, msg);
      await delay(800);
    }

    // Typebot encerrou — entra em modo espera de vídeo
    if (!data?.input) {
      await saveSession(phone, WAITING_VIDEO); // substitui session_id pelo estado especial
    }

  } catch (e) {
    console.error('relay error:', e.message);
  }

  return res.status(200).json({ ok: true });
}
