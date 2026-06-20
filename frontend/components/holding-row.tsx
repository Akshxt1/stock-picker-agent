"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { portfolio, type Holding, type HoldingVerdict } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import {
  Trash2, ChevronRight, ChevronDown, Sparkles, Loader2,
  Target, ShieldAlert, TrendingUp, TrendingDown,
} from "lucide-react"
import { formatMoney } from "@/lib/utils"

interface Props {
  holding: Holding
  displayCurrency: string
  /** Convert a value from the holding's native currency into displayCurrency. */
  convert: (value: number | null | undefined, fromCurrency: string | null | undefined) => number | null
  onChanged: () => void
}

const RECO_VARIANT: Record<string, "success" | "warning" | "destructive" | "outline"> = {
  BUY: "success", BUY_MORE: "success", HOLD: "outline", SELL: "destructive",
}

export default function HoldingRow({ holding: h, displayCurrency, convert, onChanged }: Props) {
  const router = useRouter()
  const [open, setOpen] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [verdict, setVerdict] = useState<HoldingVerdict | null>(null)

  const native  = h.currency || "INR"
  const buy     = convert(h.buy_price, native)
  const current = convert(h.current_price ?? h.buy_price, native)
  const invested = buy != null ? buy * h.quantity : null
  const value    = current != null ? current * h.quantity : null
  const pnlAmt   = (value != null && invested != null) ? value - invested : null
  const pnlPct   = h.pnl_pct
  const up       = (pnlPct ?? 0) >= 0

  const target  = convert(h.target_price ?? verdict?.target_price ?? null, native)
  const stop    = convert(h.stop_loss ?? verdict?.stop_loss ?? null, native)
  const reco    = verdict?.recommendation ?? h.recommendation ?? null
  const summary = verdict?.summary ?? h.analysis_summary ?? null
  const whyBuy  = verdict?.why_buy ?? h.why_buy ?? []
  const whyNot  = verdict?.why_not_buy ?? h.why_not_buy ?? []

  async function runAnalysis(e: React.MouseEvent) {
    e.stopPropagation()
    setAnalyzing(true)
    try {
      const v = await portfolio.analyze(h.id)
      setVerdict(v); setOpen(true); onChanged()
    } catch { /* ignore */ }
    finally { setAnalyzing(false) }
  }

  async function remove(e: React.MouseEvent) {
    e.stopPropagation()
    await portfolio.del(h.id); onChanged()
  }

  return (
    <div className="rounded-xl border border-border/60 bg-card transition-colors hover:border-border">
      {/* Main row */}
      <div className="flex items-center gap-3 px-4 py-3">
        {/* Left: identity */}
        <button onClick={() => router.push(`/stock/${encodeURIComponent(h.ticker)}`)}
          className="flex min-w-0 flex-1 items-center gap-2 text-left group">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-sm font-bold">{h.ticker.replace(/\.(NS|BO)$/, "")}</span>
              {reco && <Badge variant={RECO_VARIANT[reco] ?? "outline"} className="text-[9px]">{reco.replace("_", " ")}</Badge>}
            </div>
            <p className="truncate text-[11px] text-muted-foreground">
              {h.quantity} qty · avg {formatMoney(buy, displayCurrency)}
            </p>
          </div>
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        </button>

        {/* Right: value + P&L */}
        <div className="text-right">
          <p className="text-sm font-bold">{formatMoney(value, displayCurrency)}</p>
          {pnlPct != null ? (
            <p className={`flex items-center justify-end gap-0.5 text-[11px] font-semibold ${up ? "gain" : "loss"}`}>
              {up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {pnlAmt != null ? `${up ? "+" : "−"}${formatMoney(Math.abs(pnlAmt), displayCurrency).replace(/^[₹$]/, "")} · ` : ""}
              {up ? "+" : ""}{pnlPct.toFixed(2)}%
            </p>
          ) : <p className="text-[11px] text-muted-foreground">—</p>}
        </div>

        {/* Expand toggle */}
        <button onClick={() => setOpen(v => !v)} className="text-muted-foreground hover:text-foreground transition-colors">
          <ChevronDown className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} />
        </button>
      </div>

      {/* Expanded detail */}
      {open && (
        <div className="border-t border-border/50 px-4 py-3 space-y-3">
          <div className="grid grid-cols-3 gap-2 text-center">
            <Stat label="LTP" value={formatMoney(current, displayCurrency)} />
            <Stat label="Invested" value={formatMoney(invested, displayCurrency)} />
            <Stat label="P/E" value={h.pe_ratio != null ? String(h.pe_ratio) : "—"} />
          </div>

          {reco && (
            <div className="rounded-lg border border-border/40 bg-muted/30 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={RECO_VARIANT[reco] ?? "outline"}>{reco.replace("_", " ")}</Badge>
                {target != null && <span className="flex items-center gap-1 text-[11px] text-accent"><Target className="h-3 w-3" /> {formatMoney(target, displayCurrency)}</span>}
                {stop != null && <span className="flex items-center gap-1 text-[11px] text-destructive"><ShieldAlert className="h-3 w-3" /> {formatMoney(stop, displayCurrency)}</span>}
              </div>
              {summary && <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">{summary}</p>}
              {whyBuy.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {whyBuy.slice(0, 3).map((r, i) => <li key={i} className="flex gap-1.5 text-[11px] text-muted-foreground"><span className="text-accent">▸</span>{r}</li>)}
                </ul>
              )}
              {whyNot.length > 0 && (
                <ul className="mt-1.5 space-y-1">
                  {whyNot.slice(0, 2).map((r, i) => <li key={i} className="flex gap-1.5 text-[11px] text-muted-foreground"><span className="text-amber-500">▸</span>{r}</li>)}
                </ul>
              )}
            </div>
          )}

          <div className="flex items-center gap-2">
            <button onClick={runAnalysis} disabled={analyzing}
              className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-border/60 px-3 py-2 text-xs font-medium hover:bg-muted/50 transition-colors disabled:opacity-60">
              {analyzing ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Analysing…</>
                         : <><Sparkles className="h-3.5 w-3.5" /> {reco ? "Re-run" : "Quick Analysis"}</>}
            </button>
            <button onClick={remove} className="rounded-lg border border-border/60 px-3 py-2 text-muted-foreground hover:text-destructive hover:border-destructive/40 transition-colors" title="Remove">
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-0.5 text-sm font-semibold">{value}</p>
    </div>
  )
}
