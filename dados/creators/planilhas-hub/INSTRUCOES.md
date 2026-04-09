# Planilha Rhode Jeans — Guia de Configuração

## 1. Criar a planilha no Google Sheets

Crie UMA planilha com 4 abas com esses nomes exatos:
- `creators`
- `lives`  
- `organicos`
- `skus`

---

## 2. Colunas de cada aba

### creators
| nome | codigo_acesso | canais | modelo_pagamento | taxa | meta_gmv | meta_un | bonus |
|---|---|---|---|---|---|---|---|
| @annita.denim | ANNITA-RJ24 | live,organic | commission | 8 | 15000 | 150 | 500 |

- **canais**: live / organic / paid / live,organic / live,organic,paid
- **modelo_pagamento**: commission (% sobre GMV) / fixed (cachê fixo) / hybrid (cachê + bônus)
- **taxa**: % se commission, valor fixo R$ se fixed/hybrid
- **bonus**: valor R$ extra se meta_gmv atingida

### lives
| creator_id | sku | estoque | preco_normal | preco_flash | inicio | fim | vendas | pico | duracao |
|---|---|---|---|---|---|---|---|---|---|
| c1 | Wide Leg Cargo | 120 | 249.90 | 169.90 | 2026-04-01 20:00 | 2026-04-01 21:30 | 118 | 4200 | 90 |

- **creator_id**: deve ser o mesmo id da aba creators
- **inicio/fim**: formato YYYY-MM-DD HH:MM
- **duracao**: em minutos

### organicos
| creator_id | sku | plataforma | data | views | likes | comentarios | compartilhamentos | cliques | avg_view | vendas | receita |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c1 | Wide Leg Cargo | tiktok | 2026-04-01 | 142000 | 8900 | 420 | 1200 | 4800 | 22 | 38 | 6462 |

- **plataforma**: tiktok / instagram_reels / youtube

### skus
| nome | codigo | estoque | preco | custo |
|---|---|---|---|---|
| Wide Leg Cargo | WLC-001 | 500 | 249.90 | 89.90 |

---

## 3. Publicar cada aba como CSV

Para CADA aba:
1. Arquivo → Compartilhar → Publicar na web
2. Seleciona a aba (ex: "creators")
3. Formato: **Valores separados por vírgula (.csv)**
4. Clica "Publicar"
5. Copia a URL gerada

---

## 4. Colar no Admin

1. Abre https://rhode-circle.netlify.app
2. Login: RHODEADMIN
3. Aba **Dados** → seção Google Sheets sync
4. Cola cada URL no campo correspondente
5. Clica **Sincronizar agora**

Pronto — todos os dados aparecem no dashboard e no portal de cada creator.
