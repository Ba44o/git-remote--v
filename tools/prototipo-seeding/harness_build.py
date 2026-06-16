"""
Monta um harness local que renderiza o MÓDULO EXATO do admin (Seeding & Ativação) —
mesmo CSS (#sd-root) e mesmo JS extraídos do admin.html — com dados reais embutidos
e stubs de sbGet/ensureCP. Pra validar o render real antes de ir pro hub.
Saída: tools/prototipo-seeding/harness.html
"""
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
admin = (BASE / "rhode-vercel/public/admin.html").read_text(encoding="utf-8")

# 1) bloco <style> que contém #sd-root
m = re.search(r"<style>\s*\n\s*#sd-root\{.*?</style>", admin, re.S)
css = m.group(0)

# 2) módulo JS sd (do comentário do painel até o próximo painel)
j = re.search(r"// ── Sub-aba Seeding & Ativação \(consolidado.*?(?=\n// ── Sub-aba Creator × Produto)", admin, re.S)
js = j.group(0)

SA = json.loads((Path("/tmp/sd_sa.json")).read_text())
CP = json.loads((Path("/tmp/sd_cp.json")).read_text())

html = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Harness · Seeding & Ativação (render do admin)</title>
<style>
:root{--ink:#1a1a1a;--ink-48:#9b9b9b;--hairline:#ececec;--rhode-red:#d83b3b;--canvas:#fafafa;--body-muted:#777}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,sans-serif;background:#f4f4f5;padding:24px 28px;color:var(--ink)}
.banner{font-size:12px;color:#777;margin-bottom:14px}
</style>
__CSS__
</head><body>
<div class="banner">HARNESS LOCAL · render EXATO do módulo do admin (mesmo CSS/JS) com dados reais · não é o hub</div>
<div id="sd-root"><div style="padding:40px;text-align:center;color:var(--ink-48)">Carregando…</div></div>
<script>
const _SA=__SA__, _CP=__CP__;
let CP_DATA=[];
async function sbGet(p){return _SA;}            // stub: aqui só busca sample_applications
async function ensureCP(){CP_DATA=_CP;}
__JS__
sdLoad();
</script></body></html>"""

out = (html.replace("__CSS__", css).replace("__JS__", js)
           .replace("__SA__", json.dumps(SA, ensure_ascii=False))
           .replace("__CP__", json.dumps(CP, ensure_ascii=False)))
(HERE / "harness.html").write_text(out, encoding="utf-8")
print("OK:", HERE / "harness.html")
print(f"css {len(css)} chars · js {len(js)} chars · SA {len(SA)} · CP {len(CP)}")
