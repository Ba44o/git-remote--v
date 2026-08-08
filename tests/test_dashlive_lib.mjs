/* Teste da lib da extensão DashLive — roda sem Chrome e sem DOM:
     node tests/test_dashlive_lib.mjs

   Cobre as duas coisas que, se errarem, o painel mente a live inteira:
   1. parsing pt-BR (a tela do Seller Center é toda "R$ 1.234,56" / "28,4%");
   2. escolha da régua de CTR (dois denominadores convivem — R11).
   A parte 2 roda contra uma AMOSTRA REAL da tabela `lives`, não contra número inventado. */
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const L = require(join(HERE, "..", "dashlive-ext", "lib.js"));

let pass = 0, fail = 0;
const eq = (got, exp, nome) => {
  const ok = got === exp || (typeof got === "number" && typeof exp === "number" && Math.abs(got - exp) < 1e-9);
  ok ? pass++ : fail++;
  if (!ok) console.log(`  ✗ ${nome}: esperado ${exp}, veio ${got}`);
};
const sec = t => console.log(`\n── ${t}`);

/* ── 1. parser pt-BR ────────────────────────────────────────────────────── */
sec("parser pt-BR");
eq(L.parseNumberPtBR("R$ 1.234,56", "money"), 1234.56, "moeda com milhar e centavos");
eq(L.parseNumberPtBR("9.519", "int"), 9519, "milhar sem decimal");
eq(L.parseNumberPtBR("2,52%", "pct"), 2.52, "percentual com vírgula");
eq(L.parseNumberPtBR("28,4%", "pct"), 28.4, "percentual 1 casa");
eq(L.parseNumberPtBR("R$ 12.345.678,90", "money"), 12345678.90, "milhão");
eq(L.parseNumberPtBR("R$ 0,00", "money"), 0, "zero em moeda");
eq(L.parseNumberPtBR("1.234", "pct"), 1.234, "ponto em pct é decimal, não milhar");
eq(L.parseNumberPtBR("1,234.56", "money"), 1234.56, "formato en-US (fallback)");
eq(L.parseNumberPtBR("GMV: R$ 6.211", "money"), 6211, "número com rótulo colado");
eq(L.parseNumberPtBR("", "int"), null, "string vazia → null");
eq(L.parseNumberPtBR("—", "int"), null, "travessão da UI → null");
eq(L.parseNumberPtBR(null, "int"), null, "null → null");
eq(L.parseNumberPtBR("1.234,5", "money"), 1234.5, "uma casa decimal");
eq(L.parseNumberPtBR("47", "int"), 47, "inteiro puro");
eq(L.parseNumberPtBR("6,5", "pct"), 6.5, "CTR do padrão novo");
eq(L.parseNumberPtBR("-R$ 1.200,00", "money"), -1200, "negativo (estorno)");
eq(L.parseNumberPtBR("2.500 views", "int"), 2500, "sufixo depois do número");
eq(L.parseNumberPtBR("0,79%", "pct"), 0.79, "conv por visualização");

// O Console de LIVE abrevia número grande. Sem isso o painel lia R$ 2,80 no lugar
// de R$ 2.800 — número válido, erro invisível. Visto na tela real em 08/08/26.
sec("números abreviados do Seller Center");
eq(L.parseNumberPtBR("R$ 2,8 mil", "money"), 2800, "GMV abreviado em mil");
eq(L.parseNumberPtBR("1,4 mil", "int"), 1400, "cliques abreviados em mil");
eq(L.parseNumberPtBR("R$ 12,5 mil", "money"), 12500, "milhar com 2 dígitos");
eq(L.parseNumberPtBR("2 mil", "int"), 2000, "mil sem decimal");
eq(L.parseNumberPtBR("R$ 1,2 mi", "money"), 1200000, "milhão abreviado");
eq(L.parseNumberPtBR("3,4k", "int"), 3400, "sufixo k");
eq(L.parseNumberPtBR("R$ 1.234,56", "money"), 1234.56, "valor cheio não é afetado");
eq(L.parseNumberPtBR("9.519", "int"), 9519, "milhar por ponto não é afetado");
eq(L.ehAbreviado("R$ 2,8 mil"), true, "detecta abreviação (pra marcar aproximado)");
eq(L.ehAbreviado("R$ 2.847,90"), false, "valor cheio não é abreviado");

