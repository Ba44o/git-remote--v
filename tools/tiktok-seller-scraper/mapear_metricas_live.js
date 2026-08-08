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
        const t = textoVis(c).trim();
        if (!t || t.length > 28 || !/\d/.test(t)) continue;
        if (norm(t) === tr) continue;
        return t;
      }
      node = cont;
    }
    return null;
  };

  const dentroDeTabela = el => !!el.closest("table, [role='table'], [role='grid'], thead, tbody");

  // contador animado: dígito novo em absolute por cima do antigo em static
  // Contador animado do TikTok: cada dígito é uma coluna com o valor ANTIGO em
  // position:static e o NOVO por cima em position:absolute. textContent junta os
  // dois — o card mostrando 71 entrega "8781" (8→7 e 8→1).
  //
  // Percorre childNodes, não children: o número vem partido entre texto solto e
  // elementos ("14" + text ".48" + <span>K</span>), e olhar só os elementos come
  // o ".48". E o absoluto só substitui quando COBRE um estático na mesma coluna;
  // sem isso, os decimais (que não têm nada por cima) eram descartados.
  const textoVis = function(no, prof){
    prof = prof || 0;
    if (!no) return "";
    if (no.nodeType === 3) return no.nodeValue || "";        // texto solto
    if (no.nodeType !== 1) return "";
    if (prof > 8) return no.textContent || "";
    const filhos = Array.from(no.childNodes);
    if (!filhos.length) return no.textContent || "";

    let info;
    try {
      info = filhos.map(n => n.nodeType === 1
        ? { n, r:n.getBoundingClientRect(), pos:getComputedStyle(n).position }
        : { n, r:null, pos:"texto" });
    } catch(e){ return no.textContent || ""; }

    const abs = info.filter(x => x.pos === "absolute" && x.r && x.r.width > 0);
    if (!abs.length) return filhos.map(n => textoVis(n, prof+1)).join("");

    const out = [], usados = new Set();
    for (const x of info){
      if (x.pos === "absolute") continue;
      if (x.r){
        const cobre = abs.find(a => !usados.has(a.n) && Math.abs(a.r.left - x.r.left) <= 2);
        if (cobre){ usados.add(cobre.n); out.push(textoVis(cobre.n, prof+1)); continue; }
      }
      out.push(textoVis(x.n, prof+1));
    }
    for (const a of abs) if (!usados.has(a.n)) out.push(textoVis(a.n, prof+1));
    return out.join("");
  };
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
