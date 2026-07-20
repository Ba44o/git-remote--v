#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Refresh semanal da Performance Diária da loja (TikTok Shop API → Supabase).
# Roda LOCALMENTE — precisa do .env (tokens) + scripts coletar_dados.py/obter_token.py.
# Agendado por launchd: ~/Library/LaunchAgents/com.rhode.refresh-performance-diario.plist
# Log: logs/refresh_diario.log
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

# Diretório do próprio script — funciona no Mac (launchd) E no GitHub Actions.
PROJ="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJ" || { echo "[ERRO] não achei $PROJ"; exit 1; }
mkdir -p "$PROJ/logs"

echo "═════ Refresh Performance Diária — $(date '+%F %T') ═════"

# 1) Renova o access token (best-effort: se falhar, segue com o token atual)
echo "[1/13] Renovando token TikTok..."
python3 obter_token.py --refresh || echo "  ⚠ refresh falhou — seguindo com token atual"

# 2) ETL diário via API — janela de 14 dias (pega dias que finalizaram tarde; UPSERT idempotente)
echo "[2/13] ETL diário via API (--dias 14)..."
python3 agente_rhode/etl_diario.py --source api --dias 14 || { echo "  ❌ ETL diário FALHOU"; exit 1; }

# 3) Sync → performance_diario (load_dotenv inline pra sync_supabase achar as SUPABASE_* keys)
echo "[3/13] Sync → performance_diario..."
python3 -c "from dotenv import load_dotenv; load_dotenv(); import sys,runpy; sys.argv=['sync','--only','performance_diario']; runpy.run_path('agente_rhode/sync_supabase.py', run_name='__main__')" \
    || { echo "  ❌ SYNC diário FALHOU"; exit 1; }

# 4) ETL financeiro via API — janela de 14 dias (statements/settlements)
echo "[4/13] ETL financeiro via API (--dias 14)..."
python3 agente_rhode/etl_finance.py --dias 14 || { echo "  ❌ ETL finance FALHOU"; exit 1; }

# 5) Sync → finance_statements
echo "[5/13] Sync → finance_statements..."
python3 -c "from dotenv import load_dotenv; load_dotenv(); import sys,runpy; sys.argv=['sync','--only','finance']; runpy.run_path('agente_rhode/sync_supabase.py', run_name='__main__')" \
    || { echo "  ❌ SYNC finance FALHOU"; exit 1; }

# 5b) Settlement ITEMIZADO por pedido (statement_tx) — SEMANAL (segunda), janela 45d.
#     Root-cause fix (RUNBOOK #13): antes era manual e envelhecia; agora roda sozinho toda
#     segunda p/ pegar settlements atrasados (lag ~2-4 sem). Idempotente, não-crítico, pesado.
if [ "$(date +%u)" = "1" ]; then
  echo "[5b] statement_tx itemizado (semanal · 45d)..."
  python3 coletar_statement_tx.py --dias 45 || echo "  ⚠ statement_tx falhou (não-crítico — segue)"

  # 5c) Radar de potencial: performance por vídeo × creator (video_perf). SEMANAL (segunda), 120d.
  #     Alimenta a aba "Radar de potencial" do admin (creators que postam mas ainda não vendem).
  #     Recompute completo com guarda de total_count — aborta sem gravar se truncar. Pesado (~16k vídeos).
  echo "[5c] shop_videos → radar de potencial (semanal · 120d)..."
  python3 coletar_shop_videos.py --dias 120 || echo "  ⚠ shop_videos falhou (não-crítico — segue)"
fi

# 6) ETL devoluções via API — janela de 14 dias
echo "[6/13] ETL devoluções via API (--dias 14)..."
python3 agente_rhode/etl_devolucoes.py --dias 14 || { echo "  ❌ ETL devoluções FALHOU"; exit 1; }

# 7) Sync → devolucoes
echo "[7/13] Sync → devolucoes..."
python3 -c "from dotenv import load_dotenv; load_dotenv(); import sys,runpy; sys.argv=['sync','--only','devolucoes']; runpy.run_path('agente_rhode/sync_supabase.py', run_name='__main__')" \
    || { echo "  ❌ SYNC devoluções FALHOU"; exit 1; }

# 8) ETL afiliadas via API — janela de 14 dias (performance por creator)
echo "[8/13] ETL afiliadas via API (--dias 90)..."
python3 agente_rhode/etl_affiliate.py --dias 90 || { echo "  ❌ ETL afiliadas FALHOU"; exit 1; }

# 9) Sync → affiliate_perf
echo "[9/13] Sync → affiliate_perf..."
python3 -c "from dotenv import load_dotenv; load_dotenv(); import sys,runpy; sys.argv=['sync','--only','affiliate_perf']; runpy.run_path('agente_rhode/sync_supabase.py', run_name='__main__')" \
    || { echo "  ❌ SYNC afiliadas FALHOU"; exit 1; }

# 10) ETL seeding (target collaborations × vendas por produto) — lento (detalhes dos convites)
echo "[10/13] ETL seeding (target collaborations)..."
python3 agente_rhode/etl_seeding.py || { echo "  ❌ ETL seeding FALHOU"; exit 1; }

# 11) Sync → seeding
echo "[11/13] Sync → seeding..."
python3 -c "from dotenv import load_dotenv; load_dotenv(); import sys,runpy; sys.argv=['sync','--only','seeding']; runpy.run_path('agente_rhode/sync_supabase.py', run_name='__main__')" \
    || { echo "  ❌ SYNC seeding FALHOU"; exit 1; }