/* ── 1b. reconhecimento de rótulo (auto-mapeamento) ──────────────────────
   Rótulos colhidos da tela real do Console de LIVE em 08/08/26. As linhas com
   `null` são as armadilhas: campos que ficam ao lado dos certos e não podem casar
   ("Itens atribuídos" não é pedido; "GMV por hora" não é o GMV da live). */
sec("reconhecimento de rótulo");
const rot = [
  ["GMV atribuído", "gmv"], ["GMV da live", "gmv"], ["GMV por hora", null], ["Ticket médio", null],
  ["Pedidos", "orders"], ["Pedidos atribuídos", "orders"], ["Itens atribuídos", null],
  ["Espectadores ativos", "liveViewers"], ["Espectadores ao vivo", "liveViewers"],
  ["Visualizações", "viewers"], ["Total de espectadores", "viewers"],
  ["Cliques no produto", "clicks"], ["Porcentagem de cliques no produto", "ctr"],
  ["Porcentagem d…", "ctr"], ["Taxa de compra após clique", "co"],
  ["Impressões do produto", "impressions"], ["Comentários", "comments"],
  ["Taxa de entrada", "err"], ["Duração média de visualização", null], ["Chat", null], ["", null],
];
let rOk = 0;
for (const [txt, esp] of rot) { const g = L.metricaDoRotulo(txt); if (g === esp) rOk++; else console.log(`  ✗ "${txt}" → ${g} (esperado ${esp})`); }
eq(rOk, rot.length, `reconhece ${rOk}/${rot.length} rótulos da tela real`);
eq(L.normalizarRotulo("Porcentagem de cliques"), "porcentagem de cliques", "normaliza acento e caixa");

/* Painel de LIVE (shop.tiktok.com/workbench/live/overview) — tela densa, colhida
   em 08/08/26. Metade dos campos são armadilhas: taxas que contêm o nome de uma
   contagem ("Taxa de comentários"), derivados por hora ("GMV por hora") e
   recortes ("Visualizações de > 1 min."). Casar qualquer um deles é pior que
   não achar nada, porque entra no painel como se fosse a métrica boa. */
sec("rótulos do Painel de LIVE");
const rot2 = [
  ["GMV (R$)", "gmv"], ["GMV por hora", null], ["Itens atribuídos vendidos", null],
  ["Espectadores atuais", "liveViewers"], ["Visualizações", "viewers"],
  ["Visualizações de > 1 min.", null], ["Média de duração da vis…", null],
  ["CTR por LIVE", "ctr"], ["Taxa de pedidos (SKU)", "convView"],
  ["Impressões por hora", null], ["Taxa de comentários", null],
  ["Taxa de seguidas", null], ["Taxa de Curtidas", null], ["Porcentagem de visitant…", null],
];
let r2 = 0;
for (const [txt, esp] of rot2) { const g = L.metricaDoRotulo(txt); if (g === esp) r2++; else console.log(`  ✗ "${txt}" → ${g} (esperado ${esp})`); }
eq(r2, rot2.length, `reconhece ${r2}/${rot2.length} rótulos do Painel de LIVE`);

// "CTR por LIVE" diz o denominador no próprio nome — a régua sai daí, sem inferência.
eq(L.perfilPeloRotulo("CTR por LIVE"), "views", "rótulo declara o perfil de CTR");
eq(L.perfilPeloRotulo("Porcentagem de cliques no produto"), null, "rótulo sem denominador não declara perfil");

// CO derivado da identidade CTR × CO = convView, com os números reais da tela:
// 581 views · CTR 13,77% · taxa de pedidos (SKU) 0,34% → 2 itens vendidos.
eq(+L.deriveCO(0.34, 13.77).toFixed(2), 2.47, "CO derivado de convView ÷ CTR");
eq(+(581 * 0.34 / 100).toFixed(1), 2.0, "convView × views reproduz os itens vendidos da tela");
eq(L.deriveCO(0.34, 0), null, "CTR zero não deriva CO");
eq(L.deriveCO(null, 13.77), null, "sem convView não deriva CO");

