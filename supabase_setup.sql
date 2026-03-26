-- ============================================================
-- AI Buffett — Supabase 数据库初始化脚本
-- 在 Supabase 后台 → SQL Editor 中执行此脚本
-- ============================================================

-- ── 1. 关注列表 ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_watchlists (
    id          bigserial PRIMARY KEY,
    uid         text NOT NULL,
    market      text NOT NULL,          -- 'us' | 'hk' | 'a_share'
    symbol      text NOT NULL,
    name        text NOT NULL DEFAULT '',
    created_at  timestamptz DEFAULT now(),
    UNIQUE (uid, market, symbol)
);
CREATE INDEX IF NOT EXISTS idx_watchlists_uid ON user_watchlists(uid);

-- ── 2. 投资日志 ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_journals (
    id          bigserial PRIMARY KEY,
    uid         text NOT NULL,
    date        text NOT NULL,          -- 'YYYY-MM-DD'
    title       text NOT NULL DEFAULT '',
    content     text NOT NULL DEFAULT '',
    mood        text NOT NULL DEFAULT '',
    tags        text NOT NULL DEFAULT '',
    created_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_journals_uid ON user_journals(uid);
CREATE INDEX IF NOT EXISTS idx_journals_date ON user_journals(uid, date DESC);

-- ── 3. 用户设置 ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_settings (
    uid             text PRIMARY KEY,
    settings_json   jsonb NOT NULL DEFAULT '{}',
    updated_at      timestamptz DEFAULT now()
);

-- ── 4. 持仓记录 ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_portfolio (
    id          bigserial PRIMARY KEY,
    uid         text NOT NULL,
    symbol      text NOT NULL,
    name        text NOT NULL DEFAULT '',
    market      text NOT NULL DEFAULT 'us',
    shares      float8 NOT NULL DEFAULT 0,
    cost_price  float8 NOT NULL DEFAULT 0,
    buy_date    text NOT NULL DEFAULT '',
    note        text NOT NULL DEFAULT '',
    created_at  timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_portfolio_uid ON user_portfolio(uid);

-- ── 5. 分析历史（飞轮核心）────────────────────────────────────
CREATE TABLE IF NOT EXISTS analysis_history (
    id                  bigserial PRIMARY KEY,
    uid                 text NOT NULL,
    symbol              text NOT NULL,
    market              text NOT NULL,
    name                text NOT NULL DEFAULT '',
    analyzed_at         timestamptz DEFAULT now(),
    price               float8,
    score_total         float8,
    score_earnings      float8,
    score_moat          float8,
    score_fortress      float8,
    score_growth        float8,
    score_opportunity   float8,
    grade               text NOT NULL DEFAULT '',
    verdict             text NOT NULL DEFAULT '',
    confidence          text NOT NULL DEFAULT '',
    roe                 float8,
    pe                  float8,
    profit_margin       float8
);
CREATE INDEX IF NOT EXISTS idx_analysis_uid ON analysis_history(uid);
CREATE INDEX IF NOT EXISTS idx_analysis_symbol ON analysis_history(uid, symbol, market);
CREATE INDEX IF NOT EXISTS idx_analysis_date ON analysis_history(uid, analyzed_at DESC);

-- ── 6. 投资论点（用户记忆层）─────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_thesis (
    uid             text NOT NULL,
    symbol          text NOT NULL,
    market          text NOT NULL,
    buy_thesis      text NOT NULL DEFAULT '',
    target_price    float8,
    risk_watch      text NOT NULL DEFAULT '',
    notes           text NOT NULL DEFAULT '',
    updated_at      timestamptz DEFAULT now(),
    PRIMARY KEY (uid, symbol, market)
);
CREATE INDEX IF NOT EXISTS idx_thesis_uid ON stock_thesis(uid);

-- ── 7. 目标价提醒（C 阶段新增）───────────────────────────────
CREATE TABLE IF NOT EXISTS price_alerts (
    id              bigserial PRIMARY KEY,
    uid             text NOT NULL,
    symbol          text NOT NULL,
    market          text NOT NULL,
    name            text NOT NULL DEFAULT '',
    alert_type      text NOT NULL DEFAULT 'below',  -- 'below' | 'above'
    target_price    float8 NOT NULL,
    triggered       boolean NOT NULL DEFAULT false,
    triggered_at    timestamptz,
    created_at      timestamptz DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_alerts_uid ON price_alerts(uid);
CREATE INDEX IF NOT EXISTS idx_alerts_active ON price_alerts(uid, triggered);

-- ============================================================
-- Row Level Security（推荐开启，保护多用户数据隔离）
-- 若 Supabase anon key 直连，强烈建议开启 RLS
-- ============================================================

-- ALTER TABLE user_watchlists  ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_journals    ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_settings    ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE user_portfolio   ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE analysis_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE stock_thesis     ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE price_alerts     ENABLE ROW LEVEL SECURITY;

-- 示例 RLS Policy（需要配合 Supabase Auth JWT，目前系统用自定义 auth 暂不需要）:
-- CREATE POLICY "users_own_data" ON user_watchlists
--   FOR ALL USING (uid = current_setting('app.current_uid', true));

-- ============================================================
-- 完成！共 7 张表。
-- ============================================================
