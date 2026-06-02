# APIs TikTok Shop — Guia de Referência (Rhode)

> Levantado ao vivo em jun/2026 via `probe_scopes.py`, `discover_apis.py` e
> `probe_afiliadas*.py` (token real do app `6jebftqsep751`). Ver também ROADMAP
> decisões #11 e #12.

---

## 1. Modelo mental — 3 camadas

| Camada | O que é | Analogia |
|--------|---------|----------|
| **Escopo (scope)** | permissão que o app tem | a **chave** (liga/desliga no Partner Center) |
| **Endpoint (API)** | o lugar que a chave abre | a **porta** |
| **Dado** | o que vem quando abre | o **conteúdo** |

Duas regras:
- **Ter a chave ≠ usar.** Escopo ligado e parado é só capacidade esperando virar painel.
- **Uma chave abre várias portas.** Ex: a chave "Order" abre lista de pedidos, detalhe, etc.

**Nota técnica de versão:** o segmento de versão no path (ex: `202405`) é validado —
só versões específicas funcionam. Achar a certa é por tentativa (ver
`probe_afiliadas2.py`). Endpoints podem dar `36009007` (timeout de servidor,
transiente → retry) em janelas grandes.

---

## 2. Escopos ATIVOS hoje (todos respondendo no probe)

`Order` · `Finance` · `Product` · `Return/Refund` · `Logistics` · `Promotion` ·
`Shop Analytics` · `Affiliate Messages`

(O Partner Center mostrava ~27 ativos / 15 inativos. Inativos = Product write/delete
avançado, TAP campaign write, etc. — toggle + reautorizar pra ligar.)

---

## 3. APIs de LOJA — o que cada uma entrega

| API | Endpoint | Dado-chave | Granularidade | Usado em |
|-----|----------|-----------|---------------|----------|
| **Shop Analytics** | `GET /analytics/202405/shop/performance` | GMV, compradores, ticket, visitas, breakdown LIVE/VIDEO/PRODUCT_CARD | loja × dia | ✅ Diário |
| **Finance** | `GET /finance/202309/statements` | receita, taxa TikTok, frete, **settlement** (líquido real), payment_status | por repasse | ✅ Financeiro |
| **Return/Refund** | `POST /return_refund/202309/returns/search` | produto, **seller_sku**, **sku_name** (cor+tam), **motivo**, status, valor | por item devolvido | ✅ Devoluções |
| **Order** | `POST /order/202309/orders/search` | itens, SKU, preço, desconto, **cpf/cpf_name** (cliente), status entrega — **SEM creator** | por pedido/item | testado |
| **Product** | `POST /product/202309/products/search` | título, **status** (ativo/desativado), preço, **inventory.quantity** por armazém | por SKU | ⏳ próximo |
| **Promotion** | `POST /promotion/202309/activities/search` | flash sales, campanhas de desconto | por campanha | — |
| **Logistics** | `GET /logistics/202309/warehouses` | armazéns (endereço, status) | por armazém | — |

---

## 4. APIs de AFILIADAS (creators) ⭐ — o coração da Rhode

**Descoberta-chave:** o pedido NORMAL (`/order/...`) **não tem atribuição de creator**.
Pra saber qual creator vendeu, é a **API de Afiliado** abaixo.

### 4.1 Pedidos de Afiliado — `POST /affiliate_seller/202410/orders/search`
Venda por creator. Campos por SKU do pedido:

| Campo | Significado | Exemplo |
|-------|-------------|---------|
| `creator_username` | **handle da creator** | `amandawenzel_` |
| `content_type` | origem | `SHOP` / `VIDEO` / `LIVE` |
| `content_id` | id do conteúdo que gerou | `7493997...` |
| `product_id` / `sku_id` | produto/variante | |
| `estimated_commission_base` | **valor da venda** | R$ 109,90 |
| `estimated_paid_commission` | **comissão da creator** | R$ 8,79 |
| `commission_rate` | % (basis points: 800 = 8%) | `800` |
| `open_collaboration_id` | campanha aberta vinculada | |
| `settlement_status` / `fully_return` | status do repasse / devolvido | `To-SETTLE` |
| `create_time` | timestamp → **creator × dia** | |

**Destrava:** creator×dia automático, performance por creator via API (hoje é xlsx
manual mensal → `etl_v2` → `performance_periods`), reconciliação de comissão,
split por tipo de conteúdo (live vs vídeo vs card). É a base do item 10 do ROADMAP.

### 4.2 Outros endpoints de afiliado (existem, a explorar)
- `POST /affiliate_seller/202410/open_collaborations/search` — campanhas abertas que creators entram
- `POST /affiliate_creator/202407/orders/search` — pedidos na ótica da creator
- `/affiliate_partner/202405/campaigns/...` — campanhas TAP (TikTok Affiliate Partner)
- `seller.affiliate_messages.write` (ativo) — **enviar mensagem pra afiliada** pelo canal nativo do TikTok (hoje a comunicação é Z-API/WhatsApp)

---

## 5. Construído vs disponível (jun/2026)

**No ar (admin → Evolução):** Diário (Analytics) · Financeiro (Finance) ·
Devoluções (Return/Refund, com SKU + motivo).

**Pronto pra virar painel:** Produtos/Estoque (Product) · **Afiliadas/creator×dia
(Affiliate Orders)** ← maior valor · Order-level (clientes novos/recorrentes via CPF).

**Pipeline atual do per-creator:** ainda exports xlsx manuais → `etl_v2.py` →
`performance_periods` (mensal). A Affiliate Orders API permite automatizar + diário.

---

## 6. Como a coleta funciona (técnico)
- Auth: OAuth (`obter_token.py`), token dura ~7 dias, renovável sem browser (`--refresh`).
- Toda chamada: `app_key` + assinatura HMAC-SHA256 + `x-tts-access-token` (ver `coletar_dados.py::chamar`).
- ETLs por domínio em `agente_rhode/etl_*.py` → CSV em `warehouse/` → `sync_supabase.py` → Supabase → admin lê via anon key.
- Refresh semanal: `refresh_performance_diario.sh` via launchd (segunda 08:00).
