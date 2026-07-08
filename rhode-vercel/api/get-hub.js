// ════════════════════════════════════════════════════════════════════════════
//  /api/get-hub — backend único do Hub das creators (auth + data proxy).
//
//  Dois modos no mesmo endpoint (limite de 12 functions no plano Hobby):
//   • LOGIN  — body sem `action`: { handle, whatsapp, pin, new_pin } → fluxo de
//     PIN/WhatsApp que devolve o access_token (usado por acesso.html).
//   • DATA   — body com `action`: { token, action, ... } → leitura/escrita
//     escopada à creator dona do token (usado por hub.html e bem-vinda.html).
//
//  PORQUÊ: a service_role key fica SÓ aqui no servidor. Frontend nunca fala com
//  PostgREST direto pra dado sensível. Toda ação resolve a identidade pelo
//  access_token; nenhuma confia em creator_id vindo do cliente. Depois que o
//  frontend migrar, liga-se RLS deny-anon nas tabelas sensíveis (item 8 / Inc. 3).
// ════════════════════════════════════════════════════════════════════════════

const SB_URL = process.env.SUPABASE_URL || 'https://ivzpykuluxcxefhyzfsf.supabase.co';
// service_role: vem SÓ do env do Vercel (nunca commitada, nunca vai pro cliente).
const SB_SVC = process.env.SUPABASE_SERVICE_KEY;

const SBSH = { 'apikey': SB_SVC, 'Authorization': `Bearer ${SB_SVC}`, 'Content-Type': 'application/json' };

// Todas as leituras/escritas server-side usam a service key (bypassa RLS — por
// isso o login continua funcionando depois que RLS deny-anon for ligado).
async function sbGet(path) {
  const r = await fetch(`${SB_URL}/rest/v1/${path}`, { headers: SBSH });
  return r.ok ? r.json() : [];
}
async function sbWrite(method, path, body, prefer = 'return=minimal') {
  return fetch(`${SB_URL}/rest/v1/${path}`, {
    method, headers: { ...SBSH, 'Prefer': prefer }, body: JSON.stringify(body),
  });
}
async function sbPatch(path, body) { await sbWrite('PATCH', path, body); }

const norm = h => (h || '').toString().replace(/^[@.]+/, '').toLowerCase();
const enc  = encodeURIComponent;

// Aliases de creator p/ o Extrato: handle de login → canônico onde o dado vive.
// Mesmo mapa do coletor (coletar_extrato.py). Taci tem 3 @ = 1 pessoa.
const EXTRATO_ALIASES = {
  tacianecreator: 'tacianetorress',
  tacirecomenda:  'tacianetorress',
  natmarquesss:   'natmarquesvi',
};

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

// ════════════ DATA MODE ════════════════════════════════════════════════════
function stripSecrets(row) {
  const { pin_acesso, access_token, ...safe } = row || {};
  return safe;
}
async function resolveToken(token) {
  if (!token) return null;
  let rows = await sbGet(`affiliates?access_token=eq.${enc(token)}&limit=1`);
  if (rows?.length) {
    return { source: 'affiliates', row: stripSecrets(rows[0]),
             handle: norm(rows[0].tiktok_handle || rows[0].affiliate_id) };
  }
  rows = await sbGet(`eventos_creators?access_token=eq.${enc(token)}&limit=1`);
  if (rows?.length) {
    return { source: 'eventos', row: stripSecrets(rows[0]), handle: norm(rows[0].handle) };
  }
  return null;
}
function affIdOf(creator) {
  const r = creator.row || {};
  return (r.affiliate_id || r.tiktok_handle || creator.handle || '').toString().toUpperCase();
}

// ════════════ ADMIN MODE ════════════════════════════════════════════════════
// Login: verifica a senha (env, nunca no client) e devolve o ADMIN_TOKEN — um
// segredo de servidor. Só quem tem a senha consegue o token; o token é o que
// libera as queries. Mesmo que alguém finja o flag de sessão no admin.html, sem
// o token toda query falha (401).
async function handleAdminLogin(body, res) {
  const pass = (body.pass || '').toString();
  if (!process.env.ADMIN_PASS || pass !== process.env.ADMIN_PASS) {
    await new Promise(r => setTimeout(r, 1000)); // anti brute-force
    return res.status(401).json({ error: 'Senha incorreta.' });
  }
  return res.json({ token: process.env.ADMIN_TOKEN });
}

