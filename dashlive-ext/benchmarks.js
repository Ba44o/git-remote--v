/* GERADO por gerar_benchmarks_live.py — NÃO editar à mão.
   Fonte única: tabela `lives` no Supabase (a mesma do dash-live.html).
   Regerar:  python3 gerar_benchmarks_live.py
   Dois perfis porque `lives.ctr` troca de denominador conforme o schema (R11).
   Carregado como content_script ANTES de lib.js/content.js — sem fetch, sem remote code.
   Alvo global: `self` no Chrome, `globalThis` sob Node (usado por tests/). */
"use strict";
(typeof self !== "undefined" ? self : globalThis).DASHLIVE_BENCHMARKS = {
  "gerado_em": "2026-08-08T15:11:19+00:00",
  "fonte": "Supabase · tabela lives (mesma fonte do dash-live.html)",
  "gerador": "gerar_benchmarks_live.py",
  "total_lives_na_base": 457,
  "perfis": {
    "views": {
      "janela": {
        "de": "2026-03",
        "ate": "2026-05",
        "meses": [
          "2026-03",
          "2026-04",
          "2026-05"
        ],
        "lives": 108
      },
      "identidade": {
        "formula": "product_clicks ÷ views",
        "confere_em": 108,
        "testadas": 108
      },
      "ctr": {
        "v": 22.4334,
        "mediana": 22.0907,
        "n": 108,
        "unid": "%",
        "origem": "lives.ctr"
      },
      "co": {
        "v": 2.538,
        "mediana": 2.412,
        "n": 108,
        "unid": "%",
        "origem": "lives.ctor (taxa de compra após clique — medido, R10)"
      },
      "ticket": {
        "v": 81.88,
        "mediana": 81.04,
        "n": 108,
        "unid": "R$",
        "origem": "gmv_bruto ÷ orders por live"
      },
      "gmvPerLive": {
        "v": 3703.2137,
        "mediana": 3338.7,
        "n": 108,
        "unid": "R$",
        "origem": "lives.gmv_bruto"
      },
      "views": {
        "v": 8283.7685,
        "mediana": 8452.0,
        "n": 108,
        "unid": "views",
        "origem": "lives.views"
      },
      "peakViewers": {
        "v": 180.5455,
        "mediana": 163,
        "n": 55,
        "unid": "viewers",
        "origem": "lives.peak_viewers"
      },
      "convView": {
        "v": 0.5694,
        "unid": "%",
        "origem": "DERIVADO = ctr × co"
      },
      "avgPriceItem": {
        "v": 72.2463,
        "unid": "R$",
        "origem": "lives.avg_price (preço por ITEM — referência, não é o ticket)"
      }
    },
    "impressoes": {
      "janela": {
        "de": "2026-06",
        "ate": "2026-07",
        "meses": [
          "2026-06",
          "2026-07"
        ],
        "lives": 93
      },
      "identidade": {
        "formula": "product_clicks ÷ product_impressions",
        "confere_em": 93,
        "testadas": 93
      },
      "ctr": {
        "v": 6.5838,
        "mediana": 6.5836,
        "n": 93,
        "unid": "%",
        "origem": "lives.ctr"
      },
      "co": {
        "v": 2.8488,
        "mediana": 2.8436,
        "n": 93,
        "unid": "%",
        "origem": "lives.ctor (taxa de compra após clique — medido, R10)"
      },
      "ticket": {
        "v": 85.45,
        "mediana": 83.82,
        "n": 93,
        "unid": "R$",
        "origem": "gmv_bruto ÷ orders por live"
      },
      "gmvPerLive": {
        "v": 3379.79,
        "mediana": 2457.16,
        "n": 93,
        "unid": "R$",
        "origem": "lives.gmv_bruto"
      },
      "views": {
        "v": 5648.7957,
        "mediana": 5244,
        "n": 93,
        "unid": "views",
        "origem": "lives.views"
      },
      "peakViewers": null,
      "convView": {
        "v": 0.1876,
        "unid": "%",
        "origem": "DERIVADO = ctr × co"
      },
      "avgPriceItem": {
        "v": 85.4508,
        "unid": "R$",
        "origem": "lives.avg_price (preço por ITEM — referência, não é o ticket)"
      }
    }
  }
};
