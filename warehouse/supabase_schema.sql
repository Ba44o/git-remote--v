-- Rhode Jeans · Supabase Schema
-- Execute em: supabase.com → SQL Editor → New Query

-- ── affiliates ────────────────────────────────────────────────
create table if not exists affiliates (
  affiliate_id          text primary key,
  name                  text,
  tiktok_handle         text,
  phone                 text,
  email                 text,
  current_tier          text default 'starter',
  tier_live             text default 'starter',
  tier_video            text default 'starter',
  total_points          numeric default 0,
  points_live           numeric default 0,
  points_video          numeric default 0,
  gmv_live_mtd          numeric default 0,
  gmv_video_mtd         numeric default 0,
  live_hours_mtd        numeric default 0,
  live_sessions_mtd     int default 0,
  videos_published_mtd  int default 0,
  conversion_rate_live  numeric default 0,
  conversion_rate_video numeric default 0,
  last_updated_at       timestamptz default now()
);

-- ── sales ─────────────────────────────────────────────────────
create table if not exists sales (
  sale_id           text primary key,
  affiliate_id      text references affiliates(affiliate_id),
  campaign_id       text,
  sku_id            text,
  product_name      text,
  gmv_brl           numeric default 0,
  quantity          int default 1,
  sale_timestamp    timestamptz,
  sale_format       text default 'shoppable_video',
  is_flash_sale     boolean default false,
  flash_multiplier  numeric default 1.0,
  base_points       numeric default 0,
  points_earned     numeric default 0,
  imported_at       timestamptz default now()
);

-- ── campaigns ─────────────────────────────────────────────────
create table if not exists campaigns (
  campaign_id              text primary key default gen_random_uuid()::text,
  campaign_name            text,
  sku_id                   text,
  original_price_brl       numeric,
  live_price_brl           numeric,
  discount_pct             numeric generated always as (
    case when original_price_brl > 0
    then round((1 - live_price_brl/original_price_brl)*100, 2)
    else 0 end
  ) stored,
  start_datetime           timestamptz,
  end_datetime             timestamptz,
  duration_minutes         int generated always as (
    extract(epoch from (end_datetime - start_datetime))::int / 60
  ) stored,
  stock_allocated          int default 0,
  stock_remaining          int default 0,
  sell_through_rate        numeric default 0,
  units_per_minute         numeric default 0,
  point_multiplier         numeric default 1.0,
  campaign_type            text default 'flash_15min',
  status                   text default 'draft',
  gmv_realized             numeric default 0,
  orders_count             int default 0,
  active_affiliates_count  int default 0,
  roi_score                numeric default 0,
  created_at               timestamptz default now(),
  updated_at               timestamptz default now()
);

-- ── tier_history ──────────────────────────────────────────────
create table if not exists tier_history (
  log_id               bigint generated always as identity primary key,
  affiliate_id         text references affiliates(affiliate_id),
  tier_from            text,
  tier_to              text,
  track                text,
  evaluation_date      date default current_date,
  gmv_at_evaluation    numeric,
  hours_at_evaluation  numeric,
  videos_at_evaluation int
);

-- ── leaderboard_snapshots ─────────────────────────────────────
create table if not exists leaderboard_snapshots (
  snapshot_id    bigint generated always as identity primary key,
  period         text,
  track          text,
  affiliate_id   text references affiliates(affiliate_id),
  rank_position  int,
  gmv_period     numeric,
  points_period  numeric,
  created_at     timestamptz default now()
);

-- ── performance_periods (warehouse histórico) ─────────────────
create table if not exists performance_periods (
  id              bigint generated always as identity primary key,
  affiliate_id    text references affiliates(affiliate_id),
  periodo         text,
  periodo_inicio  date,
  periodo_fim     date,
  gmv_bruto       numeric default 0,
  gmv_liquido     numeric default 0,
  reembolso       numeric default 0,
  refund_pct      numeric default 0,
  pedidos         int default 0,
  aov             numeric default 0,
  videos          int default 0,
  lives           int default 0,
  comissao        numeric default 0,
  tier            text,
  unique(affiliate_id, periodo)
);

-- ── Índices ───────────────────────────────────────────────────
create index if not exists idx_sales_affiliate    on sales(affiliate_id);
create index if not exists idx_sales_timestamp    on sales(sale_timestamp);
create index if not exists idx_sales_campaign     on sales(campaign_id);
create index if not exists idx_perf_affiliate     on performance_periods(affiliate_id);
create index if not exists idx_perf_periodo       on performance_periods(periodo);
create index if not exists idx_leaderboard_period on leaderboard_snapshots(period, track);

-- ── RLS (Row Level Security) ──────────────────────────────────
alter table affiliates            enable row level security;
alter table sales                 enable row level security;
alter table campaigns             enable row level security;
alter table tier_history          enable row level security;
alter table leaderboard_snapshots enable row level security;
alter table performance_periods   enable row level security;

-- Política de leitura pública (ajuste conforme necessário)
create policy "read_all" on affiliates            for select using (true);
create policy "read_all" on sales                 for select using (true);
create policy "read_all" on campaigns             for select using (true);
create policy "read_all" on tier_history          for select using (true);
create policy "read_all" on leaderboard_snapshots for select using (true);
create policy "read_all" on performance_periods   for select using (true);