/* ── 2. derivados ───────────────────────────────────────────────────────── */
sec("derivados");
// abril/26: CTR 28,51% × CO 2,776% = 0,79% de conversão por visualização.
// O build antigo fazia 2,52 ÷ 28,4 = 8,9% e chamava isso de CO — invertido (R10).
eq(+L.deriveConvView(28.51, 2.776).toFixed(3), 0.791, "convView = CTR × CO");
eq(L.deriveConvView(null, 2.7), null, "sem CTR → null");
eq(L.deriveConvView(28.4, null), null, "sem CO → null");
eq(L.computeGpm(6000, 60000), 100, "GPM por 1k impressões");
eq(L.computeGpm(6000, 0), null, "GPM sem impressões → null");
eq(L.grade(1.0, 1.0, 0.8), "good", "no bench = good");
eq(L.grade(0.85, 1.0, 0.8), "warn", "entre os cortes = warn");
eq(L.grade(0.5, 1.0, 0.8), "bad", "abaixo do corte = bad");

/* ── 3. régua de CTR contra a amostra real da tabela `lives` ────────────── */
sec("detecção de perfil (amostra real de lives)");
const fx = JSON.parse(readFileSync(join(HERE, "fixtures", "dashlive_lives_amostra.json"), "utf8"));
require(join(HERE, "..", "dashlive-ext", "benchmarks.js"));   // popula globalThis.DASHLIVE_BENCHMARKS
const BENCH = globalThis.DASHLIVE_BENCHMARKS;
const esperado = { v1: "views", v2: "views", "v2-api": "impressoes" };

let exatas = 0, exatasOk = 0, magn = 0, magnErr = 0, magnMudo = 0, magnConf = 0;
for (const l of fx.lives) {
  const alvo = esperado[l.schema_version];
  if (!alvo) continue;
  // Via exata: com cliques calibrados, o perfil sai da identidade — sem chute.
  const d1 = L.detectCtrProfile(
    { ctr: l.ctr, clicks: l.product_clicks, views: l.views, impressions: l.product_impressions }, BENCH);
  exatas++; if (d1.profile === alvo && d1.method === "identidade") exatasOk++;
  // Via magnitude: sem cliques, só a ordem de grandeza.
  const d2 = L.detectCtrProfile({ ctr: l.ctr, views: l.views, impressions: l.product_impressions }, BENCH);
  magn++;
  if (d2.confident) magnConf++;
  if (d2.profile === null) magnMudo++;
  else if (d2.profile !== alvo) magnErr++;
}
eq(exatasOk, exatas, `via identidade acerta o schema em ${exatasOk}/${exatas} lives reais`);
// O contrato da via magnitude não é "acerta sempre" — é "nunca se declara confiável".
// Uma live com CTR genuinamente ruim é indistinguível de uma medida no outro
// denominador; só os cliques desempatam. Por isso ela nunca fixa o bench sozinha.
eq(magnConf, 0, "via magnitude nunca se declara confiável");
eq(magnErr <= 2, true, `via magnitude erra no máximo 2 em ${magn} (errou ${magnErr}, calou ${magnMudo})`);
console.log(`  · magnitude: ${magn - magnErr - magnMudo} certas, ${magnErr} erradas, ${magnMudo} "não sei"`);

// nenhuma leitura → nenhum palpite
eq(L.detectCtrProfile({ ctr: null }, BENCH).profile, null, "sem CTR não define perfil");
eq(L.detectCtrProfile({ ctr: 0 }, BENCH).profile, null, "CTR zero não define perfil");

/* ── 4. benchmarks vêm do arquivo gerado, não de constante ─────────────── */
sec("proveniência dos benchmarks");
eq(!!BENCH && !BENCH.stale, true, "benchmarks.js carregado (não é o fallback)");
for (const perfil of ["views", "impressoes"]) {
  const b = L.resolveBenchmarks(BENCH, perfil);
  eq(!!b, true, `perfil ${perfil} existe`);
  eq(b.co != null && b.co > 0 && b.co < 10, true, `CO do perfil ${perfil} é medido (0-10%), não os 8,9% derivados`);
  eq(+Math.abs(b.convView - b.ctr * b.co / 100).toFixed(4) < 0.001, true, `convView do perfil ${perfil} = CTR × CO`);
  eq(b.ticket > 50, true, `ticket do perfil ${perfil} é GMV÷pedidos, não preço por item`);
}

