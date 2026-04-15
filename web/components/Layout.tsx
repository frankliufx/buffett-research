"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { clsx } from "clsx"

const NAV = [
  { href: "/",           icon: "⬡", label: "Dashboard" },
  { href: "/analysis",   icon: "🔍", label: "Analysis" },
  { href: "/hedge-fund", icon: "🏦", label: "Hedge Fund" },
]

export function Layout({ children }: { children: React.ReactNode }) {
  const path = usePathname()

  return (
    <div className="flex min-h-screen" style={{ background: "var(--bg)" }}>
      {/* Sidebar */}
      <aside
        className="w-52 flex-shrink-0 flex flex-col border-r"
        style={{ borderColor: "var(--border)", background: "var(--bg-card)" }}
      >
        {/* Logo */}
        <div className="px-5 pt-6 pb-5 border-b" style={{ borderColor: "var(--border)" }}>
          <div className="serif text-lg font-light tracking-[3px]" style={{ color: "var(--gold)" }}>
            BUFFETT
          </div>
          <div className="text-[0.42rem] tracking-[5px] mt-0.5" style={{ color: "var(--text-muted)" }}>
            RESEARCH · AI
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 pt-4 space-y-1">
          {NAV.map(({ href, icon, label }) => {
            const active = href === "/" ? path === "/" : path.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-colors",
                  active
                    ? "text-[#C9A962]"
                    : "hover:text-[#E8E8F0]"
                )}
                style={{
                  background: active ? "rgba(201,169,98,0.07)" : "transparent",
                  color: active ? "var(--gold)" : "var(--text-dim)",
                }}
              >
                <span className="text-base">{icon}</span>
                <span className="tracking-wide text-[0.75rem]">{label}</span>
              </Link>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t text-[0.48rem] tracking-[2px]"
          style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
          API · localhost:8502
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  )
}
