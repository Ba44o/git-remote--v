// Rhode Jeans — Detector de marcos de tier
// Roda diariamente, soma GMV por afiliada, detecta cruzamento de threshold
// (Bronze 20k, Silver 50k, Gold 80k, Diamond 150k, Black 500k) e notifica
// o operador via WhatsApp. UPSERT em tier_milestones evita duplicação.

const SB_URL = 'https://ivzpykuluxcxefhyzfsf.supabase.co';
const SB_SVC = process.env.SUPABASE_SERVICE_KEY;

const ZAPI_INSTANCE = process.env.ZAPI_INSTANCE;
const ZAPI_TOKEN    = process.env.ZAPI_TOKEN;
const CLIENT_TOKEN  = process.env.ZAPI_CLIENT_TOKEN;
const ZAPI = `https://api.z-api.io/instances/${ZAPI_INSTANCE}/token/${ZAPI_TOKEN}`;

const OPERATOR_PHONE = '5511952759126';

const SB_H = {
  'apikey':        SB_SVC,
  'Authorization': `Bearer ${SB_SVC}`,
  'Content-Type':  'application/json',
};

const TIERS = [
  { key: 'bronze',  name: 'Bronze',  min: 20000,  badge: '🥉' },
  { key: 'silver',  name: 'Silver',  min: 50000,  badge: '🥈' },
  { key: 'gold',    name: 'Gold',    min: 80000,  badge: '🥇' },
  { key: 'diamond', name: 'Diamond', min: 150000, badge: '💎' },
  { key: 'black',   name: 'Black',   min: 500000, badge: '⬛' },
];

const delay = ms => new Promise(r => setTimeout(r, ms));

async function zapiSend(phone, message) {
  const r = await fetch(`${ZAPI}/send-text`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/json', 'Client-Token': CLIENT_TOKEN },
    body:    JSON.stringify({ phone, message }),
  });
  return r.ok;
}

function buildMessage(nome, handle, tier, gmv) {
  const Rk = v => 'R$ ' + (+v).toLocaleString('pt-BR', { maximumFractionDigits: 0 });
  const action = tier.key === 'bronze'
    ? `✅ *Ação:* benefícios digitais Bronze já liberados automaticamente. Sem ação manual.`
    : `📦 *Ação:* enviar placa física *${tier.name}*. Atualize \`tier_milestones.placa_status='shipped'\` quando despachar.`;

  return `🏅 *Novo marco de tier — ${tier.badge} ${tier.name}*\n\n*${nome}* (@${handle}) acabou de bater o tier *${tier.name}*.\n\n• GMV acumulado: ${Rk(gmv)}\n• Marco mínimo: ${Rk(tier.min)}\n\n${action}`;
}

export default async function handler(req, res) {
  if (!['GET','POST'].includes(req.method)) {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // 1. Soma GMV por afiliada a partir de performance_periods
  const perfRes = await fetch(
    `${SB_URL}/rest/v1/performance_periods?select=affiliate_id,gmv_liquido`,
    { headers: SB_H }
  );
  if (!perfRes.ok) {
    return res.status(500).json({ error: 'failed to fetch performance_periods' });
  }
  const periods = await perfRes.json();

  const gmvByAff = {};
  for (const p of periods || []) {
    const id = (p.affiliate_id || '').toUpperCase();
    if (!id) continue;
    gmvByAff[id] = (gmvByAff[id] || 0) + (+p.gmv_liquido || 0);
  }

  // 2. Para cada afiliada × tier cruzado: UPSERT (UNIQUE garante que não duplica)
  let inserted = 0;
  for (const [affId, totalGmv] of Object.entries(gmvByAff)) {
    for (const t of TIERS) {
      if (totalGmv < t.min) continue;
      const upRes = await fetch(`${SB_URL}/rest/v1/tier_milestones`, {
        method:  'POST',
        headers: { ...SB_H, 'Prefer': 'resolution=ignore-duplicates,return=minimal' },
        body:    JSON.stringify({
          affiliate_id:     affId,
          tier:             t.key,
          gmv_at_milestone: totalGmv,
        }),
      });
      // Status 201 = criado de fato; 200/204 = já existia (ignorado)
      if (upRes.status === 201) inserted++;
    }
  }

  // 3. Lê milestones ainda não notificados (cobre tanto novos quanto retries de falha)
  const pendingRes = await fetch(
    `${SB_URL}/rest/v1/tier_milestones?notified_at=is.null&select=id,affiliate_id,tier,gmv_at_milestone`,
    { headers: SB_H }
  );
  const pending = await pendingRes.json();

  if (!Array.isArray(pending) || pending.length === 0) {
    return res.status(200).json({ ok: true, inserted, pending: 0, notified: 0 });
  }

  // 4. Notifica operador para cada pendente; só marca notified_at após sucesso
  let notified = 0, errors = 0;
  for (const m of pending) {
    try {
      const tier = TIERS.find(t => t.key === m.tier);
      if (!tier) continue;

      const affRes = await fetch(
        `${SB_URL}/rest/v1/affiliates?affiliate_id=ilike.${encodeURIComponent(m.affiliate_id)}&select=affiliate_id,tiktok_handle,nome,name&limit=1`,
        { headers: SB_H }
      );
      const aff = (await affRes.json())[0] || {};
      const handle = (aff.tiktok_handle || aff.affiliate_id || m.affiliate_id || '').replace(/^[@.]+/, '');
      const nome = (aff.nome || aff.name || handle || 'Creator').split(' ')[0];

      const msg = buildMessage(nome, handle, tier, +m.gmv_at_milestone);
      const ok = await zapiSend(OPERATOR_PHONE, msg);

      if (ok) {
        await fetch(`${SB_URL}/rest/v1/tier_milestones?id=eq.${m.id}`, {
          method:  'PATCH',
          headers: { ...SB_H, 'Prefer': 'return=minimal' },
          body:    JSON.stringify({ notified_at: new Date().toISOString() }),
        });
        notified++;
        console.log(`[milestone] ✓ @${handle} → ${tier.name}`);
      } else {
        errors++;
        console.error(`[milestone] ✗ zapi falhou para ${m.affiliate_id} ${m.tier}`);
      }

      await delay(1000);
    } catch (e) {
      errors++;
      console.error(`[milestone] erro ${m.affiliate_id} ${m.tier}: ${e.message}`);
    }
  }

  return res.status(200).json({
    ok:       true,
    inserted,
    pending:  pending.length,
    notified,
    errors,
  });
}
