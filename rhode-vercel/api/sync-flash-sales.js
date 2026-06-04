/**
 * Rhode — Sync Flash Sales (Google Sheets → Supabase)
 * POST /api/sync-flash-sales
 * Header: x-admin-pass: <senha>
 *
 * Lê a planilha pública via CSV export, normaliza handle/datas e faz upsert
 * em flash_sales com origem='sheets'. Idempotente — chave natural é
 * (source_handle, inicio_at).
 */

const SHEET_ID = '1rsHo0APVX8TuE6ox9fp_gMoMxa5_ulr-l0PTrEnwCd4';
const SHEET_GID = '802325876';
const SHEET_CSV_URL = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/export?format=csv&gid=${SHEET_GID}`;

const SB_URL = 'https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1';
const SB_SVC_KEY = process.env.SUPABASE_SERVICE_KEY;
const ADMIN_PASS = 'rhode2026';

const SB_HEADERS = {
  apikey: SB_SVC_KEY,
  Authorization: `Bearer ${SB_SVC_KEY}`,
  'Content-Type': 'application/json',
  Prefer: 'resolution=merge-duplicates,return=minimal',
};

// "@tacianetorress N5" → handle limpo "TACIANETORRESS"
function normalizeHandle(raw) {
  if (!raw) return null;
  let h = raw.trim();
  h = h.replace(/^@+/, '');           // tira @ inicial
  h = h.replace(/\s+[Nn]\d+\s*$/, '');// tira sufixo " N1", " n2", etc
  return h.toUpperCase().trim();
}

// "03/05/2026 15:03" → "2026-05-03T15:03:00-03:00" (Brasília UTC-3)
function parseBrDate(raw) {
  if (!raw) return null;
  const m = raw.trim().match(/^(\d{2})\/(\d{2})\/(\d{4})\s+(\d{1,2}):(\d{2})$/);
  if (!m) return null;
  const [, dd, mm, yyyy, hh, min] = m;
  // -03:00 = horário de Brasília (sem horário de verão)
  return `${yyyy}-${mm}-${dd}T${hh.padStart(2,'0')}:${min}:00-03:00`;
}

// CSV parser simples (lida com aspas básicas)
function parseCsv(text) {
  const lines = text.split(/\r?\n/).filter(l => l.trim());
  const rows = [];
  for (const line of lines) {
    const cols = [];
    let cur = '', inQ = false;
    for (let i = 0; i < line.length; i++) {
      const c = line[i];
      if (c === '"' && line[i+1] === '"') { cur += '"'; i++; continue; }
      if (c === '"') { inQ = !inQ; continue; }
      if (c === ',' && !inQ) { cols.push(cur); cur = ''; continue; }
      cur += c;
    }
    cols.push(cur);
    rows.push(cols.map(c => c.trim()));
  }
  return rows;
}

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type,x-admin-pass');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST')    return res.status(405).json({ error: 'Method not allowed' });

  const pass = req.headers['x-admin-pass'] || (req.body && req.body.admin_pass);
  if (pass !== ADMIN_PASS) return res.status(401).json({ error: 'Unauthorized' });

  const t0 = Date.now();
  try {
    const r = await fetch(SHEET_CSV_URL, { redirect: 'follow' });
    if (!r.ok) return res.status(502).json({ error: `Sheet ${r.status}` });
    const csv = await r.text();
    const rows = parseCsv(csv);
    if (rows.length < 2) return res.status(502).json({ error: 'Planilha vazia' });

    const header = rows[0];
    // Detecta colunas (case-insensitive, tolera variações)
    const idxHandle = header.findIndex(h => /usu[aá]rio|handle|creator/i.test(h));
    const idxIni    = header.findIndex(h => /in[ií]cio/i.test(h));
    const idxFim    = header.findIndex(h => /t[eé]rmino|fim/i.test(h));
    const idxStatus = header.findIndex(h => /coluna 1|status/i.test(h));

    if (idxHandle < 0 || idxIni < 0 || idxFim < 0) {
      return res.status(502).json({ error: 'Cabeçalho da planilha não reconhecido', header });
    }

    const upserts = [];
    const erros = [];

    for (let i = 1; i < rows.length; i++) {
      const row = rows[i];
      const rawHandle = row[idxHandle] || '';
      const rawIni    = row[idxIni] || '';
      const rawFim    = row[idxFim] || '';
      const rawStatus = (idxStatus >= 0 ? row[idxStatus] : '') || '';

      if (!rawHandle.trim() || !rawIni.trim() || !rawFim.trim()) continue;

      const handleLimpo = normalizeHandle(rawHandle);
      const inicioAt    = parseBrDate(rawIni);
      const fimAt       = parseBrDate(rawFim);

      if (!handleLimpo || !inicioAt || !fimAt) {
        erros.push({ row: i + 1, raw: { rawHandle, rawIni, rawFim }, motivo: 'parsing' });
        continue;
      }

      const ativo = !/encerrada/i.test(rawStatus); // "Em andamento" ou vazio = ativo

      upserts.push({
        sku: null,
        inicio_at: inicioAt,
        fim_at: fimAt,
        tier_minimo: 'Iniciante',          // sem restrição de tier — flash é específica desta creator
        creators_convidadas: [handleLimpo],
        briefing: null,
        ativo,
        origem: 'sheets',
        source_handle: rawHandle.trim(),    // preserva " N5" pra dedup
      });
    }

    // DELETE-then-INSERT: limpa as flashes da planilha antes de inserir as novas.
    // Isso preserva flashes manuais (origem='manual') intocadas.
    let sucesso = 0;
    let falhas = 0;
    const upsertErros = [];
    if (upserts.length) {
      // 1. Apaga sheets antigas
      const rDel = await fetch(`${SB_URL}/flash_sales?origem=eq.sheets`, {
        method: 'DELETE',
        headers: { ...SB_HEADERS, Prefer: 'return=minimal' },
      });
      if (!rDel.ok && rDel.status !== 404) {
        upsertErros.push(`DELETE: ${rDel.status} ${(await rDel.text()).slice(0, 200)}`);
      }
      // 2. Insere novas em batch
      const r2 = await fetch(`${SB_URL}/flash_sales`, {
        method: 'POST',
        headers: SB_HEADERS,
        body: JSON.stringify(upserts),
      });
      if (r2.ok) {
        sucesso = upserts.length;
      } else {
        falhas = upserts.length;
        upsertErros.push(`INSERT: ${r2.status} ${(await r2.text()).slice(0, 250)}`);
      }
    }

    return res.status(200).json({
      ok: true,
      linhas_planilha: rows.length - 1,
      processadas: upserts.length,
      sincronizadas: sucesso,
      falhas_upsert: falhas,
      erros_parsing: erros.length,
      erros_detalhe: [...upsertErros, ...erros.slice(0, 5)],
      duracao_ms: Date.now() - t0,
    });
  } catch (e) {
    return res.status(500).json({ error: e.message, duracao_ms: Date.now() - t0 });
  }
}
