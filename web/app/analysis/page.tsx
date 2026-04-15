"use client"

import { useState, useCallback, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { streamAnalysis } from "@/lib/api"
import { SignalBadge } from "@/components/SignalBadge"
import type { StreamEvent } from "@/lib/types"

type StepKey = "quote" | "fundamentals" | "technical" | "valuation" | "risk" | "ai"

const STEPS: { key: StepKey; label: string }[] = [
  { key: "quote",        label: "行情数据" },
  { key: "fundamentals", label: "基本面" },
  { key: "technical",    label: "技术指标" },
  { key: "valuation",    label: "估值模型" },
  { key: "risk",         label: "风险评估" },
  { key: "ai",           label: "AI 综合" },
]

function fmt(v: number | null | undefined, pct = false) {
  if (v == null) return "—"
  return pct ? `${v.toFixed(1)}%` : v.toFixed(2)
}

function AnalysisContent() {
  const params = useSearchParams()
  const [ticker, setTicker] = useState(params.get("ticker") ?? "")
  const [market, setMarket] = useState(params.get("market") ?? "US")
  const [running, setRunning] = useState(false)
  const [done, setDone] = useState(false)
  const [steps, setSteps] = useState<Partial<Record<StepKey, "pending" | "running" | "done">>>({})
  const [data, setData] = useState<Record<string, unknown>>({})
  const [aiText, setAiText] = useState("")
  const [error, setError] = useState("")

  const run = useCallback(async () => {
    if (!ticker) return
    setRunning(true)
    setDone(false)
    setSteps({})
    setData({})
    setAiText("")
    setError("")

    try {
      for await (const evt of streamAnalysis(ticker.toUpperCase(), market)) {
        const e = evt as StreamEvent
        switch (e.event) {
          case "step":
            setSteps(s => ({ ...s, [e.data.step as StepKey]: "running" }))
            break
          case "quote":
          case "fundamentals":
          case "technical":
          case "valuation":
          case "risk":
            setData(d => ({ ...d, [e.event]: e.data }))
            setSteps(s => ({ ...s, [e.event]: "done" }))
            break
          case "ai":
            setAiText(e.data.summary)
            setSteps(s => ({ ...s, ai: "done" }))
            break
          case "ai_error":
            setSteps(s => ({ ...s, ai: "done" }))
            break
          case "error":
            setError(e.data.msg)
            break
          case "done":
            setDone(true)
            break
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "请求失败")
    } finally {
      setRunning(false)
    }
  }, [ticker, market])

  const quote = data.quote as { name?: string; price?: number } | undefined
  const norm = (data.fundamentals as { normalized?: Record<string, number | null> })?.normalized
  const tech = (data.technical as { tech?: Record<string, unknown> })?.tech
  const val = data.valuation as {
    moat?: { percentage?: number; grade?: string }
    dcf?: { intrinsic_value?: number; safety_margin_pct?: number }
    multi_val?: { weighted_intrinsic_value?: number; weighted_safety_margin_pct?: number; verdict?: string }
  } | undefined
  const risk = data.risk as {
    volatility?: { annual_vol_pct?: number; regime?: string }
    position?: { max_position_pct?: number }
    risk_report?: { risk_score?: number; recommendations?: string[] }
  } | undefined

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h2 className="serif text-2xl font-light tracking-[4px] mb-1"
          style={{ color: "var(--gold)" }}>ANALYSIS</h2>
        <p className="text-[0.6rem] tracking-[4px] uppercase" style={{ color: "var(--text-muted)" }}>
          流式 AI 分析 · 实时输出
        </p>
      </div>

      {/* Input bar */}
      <div className="flex gap-3 mb-8">
        <input
          value={ticker}
          onChange={e => setTicker(e.target.value.toUpperCase())}
          onKeyDown={e => e.key === "Enter" && run()}
          placeholder="股票代码  AAPL / 600519"
          className="w-48 px-4 py-2.5 text-sm rounded outline-none"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text)" }}
        />
        <select
          value={market}
          onChange={e => setMarket(e.target.value)}
          className="px-3 py-2.5 text-sm rounded outline-none"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text)" }}
        >
          <option value="US">美股</option>
          <option value="CN">A股</option>
          <option value="HK">港股</option>
        </select>
        <button
          onClick={run}
          disabled={running || !ticker}
          className="px-6 py-2.5 text-sm font-medium rounded transition-opacity disabled:opacity-40"
          style={{ background: "rgba(201,169,98,0.15)", border: "1px solid var(--border)", color: "var(--gold)" }}
        >
          {running ? "分析中..." : "开始分析 →"}
        </button>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded text-sm text-[#F44336]"
          style={{ background: "rgba(244,67,54,0.08)", border: "1px solid rgba(244,67,54,0.2)" }}>
          {error}
        </div>
      )}

      {/* Progress steps */}
      {(running || done) && (
        <div className="flex gap-2 mb-6 flex-wrap">
          {STEPS.map(({ key, label }) => {
            const st = steps[key]
            return (
              <div
                key={key}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[0.6rem]"
                style={{
                  background: "var(--bg-card)",
                  border: `1px solid ${st === "done" ? "rgba(201,169,98,0.3)" : st === "running" ? "rgba(201,169,98,0.15)" : "var(--border)"}`,
                  color: st === "done" ? "var(--gold)" : st === "running" ? "var(--text)" : "var(--text-muted)",
                }}
              >
                {st === "running" && (
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#C9A962] animate-pulse" />
                )}
                {st === "done" && <span className="text-[#C9A962]">✓</span>}
                {!st && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#2A2A36]" />}
                {label}
              </div>
            )
          })}
        </div>
      )}

      {/* Results grid */}
      {done && (
        <div className="space-y-4">
          {/* Stock header */}
          {quote && (
            <div className="p-5 rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="flex justify-between items-start">
                <div>
                  <div className="serif text-3xl font-light" style={{ color: "var(--text)" }}>
                    {quote.price?.toFixed(2)}
                  </div>
                  <div className="text-sm mt-1" style={{ color: "var(--text-dim)" }}>{quote.name}</div>
                </div>
                <div className="text-right">
                  <div className="text-[0.44rem] tracking-[4px] uppercase mb-1" style={{ color: "var(--text-muted)" }}>
                    {ticker} · {market}
                  </div>
                  {val?.moat && (
                    <div className="text-sm font-medium" style={{ color: "var(--gold)" }}>
                      护城河 {val.moat.percentage?.toFixed(0)}分 · {val.moat.grade}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* 2-column: fundamentals + technical */}
          <div className="grid grid-cols-2 gap-4">
            {norm && (
              <div className="p-4 rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                <div className="text-[0.44rem] tracking-[4px] uppercase mb-3" style={{ color: "var(--gold-dim)" }}>
                  基本面
                </div>
                <div className="space-y-2">
                  {[
                    ["PE", fmt(norm.pe_trailing)],
                    ["PB", fmt(norm.pb)],
                    ["ROE", fmt(norm.roe, true)],
                    ["毛利率", fmt(norm.gross_margin, true)],
                    ["净利率", fmt(norm.profit_margin, true)],
                    ["负债权益", fmt(norm.debt_to_equity)],
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between text-[0.68rem]">
                      <span style={{ color: "var(--text-muted)" }}>{k}</span>
                      <span style={{ color: "var(--text)" }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tech && (
              <div className="p-4 rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                <div className="text-[0.44rem] tracking-[4px] uppercase mb-3" style={{ color: "var(--gold-dim)" }}>
                  技术面
                </div>
                <div className="space-y-2">
                  {[
                    ["趋势", String(tech.trend ?? "—")],
                    ["动量", String(tech.momentum ?? "—")],
                    ["RSI", fmt(tech.rsi as number | null)],
                    ["MACD", fmt(tech.macd as number | null)],
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between text-[0.68rem]">
                      <span style={{ color: "var(--text-muted)" }}>{k}</span>
                      <span style={{ color: "var(--text)" }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Valuation */}
          {val?.multi_val && (
            <div className="p-4 rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="text-[0.44rem] tracking-[4px] uppercase mb-3" style={{ color: "var(--gold-dim)" }}>
                四模型估值
              </div>
              <div className="flex justify-between items-center">
                <div>
                  <div className="serif text-2xl font-light">
                    {val.multi_val.weighted_intrinsic_value?.toFixed(2)}
                  </div>
                  <div className="text-[0.6rem] mt-1" style={{ color: "var(--text-muted)" }}>
                    加权内在价值
                  </div>
                </div>
                <div className="text-right">
                  <div
                    className="serif text-2xl font-light"
                    style={{
                      color: (val.multi_val.weighted_safety_margin_pct ?? 0) > 0
                        ? "var(--green)" : "var(--red)"
                    }}
                  >
                    {(val.multi_val.weighted_safety_margin_pct ?? 0) > 0 ? "+" : ""}
                    {val.multi_val.weighted_safety_margin_pct?.toFixed(1)}%
                  </div>
                  <div className="text-[0.6rem] mt-1" style={{ color: "var(--text-muted)" }}>安全边际</div>
                </div>
                <div className="text-sm font-medium" style={{
                  color: (val.multi_val.weighted_safety_margin_pct ?? 0) > 10
                    ? "var(--green)" : (val.multi_val.weighted_safety_margin_pct ?? 0) < -10
                    ? "var(--red)" : "var(--gold)"
                }}>
                  {val.multi_val.verdict}
                </div>
              </div>
            </div>
          )}

          {/* Risk */}
          {risk && (
            <div className="p-4 rounded" style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
              <div className="text-[0.44rem] tracking-[4px] uppercase mb-3" style={{ color: "var(--gold-dim)" }}>
                风险管理
              </div>
              <div className="grid grid-cols-3 gap-4 mb-3">
                {[
                  ["波动率", `${risk.volatility?.annual_vol_pct?.toFixed(1)}%`],
                  ["最大仓位", `${risk.position?.max_position_pct?.toFixed(0)}%`],
                  ["风险评分", String(risk.risk_report?.risk_score ?? "—")],
                ].map(([k, v]) => (
                  <div key={k} className="text-center">
                    <div className="serif text-xl font-light">{v}</div>
                    <div className="text-[0.52rem] mt-1" style={{ color: "var(--text-muted)" }}>{k}</div>
                  </div>
                ))}
              </div>
              {risk.risk_report?.recommendations?.map((r, i) => (
                <div key={i} className="text-[0.65rem] py-1.5 border-t"
                  style={{ color: "var(--text-dim)", borderColor: "var(--border)" }}>
                  {r}
                </div>
              ))}
            </div>
          )}

          {/* AI Summary */}
          {aiText && (
            <div className="p-5 rounded" style={{
              background: "var(--bg-card)",
              border: "1px solid rgba(201,169,98,0.2)",
              borderTop: "2px solid var(--gold)",
            }}>
              <div className="text-[0.44rem] tracking-[4px] uppercase mb-3" style={{ color: "var(--gold-dim)" }}>
                AI 综合分析
              </div>
              <p className="text-sm leading-7" style={{ color: "var(--text-dim)" }}>{aiText}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function AnalysisPage() {
  return (
    <Suspense>
      <AnalysisContent />
    </Suspense>
  )
}
