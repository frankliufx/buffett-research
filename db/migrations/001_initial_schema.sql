-- ============================================================================
-- Stock Analyst · Initial Schema (v1.0)
-- 设计原则: 稳定 / 真实 / 准确
--   - 稳定: BIGSERIAL 代理键 + 算法版本化 + migration 版本化
--   - 真实: raw_* 不可变层 + 每条数据带 source + 退市保留
--   - 准确: NUMERIC 精度 + TIMESTAMPTZ + UNIQUE 约束 + 多源对账
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 0. 迁移版本表
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ----------------------------------------------------------------------------
-- 1. 数据源注册（数据可信度的根基）
-- ----------------------------------------------------------------------------
CREATE TABLE data_sources (
    code            VARCHAR(20) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    base_url        TEXT,
    priority        INT NOT NULL DEFAULT 50,    -- 1=最优先, 100=最后兜底
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_health_check TIMESTAMPTZ,
    notes           TEXT
);

INSERT INTO data_sources (code, name, priority, notes) VALUES
    ('tencent',    '腾讯证券',           10, '行情主源，GBK 编码'),
    ('sina',       '新浪财经',           20, 'A 股财务指标 HTML 解析'),
    ('eastmoney',  '东方财富',           20, '美股/港股基本面 JSON API'),
    ('yfinance',   'Yahoo Finance',     30, '美股兜底'),
    ('fred',       'FRED',              40, '美国宏观');

-- ----------------------------------------------------------------------------
-- 2. 股票主数据（symbol 退市可能复用 → 用代理键）
-- ----------------------------------------------------------------------------
CREATE TABLE stocks (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(20)  NOT NULL,            -- '600519' / 'AAPL' / '00700'
    market          VARCHAR(20)  NOT NULL,            -- 'a_share' / 'us' / 'hk'
    exchange        VARCHAR(20),                       -- 'sh','sz','NYSE','NASDAQ','HKEX'
    name            VARCHAR(200) NOT NULL,
    name_en         VARCHAR(200),
    industry        VARCHAR(100),
    sector          VARCHAR(100),
    listing_date    DATE,
    delisting_date  DATE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_market CHECK (market IN ('a_share','us','hk'))
);

CREATE UNIQUE INDEX uq_stocks_active
    ON stocks (symbol, market) WHERE is_active = TRUE;
CREATE INDEX idx_stocks_industry ON stocks (industry);
CREATE INDEX idx_stocks_market ON stocks (market) WHERE is_active = TRUE;

-- ----------------------------------------------------------------------------
-- 3. 行情数据
-- ----------------------------------------------------------------------------

-- 3a. 原始行情 payload（不可变 audit log）
CREATE TABLE raw_quotes (
    id              BIGSERIAL PRIMARY KEY,
    stock_id        BIGINT      NOT NULL REFERENCES stocks(id),
    source          VARCHAR(20) NOT NULL REFERENCES data_sources(code),
    fetched_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw_payload     JSONB       NOT NULL
);
CREATE INDEX idx_raw_quotes_stock_time ON raw_quotes (stock_id, fetched_at DESC);
CREATE INDEX idx_raw_quotes_source_time ON raw_quotes (source, fetched_at DESC);

-- 3b. 实时行情快照（按 stock_id 唯一一行，每次更新覆盖）
CREATE TABLE quotes_latest (
    stock_id        BIGINT       PRIMARY KEY REFERENCES stocks(id),
    quote_ts        TIMESTAMPTZ  NOT NULL,           -- 价格时点
    price           NUMERIC(20, 4) NOT NULL,
    open            NUMERIC(20, 4),
    high            NUMERIC(20, 4),
    low             NUMERIC(20, 4),
    prev_close      NUMERIC(20, 4),
    change_pct      NUMERIC(10, 4),
    volume          BIGINT,
    turnover        NUMERIC(20, 2),
    market_cap      NUMERIC(20, 2),
    pe              NUMERIC(10, 4),
    pb              NUMERIC(10, 4),
    primary_source  VARCHAR(20)  NOT NULL REFERENCES data_sources(code),
    quality         VARCHAR(20)  NOT NULL DEFAULT 'single_source',
    fetched_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_quality CHECK (quality IN ('verified','single_source','stale','disagreement'))
);

