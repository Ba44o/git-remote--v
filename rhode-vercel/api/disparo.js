/**
 * Rhode — Disparo Segmentado via Z-API
 * POST /api/disparo
 * Header: x-admin-pass
 * Body: { template_id, filtros, dry_run? }
 *
 * Modos:
 *  - dry_run=true → busca alvos, retorna preview da mensagem renderizada
 *                    pra primeiro creator. NÃO dispara nada.
 *  - dry_run=false → dispara via Z-API com pausa de 1.5s entre envios.
 *                     Limite de 30 envios por chamada (timeout Vercel).
 */

const SB_URL     = 'https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1';
const SB_SVC_KEY = process.env.SUPABASE_SERVICE_KEY;
const ADMIN_PASS = process.env.ADMIN_PASS || 'rhode2026';
const ADMIN_TOKEN = process.env.ADMIN_TOKEN;

const ZAPI_URL     = `https://api.z-api.io/instances/${process.env.ZAPI_INSTANCE}/token/${process.env.ZAPI_TOKEN}`;
const ZAPI_CLIENT  = process.env.ZAPI_CLIENT_TOKEN;
const HUB_BASE     = 'https://creators.rhodejeans.com.br/hub.html';

const SB_HEADERS = {
  apikey: SB_SVC_KEY,
  Authorization: `Bearer ${SB_SVC_KEY}`,
  'Content-Type': 'application/json',
};

const TIER_RANK = { Iniciante: 0, Bronze: 1, Silver: 2, Gold: 3, Diamond: 4, Black: 5 };
// Comissão dual (parceria.html): % orgânica + bônus em vendas via ADS.
// Template `{{tier_comissao}}` renderiza ambos pra deixar explícito no WhatsApp.
const TIER_COMM = {
  Iniciante: '—',
  Bronze:    '8% (+3% em ads)',
  Silver:    '9% (+3% em ads)',
  Gold:      '10% (+3% em ads)',
  Diamond:   '12% (+5% em ads)',
  Black:     '12% (+5% em ads)',
};

const SLEEP = (ms) => new Promise((r) => setTimeout(r, ms));

function chunk(arr, n) {
  const out = [];
  for (let i = 0; i < arr.length; i += n) out.push(arr.slice(i, i + n));
  return out;
}

async function sbGetPaged(path) {
  const sep = path.includes('?') ? '&' : '?';
  const out = [];
  let offset = 0;
  while (true) {
    const r = await fetch(`${SB_URL}/${path}${sep}limit=1000&offset=${offset}`, { headers: SB_HEADERS });
    if (!r.ok) break;
    const batch = await r.json();
    if (!batch.length) break;
    out.push(...batch);
    if (batch.length < 1000) break;
    offset += 1000;
    if (offset > 50000) break;
  }
  return out;
}

function normalizePhone(raw) {
  const digits = String(raw || '').replace(/\D/g, '');
  if (!digits) return null;
  return digits.startsWith('55') ? digits : '55' + digits;
}

function calcTier(gmvAcum) {
  if (gmvAcum >= 500000) return 'Black';
  if (gmvAcum >= 150000) return 'Diamond';
  if (gmvAcum >= 80000)  return 'Gold';
  if (gmvAcum >= 50000)  return 'Silver';
  if (gmvAcum >= 20000)  return 'Bronze';
  return 'Iniciante';
}