// Passthrough PostgREST autenticado pelo ADMIN_TOKEN. Admin é papel all-access
// (lê/escreve tudo legitimamente) — a service key fica no servidor; o acesso
// exige o token (obtido só via senha). Bloqueia path com barra inicial/.. .
async function handleAdminQuery(body, res) {
  if (!process.env.ADMIN_TOKEN || body.adminToken !== process.env.ADMIN_TOKEN) {
    return res.status(401).json({ error: 'não autorizado' });
  }
  const method = (body.method || 'GET').toUpperCase();
  const path = (body.path || '').toString();
  if (!/^[a-zA-Z]/.test(path) || path.includes('..')) {
    return res.status(400).json({ error: 'path inválido' });
  }
  // Modo paginado: o servidor faz o loop de offset (co-localizado com o Supabase,
  // rápido) e devolve TUDO numa resposta só — evita N round-trips do cliente.
  if (body.paged && method === 'GET') {
    const all = []; let offset = 0; const PS = 1000;
    const sep = path.includes('?') ? '&' : '?';
    while (true) {
      const rr = await fetch(`${SB_URL}/rest/v1/${path}${sep}limit=${PS}&offset=${offset}`, { headers: SBSH });
      if (!rr.ok) return res.status(rr.status).json({ error: (await rr.text()).slice(0, 300) });
      const batch = await rr.json();
      if (Array.isArray(batch)) all.push(...batch);
      if (!Array.isArray(batch) || batch.length < PS) break;
      offset += PS;
      if (offset > 200000) break; // safeguard
    }
    return res.json({ ok: true, status: 200, data: all });
  }

  const opts = { method, headers: { ...SBSH } };
  if (body.prefer) opts.headers['Prefer'] = body.prefer;
  if (method !== 'GET' && method !== 'HEAD' && body.body !== undefined) {
    opts.body = JSON.stringify(body.body);
  }
  const r = await fetch(`${SB_URL}/rest/v1/${path}`, opts);
  const text = await r.text();
  if (!r.ok) return res.status(r.status).json({ error: text.slice(0, 300) });
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch (_) { data = text; }
  return res.json({ ok: true, status: r.status, data });
}

// ════════════ BIO_UPLOAD (imagem de fundo do bio via admin) ═════════════════
// Recebe base64 data-URL, valida (image/*, <3MB), upload no bucket 'bio-assets'
// via service_role, devolve URL pública. Bucket definido em bio_customization_v2.sql
async function handleBioUpload(body, res) {
  if (!process.env.ADMIN_TOKEN || body.adminToken !== process.env.ADMIN_TOKEN) {
    return res.status(401).json({ error: 'não autorizado' });
  }
  const b64 = (body.dataUrl || '').toString();
  const m = b64.match(/^data:(image\/(png|jpe?g|webp|gif));base64,(.+)$/i);
  if (!m) return res.status(400).json({ error: 'formato inválido — só PNG/JPG/WEBP/GIF em data-URL' });
  const mime = m[1].toLowerCase();
  const ext = m[2].toLowerCase() === 'jpeg' ? 'jpg' : m[2].toLowerCase();
  const data = Buffer.from(m[3], 'base64');
  if (data.length > 3 * 1024 * 1024) {
    return res.status(413).json({ error: 'imagem > 3MB — comprima antes' });
  }
  const filename = `bg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.${ext}`;
  const path = `bg/${filename}`;
  const r = await fetch(`${SB_URL}/storage/v1/object/bio-assets/${path}`, {
    method: 'POST',
    headers: {
      apikey: SB_SVC,
      Authorization: `Bearer ${SB_SVC}`,
      'Content-Type': mime,
      'x-upsert': 'true',
    },
    body: data,
  });
  if (!r.ok) return res.status(r.status).json({ error: (await r.text()).slice(0, 300) });
  return res.json({
    ok: true,
    url: `${SB_URL}/storage/v1/object/public/bio-assets/${path}`,
    path,
  });
}