-- 3c. 历史日线（每只股每天一条）
CREATE TABLE quotes_daily (
    stock_id        BIGINT       NOT NULL REFERENCES stocks(id),
    trade_date      DATE         NOT NULL,
    open            NUMERIC(20, 4),
    high            NUMERIC(20, 4),
    low             NUMERIC(20, 4),
    close           NUMERIC(20, 4) NOT NULL,
    volume          BIGINT,
    turnover        NUMERIC(20, 2),
    adj_factor      NUMERIC(10, 6),
    source          VARCHAR(20)  NOT NULL REFERENCES data_sources(code),
    fetched_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (stock_id, trade_date)
);
CREATE INDEX idx_quotes_daily_date ON quotes_daily (trade_date DESC);

-- ----------------------------------------------------------------------------
-- 4. 基本面数据（每个 source × period 各一条 → 多源对账）
-- ----------------------------------------------------------------------------

-- 4a. 原始财报 payload
CREATE TABLE raw_fundamentals (
    id              BIGSERIAL PRIMARY KEY,
    stock_id        BIGINT       NOT NULL REFERENCES stocks(id),
    source          VARCHAR(20)  NOT NULL REFERENCES data_sources(code),
    period          DATE         NOT NULL,           -- 报告期 2024-12-31
    period_type     VARCHAR(10)  NOT NULL,           -- 'Q1','Q2','Q3','Q4','annual','ttm'
    fetched_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    raw_payload     JSONB        NOT NULL,
    CONSTRAINT chk_period_type CHECK (
        period_type IN ('Q1','Q2','Q3','Q4','annual','ttm')
    )
);
CREATE INDEX idx_raw_fund_stock_period ON raw_fundamentals (stock_id, period DESC);

-- 4b. 标准化基本面（每个 source 一条）
CREATE TABLE fundamentals (
    id                 BIGSERIAL PRIMARY KEY,
    stock_id           BIGINT       NOT NULL REFERENCES stocks(id),
    period             DATE         NOT NULL,
    period_type        VARCHAR(10)  NOT NULL,
    source             VARCHAR(20)  NOT NULL REFERENCES data_sources(code),
    -- 盈利能力
    revenue            NUMERIC(20, 2),
    net_income         NUMERIC(20, 2),
    gross_profit       NUMERIC(20, 2),
    operating_income   NUMERIC(20, 2),
    eps                NUMERIC(10, 4),
    -- 比率
    roe                NUMERIC(10, 4),
    roa                NUMERIC(10, 4),
    gross_margin       NUMERIC(10, 4),
    operating_margin   NUMERIC(10, 4),
    net_margin         NUMERIC(10, 4),
    -- 财务结构
    total_assets       NUMERIC(20, 2),
    total_liabilities  NUMERIC(20, 2),
    total_equity       NUMERIC(20, 2),
    debt_to_equity     NUMERIC(10, 4),
    debt_ratio         NUMERIC(10, 4),
    current_ratio      NUMERIC(10, 4),
    quick_ratio        NUMERIC(10, 4),
    -- 成长
    revenue_growth     NUMERIC(10, 4),
    net_income_growth  NUMERIC(10, 4),
    -- 现金流
    operating_cash_flow NUMERIC(20, 2),
    free_cash_flow     NUMERIC(20, 2),
    capex              NUMERIC(20, 2),
    dividend_per_share NUMERIC(10, 4),
    -- 元数据
    quality            VARCHAR(20) NOT NULL DEFAULT 'single_source',
    confidence         INT         NOT NULL DEFAULT 50,
    notes              TEXT,
    fetched_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fund UNIQUE (stock_id, period, period_type, source),
    CONSTRAINT chk_fund_period_type CHECK (
        period_type IN ('Q1','Q2','Q3','Q4','annual','ttm')
    ),
    CONSTRAINT chk_fund_confidence CHECK (confidence BETWEEN 0 AND 100)
);
CREATE INDEX idx_fund_stock_period ON fundamentals (stock_id, period DESC);
CREATE INDEX idx_fund_period ON fundamentals (period DESC);

-- 4c. 多源共识视图（聚合分歧度）
CREATE OR REPLACE VIEW fundamentals_consensus AS
SELECT
    stock_id,
    period,
    period_type,
    -- 多源中位数
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY roe) AS roe,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY net_margin) AS net_margin,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY revenue) AS revenue,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY net_income) AS net_income,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY debt_ratio) AS debt_ratio,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY revenue_growth) AS revenue_growth,
    -- 分歧度
    COALESCE(STDDEV(roe), 0)        AS roe_disagreement,
    COALESCE(STDDEV(net_margin), 0) AS net_margin_disagreement,
    COUNT(DISTINCT source)          AS source_count,
    ARRAY_AGG(DISTINCT source ORDER BY source) AS sources,
    MAX(fetched_at)                 AS last_fetched_at
