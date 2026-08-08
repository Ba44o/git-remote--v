/* Extrai TODOS os pares rótulo→valor visíveis da tela de live commerce do Seller Center.
   Roda dentro da aba logada do Chrome (via AppleScript) — read-only, não clica em nada.
   Serve pra montar o dicionário da extensão DashLive a partir do DOM real, em vez de
   deduzir por screenshot. Devolve JSON como string. */
(() => {
  const norm = t => String(t == null ? "" : t)
    .normalize("NFD").replace(/[̀-ͯ]/g, "")
    .toLowerCase().replace(/[.…:%()$>]/g, " ").replace(/\s+/g, " ").trim();

  const visivel = el => {
    if (!el || !el.getBoundingClientRect) return false;
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) return false;
    const st = getComputedStyle(el);
    return st.visibility !== "hidden" && st.display !== "none" && +st.opacity > 0.05;
  };

  // mesma heurística da extensão: o valor é irmão do rótulo, de preferência o de baixo
  const valorPerto = rot => {
    const tr = norm(rot.textContent);
    let node = rot;
    for (let up = 0; up < 3 && node; up++) {
      const cont = node.parentElement;
      if (!cont || cont === document.body) break;
      const irmaos = Array.from(cont.children).filter(x => x !== node && visivel(x));
      const pos = x => (node.compareDocumentPosition(x) & Node.DOCUMENT_POSITION_FOLLOWING) ? 0 : 1;
      irmaos.sort((a, b) => pos(a) - pos(b));
      for (const c of irmaos) {
        const t = (c.textContent || "").trim();
        if (!t || t.length > 28 || !/\d/.test(t)) continue;
        if (norm(t) === tr) continue;
        return t;
      }
      node = cont;
    }
    return null;
  };

  const dentroDeTabela = el => !!el.closest("table, [role='table'], [role='grid'], thead, tbody");

  const out = [];
  const vistos = new Set();
  const cands = Array.from(document.querySelectorAll("body *"))
    .filter(el => el.children.length <= 3 && visivel(el))
    .map(el => { const r = el.getBoundingClientRect(); return { el, top: Math.round(r.top + scrollY), left: Math.round(r.left) }; })
    .sort((a, b) => a.top - b.top || a.left - b.left);

  for (const { el, top, left } of cands) {
    const rot = (el.textContent || "").trim();
    if (!rot || rot.length > 60 || /^[\d\-+]/.test(rot)) continue;
    const val = valorPerto(el);
    if (!val) continue;
    const chave = rot + "||" + val;
    if (vistos.has(chave)) continue;
    vistos.add(chave);
    out.push({ rotulo: rot, valor: val, top, left, tabela: dentroDeTabela(el) });
    if (out.length >= 250) break;
  }

  return JSON.stringify({
    url: location.href,
    titulo: document.title,
    capturado_em: new Date().toISOString(),
    total: out.length,
    pares: out,
  });
})();
