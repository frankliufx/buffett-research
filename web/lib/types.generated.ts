/* tslint:disable */
/* eslint-disable */
/**
/* This file was automatically generated from pydantic models by running pydantic2ts.
/* Do not modify it by hand - just update the pydantic models and then re-run the script
*/

export interface AISummaryPayload {
  summary: string;
  [k: string]: unknown;
}
export interface Analyst {
  id: string;
  name: string;
  name_cn: string;
  icon: string;
  group: string;
  style: string;
  [k: string]: unknown;
}
export interface AnalystResult {
  id: string;
  name: string;
  name_cn: string;
  icon: string;
  group: string;
  style: string;
  signal: "bullish" | "bearish" | "neutral";
  confidence: number;
  reasoning: string;
  error?: string | null;
  [k: string]: unknown;
}
export interface DCFResult {
  intrinsic_value?: number | null;
  safety_margin_pct?: number | null;
  method?: string | null;
  [k: string]: unknown;
}
export interface FundamentalsPayload {
  normalized?: {
    [k: string]: number | null;
  };
  [k: string]: unknown;
}
export interface HedgeFundConsensus {
  signal: "bullish" | "bearish" | "neutral";
  verdict: string;
  unanimity: string;
  confidence: number;
  [k: string]: unknown;
}
export interface HedgeFundResult {
  symbol: string;
  analysts: AnalystResult[];
  consensus: HedgeFundConsensus;
  weighted_score: number;
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
  [k: string]: unknown;
}
/**
 * Request body for POST /api/hedge-fund/run.
 */
export interface HedgeFundRunRequest {
  ticker: string;
  market?: string;
  analyst_ids?: string[] | null;
}
/**
 * 三档周期信号灯（替代单点判断），用于 UI 信号灯渲染。
 *
 * 每档表示一个时间窗口的信号强度：
 *   - past:    回看近期催化是否仍在窗口内
 *   - current: 当前周期阶段的强度
 *   - future:  下次窗口接近度
 * 每档 0/1/2 → 灯色 灰/黄/绿（退坡期会变红）。
 */
export interface LifecycleSignal {
  past?: number;
  current?: number;
  future?: number;
  label?: string;
  color?: string;
  [k: string]: unknown;
}
/**
 * Generic single-message payload used by `error`, `ai_error`, `done`.
 */
export interface MessagePayload {
  msg: string;
  [k: string]: unknown;
}
export interface MoatDimension {
  name?: string | null;
  score?: number | null;
  weight?: number | null;
  notes?: string | null;
  [k: string]: unknown;
}
export interface MoatScore {
  percentage?: number;
  grade?: string;
  dimensions?: MoatDimension[];
  [k: string]: unknown;
}
/**
 * 单只股票的主题对齐汇总（取代旧的 dict 返回值）。
 */
export interface PolicyAlignment {
  symbol: string;
  /**
   * 0-100 综合对齐分（详见 policy_themes.score()）
   */
  score: number;
  level: "核心主线" | "受益方向" | "暂无明显政策主题";
  matches?: PolicyThemeMatch[];
  /**
   * 股票所属概念板块原始列表（含非政策类）
   */
  raw_concepts?: string[];
  [k: string]: unknown;
}
/**
 * 单个主题对单只股票的匹配结果（带匹配证据）。
 */
export interface PolicyThemeMatch {
  theme_id: string;
  theme_name: string;
  tier: 1 | 2 | 3;
  phase: "蓄势期" | "爆发期" | "退坡期" | "未知";
  /**
   * 该股票命中的具体概念板块名称
   */
  matched_concepts?: string[];
  matched_keywords?: string[];
  [k: string]: unknown;
}
/**
 * 主题在政策周期中的位置（人工标注，季度 review）。
 */
export interface PolicyLifecycle {
  phase?: "蓄势期" | "爆发期" | "退坡期" | "未知";
  since?: string | null;
  /**
   * 最近一次最高级别政策表态（部委文件/中央会议/国务院常务会议）
   */
  last_catalyst?: string | null;
  /**
   * 下一次预期催化窗口（下次部委部署/规划落地节点）
   */
  next_window?: string | null;
  /**
   * 预期退坡时点（补贴退出/政策周期收尾）
   */
  decay_after?: string | null;
  notes?: string | null;
  [k: string]: unknown;
}
/**
 * 单个政策主题的完整画像（来自 YAML）。
 */
export interface PolicyTheme {
  /**
   * 稳定 slug — 不要改，会被 git 历史依赖
   */
  id: string;
  /**
   * 主题中文名 — 会在 UI 卡片标题展示
   */
  name: string;
  plan: "十四五" | "十五五";
  /**
   * 上位主线（如：新质生产力、安全自主可控）
   */
  pillar: string;
  tier: 1 | 2 | 3;
  lifecycle?: PolicyLifecycle;
  /**
   * 用于匹配概念板块的关键词（粗匹配，子串包含即命中）
   */
  keywords?: string[];
  /**
   * 申万二级行业名（用于按行业反查）
   */
  related_industries?: string[];
  [k: string]: unknown;
}
export interface Quote {
  ticker: string;
  name: string;
  price: number;
  change_pct?: number | null;
  market?: "US" | "CN" | "HK";
  [k: string]: unknown;
}
export interface QuotePayload {
  ticker: string;
  name: string;
  price: number;
  [k: string]: unknown;
}
export interface RiskPayload {
  volatility?: unknown;
  position?: unknown;
  risk_report?: unknown;
  [k: string]: unknown;
}
export interface StepPayload {
  step: string;
  msg: string;
  [k: string]: unknown;
}
export interface StockData {
  ticker: string;
  market: "US" | "CN" | "HK";
  name: string;
  price: number;
  change_pct?: number | null;
  normalized?: {
    [k: string]: number | null;
  };
  buffett?: {
    [k: string]: unknown;
  };
  moat?: MoatScore;
  dcf?: DCFResult;
  tech?: TechSignal;
  [k: string]: unknown;
}
export interface TechSignal {
  trend?: string | null;
  momentum?: string | null;
  rsi?: number | null;
  macd?: number | null;
  [k: string]: unknown;
}
export interface TechnicalPayload {
  tech?: {
    [k: string]: unknown;
  };
  ensemble?: unknown;
  [k: string]: unknown;
}
export interface ValuationPayload {
  buffett?: {
    [k: string]: unknown;
  };
  moat?: {
    [k: string]: unknown;
  };
  dcf?: {
    [k: string]: unknown;
  };
  multi_val?: unknown;
  [k: string]: unknown;
}