FROM fundamentals
GROUP BY stock_id, period, period_type;

-- ----------------------------------------------------------------------------
-- 5. 评分算法版本化
-- ----------------------------------------------------------------------------
CREATE TABLE scoring_algorithms (
    version         VARCHAR(20) PRIMARY KEY,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    weight_config   JSONB,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO scoring_algorithms (version, name, description, weight_config) VALUES
    ('v1.0', 'Buffett 5-Dimension', '初版巴菲特五维度评分',
     '{"profitability":0.25,"moat":0.25,"balance":0.20,"growth":0.15,"valuation":0.15}'::jsonb);

CREATE TABLE scores (
    id                  BIGSERIAL PRIMARY KEY,
    stock_id            BIGINT      NOT NULL REFERENCES stocks(id),
    score_date          DATE        NOT NULL,
    algorithm_version   VARCHAR(20) NOT NULL REFERENCES scoring_algorithms(version),
    profitability_score NUMERIC(5, 2),
    moat_score          NUMERIC(5, 2),
    balance_sheet_score NUMERIC(5, 2),
    growth_score        NUMERIC(5, 2),
    valuation_score     NUMERIC(5, 2),
    total_score         NUMERIC(5, 2),
    rationale           JSONB,                        -- 每个维度的评分理由
    inputs_snapshot     JSONB,                        -- 计算时使用的输入数据快照
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_scores UNIQUE (stock_id, score_date, algorithm_version),
    CONSTRAINT chk_score_range CHECK (
        (profitability_score IS NULL OR profitability_score BETWEEN 0 AND 100) AND
        (moat_score IS NULL OR moat_score BETWEEN 0 AND 100) AND
        (balance_sheet_score IS NULL OR balance_sheet_score BETWEEN 0 AND 100) AND
        (growth_score IS NULL OR growth_score BETWEEN 0 AND 100) AND
        (valuation_score IS NULL OR valuation_score BETWEEN 0 AND 100) AND
        (total_score IS NULL OR total_score BETWEEN 0 AND 100)
    )
);
CREATE INDEX idx_scores_stock_date ON scores (stock_id, score_date DESC);
CREATE INDEX idx_scores_total ON scores (total_score DESC) WHERE algorithm_version = 'v1.0';

-- ----------------------------------------------------------------------------
-- 6. 数据源健康监控（数据可信度）
-- ----------------------------------------------------------------------------
CREATE TABLE fetch_audit (
    id              BIGSERIAL PRIMARY KEY,
    source          VARCHAR(20)  NOT NULL REFERENCES data_sources(code),
    endpoint        TEXT         NOT NULL,
    stock_id        BIGINT       REFERENCES stocks(id),
    success         BOOLEAN      NOT NULL,
    duration_ms     INT,
    http_status     INT,
    error_message   TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_source_time ON fetch_audit (source, created_at DESC);
CREATE INDEX idx_audit_failures ON fetch_audit (created_at DESC) WHERE success = FALSE;

-- ----------------------------------------------------------------------------
-- 7. 用户关注列表（多用户预留，当前只有你一人）
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    username        VARCHAR(50) UNIQUE NOT NULL,
    display_name    VARCHAR(100),
    is_admin        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO users (username, display_name, is_admin) VALUES
    ('frank', 'Frank Liu', TRUE);

CREATE TABLE watchlists (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT      NOT NULL REFERENCES users(id),
    stock_id        BIGINT      NOT NULL REFERENCES stocks(id),
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_watchlist UNIQUE (user_id, stock_id)
);
CREATE INDEX idx_watchlists_user ON watchlists (user_id);

-- ----------------------------------------------------------------------------
-- 8. 自动更新 updated_at 触发器
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_timestamp_stocks
    BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION trigger_set_timestamp();

-- ----------------------------------------------------------------------------
-- 完成
-- ----------------------------------------------------------------------------
INSERT INTO schema_migrations (version, description) VALUES
    ('001', 'Initial schema: stocks, quotes, fundamentals, scores, watchlists');

COMMIT;
