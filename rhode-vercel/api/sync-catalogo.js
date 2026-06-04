/**
 * Rhode — Sync Catálogo (rhodejeans.com.br → Supabase)
 * POST /api/sync-catalogo
 * Header: x-admin-pass: <senha do admin>
 *
 * Lê o sitemap-produto, extrai JSON-LD (schema.org Product) e popula
 * a tabela `produtos` via upsert (on_conflict=sku).
 */

const SITEMAP_URL = 'https://www.rhodejeans.com.br/sitemap-produto.xml';
const SB_URL      = 'https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1';
const SB_SVC_KEY  = process.env.SUPABASE_SERVICE_KEY;
const ADMIN_PASS = process.env.ADMIN_PASS || 'rhode2026';
const ADMIN_TOKEN = process.env.ADMIN_TOKEN;

const HTTP_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (compatible; Rhode-Catalog-Sync/1.0)',
};

const SB_HEADERS = {
  apikey: SB_SVC_KEY,
  Authorization: `Bearer ${SB_SVC_KEY}`,
  'Content-Type': 'application/json',
  Prefer: 'resolution=merge-duplicates,return=minimal',
};

function detectCategory(url) {
  const slug = (url.split('/').pop() || '').toLowerCase();
  if (slug.startsWith('calca')) {
    if (slug.includes('wide-leg')) return 'wide_leg';
    if (slug.includes('mom'))      return 'mom_jeans';
    if (slug.includes('skinny'))   return 'skinny';
    if (slug.includes('reta'))     return 'reta';
    return 'outro';
  }
  if (slug.startsWith('shorts'))  return 'shorts';
  if (slug.startsWith('body'))    return 'body';
  if (slug.startsWith('saia'))    return 'saia';
  if (slug.startsWith('blusa') || slug.startsWith('bata')) return 'bata';
  if (slug.startsWith('vestido')) return 'vestido';
  if (slug.startsWith('top'))     return 'top';
  return 'outro';
}

function decodeEntities(s) {
  if (!s) return s;
  return s
    .replace(/&ccedil;/g, 'ç').replace(/&Ccedil;/g, 'Ç')
    .replace(/&atilde;/g, 'ã').replace(/&Atilde;/g, 'Ã')
    .replace(/&otilde;/g, 'õ').replace(/&Otilde;/g, 'Õ')
    .replace(/&aacute;/g, 'á').replace(/&Aacute;/g, 'Á')
    .replace(/&eacute;/g, 'é').replace(/&Eacute;/g, 'É')
    .replace(/&iacute;/g, 'í').replace(/&Iacute;/g, 'Í')
    .replace(/&oacute;/g, 'ó').replace(/&Oacute;/g, 'Ó')
    .replace(/&uacute;/g, 'ú').replace(/&Uacute;/g, 'Ú')
    .replace(/&acirc;/g, 'â').replace(/&Acirc;/g, 'Â')
    .replace(/&ecirc;/g, 'ê').replace(/&Ecirc;/g, 'Ê')
    .replace(/&ocirc;/g, 'ô').replace(/&Ocirc;/g, 'Ô')
    .replace(/&ntilde;/g, 'ñ')
    .replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&nbsp;/g, ' ');
}

const JSONLD_RE = /<script[^>]*type="application\/ld\+json"[^>]*>([\s\S]*?)<\/script>/gi;

