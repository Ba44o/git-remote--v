"""
Rhode — Sync Catálogo
=====================
Lê o sitemap de produtos do site rhodejeans.com.br, extrai JSON-LD de cada
página e popula a tabela `produtos` no Supabase.

Uso:
  python sync_catalogo.py            # dry-run (lista sem inserir)
  python sync_catalogo.py --upsert   # insere/atualiza no Supabase
  python sync_catalogo.py --upsert --limpar  # apaga produtos placeholder antigos antes
"""
import sys
import re
import json
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

# ── Config ────────────────────────────────────────────────────────────────────

SITEMAP_URL = "https://www.rhodejeans.com.br/sitemap-produto.xml"
SB_URL      = "https://ivzpykuluxcxefhyzfsf.supabase.co/rest/v1"
SB_SVC_KEY  = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml2enB5a3VsdXhjeGVmaHl6ZnNmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTczNzkzNiwiZXhwIjoyMDkxMzEzOTM2fQ.qlHnvGOnGSMwniuS_YYKQaQa-gD_F5asDQTIT2B42hk"

HEADERS_HTTP = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Rhode-Catalog-Sync/1.0",
}
HEADERS_SB = {
    "apikey": SB_SVC_KEY,
    "Authorization": f"Bearer {SB_SVC_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates,return=representation",
}

# Mapping de categoria por slug
def detect_category(url: str) -> str:
    slug = url.rsplit("/", 1)[-1].lower()
    if slug.startswith("calca"):
        if "wide-leg" in slug: return "wide_leg"
        if "mom" in slug:       return "mom_jeans"
        if "skinny" in slug:    return "skinny"
        if "reta" in slug:      return "reta"
        return "outro"
    if slug.startswith("shorts"):  return "shorts"
    if slug.startswith("body"):    return "body"
    if slug.startswith("saia"):    return "saia"
    if slug.startswith("blusa") or slug.startswith("bata"): return "bata"
    if slug.startswith("vestido"): return "vestido"
    if slug.startswith("top"):     return "top"
    return "outro"

JSONLD_RE = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)


def fetch_sitemap_urls():
    print("▶ Lendo sitemap...")
    r = requests.get(SITEMAP_URL, headers=HEADERS_HTTP, timeout=30)
    r.raise_for_status()
    urls = re.findall(r"<loc>([^<]+)</loc>", r.text)
    print(f"  → {len(urls)} URLs no sitemap-produto")
    return urls


def extract_product(url):
    """Baixa a página e extrai o Product JSON-LD."""
    try:
        r = requests.get(url, headers=HEADERS_HTTP, timeout=20)
        r.raise_for_status()
    except Exception as e:
        return {"_url": url, "_erro": str(e)[:80]}

    matches = JSONLD_RE.findall(r.text)
    product = None
    for raw in matches:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        # Pode ser dict, lista, ou @graph
        candidates = []
        if isinstance(data, dict):
            if data.get("@type") == "Product":
                candidates.append(data)
            elif "@graph" in data:
                candidates.extend([n for n in data["@graph"] if n.get("@type") == "Product"])
        elif isinstance(data, list):
            candidates.extend([n for n in data if isinstance(n, dict) and n.get("@type") == "Product"])
        if candidates:
            product = candidates[0]
            break

    if not product:
        return {"_url": url, "_erro": "sem JSON-LD Product"}

    # Extrai campos
    sku = product.get("sku") or product.get("productID") or ""
    nome = (product.get("name") or "").strip()
    img = product.get("image")
    if isinstance(img, list):
        img = img[0] if img else None
    # Limpa query string da imagem (ims=475x650 dá foto pequena, vamos manter)
    foto = img

    desc = (product.get("description") or "").strip()
    # Normaliza HTML entities básicas
    desc = (desc.replace("&ccedil;", "ç").replace("&atilde;", "ã").replace("&aacute;", "á")
                .replace("&eacute;", "é").replace("&iacute;", "í").replace("&oacute;", "ó")
                .replace("&uacute;", "ú").replace("&Ccedil;", "Ç").replace("&Atilde;", "Ã")
                .replace("&Aacute;", "Á").replace("&Eacute;", "É").replace("&ntilde;", "ñ")
                .replace("&otilde;", "õ").replace("&acirc;", "â").replace("&ecirc;", "ê")
                .replace("&ocirc;", "ô").replace("&Otilde;", "Õ").replace("&Acirc;", "Â"))
    # Tira tags HTML básicas
    desc = re.sub(r"<[^>]+>", " ", desc)
    desc = re.sub(r"\s+", " ", desc).strip()[:400]

    offers = product.get("offers") or {}
    if isinstance(offers, dict):
        preco = offers.get("lowPrice") or offers.get("price")
    else:
        preco = None
    try:
        preco = float(preco) if preco else None
    except (ValueError, TypeError):
        preco = None

    return {
        "sku": sku,
        "nome": nome,
        "categoria": detect_category(url),
        "preco_venda": preco,
        "foto_url": foto,
        "descricao": desc or None,
        "ativo": True,
        "_url": url,
    }


