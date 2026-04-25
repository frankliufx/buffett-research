/**
 * Public type surface for the Next.js app.
 *
 * Most interfaces are auto-generated from `schemas/` (Pydantic v2) — see
 * `types.generated.ts`. This file:
 *   1. Re-exports the generated types so callers `import { StockData } from "./types"`.
 *   2. Adds the `Signal` alias used across the UI.
 *   3. Hand-assembles the `StreamEvent` discriminated union (event-name
 *      literals come from FastAPI's `_sse(event, ...)` calls — see
 *      `api/routes/analysis.py`).
 *
 * To regenerate the auto part: `make types` (from project root).
 */

import type {
  AISummaryPayload,
  FundamentalsPayload,
  MessagePayload,
  QuotePayload,
  RiskPayload,
  StepPayload,
  TechnicalPayload,
  ValuationPayload,
} from "./types.generated"

// Re-export the full generated surface so consumers have one import path.
export type {
  AISummaryPayload,
  Analyst,
  AnalystResult,
  DCFResult,
  FundamentalsPayload,
  HedgeFundConsensus,
  HedgeFundResult,
  HedgeFundRunRequest,
  MessagePayload,
  MoatDimension,
  MoatScore,
  Quote,
  QuotePayload,
  RiskPayload,
  StepPayload,
  StockData,
  TechSignal,
  TechnicalPayload,
  ValuationPayload,
} from "./types.generated"

/** Verdict polarity used across signal badges and consensus cards. */
export type Signal = "bullish" | "bearish" | "neutral"

/**
 * SSE events emitted by `GET /api/analysis/{ticker}/stream`.
 *
 * Event-name literals must stay in sync with `_sse(event, ...)` calls
 * in `api/routes/analysis.py`. Payload shapes come from `schemas/stream.py`.
 */
export type StreamEvent =
  | { event: "step";         data: StepPayload }
  | { event: "quote";        data: QuotePayload }
  | { event: "fundamentals"; data: FundamentalsPayload }
  | { event: "technical";    data: TechnicalPayload }
  | { event: "valuation";    data: ValuationPayload }
  | { event: "risk";         data: RiskPayload }
  | { event: "ai";           data: AISummaryPayload }
  | { event: "ai_error";     data: MessagePayload }
  | { event: "error";        data: MessagePayload }
  | { event: "done";         data: MessagePayload }
