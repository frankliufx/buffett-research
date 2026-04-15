import type { StockData, Analyst, HedgeFundResult, StreamEvent } from "./types"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8502"

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? "请求失败")
  }
  return res.json()
}

export const api = {
  health: () => get<{ status: string }>("/api/health"),

  stock: (ticker: string, market = "US") =>
    get<StockData>(`/api/stock/${ticker}?market=${market}`),

  analysts: () => get<Analyst[]>("/api/hedge-fund/analysts"),

  hedgeFund: (ticker: string, market = "US", analystIds?: string[]) =>
    fetch(`${BASE}/api/hedge-fund/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticker, market, analyst_ids: analystIds ?? null }),
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail ?? "分析失败")
      }
      return res.json() as Promise<HedgeFundResult>
    }),
}

/** SSE 流式分析 — 返回 AsyncGenerator */
export async function* streamAnalysis(
  ticker: string,
  market = "US"
): AsyncGenerator<StreamEvent> {
  const url = `${BASE}/api/analysis/${ticker}/stream?market=${market}`
  const res = await fetch(url)
  if (!res.body) throw new Error("No response body")

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ""

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })

    const parts = buf.split("\n\n")
    buf = parts.pop() ?? ""

    for (const part of parts) {
      const lines = part.trim().split("\n")
      let event = ""
      let data = ""
      for (const line of lines) {
        if (line.startsWith("event: ")) event = line.slice(7)
        if (line.startsWith("data: "))  data  = line.slice(6)
      }
      if (event && data) {
        try {
          yield { event, data: JSON.parse(data) } as StreamEvent
        } catch {
          // skip malformed
        }
      }
    }
  }
}
