# Stock Analyst · Database Schema 设计说明

> 版本 v1.0 · 2026-04-29
> 设计原则：**稳定 / 真实 / 准确**
> 迁移文件：[db/migrations/001_initial_schema.sql](../db/migrations/001_initial_schema.sql)

---

## 三大原则如何落地

### 1. 稳定（Stability）

| 设计 | 原因 |
|------|------|
| `BIGSERIAL` 代理键替代业务键 | A 股退市 symbol 会回收（如新世界 600628 退市后 symbol 复用），用业务键作 PK 会撞 |
| `schema_migrations` 表 | 任何 schema 变更走 SQL 文件版本化，可重放 |
| `scoring_algorithms` 版本表 | 评分算法迭代时旧分数仍可查（v1.0 vs v1.1 对比） |
| `is_active` + `delisting_date` 软删除 | 退市股保留历史，不真删 |

### 2. 真实（Truthfulness）

| 设计 | 原因 |
|------|------|
| `raw_quotes` / `raw_fundamentals` 不可变层 | 抓到的原始 payload 永不修改、永不删除，万一解析逻辑写错可重放 |
| 每条标准化数据带 `source` | 不掩盖来源，雪球一个值新浪一个值都各自存 |
| `fundamentals_consensus` 视图 | 自动暴露多源分歧 → UI 可显示「3 源一致 ✓」或「源间分歧 ⚠」 |
| `fetch_audit` 表 | 每次抓取记录成功率/延时，监控数据源质量 |
| `quality` 字段（'verified'/'single_source'/'stale'/'disagreement'） | 让前端知道这条数据有多可信 |

### 3. 准确（Accuracy）

| 设计 | 原因 |
|------|------|
| 金额一律 `NUMERIC(20,2)` 或 `(20,4)` | FLOAT 有精度损失（0.1+0.2≠0.3），财务数据不能容忍 |
| 时间一律 `TIMESTAMPTZ` | 避免「这个 timestamp 是哪个时区」的踩坑 |
| `CHECK` 约束（评分 0-100、period_type 枚举） | 数据库级别拦截脏数据 |
| `UNIQUE` 约束（`stock_id, period, source`） | 同一报告期同一源不会有重复记录 |
| 触发器 `updated_at` 自动维护 | 不依赖应用代码记得更新 |

---

## 表清单（14 项）

```
元数据 (3)            主数据 (1)         行情 (3)
├─ schema_migrations  └─ stocks         ├─ raw_quotes
├─ data_sources                          ├─ quotes_latest
└─ scoring_algorithms                    └─ quotes_daily

基本面 (3)            评分 (1)          监控/用户 (3)
├─ raw_fundamentals   └─ scores         ├─ fetch_audit
├─ fundamentals                          ├─ users
└─ fundamentals_consensus (view)         └─ watchlists
```

---

## 关键设计决策

### 为什么用代理键（BIGSERIAL）而不是 (symbol, market) 复合主键？

**Bug 案例**：A 股 600628 「新世界」2022 年退市，symbol 进入回收池，未来可能被新公司复用。
如果用业务键作 PK，关联表（quotes、fundamentals、scores）的历史数据会和新公司的数据混在一起。

**解法**：用代理键 `stocks.id`，业务键加 `is_active=TRUE` 部分唯一索引。退市后 `is_active=FALSE`，新公司可以再 INSERT 一条 `is_active=TRUE`。

### 为什么 raw_* 表保留原始 payload？

**Bug 案例**：新浪财务页 HTML 改版，解析出来 ROE 字段错位，但所有股票评分都已经基于错误 ROE 写入了 fundamentals 表。

**解法**：raw_fundamentals 存的是抓回来的原始 HTML（或 JSON），即使解析逻辑错了，修好后可以从 raw 重新生成 fundamentals，不丢任何数据。

### 为什么 fundamentals 一只股一个报告期会有多条？

**真实需求**：用户看 ROE 时希望知道「腾讯说 26.3%、新浪说 26.3%、东财说 25.8%」——多源一致才放心。
所以每个 source 各写一条，UI 通过 `fundamentals_consensus` 视图聚合，并显示分歧度。

### 为什么评分要算法版本化？

**未来需求**：v1.0 的评分权重可能不准，v1.1 会调整。如果直接覆盖，回测失效（无法对比新旧算法在同一段时间的表现差异）。
所以 `scores` 表按 `(stock_id, score_date, algorithm_version)` 唯一，每个版本各存一份。

### `inputs_snapshot` 字段的意义

每次评分把当时使用的输入数据（哪条 fundamentals 记录、哪条 quotes）快照成 JSONB 存下来。
半年后回看：「这个分数是基于什么数据算出来的？」可以一查到底，避免「数据被覆盖了，无法重现」的尴尬。

---

## 数据流向

```
[外部 API: 腾讯/新浪/东财]
          │ fetch + 重试 + audit
          ▼
   raw_quotes / raw_fundamentals    ← 不可变层
          │ 解析 + 标准化
          ▼
   quotes_* / fundamentals          ← 业务层（多源对账）
          │ 共识聚合
          ▼
   fundamentals_consensus (view)    ← 给评分算法用
          │ 巴菲特五维度计算
          ▼
   scores (按算法版本)              ← 给前端展示
```

---

## 后续迁移

新增字段或表 → 在 `db/migrations/` 下加 `002_xxx.sql`，运行 `python db/run_migrations.py`。

**永远只新增 migration，不修改已应用的旧 migration**。