def upsert_produtos(produtos):
    """Insere/atualiza produtos no Supabase. Retorna (sucesso, falhas)."""
    payload = []
    for p in produtos:
        if not p.get("sku") or not p.get("nome"):
            continue
        payload.append({
            "sku":            p["sku"],
            "nome":           p["nome"],
            "categoria":      p.get("categoria"),
            "preco_venda":    p.get("preco_venda"),
            "foto_url":       p.get("foto_url"),
            "descricao":      p.get("descricao"),
            "ativo":          True,
        })

    sucesso = 0
    falhas = 0
    BATCH = 50
    for i in range(0, len(payload), BATCH):
        batch = payload[i:i + BATCH]
        try:
            r = requests.post(
                f"{SB_URL}/produtos?on_conflict=sku",
                headers=HEADERS_SB,
                json=batch,
                timeout=30,
            )
            if r.status_code in (200, 201):
                sucesso += len(batch)
            else:
                print(f"  [ERRO batch {i}] {r.status_code} {r.text[:200]}")
                falhas += len(batch)
        except Exception as e:
            print(f"  [ERRO batch {i}] {e}")
            falhas += len(batch)
    return sucesso, falhas


def limpar_produtos_placeholder():
    """Remove os 10 produtos placeholder WIDE-MARM, WIDE-ROSA etc — só se não tiverem sido usados em amostras."""
    placeholders = [
        "WIDE-MARM", "WIDE-ROSA", "WIDE-AZUL", "WIDE-PRETA", "WIDE-BRANCA",
        "WIDE-CHOCO", "WIDE-AMAMNTG", "WIDE-STONE", "WIDE-SKY", "WIDE-PRMARM",
    ]
    # Confere se algum foi usado em amostras
    r = requests.get(
        f"{SB_URL}/amostras_enviadas?select=sku&sku=in.({','.join(placeholders)})",
        headers={"apikey": SB_SVC_KEY, "Authorization": f"Bearer {SB_SVC_KEY}"},
        timeout=20,
    )
    usados = {row["sku"] for row in r.json()} if r.ok else set()
    a_apagar = [p for p in placeholders if p not in usados]
    if usados:
        print(f"  [INFO] {len(usados)} placeholders mantidos pq já têm amostras: {sorted(usados)}")
    if not a_apagar:
        print("  [INFO] Nenhum placeholder pra apagar")
        return
    list_str = ",".join(a_apagar)
    r = requests.delete(
        f"{SB_URL}/produtos?sku=in.({list_str})",
        headers={"apikey": SB_SVC_KEY, "Authorization": f"Bearer {SB_SVC_KEY}", "Prefer": "return=minimal"},
        timeout=20,
    )
    print(f"  [✓] {len(a_apagar)} placeholders apagados (status {r.status_code})")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--upsert", action="store_true", help="Insere/atualiza no Supabase (sem isso, é dry-run)")
    parser.add_argument("--limpar", action="store_true", help="Apaga produtos placeholder antigos (WIDE-*) antes do upsert")
    parser.add_argument("--workers", type=int, default=5)
    args = parser.parse_args()

    print("\n" + "═" * 60)
    print("  Rhode — Sync Catálogo (rhodejeans.com.br → Supabase)")
    print("═" * 60 + "\n")

    urls = fetch_sitemap_urls()
    print(f"\n▶ Baixando {len(urls)} páginas em paralelo ({args.workers} workers)...")

    produtos = []
    erros = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(extract_product, url): url for url in urls}
        for f in as_completed(futures):
            r = f.result()
            if r and r.get("_erro"):
                erros.append(r)
            elif r and r.get("sku"):
                produtos.append(r)
    elapsed = time.time() - t0

    print(f"  → {len(produtos)} extraídos, {len(erros)} erros em {elapsed:.1f}s\n")

    # Sumário por categoria
    from collections import Counter
    print("▶ Por categoria:")
    cats = Counter(p["categoria"] for p in produtos)
    for cat, n in cats.most_common():
        print(f"    {cat:<12} {n:>3}")

    # Amostra
    print("\n▶ Amostra (3 primeiros):")
    for p in produtos[:3]:
        preco = f"R$ {p['preco_venda']:.2f}" if p['preco_venda'] else "—"
        print(f"    {p['sku']:<12} · {p['nome'][:50]:<50} · {p['categoria']:<10} · {preco}")

    if erros:
        print(f"\n▶ Erros ({len(erros)}):")
        for e in erros[:5]:
            print(f"    {e.get('_url','?')}: {e.get('_erro','?')}")

    if not args.upsert:
        print("\n" + "─" * 60)
        print("DRY-RUN concluído. Para inserir no Supabase:")
        print("  python sync_catalogo.py --upsert")
        print("  python sync_catalogo.py --upsert --limpar  # apaga placeholders WIDE-* não usados")
        return

    if args.limpar:
        print("\n▶ Limpando placeholders antigos...")
        limpar_produtos_placeholder()

    print("\n▶ Sincronizando com Supabase (upsert)...")
    sucesso, falhas = upsert_produtos(produtos)
    print(f"  [✓] {sucesso} produtos sincronizados")
    if falhas:
        print(f"  [!] {falhas} falhas — ver erros acima")

    print("\n✅ Sync concluído.")


if __name__ == "__main__":
    main()
