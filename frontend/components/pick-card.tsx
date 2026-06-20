"use client"

import { useRouter } from "next/navigation"
import type { Pick } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import AddToPortfolio from "@/components/add-to-portfolio"
import { TrendingUp, TrendingDown, ChevronRight, CalendarDays } from "lucide-react"
import { formatMoney } from "@/lib/utils"

function Metric({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold">{value == null || value === "" ? "—" : value}</span>
    </div>
  )
}

export default function PickCard({ pick }: { pick: Pick }) {
  const router = useRouter()
  const isBuy = (pick.recommendation || pick.technical_signal || "").toUpperCase().includes("BULL")
    || (pick.recommendation || "").toUpperCase() === "BUY"
  const conf = (pick.confidence || "").toString()

  const go = () => router.push(`/stock/${encodeURIComponent(pick.ticker)}`)

  return (
    <div
      onClick={go}
      role="button"
      className="group cursor-pointer rounded-xl border border-border/60 bg-card p-4 transition-all hover:border-primary/40 hover:shadow-lg"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold">{pick.ticker}</span>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
          <p className="truncate text-xs text-muted-foreground">{pick.company_name || "—"}</p>
        </div>
        <Badge variant={isBuy ? "success" : "warning"} className="shrink-0 gap-1 text-[10px] font-bold">
          {isBuy ? <TrendingUp className="h-2.5 w-2.5" /> : <TrendingDown className="h-2.5 w-2.5" />}
          {pick.recommendation || pick.technical_signal || "—"}
        </Badge>
      </div>

      {/* Price + confidence */}
      <div className="mt-3 flex items-end justify-between">
        <span className="text-lg font-bold">{formatMoney(pick.current_price, pick.currency || "INR")}</span>
        {conf && (
          <span className="text-[11px] text-muted-foreground">
            Confidence <span className="font-semibold text-foreground">{conf}</span>
          </span>
        )}
      </div>

      {/* Fundamentals */}
      <div className="mt-3 grid grid-cols-4 gap-2 border-t border-border/40 pt-3">
        <Metric label="ROE" value={pick.roe} />
        <Metric label="D/E" value={pick.debt_to_equity} />
        <Metric label="Rev↑" value={pick.revenue_growth} />
        <Metric label="P/E" value={pick.pe_ratio} />
      </div>

      {/* Footer */}
      <div className="mt-3 flex items-center justify-between">
        <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
          <CalendarDays className="h-3 w-3" />
          {pick.analysis_date || "—"}
          {pick.run_by_username && <span className="text-muted-foreground/70"> · by {pick.run_by_username}</span>}
        </span>
        <AddToPortfolio
          ticker={pick.ticker}
          defaultPrice={pick.current_price}
          currency={pick.currency}
        />
      </div>
    </div>
  )
}