# 12) ETL creator×produto (base de inteligência de creator)
# NOTA: este + seeding + affiliate_perf re-coletam affiliate orders separadamente.
# Otimização futura: coletar 1x e alimentar os 3 (ver ROADMAP).
echo "[12/13] ETL creator×produto..."
python3 agente_rhode/etl_creator_product.py --dias 90 || { echo "  ❌ ETL creator×produto FALHOU"; exit 1; }

# 13) Sync → affiliate_creator_product
echo "[13/13] Sync → affiliate_creator_product..."
python3 -c "from dotenv import load_dotenv; load_dotenv(); import sys,runpy; sys.argv=['sync','--only','creator_product']; runpy.run_path('agente_rhode/sync_supabase.py', run_name='__main__')" \
    || { echo "  ❌ SYNC creator×produto FALHOU"; exit 1; }

# 14) Extrato de Comissões (Central de Comissões / Meu Extrato — creator-facing)
#     Janela de 21d cobre o que ainda está liquidando. UPSERT direto no Supabase
#     (extrato_resumo + extrato_pedidos). Aditivo: não toca performance_periods.
echo "[14/15] Extrato de comissões (--dias 21)..."
python3 coletar_extrato.py --dias 21 || echo "  ⚠ extrato falhou (não-crítico — segue)"

# 15) Pedidos por SKU (lado LOJA — conciliação/margem admin-only).
#     Persiste line_items por (order_id, sku) em pedidos_sku. Aditivo: tabela
#     nova, não lida por creator. UPSERT idempotente direto no Supabase.
echo "[15/17] Pedidos por SKU (--dias 21)..."
python3 coletar_pedidos_sku.py --dias 21 || echo "  ⚠ pedidos_sku falhou (não-crítico — segue)"

# 15b) Custo GMV Max via Business/Ads API — mata o import manual do "Campaign overview".
#      metric `cost` do /gmv_max/report/get/ = "Custo do GMV máximo" do Seller Center
#      (validado ao centavo). Popula ads_custo (total diário). --dias 35 (API chunka 30d).
echo "[15b] Custo GMV Max (Ads API)..."
python3 coletar_gmvmax_api.py --dias 35 || echo "  ⚠ GMV Max API falhou (não-crítico — segue)"

# 15c) Live por sessão (Business API room-level, GMV Max/ads) + GMV de live total (Analytics).
echo "[15c] Live GMV Max (sessão) + GMV total..."
python3 coletar_lives_api.py --dias 35 || echo "  ⚠ lives GMV Max falhou (não-crítico — segue)"

# 15d) Live ATRIBUÍDA do Seller Center via API (/analytics/202509/shop_lives/performance,
#      filtra username=rhodejeans). Fonte da verdade do GMV de live (bate com o export ~0,02%).
#      Popula live_attr. Mata o import manual do Livestream.
echo "[15d] Live atribuída (Seller Center via API)..."
python3 coletar_lives_attr_api.py --dias 40 || echo "  ⚠ live_attr API falhou (não-crítico — segue)"

# 15e) Enriquece live_attr com VIEWS a partir de exports do Livestream dropados em
#      dados/lives/exports/ (a API não traz views). Casa por room_id. Idempotente.
echo "[15e] Views de live (export → live_attr)..."
python3 importar_live_performance.py || echo "  ⚠ import de views falhou (não-crítico — segue)"

# 15f) Painel INTERNO dash-live (tabela `lives`): funil do export do Seller Center (formato
#      novo/performance_detail) + ads do GMV Max (live_sessao, casado por room_id). ROOT (não
#      dispara etl_sync). Deixa o painel dash.rhodejeans.com.br atual e com ROAS/ROI vivos.
echo "[15f] Painel dash-live (lives + ads via API)..."
python3 atualizar_painel_lives.py || echo "  ⚠ painel dash-live falhou (não-crítico — segue)"

# 15g) Tracker da meta 10 mil peças/mês por canal (origem × conteúdo, dedup cascata).
#      Usa live_attr + affiliate_perf + pedidos_sku (já coletados acima). Popula tracker_canais.
echo "[15g] Tracker meta 10k por canal..."
python3 tracker_canais.py || echo "  ⚠ tracker meta falhou (não-crítico — segue)"

# 15h) Liquidação por cor(lavagem)×canal na base settlement real (aba Liquidação SKU do console).
#      Usa conciliacao_pedido + extrato_pedidos + pedidos_sku + custos_sku (já coletados acima).
echo "[15h] Liquidação cor×canal (settlement real)..."
python3 liquidacao_cor_canal.py || echo "  ⚠ liquidação cor×canal falhou (não-crítico — segue)"

# 16) ETL sample_applications (free sample REAL — peças por creator × SKU + data do convite)
echo "[16/17] ETL sample_applications (free sample real)..."
python3 agente_rhode/etl_sample_applications.py || echo "  ⚠ ETL sample_applications falhou (não-crítico — segue)"

# 17) Sync → sample_applications
echo "[17/17] Sync → sample_applications..."
python3 -c "from dotenv import load_dotenv; load_dotenv(); import sys,runpy; sys.argv=['sync','--only','sample_applications']; runpy.run_path('agente_rhode/sync_supabase.py', run_name='__main__')" \
    || echo "  ⚠ SYNC sample_applications falhou (não-crítico — segue)"

echo "═════ Concluído — $(date '+%F %T') ═════"
