# Módulo Clientes (CRM / Inteligência de Cliente) — estudo de implementação

> 2026-07-15. Integrar o CRM (CPF/LTV/geo/recompra/VIP) ao painel interno. Espelha o padrão
> da feature "Liquidação SKU" (coletor → tabela → admProxy → aba → cron). ~80% já existe.
> Protótipo visual (Monefy): artifact do módulo Clientes.

## 1. Placement
Regra firme ([[feedback_conciliacao_vs_admin_scope]]): `conciliacao.html` = financeiro/gasto ·
`admin.html` = performance (creator/hook/funil). CRM = **terceiro domínio** (inteligência de
receita/cliente). **Recomendação: aba "Clientes" no `conciliacao.html`** (lente de negócio/CFO —
LTV, receita por geo, recompra; não é performance de creator). Alternativa: módulo próprio quando
virar produto (Monefy). Decisão do dono.

## 2. Desafio central
Dado de cliente (CPF/nome/endereço/LTV) **NÃO é persistido** — só vem da Orders API pedido a pedido
(ver [[reference_cliente_dados_ltv]]: 100% CPF, sem email/telefone real). Precisa de coletor + tabela nova.

## 3. Camada de dados
- **`coletar_clientes.py`** (ROOT, cron): pagina `/order/202309/orders/search` (janela `--dias`),
  extrai `(cpf, uf, cidade, total, data, status)`, **hasheia o CPF (sha256)** e agrega por cliente.
  Base = `analise_clientes_ltv.py` + persistência. Idempotente (upsert por hash).
- **Tabelas** (RLS deny-anon, admin-only — padrão `rls_hardening`):
  - `cliente` (PK `cpf_hash`): `n_pedidos, gmv_total, primeiro_pedido, ultimo_pedido, uf, cidade, updated_at`
    → dedup, LTV, recompra, VIP, coorte de frequência.
  - `cliente_uf` (PK `periodo:uf`): `pedidos, gmv` → mapa geográfico leve (não recalcula 23k no cliente).
- Derivados no cliente/UI: LTV=gmv_total/1, recorrente = n_pedidos≥2, coorte = bucket de n_pedidos.

## 4. LGPD (obrigatório)
- **v1 = só `cpf_hash`** → dedup/LTV/recompra/geo sem reter o CPF cru. Risco baixo (é o que o protótipo faz).
- **Contato/campanha = fase 2**: nome/telefone(parcial)/endereço = PII sensível → base legal (execução de
  contrato / legítimo interesse), armazenamento cripto, finalidade + retenção definidas. Painel interno da
  Rhode (seus clientes, seu uso) = base sólida. SaaS multi-tenant = você é **operador** do dado de cada seller.

## 5. Proxy + UI
- `conciliacao.html` lê via **`admProxy` (action=admin_query)** direto das tabelas — NÃO precisa de novo
  `which=` no `get-hub.js` (diferente do dash-live). Igual à aba Liquidação SKU.
- Aba no padrão **lazy-load**: `renderClientesShell()` + `loadClientes()` (fetch tabelas → render).
  Componentes = o protótipo: KPIs · mapa real (choropleth `br-map.json`) · card VIP · coorte de frequência ·
  top cidades. **Filtros temporais** (janela/mês/data — [[feedback_sempre_filtros_temporais]]).
- Mapa: embutir os paths reais por UF (`br-map.json`, ~55 KB, projetado do GeoJSON IBGE) uma vez.

## 6. Cron
`coletar_clientes.py --dias 30` no `refresh_performance_diario.sh` (diário incremental; 1ª carga =
backfill `--inicio 2026-04-01`). ⚠️ pull pesado (~23k/mês) na 1ª vez; incremental depois.

## 7. Esforço / risco
| Item | Esforço | Nota |
|---|---|---|
| coletar_clientes.py + SQL | ~½ dia | base = analise_clientes_ltv.py |
| aba Clientes (UI) | ~½ dia | molde = aba Liquidação SKU |
| LGPD v1 (hash) | baixo | tratar antes de contato/campanha |
| pull inicial | pesado | incremental depois, idempotente |

## 8. Reúso (o que já existe)
`analise_clientes_ltv.py` (coletor/LTV) · `br-map.json` (mapa) · padrão exato da aba Liquidação SKU
(coletor+tabela+admProxy+aba+cron) · números geo/LTV/coorte já validados. Ver [[reference_cliente_dados_ltv]],
[[reference_dashboardly_competitor]] (Dashboardly tem LTV genérico; o diferencial BR é CPF+geo+fisco).
