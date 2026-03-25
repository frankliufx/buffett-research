-- Buffett Research — Supabase 数据库建表脚本
-- 在 Supabase 控制台 SQL Editor 中执行此脚本
-- https://supabase.com → 你的项目 → SQL Editor → New query → 粘贴此内容 → Run

-- ── 用户关注列表 ────────────────────────────────────────────────────────────
create table if not exists user_watchlists (
  id          uuid        default gen_random_uuid() primary key,
  uid         text        not null,
  market      text        not null,  -- 'us' / 'hk' / 'a_share'
  symbol      text        not null,
  name        text        not null default '',
  created_at  timestamptz default now(),
  unique(uid, market, symbol)
);

-- ── 投资日志 ────────────────────────────────────────────────────────────────
create table if not exists user_journals (
  id          uuid        default gen_random_uuid() primary key,
  uid         text        not null,
  entry_type  text        not null default 'note',  -- 'decision' / 'review' / 'note'
  title       text        not null default '',
  content     text        not null default '',
  symbol      text                 default '',
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);

-- ── 用户个性化设置 ───────────────────────────────────────────────────────────
create table if not exists user_settings (
  uid           text        primary key,
  settings_json jsonb       not null default '{}',
  updated_at    timestamptz default now()
);

-- ── 行级安全 (RLS) ───────────────────────────────────────────────────────────
-- 使用 service_role key 时绕过 RLS，普通 anon key 则受限
alter table user_watchlists enable row level security;
alter table user_journals    enable row level security;
alter table user_settings    enable row level security;

-- 允许 service_role 完全访问（后端使用 service_role key）
create policy "service_role_all" on user_watchlists
  using (true) with check (true);

create policy "service_role_all" on user_journals
  using (true) with check (true);

create policy "service_role_all" on user_settings
  using (true) with check (true);

-- ── 索引（加速按用户查询）───────────────────────────────────────────────────
create index if not exists idx_watchlists_uid on user_watchlists(uid);
create index if not exists idx_journals_uid   on user_journals(uid);
create index if not exists idx_journals_uid_type on user_journals(uid, entry_type);
