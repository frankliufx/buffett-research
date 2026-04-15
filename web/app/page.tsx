"use client"

import { useState } from "react"
import Link from "next/link"

const QUICK_STOCKS = [
  { ticker: "AAPL",   name: "Apple",     market: "US" },
  { ticker: "NVDA",   name: "Nvidia",    market: "US" },
  { ticker: "BRK-B",  name: "Berkshire", market: "US" },
  { ticker: "600519", name: "贵州茅台",   market: "CN" },
  { ticker: "0700",   name: "腾讯",      market: "HK" },
]

export default function DashboardPage() {
  const [input, setInput] = useState("")

  return (
    <div className="max-w-3xl mx-auto pt-8">
      {/* Hero */}
      <div className="mb-10">
        <h1 className="serif text-4xl font-light tracking-[5px] mb-2"
          style={{ color: "var(--gold)" }}>
          BUFFETT RESEARCH
        </h1>
        <p className="text-[0.62rem] tracking-[5px] uppercase"
          style={{ color: "var(--text-muted)" }}>
          AI-Powered Value Intelligence · 13 Legendary Investors
        </p>
      </div>

      {/* Search */}
      <div className="flex gap-3 mb-8">
        <input
          value={input}
          onChange={e => setInput(e.target.value.toUpperCase())}
          onKeyDown={e => {
            if (e.key === "Enter" && input)
              window.location.href = `/analysis?ticker=${input}&market=US`
          }}
          placeholder="输入股票代码  AAPL / 600519 / 0700"
          className="flex-1 px-4 py-3 text-sm rounded outline-none"
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            color: "var(--text)",
          }}
        />
        <Link
          href={input ? `/analysis?ticker=${input}&market=US` : "#"}
          className="px-6 py-3 text-sm font-medium rounded"
          style={{
            background: input ? "rgba(201,169,98,0.15)" : "var(--bg-card)",
            border: "1px solid var(--border)",
            color: input ? "var(--gold)" : "var(--text-muted)",
          }}
        >
          分析 →
        </Link>
      </div>

      {/* Quick picks */}
      <div className="mb-3 text-[0.44rem] tracking-[5px] uppercase"
        style={{ color: "var(--text-muted)" }}>
        快速访问
      </div>
      <div className="grid grid-cols-5 gap-3 mb-12">
        {QUICK_STOCKS.map(s => (
          <Link
            key={s.ticker}
            href={`/analysis?ticker=${s.ticker}&market=${s.market}`}
            className="p-4 rounded text-center"
            style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}
          >
            <div className="text-sm font-semibold mb-1">{s.ticker}</div>
            <div className="text-[0.58rem]" style={{ color: "var(--text-muted)" }}>{s.name}</div>
          </Link>
        ))}
      </div>

      {/* Feature cards */}
      <div className="grid grid-cols-2 gap-4">
        <Link href="/analysis"
          className="p-5 rounded border"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="text-xl mb-3">🔍</div>
          <div className="font-medium mb-1">智能分析</div>
          <div className="text-[0.65rem]" style={{ color: "var(--text-dim)" }}>
            SSE 流式输出 · 实时看到每个分析步骤
          </div>
        </Link>
        <Link href="/hedge-fund"
          className="p-5 rounded border"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          <div className="text-xl mb-3">🏦</div>
          <div className="font-medium mb-1">AI 对冲基金</div>
          <div className="text-[0.65rem]" style={{ color: "var(--text-dim)" }}>
            13位传奇投资人 · 并行投票 · 加权共识
          </div>
        </Link>
      </div>
    </div>
  )
}