async function extractProduct(url) {
  try {
    const r = await fetch(url, { headers: HTTP_HEADERS, signal: AbortSignal.timeout(15000) });
    if (!r.ok) return null;
    const html = await r.text();

    let product = null;
    let m;
    JSONLD_RE.lastIndex = 0;
    while ((m = JSONLD_RE.exec(html))) {
      let data;
      try { data = JSON.parse(m[1]); } catch { continue; }
      const candidates = [];
      if (Array.isArray(data)) {
        for (const n of data) if (n && n['@type'] === 'Product') candidates.push(n);
      } else if (data && typeof data === 'object') {
        if (data['@type'] === 'Product') candidates.push(data);
        else if (Array.isArray(data['@graph'])) {
          for (const n of data['@graph']) if (n['@type'] === 'Product') candidates.push(n);
        }
      }
      if (candidates.length) { product = candidates[0]; break; }
    }
    if (!product) return null;

    let foto = product.image;
    if (Array.isArray(foto)) foto = foto[0];

    let preco = null;
    const offers = product.offers || {};
    const rawPrice = offers.lowPrice || offers.price;
    if (rawPrice) {
      const n = parseFloat(rawPrice);
      if (!isNaN(n)) preco = n;
    }

    let desc = decodeEntities(product.description || '');
    desc = desc.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 400);

    const sku = (product.sku || product.productID || '').toString().trim();
    const nome = decodeEntities((product.name || '').trim());
    if (!sku || !nome) return null;

    return {
      sku,
      nome,
      categoria: detectCategory(url),
      preco_venda: preco,
      foto_url: foto || null,
      descricao: desc || null,
      ativo: true,
    };
  } catch (e) {
    return null;
  }
}

async function upsertProdutos(produtos) {
  const BATCH = 50;
  let sucesso = 0, falhas = 0;
  const erros = [];
  for (let i = 0; i < produtos.length; i += BATCH) {
    const batch = produtos.slice(i, i + BATCH);
    try {
      const r = await fetch(`${SB_URL}/produtos?on_conflict=sku`, {
        method: 'POST',
        headers: SB_HEADERS,
        body: JSON.stringify(batch),
      });
      if (r.ok) sucesso += batch.length;
      else {
        falhas += batch.length;
        erros.push(`batch ${i}: ${r.status} ${(await r.text()).slice(0, 200)}`);
      }
    } catch (e) {
      falhas += batch.length;
      erros.push(`batch ${i}: ${e.message}`);
    }
  }
  return { sucesso, falhas, erros };
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,x-admin-pass');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST')    return res.status(405).json({ error: 'Method not allowed' });

  // Auth simples
  const pass = req.headers['x-admin-pass'] || (req.body && req.body.admin_pass);
  if (pass !== ADMIN_PASS && (!ADMIN_TOKEN || pass !== ADMIN_TOKEN)) return res.status(401).json({ error: 'Unauthorized' });

  const t0 = Date.now();
  try {
    // 1. Sitemap
    const r = await fetch(SITEMAP_URL, { headers: HTTP_HEADERS });
    if (!r.ok) return res.status(502).json({ error: `Sitemap ${r.status}` });
    const xml = await r.text();
    const urls = Array.from(xml.matchAll(/<loc>([^<]+)<\/loc>/g)).map((m) => m[1]);
    if (!urls.length) return res.status(502).json({ error: 'Sitemap vazio' });

    // 2. Extrai em paralelo (limite 8 simultâneos pra não estourar tempo)
    const CONC = 8;
    const produtos = [];
    let erros = 0;
    for (let i = 0; i < urls.length; i += CONC) {
      const slice = urls.slice(i, i + CONC);
      const results = await Promise.all(slice.map(extractProduct));
      for (const p of results) {
        if (p) produtos.push(p);
        else erros++;
      }
    }

    // 3. Upsert
    const { sucesso, falhas, erros: upsertErros } = await upsertProdutos(produtos);

    // 4. Por categoria (resumo)
    const porCategoria = {};
    for (const p of produtos) {
      porCategoria[p.categoria] = (porCategoria[p.categoria] || 0) + 1;
    }

    return res.status(200).json({
      ok: true,
      total_urls: urls.length,
      extraidos: produtos.length,
      erros_extracao: erros,
      sincronizados: sucesso,
      falhas_upsert: falhas,
      por_categoria: porCategoria,
      duracao_ms: Date.now() - t0,
      erros_detalhe: upsertErros.slice(0, 5),
    });
  } catch (e) {
    return res.status(500).json({ error: e.message, duracao_ms: Date.now() - t0 });
  }
}