// ════════════ CADASTRO (signup público) ═════════════════════════════════════
// Insert/upsert de novo cadastro em eventos_creators com a service key, pra essa
// tabela poder ficar 100% deny-anon. É público (form de cadastro) — mesmo nível
// de exposição do insert anônimo de antes, mas sem expor a tabela pra leitura.
async function handleCadastro(body, res) {
  const nome = (body.nome || '').toString().trim();
  const handleRaw = (body.handle || '').toString().trim();
  const whatsapp = (body.whatsapp || '').toString().trim();
  if (!nome || !handleRaw) return res.status(400).json({ error: 'nome e @ obrigatórios' });
  const handle = handleRaw.replace(/^@/, '').toUpperCase(); // = normalizeHandle do cadastro.html
  const token = generateToken();
  const r = await sbWrite('POST', 'eventos_creators',
    { handle, nome, whatsapp, evento: 'Evento_13_04', access_token: token },
    'resolution=merge-duplicates,return=representation');
  if (!r.ok) return res.status(500).json({ error: (await r.text()).slice(0, 200) });
  let rows = []; try { rows = await r.json(); } catch (_) {}
  return res.json({ token: (rows[0] && rows[0].access_token) || token });
}

// ════════════ DASH-LIVE (dashboard público de lives) ════════════════════════
// lives/store_daily são métricas agregadas da loja (sem credencial/PII). Público
// como antes — só sai do anon key direto pro proxy, pra essas 2 tabelas poderem
// ficar deny-anon também (anon key vira inútil pra leitura de qualquer tabela).
async function handleDashlive(body, res) {
  if (body.which === 'lives')
    return res.json(await sbGet('lives?select=*&order=started_at.asc&limit=2000'));
  if (body.which === 'store_daily')
    return res.json(await sbGet('store_daily?select=date,month,gmv_bruto,reembolsos&order=date.asc&limit=2000'));
  if (body.which === 'live_produto')
    return res.json(await sbGet('live_produto?select=*&order=gmv.desc&limit=300'));
  if (body.which === 'tracker')
    return res.json(await sbGet('tracker_canais?select=*&order=mes.desc&limit=200'));
  return res.status(400).json({ error: 'which inválido' });
}

