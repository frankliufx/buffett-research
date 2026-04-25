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
