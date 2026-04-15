import type { Metadata } from "next"
import { Inter } from "next/font/google"
import { Layout } from "@/components/Layout"
import "./globals.css"

const inter = Inter({ subsets: ["latin"] })

export const metadata: Metadata = {
  title: "Buffett Research · AI",
  description: "AI-Powered Value Intelligence Platform",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh" className={inter.className}>
      <body>
        <Layout>{children}</Layout>
      </body>
    </html>
  )
}
