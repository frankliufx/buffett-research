-- ============================================================================
-- Stock Analyst · Hedge Fund Decisions (v1.1)
-- 设计原则: 稳定 / 真实 / 准确
--   - 稳定: 与 stocks 主键 FK 关联，algorithm_version 字段便于回归
--   - 真实: 投票/新闻/风险/最终决策原始 JSONB 全量保留
--   - 准确: NUMERIC 精度，TIMESTAMPTZ，唯一索引避免重复落库
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- hedge_fund_decisions: 每次 run_full_workflow 落一行
-- ----------------------------------------------------------------------------
CREATE TABLE hedge_fund_decisions (
    id                  BIGSERIAL PRIMARY KEY,
    stock_id            BIGINT       NOT NULL REFERENCES stocks(id),
    decided_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- 现价快照（决策当下）
    price               NUMERIC(20,4) NOT NULL,

    -- 13 大师投票
    analyst_ids         TEXT[]        NOT NULL,           -- 选中的 analyst id 列表
    bullish_count       INT           NOT NULL DEFAULT 0,
    bearish_count       INT           NOT NULL DEFAULT 0,
    neutral_count       INT           NOT NULL DEFAULT 0,
    weighted_score      NUMERIC(6,2),                     -- -100..+100
    consensus_signal    VARCHAR(20),                      -- bullish/bearish/neutral
    consensus_verdict   VARCHAR(40),                      -- 强烈看多/看多/...
    unanimity           VARCHAR(20),                      -- 高度一致/多数一致/分歧明显
    votes_payload       JSONB         NOT NULL,           -- 每位大师的 signal/confidence/reasoning

    -- 新闻情绪
    news_score          INT,                              -- -100..+100
    news_label          VARCHAR(20),
    news_article_count  INT           NOT NULL DEFAULT 0,
    news_payload        JSONB,                            -- 完整 NewsSentiment dict

    -- 风险评估
    annual_vol_pct      NUMERIC(6,2),
    risk_regime         VARCHAR(40),
    risk_level          VARCHAR(20),
    max_position_pct    NUMERIC(5,2),
    risk_payload        JSONB,

    -- Portfolio Manager 最终决策
    action              VARCHAR(20)   NOT NULL,           -- 买入/加仓/持有/减仓/卖出
    conviction          VARCHAR(10)   NOT NULL,           -- 高/中/低
    combined_score      INT           NOT NULL,           -- -100..+100
    position_pct        NUMERIC(5,2),
    horizon             VARCHAR(40),
    entry_payload       JSONB,                            -- {ideal, acceptable, expensive_above, anchor}
    stop_loss_payload   JSONB,                            -- {price, drop_pct, rationale}
    take_profit_payload JSONB,                            -- {price, rationale}
    reasoning           TEXT,                             -- LLM-generated 推理链

    -- 元数据
    algorithm_version   VARCHAR(20)   NOT NULL DEFAULT 'v1.0',
    provider_name       VARCHAR(40),                      -- 调用的 LLM provider
    extra               JSONB,                            -- 兼容字段

    CONSTRAINT chk_action CHECK (action IN ('买入','加仓','持有','减仓','卖出')),
    CONSTRAINT chk_conviction CHECK (conviction IN ('高','中','低')),
    CONSTRAINT chk_combined_score CHECK (combined_score BETWEEN -100 AND 100)
);

CREATE INDEX idx_hf_decisions_stock_time ON hedge_fund_decisions (stock_id, decided_at DESC);
CREATE INDEX idx_hf_decisions_action ON hedge_fund_decisions (action, decided_at DESC);
CREATE INDEX idx_hf_decisions_time ON hedge_fund_decisions (decided_at DESC);

-- ----------------------------------------------------------------------------
-- 视图：最近一次决策（每只股票）
-- ----------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_latest_hedge_fund_decisions AS
SELECT DISTINCT ON (s.id)
    s.symbol,
    s.market,
    s.name,
    d.decided_at,
    d.price,
    d.action,
    d.conviction,
    d.combined_score,
    d.position_pct,
    d.consensus_verdict,
    d.unanimity,
    d.news_label,
    d.risk_level,
    d.horizon,
    d.id AS decision_id
FROM stocks s
JOIN hedge_fund_decisions d ON d.stock_id = s.id
ORDER BY s.id, d.decided_at DESC;

-- ----------------------------------------------------------------------------
-- 完成
-- ----------------------------------------------------------------------------
INSERT INTO schema_migrations (version, description) VALUES
    ('002', 'Hedge fund decisions: votes/news/risk/final action persistence');

COMMIT;