async function handleData(body, res) {
  const { token, action } = body;
  const creator = await resolveToken(token);
  if (!creator) return res.status(401).json({ error: 'token inválido' });

  const affId  = affIdOf(creator);
  const handle = creator.handle;
  const p = body;

  try {
    switch (action) {
      case 'bootstrap':
        return res.json({ source: creator.source, row: creator.row, handle });

      case 'perf':
        return res.json(await sbGet(
          `performance_periods?affiliate_id=ilike.${enc(affId)}&order=periodo.desc&limit=24`));

      case 'leaderboard': {
        if (!p.periodo) return res.json({ ranking: [], total: 0 });
        const rows = await sbGet(
          `performance_periods?periodo=eq.${enc(p.periodo)}&select=affiliate_id,gmv_liquido&order=gmv_liquido.desc&limit=500`);
        const active = (rows || []).filter(r => (+r.gmv_liquido || 0) > 0).map(r => r.affiliate_id);
        return res.json({ ranking: active, total: active.length });
      }

      case 'flash': {
        // Flash sales ATIVAS DESTA creator — SÓ a flash dedicada do @handle dela.
        // Nunca flashes da loja/"Geral" (regra: o time sobe flash dedicada por handle).
        // Fonte: Promotion API (coletar_flash_sales.py). Janela begin/end em epoch.
        const eh = EXTRATO_ALIASES[handle] || handle;
        const now = Math.floor(Date.now() / 1000);
        return res.json(await sbGet(
          `flash_sales?creator=eq.${enc(eh)}&end_ts=gt.${now}&begin_ts=lte.${now}&order=end_ts.asc`));
      }

      case 'tarefas': {
        const cutoff = p.cutoff || '';
        const amostras = await sbGet(
          `amostras_enviadas?creator_id=eq.${enc(affId)}&or=(video_url.is.null,data_envio.gte.${enc(cutoff)})&order=data_envio.desc&limit=20`);
        const [produtos, campanhas] = await Promise.all([
          sbGet(`produtos?select=sku,nome`),
          sbGet(`campanhas?select=*`),
        ]);
        return res.json({ amostras, produtos, campanhas });
      }

      case 'notifs':
        return res.json(await sbGet(
          `notificacoes?select=id,tipo,titulo,corpo,link,lida,created_at&creator_id=eq.${enc(affId)}&order=lida.asc,created_at.desc&limit=30`));

      case 'novidades': {
        const skus = Array.isArray(p.skus) ? p.skus : [];
        const inList = skus.map(s => enc(s)).join(',');
        const produtos = inList
          ? await sbGet(`produtos?select=sku,nome,preco_venda,foto_url,categoria,colecao,created_at&ativo=eq.true&sku=in.(${inList})`)
          : [];
        const pend = await sbGet(
          `amostras_enviadas?select=sku&creator_id=eq.${enc(affId)}&aprovada=eq.false&dispensada=not.eq.true&origem=eq.solicitacao_creator`);
        return res.json({ produtos, solicitadas: (pend || []).map(x => x.sku) });
      }

      case 'profile':
        return res.json(await sbGet(`creator_profiles?affiliate_id=eq.${enc(handle)}&limit=1`));

      case 'scripts':
        return res.json(await sbGet(
          `scripts_gerados?affiliate_id=eq.${enc(handle)}&order=created_at.desc&limit=30`));

      // ── Central de Comissões / Meu Extrato (só o dado da própria creator) ──
      // Resolve aliases de handle p/ o canônico (ex: Taci loga com qualquer um
      // dos 3 @ e cai no extrato consolidado). Mesmo mapa do coletor.
      case 'extrato_resumo': {
        const eh = EXTRATO_ALIASES[handle] || handle;
        return res.json(await sbGet(`extrato_resumo?creator=eq.${enc(eh)}&order=periodo.desc`));
      }

      case 'extrato_pedidos': {
        const eh = EXTRATO_ALIASES[handle] || handle;
        const per = p.periodo ? `&periodo=eq.${enc(p.periodo)}` : '';
        return res.json(await sbGet(
          `extrato_pedidos?creator=eq.${enc(eh)}${per}&order=data.desc&limit=2000`));
      }

      // ── Produtos campeões da creator (top SKU por GMV) ────────────────────
      case 'top_produtos': {
        const eh = EXTRATO_ALIASES[handle] || handle;
        // pagina todos os pedidos da creator (server-side) e agrega por produto
        const all = []; let off = 0;
        while (true) {
          const batch = await sbGet(
            `extrato_pedidos?creator=eq.${enc(eh)}&select=product_id,produto,gmv,comissao_estimada,comissao_paga,status,reembolso,order_id&limit=1000&offset=${off}`);
          if (!Array.isArray(batch) || !batch.length) break;
          all.push(...batch);
          if (batch.length < 1000) break;
          off += 1000; if (off > 30000) break;
        }
        const m = {};
        for (const x of all) {
          if (x.reembolso) continue;                       // exclui reembolsado
          const k = x.product_id || x.produto || '?';
          const d = m[k] || (m[k] = { produto: x.produto || x.product_id, product_id: x.product_id,
                                      gmv: 0, comissao: 0, orders: new Set() });
          d.gmv += (+x.gmv || 0);
          d.comissao += (x.status === 'liquidado' ? (+x.comissao_paga || 0) : (+x.comissao_estimada || 0));
          if (x.order_id) d.orders.add(x.order_id);
        }
        const top = Object.values(m)
          .map(d => ({ produto: d.produto, product_id: d.product_id,
                       gmv: Math.round(d.gmv * 100) / 100, comissao: Math.round(d.comissao * 100) / 100,
                       pedidos: d.orders.size }))
          .sort((a, b) => b.gmv - a.gmv).slice(0, Math.min(+p.limit || 6, 20));
        return res.json(top);
      }

      // ════ ESCRITAS — escopadas à creator dona do token ════
      case 'confirmar_tarefa': {
        const ids = (p.ids || []).map(Number).filter(Boolean);
        if (!ids.length) return res.status(400).json({ error: 'sem ids' });
        await sbPatch(`amostras_enviadas?id=in.(${ids.join(',')})&creator_id=eq.${enc(affId)}`,
          { confirmada_em: new Date().toISOString() });
        return res.json({ ok: true });
      }

      case 'anexar_video': {
        const ids = (p.ids || []).map(Number).filter(Boolean);
        if (!ids.length || !p.url) return res.status(400).json({ error: 'sem ids/url' });
        const now = new Date().toISOString();
        await sbPatch(`amostras_enviadas?id=in.(${ids.join(',')})&creator_id=eq.${enc(affId)}`,
          { video_url: p.url, video_postado_em: now, confirmada_em: now });
        return res.json({ ok: true });
      }

      case 'pedir_amostra': {
        if (!p.sku) return res.status(400).json({ error: 'sem sku' });
        const r = await sbWrite('POST', `amostras_enviadas`, {
          creator_id: affId, sku: p.sku, quantidade: 1, origem: 'solicitacao_creator',
          aprovada: false, solicitada_em: new Date().toISOString(),
          tier_no_envio: (creator.row?.current_tier || '').toString(),
        });
        if (!r.ok) return res.status(500).json({ error: (await r.text()).slice(0, 200) });
        return res.json({ ok: true });
      }

      case 'marcar_notif': {
        if (!p.id) return res.status(400).json({ error: 'sem id' });
        await sbPatch(`notificacoes?id=eq.${enc(p.id)}&creator_id=eq.${enc(affId)}`,
          { lida: true, read_at: new Date().toISOString() });
        return res.json({ ok: true });
      }

      case 'marcar_todas_notif': {
        await sbPatch(`notificacoes?creator_id=eq.${enc(affId)}&lida=eq.false`,
          { lida: true, read_at: new Date().toISOString() });
        return res.json({ ok: true });
      }

      case 'salvar_profile': {
        const f = p.fields || {};
        await sbWrite('POST', `creator_profiles`, {
          affiliate_id: handle, nome: f.nome || '', altura: f.altura || '', peso: f.peso || '',
          quadril: f.quadril || '', tamanho: f.tamanho || '', updated_at: new Date().toISOString(),
        }, 'resolution=merge-duplicates');
        return res.json({ ok: true });
      }

      case 'salvar_script': {
        const d = p.data || {};
        await sbWrite('POST', `scripts_gerados`, {
          affiliate_id: handle, produto: p.produto || '', formato: p.formato || '',
          titulo: d.titulo || '', hooks: d.hooks || [], script: d.script || '',
          ctas: d.ctas || [], hashtags: d.hashtags || [], notas_direcao: d.notas_direcao || [],
          status: 'pendente',
        });
        return res.json({ ok: true });
      }

      case 'script_converteu': {
        if (!p.id) return res.status(400).json({ error: 'sem id' });
        await sbPatch(`scripts_gerados?id=eq.${enc(p.id)}&affiliate_id=eq.${enc(handle)}`,
          { converteu: !!p.novo });
        return res.json({ ok: true });
      }

      // bem-vinda.html: resumo da creator por token (triagem)
      case 'triagem_lookup': {
        const r = creator.row || {};
        if (creator.source === 'affiliates') {
          const since = new Date(Date.now() - 60 * 864e5).toISOString().slice(0, 7); // YYYY-MM
          const ps = await sbGet(
            `performance_periods?affiliate_id=ilike.${enc(affId)}&periodo=gte.${enc(since)}&select=gmv_liquido`);
          const gmv60d = (ps || []).reduce((s, x) => s + (+x.gmv_liquido || 0), 0);
          return res.json({ kind: 'affiliate', nome: (r.nome || r.name || '@' + handle).split(' ')[0],
                            handle, gmv60d, modelo: r.modelo || null });
        }
        return res.json({ kind: 'evento', nome: (r.nome || r.name || '').split(' ')[0],
                          handle, whatsapp: r.whatsapp || '' });
      }

      default:
        return res.status(400).json({ error: `ação desconhecida: ${action}` });
    }
  } catch (e) {
    return res.status(500).json({ error: e.message });
  }
}