function fmtR(v) {
  return 'R$ ' + (Number(v) || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function renderTemplate(tpl, vars) {
  return tpl.replace(/\{\{(\w+)\}\}/g, (_, key) => (vars[key] != null ? String(vars[key]) : `{{${key}}}`));
}

async function buscarAlvos(filtros) {
  // Fonte primária de phone: eventos_creators.whatsapp (201 creators registradas).
  // affiliates.phone existe no schema mas está sempre NULL — não usa.
  const evcRows = await sbGetPaged('eventos_creators?select=handle,nome,whatsapp,access_token&whatsapp=not.is.null');
  if (!evcRows.length) return [];

  // Dedup por handle: pega 1 row por handle (a mais recente, eventos_creators tem id serial)
  const byHandle = new Map();
  for (const r of evcRows) {
    const h = String(r.handle || '').toUpperCase().replace(/^[@.]+/, '');
    if (!h) continue;
    if (!byHandle.has(h)) byHandle.set(h, r);
  }

  // Tier/access_token de affiliates por handle
  const handles = Array.from(byHandle.keys());
  let affMap = {};
  if (handles.length) {
    // Busca em chunks pra não estourar URL
    for (const ch of chunk(handles, 100)) {
      const inList = ch.map((h) => `"${h}"`).join(',');
      const aff = await sbGetPaged(`affiliates?select=affiliate_id,nome,access_token&affiliate_id=in.(${inList})`);
      aff.forEach((a) => {
        const id = String(a.affiliate_id || '').toUpperCase().replace(/^[@.]+/, '');
        affMap[id] = a;
      });
    }
  }

  // Acumula GMV de performance_periods por creator
  const periodos = await sbGetPaged('performance_periods?select=affiliate_id,gmv_liquido,refund_pct,periodo&order=periodo.desc');
  const gmvMap = {};
  const refundMap = {};
  const ultimoPeriodo = {};
  periodos.forEach((p) => {
    const id = String(p.affiliate_id || '').toUpperCase().replace(/^[@.]+/, '');
    gmvMap[id] = (gmvMap[id] || 0) + (Number(p.gmv_liquido) || 0);
    if (!ultimoPeriodo[id]) {
      ultimoPeriodo[id] = p.periodo;
      refundMap[id] = Number(p.refund_pct) || 0;
    }
  });

  // Filtros
  const minGmv = Number(filtros.gmv_min) || 0;
  const maxGmv = filtros.gmv_max != null && filtros.gmv_max !== '' ? Number(filtros.gmv_max) : Infinity;
  const tiersAceitos = filtros.tiers && filtros.tiers.length ? new Set(filtros.tiers) : null;
  const refundMinPct = filtros.refund_min != null && filtros.refund_min !== '' ? Number(filtros.refund_min) : null;
  const apenasInativas = !!filtros.apenas_inativas;
  const handlesEspecificos = filtros.handles && filtros.handles.length ? new Set(filtros.handles.map((h) => String(h).toUpperCase().replace(/^[@.]+/, ''))) : null;

  const alvos = [];
  for (const [id, evc] of byHandle) {
    if (handlesEspecificos && !handlesEspecificos.has(id)) continue;

    const gmv = gmvMap[id] || 0;
    const tier = calcTier(gmv);
    const refund = refundMap[id] || 0;
    const aff = affMap[id] || {};

    if (tiersAceitos && !tiersAceitos.has(tier)) continue;
    if (gmv < minGmv) continue;
    if (gmv > maxGmv) continue;
    if (refundMinPct != null && refund < refundMinPct) continue;
    if (apenasInativas && gmv > 0) continue;

    alvos.push({
      affiliate_id: id,
      phone: normalizePhone(evc.whatsapp),
      nome: (evc.nome || aff.nome || id).split(' ')[0],
      tier,
      gmv,
      refund,
      access_token: evc.access_token || aff.access_token,
    });
  }
  return alvos;
}

function buildVars(creator) {
  return {
    nome: creator.nome,
    handle: creator.affiliate_id.toLowerCase(),
    tier: creator.tier,
    tier_comissao: TIER_COMM[creator.tier] || '—',
    gmv_total: fmtR(creator.gmv),
    refund_pct: (creator.refund || 0).toFixed(1) + '%',
    link_hub: creator.access_token ? `${HUB_BASE}?token=${creator.access_token}` : 'creators.rhodejeans.com.br/acesso.html',
  };
}

async function generateTokenIfMissing(creator) {
  if (creator.access_token) return creator.access_token;
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let token = '';
  for (let i = 0; i < 24; i++) token += chars[Math.floor(Math.random() * chars.length)];
  await fetch(`${SB_URL}/affiliates?affiliate_id=eq.${encodeURIComponent(creator.affiliate_id)}`, {
    method: 'PATCH',
    headers: { ...SB_HEADERS, Prefer: 'return=minimal' },
    body: JSON.stringify({ access_token: token }),
  });
  creator.access_token = token;
  return token;
}

async function zapiSend(phone, message) {
  try {
    const r = await fetch(`${ZAPI_URL}/send-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Client-Token': ZAPI_CLIENT },
      body: JSON.stringify({ phone, message }),
    });
    return r.ok;
  } catch (e) {
    return false;
  }
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,x-admin-pass');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST')    return res.status(405).json({ error: 'Method not allowed' });

  const pass = req.headers['x-admin-pass'];
  if (pass !== ADMIN_PASS && (!ADMIN_TOKEN || pass !== ADMIN_TOKEN)) return res.status(401).json({ error: 'Unauthorized' });

  const { template_id, filtros = {}, dry_run = true } = req.body || {};
  if (!template_id) return res.status(400).json({ error: 'template_id obrigatório' });

  const t0 = Date.now();
  try {
    // Carrega template
    const tplR = await fetch(`${SB_URL}/mensagens_templates?id=eq.${template_id}&limit=1`, { headers: SB_HEADERS });
    const tpls = await tplR.json();
    if (!tpls.length) return res.status(404).json({ error: 'Template não encontrado' });
    const tpl = tpls[0];

    // Busca alvos
    const alvos = await buscarAlvos(filtros);
    if (!alvos.length) {
      return res.status(200).json({ ok: true, total_alvos: 0, dry_run, preview: null, msg: 'Nenhum creator atende aos filtros.' });
    }

    // Preview com primeiro creator
    const preview = renderTemplate(tpl.corpo, buildVars(alvos[0]));

    if (dry_run) {
      return res.status(200).json({
        ok: true,
        dry_run: true,
        total_alvos: alvos.length,
        amostra: alvos.slice(0, 3).map((a) => ({ id: a.affiliate_id, tier: a.tier, gmv: a.gmv, phone: a.phone })),
        preview,
        duracao_ms: Date.now() - t0,
      });
    }

    // Rate limit: bloqueia se houve disparo nos últimos 5 min
    const rateR = await fetch(`${SB_URL}/disparos_log?select=created_at&order=created_at.desc&limit=1`, { headers: SB_HEADERS });
    const ult = await rateR.json();
    if (ult.length) {
      const since = Date.now() - new Date(ult[0].created_at).getTime();
      if (since < 5 * 60 * 1000) {
        const wait = Math.ceil((5 * 60 * 1000 - since) / 1000);
        return res.status(429).json({ error: `Rate limit. Aguarde ${wait}s antes do próximo disparo.` });
      }
    }

    // Limite de envios por chamada (timeout Vercel)
    const MAX = 30;
    const PAUSE_MS = 1500;
    const lote = alvos.slice(0, MAX);

    let enviados = 0;
    let falhas = 0;
    for (const c of lote) {
      if (!c.phone) { falhas++; continue; }
      // Garante que tem token (se template precisar de link_hub)
      if (tpl.corpo.includes('{{link_hub}}')) await generateTokenIfMissing(c);
      const msg = renderTemplate(tpl.corpo, buildVars(c));
      const ok = await zapiSend(c.phone, msg);
      if (ok) enviados++; else falhas++;
      if (lote.indexOf(c) < lote.length - 1) await SLEEP(PAUSE_MS);
    }

    // Persiste log
    await fetch(`${SB_URL}/disparos_log`, {
      method: 'POST',
      headers: { ...SB_HEADERS, Prefer: 'return=minimal' },
      body: JSON.stringify({
        template_id,
        filtro_aplicado: filtros,
        total_alvos: alvos.length,
        total_enviados: enviados,
        total_falhas: falhas,
        duracao_ms: Date.now() - t0,
        preview: preview.slice(0, 500),
      }),
    });

    return res.status(200).json({
      ok: true,
      dry_run: false,
      total_alvos: alvos.length,
      processados: lote.length,
      enviados,
      falhas,
      excedente: Math.max(0, alvos.length - MAX),
      duracao_ms: Date.now() - t0,
    });
  } catch (e) {
    return res.status(500).json({ error: e.message, duracao_ms: Date.now() - t0 });
  }
}