/* ── 5. round-trip: número real → como a tela pinta → de volta ao número ──
   É o teste que fecha a Fase 4. Cada valor da tabela `lives` é formatado em pt-BR
   do jeito que o Seller Center mostra e devolvido ao parser. Se o round-trip fecha,
   o que o painel lê ao vivo é o mesmo número que vai pro dashboard depois. */
sec("round-trip com valores reais da tabela lives");
const brl = n => "R$ " + n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const int = n => Math.round(n).toLocaleString("pt-BR");
const pc1 = n => n.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + "%";
const pc2 = n => n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + "%";

let rt = 0, rtOk = 0, piorTicket = 0;
for (const l of fx.lives) {
  const checa = (fmt, val, tipo, casas) => {
    rt++;
    const volta = L.parseNumberPtBR(fmt, tipo);
    if (Math.abs(volta - +val.toFixed(casas)) < 1e-9) rtOk++;
    else console.log(`  ✗ round-trip ${tipo}: "${fmt}" → ${volta} (esperado ${+val.toFixed(casas)})`);
  };
  if (l.gmv_bruto != null) checa(brl(l.gmv_bruto), l.gmv_bruto, "money", 2);
  if (l.views) checa(int(l.views), l.views, "int", 0);
  if (l.product_impressions) checa(int(l.product_impressions), l.product_impressions, "int", 0);
  if (l.orders) checa(int(l.orders), l.orders, "int", 0);
  if (l.ctr != null) checa(pc1(l.ctr), l.ctr, "pct", 1);
  if (l.ctor != null) checa(pc2(l.ctor), l.ctor, "pct", 2);

  // O ticket que o painel mostra (GMV lido ÷ pedidos lidos) tem que reproduzir o
  // ticket que sai da tabela — é o número que vai bater com a conciliação depois.
  if (l.orders > 0 && l.gmv_bruto != null) {
    const gmvLido = L.parseNumberPtBR(brl(l.gmv_bruto), "money");
    const pedLidos = L.parseNumberPtBR(int(l.orders), "int");
    piorTicket = Math.max(piorTicket, Math.abs(gmvLido / pedLidos - l.gmv_bruto / l.orders));
  }
}
eq(rtOk, rt, `round-trip fecha em ${rtOk}/${rt} valores reais`);
eq(piorTicket < 0.01, true, `ticket derivado da leitura bate com o da tabela (pior desvio R$ ${piorTicket.toFixed(4)})`);

/* ── 6. o bench antigo condenava a operação inteira ──────────────────────
   Regressão do achado R10: com CO=8,9% (derivado errado), praticamente toda live
   real da nossa base entrava em vermelho no semáforo — não por performance, por
   régua. Este teste trava a correção: o bench medido tem que julgar as mesmas
   lives de forma distribuída, e o antigo tem que reprovar quase todas. */
sec("regressão R10 — CO derivado vs CO medido");
const CO_ANTIGO = 8.9;
const coMedido = L.resolveBenchmarks(BENCH, "views").co;
let ruimAntigo = 0, ruimNovo = 0, n = 0;
for (const l of fx.lives) {
  if (l.ctor == null || esperado[l.schema_version] !== "views") continue;
  n++;
  if (L.grade(l.ctor / CO_ANTIGO, 1.0, 0.8) === "bad") ruimAntigo++;
  if (L.grade(l.ctor / coMedido, 1.0, 0.8) === "bad") ruimNovo++;
}
console.log(`  · com CO=8,9% (antigo): ${ruimAntigo}/${n} lives em VERMELHO`);
console.log(`  · com CO=${coMedido}% (medido): ${ruimNovo}/${n} lives em VERMELHO`);
eq(ruimAntigo, n, "bench antigo reprovava 100% das lives reais");
eq(ruimNovo < n * 0.6, true, `bench medido distribui o julgamento (${ruimNovo}/${n} vermelhas)`);

console.log(`\n${fail === 0 ? "✓" : "✗"} ${pass} passaram, ${fail} falharam\n`);
process.exit(fail === 0 ? 0 : 1);
