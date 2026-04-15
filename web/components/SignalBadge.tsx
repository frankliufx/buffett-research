import type { Signal } from "@/lib/types"

const MAP: Record<Signal, { label: string; cls: string }> = {
  bullish: { label: "BULLISH", cls: "text-[#00C853] border-[#00C853]" },
  bearish: { label: "BEARISH", cls: "text-[#F44336] border-[#F44336]" },
  neutral: { label: "NEUTRAL", cls: "text-[#C9A962] border-[#C9A962]" },
}

export function SignalBadge({ signal }: { signal: Signal }) {
  const { label, cls } = MAP[signal] ?? MAP.neutral
  return (
    <span className={`text-[0.5rem] font-bold tracking-[3px] px-2 py-0.5 border rounded-sm ${cls}`}>
      {label}
    </span>
  )
}

export function signalColor(signal: Signal) {
  return { bullish: "#00C853", bearish: "#F44336", neutral: "#C9A962" }[signal] ?? "#C9A962"
}