// ════════════ LOGIN MODE ════════════════════════════════════════════════════
// ════════════ VITRINE OPT-IN (WhatsApp opt-in do estado BETWEEN do /live) ═══
const ZAPI_URL = 'https://api.z-api.io/instances/3F173410FA03D317C69AAAE399BC1248/token/23F1D0021AF2CC2A39C7AFE3';
const ZAPI_CLIENT = 'F92b6dc75c19f490188eea81fcc29b6aaS';
const VITRINE_PHONE_RE = /^55(1[1-9]|2[12478]|3[1-578]|4[1-9]|5[13-5]|6[1-9]|7[13-9]|8[1-9]|9[1-9])(9\d{8}|[2-5]\d{7})$/;
function vitrineNormalizePhone(raw) {
  const d = String(raw || '').replace(/\D/g, '');
  if (!d) return null;
  const withCountry = d.startsWith('55') ? d : '55' + d;
  return VITRINE_PHONE_RE.test(withCountry) ? withCountry : null;
}
const _vitrineOptinIpHits = new Map();
function vitrineOptinRateLimit(ip) {
  const now = Date.now();
  const arr = (_vitrineOptinIpHits.get(ip) || []).filter(t => now - t < 10 * 60 * 1000);
  if (arr.length >= 3) return false;
  arr.push(now); _vitrineOptinIpHits.set(ip, arr); return true;
}
async function vitrineHasRecentScan(sessionId, creator) {
  if (!sessionId || !creator) return false;
  try {
    const since = new Date(Date.now() - 10 * 60 * 1000).toISOString();
    const url = `${SB_URL}/rest/v1/hub_eventos?session_id=eq.${enc(sessionId)}&affiliate_id=eq.${enc(creator)}&evento=eq.qr_scanned&created_at=gte.${enc(since)}&select=id&limit=1`;
    const r = await fetch(url, { headers: SBSH });
    if (!r.ok) return false;
    const rows = await r.json();
    return Array.isArray(rows) && rows.length > 0;
  } catch (e) { return false; }
}
async function vitrineZapiSend(phone, message) {
  try {
    const r = await fetch(`${ZAPI_URL}/send-text`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Client-Token': ZAPI_CLIENT },
      body: JSON.stringify({ phone, message }),
    });
    return r.ok;
  } catch (e) { return false; }
}
async function handleVitrineOptin(body, req, res) {
  const ip = (req.headers['x-forwarded-for'] || '').split(',')[0].trim()
          || req.socket?.remoteAddress || 'unknown';
  if (!vitrineOptinRateLimit(ip)) return res.status(429).json({ error: 'rate_limited_ip' });
  const phone = vitrineNormalizePhone(body.phone);
  const creator = String(body.creator || '').toUpperCase().replace(/^[@.]+/, '').replace(/[^A-Z0-9_.-]/g, '').slice(0, 40);
  const sessionId = String(body.session_id || '').slice(0, 60);
  if (!phone || !creator) return res.status(400).json({ error: 'invalid' });
  // prova-de-scan
  const proven = await vitrineHasRecentScan(sessionId, creator);
  if (!proven) return res.status(403).json({ error: 'no_recent_scan' });
  // rate-limit por (phone+creator) — anti-flood
  try {
    const since = new Date(Date.now() - 30 * 60 * 1000).toISOString();
    const url = `${SB_URL}/rest/v1/vitrine_optins?phone=eq.${enc(phone)}&creator_handle=eq.${enc(creator)}&last_confirmation_at=gte.${enc(since)}&select=id&limit=1`;
    const r = await fetch(url, { headers: SBSH });
    if (r.ok) { const rows = await r.json(); if (Array.isArray(rows) && rows.length) return res.status(200).json({ ok: true, skipped: 'rate_limited' }); }
  } catch (e) {}
  // rate-limit cross-creator (mesma pessoa, vários creators em 1h)
  try {
    const since = new Date(Date.now() - 60 * 60 * 1000).toISOString();
    const url = `${SB_URL}/rest/v1/vitrine_optins?phone=eq.${enc(phone)}&last_confirmation_at=gte.${enc(since)}&select=id&limit=1`;
    const r = await fetch(url, { headers: SBSH });
    if (r.ok) { const rows = await r.json(); if (Array.isArray(rows) && rows.length) return res.status(200).json({ ok: true, skipped: 'cross_creator_rate_limited' }); }
  } catch (e) {}
  // lookup próxima live
  let next = null;
  try {
    const url = `${SB_URL}/rest/v1/live_schedule?creator_handle=eq.${enc(creator)}&status=eq.scheduled&scheduled_start=gte.${enc(new Date().toISOString())}&order=scheduled_start.asc&limit=1`;
    const r = await fetch(url, { headers: SBSH });
    if (r.ok) { const rows = await r.json(); next = rows && rows[0] || null; }
  } catch (e) {}
  const handleLower = creator.toLowerCase();
  let whenStr = null;
  if (next) {
    try {
      const fmt = new Intl.DateTimeFormat('pt-BR', { timeZone: 'America/Sao_Paulo', day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
      whenStr = fmt.format(new Date(next.scheduled_start)).replace(',', ' às');
    } catch (e) {}
  }
  const msg = [
    'Oi! Salvamos seu contato 💛',
    '',
    whenStr ? `Te avisamos quando a @${handleLower} entrar ao vivo — próxima prevista: ${whenStr}.`
            : `Te avisamos assim que a @${handleLower} entrar ao vivo.`,
    '',
    'Cupom da vitrine: *VITRINE10* (10% off no TikTok Shop Rhode).',
    '',
    'Pra parar de receber, responda PARAR.',
  ].join('\n');
  const sent = await vitrineZapiSend(phone, msg);
  try {
    await fetch(`${SB_URL}/rest/v1/vitrine_optins?phone=eq.${enc(phone)}&creator_handle=eq.${enc(creator)}`, {
      method: 'PATCH',
      headers: { ...SBSH, 'Prefer': 'return=minimal' },
      body: JSON.stringify({ last_confirmation_at: new Date().toISOString() }),
    });
  } catch (e) {}
  return res.status(200).json({ ok: true, sent });
}

// ════════════ VITRINE TRACK (proxy thin pra sendBeacon do /live) ═══════════
// Aceita eventos qr_scanned / tiktok_redirected / optin_shown / optin_submitted / action
// somente com aba='vitrine'. Hash do IP pra rate-limit sem armazenar PII.
const VITRINE_EVENTOS_OK = new Set(['qr_scanned','tiktok_redirected','optin_shown','optin_submitted','action']);
const _vitrineHits = new Map();
function vitrineRateLimit(ip) {
  const now = Date.now();
  const arr = (_vitrineHits.get(ip) || []).filter(t => now - t < 60000);
  if (arr.length >= 60) return false;
  arr.push(now); _vitrineHits.set(ip, arr); return true;
}
async function handleVitrineTrack(body, req, res) {
  try {
    const ip = (req.headers['x-forwarded-for'] || '').split(',')[0].trim()
            || req.socket?.remoteAddress || 'unknown';
    if (!vitrineRateLimit(ip)) return res.status(204).end();
    const evento = String(body.evento || '').slice(0, 40);
    if (!VITRINE_EVENTOS_OK.has(evento)) return res.status(400).end();
    if (String(body.aba || '') !== 'vitrine') return res.status(400).end();
    const ua = String(req.headers['user-agent'] || '').slice(0, 300);
    const meta = (body.meta && typeof body.meta === 'object') ? body.meta : {};
    if (/bot|crawl|spider|preview|facebookexternalhit|whatsapp|telegram|slack|linkedin/i.test(ua)) meta.is_likely_bot = true;
    const crypto = await import('crypto');
    const ip_hash = crypto.createHash('sha256').update(ip + ':rhode-vitrine-salt').digest('hex').slice(0, 16);
    await fetch(`${SB_URL}/rest/v1/hub_eventos`, {
      method: 'POST',
      headers: { ...SBSH, 'Prefer': 'return=minimal' },
      body: JSON.stringify({
        affiliate_id: String(body.affiliate_id || '').slice(0, 40) || null,
        session_id: String(body.session_id || '').slice(0, 60) || null,
        evento, aba: 'vitrine', meta,
        referrer: String(body.referrer || '').slice(0, 500) || null,
        user_agent: ua,
        ip_hash,
      }),
    });
  } catch (e) {}
  return res.status(204).end();
}

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const body = req.body || {};
  // Modo ADMIN: login + passthrough autenticado (admin.html)
  if (body.action === 'admin_login') return handleAdminLogin(body, res);
  if (body.action === 'admin_query') return handleAdminQuery(body, res);
  if (body.action === 'bio_upload') return handleBioUpload(body, res);
  // Cadastro público (cadastro.html)
  if (body.action === 'cadastro') return handleCadastro(body, res);
  // Dash de lives público (dash-live.html) — dado agregado da loja, sem PII
  if (body.action === 'dashlive') return handleDashlive(body, res);
  // Tracking público da página /live (vitrine QR) — proxy thin pra sendBeacon → hub_eventos
  if (body.action === 'track') return handleVitrineTrack(body, req, res);
  // Opt-in WhatsApp do estado BETWEEN do /live (com Z-API + rate limits)
  if (body.action === 'live_optin') return handleVitrineOptin(body, req, res);
  // Modo DATA: demais `action` resolvem por access_token (hub.html / bem-vinda.html)
  if (body.action) return handleData(body, res);

  // Modo LOGIN: fluxo de PIN/WhatsApp (acesso.html)
  const { handle, whatsapp, pin, new_pin } = body;
  if (!handle) return res.status(400).json({ error: 'Informe seu @ do TikTok.' });

  const cleanHandle = handle.trim().replace(/^[@.]+/, '').toLowerCase();

  // 1. Busca em eventos_creators
  let rows = await sbGet(
    `eventos_creators?handle=ilike.${enc(cleanHandle)}&select=id,handle,whatsapp,pin_acesso,access_token&limit=5`
  );
  let table = 'eventos_creators';

  // 2. Fallback: busca em affiliates
  if (!rows?.length) {
    const affRows = await sbGet(
      `affiliates?or=(affiliate_id.ilike.${enc(cleanHandle)},tiktok_handle.ilike.${enc(cleanHandle)})&select=affiliate_id,tiktok_handle,phone,pin_acesso,access_token&limit=5`
    );
    table = 'affiliates';
    rows = (affRows || []).map(r => ({
      ...r,
      id:       r.affiliate_id,
      whatsapp: r.phone || '',
      handle:   r.tiktok_handle || r.affiliate_id,
      _pk:      'affiliate_id',
    }));
  }

  if (!rows?.length) {
    return res.status(404).json({ error: 'Handle não encontrado na nossa base. Verifique seu @ ou fale com a Rhode.' });
  }

  const creator = { ...rows[0], _table: table };
  const pkClause = creator._pk ? `${creator._pk}=eq.${creator.id}` : `id=eq.${creator.id}`;

  // ── MODO 1: Creator já tem PIN → valida e entra ──
  if (creator.pin_acesso) {
    if (!pin) return res.status(200).json({ step: 'enter_pin' });
    if (pin.trim() !== creator.pin_acesso) {
      await new Promise(r => setTimeout(r, 1000)); // anti brute-force
      return res.status(401).json({ error: 'Código incorreto. Tente novamente.' });
    }
    let token = creator.access_token;
    if (!token) {
      token = generateToken();
      await sbPatch(`${creator._table}?${pkClause}`, { access_token: token });
    }
    return res.status(200).json({ token });
  }

  // ── MODO 2: Primeiro acesso → verifica WhatsApp e cria PIN ──
  if (!whatsapp) return res.status(200).json({ step: 'first_access' });

  const phone   = normalizePhone(whatsapp);
  const digits  = phone.replace(/^55/, '');
  const storedW = (creator.whatsapp || '').replace(/\D/g, '');

  if (storedW && !storedW.includes(digits) && !digits.includes(storedW.slice(-8))) {
    return res.status(401).json({ error: 'WhatsApp não confere com o cadastro. Verifique o número.' });
  }
  if (!storedW) {
    await sbPatch(`${creator._table}?${pkClause}`, { phone: phone, whatsapp: phone });
  }
  if (!new_pin) return res.status(200).json({ step: 'create_pin' });
  if (!/^\d{4,6}$/.test(new_pin.trim())) {
    return res.status(400).json({ error: 'O código deve ter entre 4 e 6 números.' });
  }

  let token = creator.access_token || generateToken();
  await sbPatch(`${creator._table}?${pkClause}`, {
    pin_acesso:   new_pin.trim(),
    access_token: token
  });
  return res.status(200).json({ token });
}
