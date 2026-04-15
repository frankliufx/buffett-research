"use client"

import { useState, useEffect } from "react"
import { api } from "@/lib/api"
import { SignalBadge, signalColor } from "@/components/SignalBadge"
import type { Analyst, HedgeFundResult } from "@/lib/types"

export default function HedgeFundPage() {
  const [ticker, setTicker] = useState("")
  const [market, setMarket] = useState("US")
  const [analysts, setAnalysts] = useState<Analyst[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [running, setRunning] = useState(false)
  const [result, setResult] = useState<HedgeFundResult | null>(null)
  const [error, setError] = useState("")

  useEffect(() => {
    api.analysts().then(list => {
      setAnalysts(list)
      setSelected(new Set(list.slice(0, 6).map(a => a.id)))
    }).catch(() => {})
  }, [])

  // Group analysts by group field
  const groups = analysts.reduce<Record<string, Analyst[]>>((acc, a) => {
    ;(acc[a.group] ??= []).push(a)
    return acc
  }, {})

  const toggle = (id: string) =>
    setSelected(s => {
      const next = new Set(s)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })

  const run = async () => {
    if (!ticker || selected.size === 0) return
    setRunning(true)
    setResult(null)
    setError("")
    try {
      const r = await api.hedgeFund(ticker.toUpperCase(), market, [...selected])
      setResult(r)
    } catch (e) {
      setError(e instanceof Error ? e.message : "请求失败")
    } finally {
      setRunning(false)
    }
  }

  const sc = result ? signalColor(result.consensus.signal) : "var(--gold)"
  const total = result ? (result.bullish_count + result.bearish_count + result.neutral_count) || 1 : 1
  const gp = result ? ((result.weighted_score + 100) / 200) * 100 : 50

  return (
    <div className="flex gap-6 h-full">
      {/* Left control panel */}
      <div className="w-52 flex-shrink-0 space-y-4">
        <div>
          <h2 className="serif text-xl font-light tracking-[4px] mb-1" style={{ color: "var(--gold)" }}>
            HEDGE FUND
          </h2>
          <p className="text-[0.52rem] tracking-[4px] uppercase" style={{ color: "var(--text-muted)" }}>
            13 Legends · Parallel
          </p>
        </div>

        {/* Ticker input */}
        <div className="space-y-2">
          <input
            value={ticker}
            onChange={e => setTicker(e.target.value.toUpperCase())}
            placeholder="股票代码"
            className="w-full px-3 py-2 text-sm rounded outline-none"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text)" }}
          />
          <select
            value={market}
            onChange={e => setMarket(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded outline-none"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--text)" }}
          >
            <option value="US">美股</option>
            <option value="CN">A股</option>
            <option value="HK">港股</option>
          </select>
        </div>

        {/* Analyst selection */}
        <div className="space-y-3">
          {Object.entries(groups).map(([group, list]) => (
            <div key={group}>
              <div className="text-[0.42rem] tracking-[4px] uppercase mb-1.5"
                style={{ color: "rgba(201,169,98,0.45)" }}>
                {group}
              </div>
              {list.map(a => (
                <label key={a.id}
                  className="flex items-center gap-2 py-1 cursor-pointer text-[0.68rem]"
                  style={{ color: selected.has(a.id) ? "var(--text)" : "var(--text-muted)" }}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(a.id)}
                    onChange={() => toggle(a.id)}
                    className="w-3 h-3 accent-[#C9A962]"
                  />
                  <span>{a.icon}</span>
                  <span>{a.name_cn}</span>
                </label>
              ))}
            </div>
          ))}
        </div>

        <button
          onClick={run}
          disabled={running || !ticker || selected.size === 0}
          className="w-full py-2.5 text-sm font-medium rounded transition-opacity disabled:opacity-40"
          style={{
            background: "rgba(201,169,98,0.12)",
            border: "1px solid rgba(201,169,98,0.25)",
            color: "var(--gold)",
          }}
        >
          {running ? `分析中 ${selected.size} 位...` : `🚀 运行 ${selected.size} 位`}
        </button>
      </div>

      {/* Right results */}
      <div className="flex-1 overflow-auto">
        {error && (
          <div className="mb-4 px-4 py-3 rounded text-sm"
            style={{ background: "rgba(244,67,54,0.08)", border: "1px solid rgba(244,67,54,0.2)", color: "#F44336" }}>
            {error}
          </div>
        )}

        {running && (
          <div className="flex items-center gap-3 py-12 justify-center"
            style={{ color: "var(--text-muted)" }}>
            <span className="w-2 h-2 rounded-full bg-[#C9A962] animate-pulse" />
            <span className="text-sm tracking-widest">
              并行调用 {selected.size} 位分析师...
            </span>
          </div>
        )}

        {!running && !result && (
          <div className="flex flex-col items-center justify-center py-20"
            style={{ color: "var(--text-muted)" }}>
            <div className="text-5xl mb-4 opacity-20">🏦</div>
            <div className="serif text-lg tracking-[3px]">AI HEDGE FUND</div>
            <div className="text-[0.6rem] tracking-[2px] mt-2">
              选择股票和分析师，点击运行
            </div>
          </div>
        )}

        {result && (
          <div className="space-y-4">
            {/* Consensus card */}
            <div className="p-5 rounded" style={{
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              borderTop: `2px solid ${sc}`,
            }}>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <div className="text-[0.42rem] tracking-[5px] uppercase px-2 py-0.5 inline-block mb-2"
                    style={{
                      border: "1px solid rgba(201,169,98,0.2)",
                      color: "var(--gold-dim)",
                    }}>
                    {result.consensus.unanimity}
                  </div>
                  <div className="serif text-2xl font-semibold tracking-[2px]" style={{ color: sc }}>
                    {result.consensus.verdict}
                  </div>
                  <div className="text-[0.6rem] mt-1" style={{ color: "var(--text-muted)" }}>
                    {result.symbol} · {result.analysts.length} 位分析师
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[0.42rem] tracking-[3px] uppercase mb-1"
                    style={{ color: "var(--text-muted)" }}>综合得分</div>
                  <div className="serif text-4xl font-light" style={{ color: sc }}>
                    {result.weighted_score > 0 ? "+" : ""}{result.weighted_score.toFixed(0)}
                  </div>
                </div>
              </div>

              {/* Gauge */}
              <div className="relative h-4 mb-1">
                <div className="absolute top-1.5 left-0 right-0 h-1 rounded"
                  style={{ background: "linear-gradient(90deg,#F44336,#FF9800,#C9A962,#69F0AE,#00C853)" }} />
                <div className="absolute top-0 w-4 h-4 rounded-full border-2"
                  style={{
                    left: `${gp}%`,
                    transform: "translateX(-50%)",
                    background: sc,
                    borderColor: "var(--bg)",
                  }} />
              </div>
              <div className="flex justify-between text-[0.44rem]" style={{ color: "var(--text-muted)" }}>
                <span>极度看空</span><span>中性</span><span>极度看多</span>
              </div>

              {/* Vote bar */}
              <div className="flex h-1.5 rounded overflow-hidden mt-3">
                <div style={{ width: `${result.bullish_count / total * 100}%`, background: "#00C853" }} />
                <div style={{ width: `${result.neutral_count / total * 100}%`, background: "#C9A962" }} />
                <div style={{ width: `${result.bearish_count / total * 100}%`, background: "#F44336" }} />
              </div>
              <div className="flex gap-4 mt-2">
                <span className="text-[0.56rem]" style={{ color: "#00C853" }}>▲ {result.bullish_count}</span>
                <span className="text-[0.56rem]" style={{ color: "#C9A962" }}>● {result.neutral_count}</span>
                <span className="text-[0.56rem]" style={{ color: "#F44336" }}>▼ {result.bearish_count}</span>
              </div>
            </div>

            {/* Analyst cards */}
            <div className="grid grid-cols-2 gap-3">
              {result.analysts.map(a => {
                const ac = signalColor(a.signal)
                return (
                  <div key={a.id} className="p-4 rounded"
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      borderLeft: `3px solid ${ac}`,
                    }}>
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{a.icon}</span>
                        <div>
                          <div className="text-sm font-semibold">{a.name_cn}</div>
                          <div className="text-[0.48rem] tracking-[2px] uppercase"
                            style={{ color: "var(--text-muted)" }}>
                            {a.style.split("·")[0].trim()}
                          </div>
                        </div>
                      </div>
                      <SignalBadge signal={a.signal} />
                    </div>
                    <p className="text-[0.68rem] leading-6 mb-2 pl-2"
                      style={{
                        color: "var(--text-dim)",
                        borderLeft: "2px solid var(--border)",
                      }}>
                      {a.reasoning}
                    </p>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-0.5 rounded overflow-hidden" style={{ background: "var(--border)" }}>
                        <div className="h-full rounded" style={{ width: `${a.confidence}%`, background: ac }} />
                      </div>
                      <span className="text-[0.54rem]" style={{ color: "var(--text-muted)" }}>
                        {a.confidence}%
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
