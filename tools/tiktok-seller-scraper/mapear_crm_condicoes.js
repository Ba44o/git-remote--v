(() => {
  // READ-ONLY: extrai a árvore de condições do criador de segmento do CRM lendo as PROPS do
  // React (fiber), sem clicar/abrir menu. Cascaders guardam o catálogo inteiro em options/treeData.
  const out = { url: location.href, arvores: [], chavesVistas: [], amostraTexto: [], erro: null };
  try {
    const fiberKey = (el) => Object.keys(el).find(k => k.startsWith("__reactFiber$") || k.startsWith("__reactInternalInstance$"));
    const propsKey = (el) => Object.keys(el).find(k => k.startsWith("__reactProps$"));

    // heurística: um nó de opção tem label/value/title e um array de filhos
    const ehOpcao = (o) => o && typeof o === "object" && !Array.isArray(o) &&
      (("label" in o) || ("title" in o) || ("name" in o)) && (("value" in o) || ("key" in o) || ("children" in o) || ("id" in o));
    const rotulo = (o) => o.label ?? o.title ?? o.name ?? o.text ?? null;
    const filhos = (o) => o.children ?? o.options ?? o.subConditions ?? o.items ?? null;

    const serial = (o, prof) => {
      if (prof > 4) return null;
      const r = { rotulo: String(rotulo(o) ?? "").slice(0, 80) };
      const v = o.value ?? o.key ?? o.id; if (v != null && typeof v !== "object") r.valor = String(v).slice(0, 60);
      if (o.type) r.tipo = String(o.type).slice(0, 30);
      if (o.unit) r.unidade = String(o.unit).slice(0, 20);
      if (o.operators) r.operadores = JSON.stringify(o.operators).slice(0, 200);
      const f = filhos(o);
      if (Array.isArray(f) && f.length) { r.filhos = f.map(x => ehOpcao(x) ? serial(x, prof + 1) : String(rotulo(x) ?? x).slice(0,60)).filter(Boolean); }
      return r;
    };

    // varre todos os fibers da página atrás de arrays de opções
    const achados = new Map();
    const visitados = new WeakSet();
    const varreValor = (val, prof) => {
      if (!val || prof > 6) return;
      if (Array.isArray(val)) {
        if (val.length >= 2 && val.length < 200 && val.every(ehOpcao)) {
          const rots = val.map(x => String(rotulo(x))).join(" | ");
          if (/demogr|comport|engaj|divulga|idade|g[êe]nero|regi[ãa]o/i.test(rots) && !achados.has(rots)) {
            achados.set(rots, val.map(x => serial(x, 0)));
          }
        }
        if (val.length < 80) val.forEach(v => varreValor(v, prof + 1));
        return;
      }
      if (typeof val === "object") {
        if (visitados.has(val)) return; visitados.add(val);
        for (const k of Object.keys(val)) {
          if (/^(_owner|_store|stateNode|return|child|sibling|memoizedState|dependencies|alternate)$/.test(k)) continue;
          try { varreValor(val[k], prof + 1); } catch (e) {}
        }
      }
    };

    const raizes = [...document.querySelectorAll("body > div, [id^=root], [id^=app]")];
    for (const el of raizes) {
      const fk = fiberKey(el); if (!fk) continue;
      let f = el[fk], n = 0;
      const pilha = [f];
      while (pilha.length && n < 60000) {
        const cur = pilha.pop(); n++;
        if (!cur) continue;
        if (cur.memoizedProps) varreValor(cur.memoizedProps, 0);
        if (cur.child) pilha.push(cur.child);
        if (cur.sibling) pilha.push(cur.sibling);
      }
      out.chavesVistas.push(`${el.tagName}#${el.id||""}: ${n} fibers`);
    }
    out.arvores = [...achados.values()];

    // fallback: texto do modal, se houver
    const modal = document.querySelector('[class*="drawer"],[class*="modal"],[role="dialog"]');
    if (modal) out.amostraTexto.push((modal.innerText || "").replace(/\s+/g, " ").slice(0, 1200));
  } catch (e) { out.erro = String(e).slice(0, 300); }
  return JSON.stringify(out);
})();
