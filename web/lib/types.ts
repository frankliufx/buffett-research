export type Signal = "bullish" | "bearish" | "neutral"

export interface StockData {
  ticker: string
  market: string
  name: string
  price: number
  change_pct: number | null
  normalized: Record<string, number | null>
  buffett: Record<string, unknown>
  moat: { percentage: number; grade: string; dimensions?: unknown[] }
  dcf: { intrinsic_value?: number; safety_margin_pct?: number; method?: string }
  tech: { trend?: string; momentum?: string; rsi?: number; macd?: number }
}

export interface Analyst {
  id: string
  name: string
  name_cn: string
  icon: string
  group: string
  style: string
}

export interface AnalystResult extends Analyst {
  signal: Signal
  confidence: number
  reasoning: string
  error: string | null
}

export interface HedgeFundResult {
  symbol: string
  analysts: AnalystResult[]
  consensus: {
    signal: Signal
    verdict: string
    unanimity: string
    confidence: number
  }
  weighted_score: number
  bullish_count: number
  bearish_count: number
  neutral_count: number
}

// SSE stream events
export type StreamEvent =
  | { event: "step";        data: { step: string; msg: string } }
  | { event: "quote";       data: { ticker: string; name: string; price: number } }
  | { event: "fundamentals";data: { normalized: Record<string, number | null> } }
  | { event: "technical";   data: { tech: Record<string, unknown>; ensemble: unknown } }
  | { event: "valuation";   data: { buffett: unknown; moat: unknown; dcf: unknown; multi_val: unknown } }
  | { event: "risk";        data: { volatility: unknown; position: unknown; risk_report: unknown } }
  | { event: "ai";          data: { summary: string } }
  | { event: "ai_error";    data: { msg: string } }
  | { event: "error";       data: { msg: string } }
  | { event: "done";        data: { msg: string } }
