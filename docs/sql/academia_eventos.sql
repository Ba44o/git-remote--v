-- Tracker de uso da Academia (Rhode Creators)
-- Rodar UMA vez no Supabase → SQL Editor. Só o service key (server, api/relay.js) grava.
create table if not exists public.academia_eventos (
  id       bigint generated always as identity primary key,
  ts       timestamptz not null default now(),
  evento   text not null,   -- abriu_pagina | abriu_modulo | concluiu_aula | baixou_template | abriu_drive | clicou_campeao
  modulo   text,            -- id do modulo/aula (quando aplicavel)
  creator  text,            -- handle se veio do Hub (?c=handle); senao null
  sess     text,            -- id anonimo de sessao (localStorage)
  ref      text             -- referrer / hash / handle do campeao
);
create index if not exists academia_eventos_ts_idx    on public.academia_eventos (ts desc);
create index if not exists academia_eventos_evento_idx on public.academia_eventos (evento);
-- RLS ligado SEM policy: anon nao le nem escreve; service key (server) ignora RLS e grava.
alter table public.academia_eventos enable row level security;
