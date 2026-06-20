"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { portfolio, type Holding, type HoldingVerdict } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Trash2, ChevronRight, Sparkles, Loader2, Target, ShieldAlert,
} from "lucide-react"
import { formatMoney } from "@/lib/utils"

interface Props {
  holding: Holding
  /** Currency to render values in (after any conversion). */
  displayCurrency: string
  /** Converts a value from the holding's native currency into displayCurrency. */
  convert: (value: number | null | undefined, fromCurrency: string | null | undefined) => number | null
  onChanged: () => void
}

const RECO_VARIANT: Record<string, "success" | "warning" | "destructive" | "outline"> = {
  BUY: "success", BUY_MORE: "success", HOLD: "outline", SELL: "destructive",
}

export default function HoldingCard({ holding: h, displayCurrency, convert, onChanged }: Props) {
  const router = useRouter()
  const [analyzing, setAnalyzing] = useState(false)
  const [verdict, setVerdict] = useState<HoldingVerdict | null>(null)

  const native = h.currency || "INR"
  const buy     = convert(h.buy_price, native)
  const current = convert(h.current_price, native)
  const pnl     = h.pnl_pct
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
      setVerdict(v)
      onChanged()
    } catch { /* ignore */ }
    finally { setAnalyzing(false) }
  }

  async function remove(e: React.MouseEvent) {
    e.stopPropagation()
    await portfolio.del(h.id)
    onChanged()
  }

  const go = () => router.push(`/stock/${encodeURIComponent(h.ticker)}`)

  return (
    <div
      onClick={go}
      role="button"
      className="group cursor-pointer rounded-xl border border-border/60 bg-card p-4 transition-all hover:border-primary/40 hover:shadow-lg"
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold">{h.ticker}</span>
          {h.market && <Badge variant="outline" className="text-[9px]">{h.market}</Badge>}
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        <button onClick={remove} className="text-muted-foreground hover:text-destructive transition-colors" title="Remove">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Numbers */}
      <div className="mt-3 grid grid-cols-4 gap-2">
        <Cell label="Qty" value={String(h.quantity)} />
        <Cell label="Buy" value={formatMoney(buy, displayCurrency)} />
        <Cell label="Current" value={formatMoney(current, displayCurrency)} />
        <Cell label="P/E" value={h.pe_ratio != null ? String(h.pe_ratio) : "—"} />
      </div>

      {/* P&L */}
      <div className="mt-3 flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground">Unrealised P&amp;L</span>
        {pnl != null ? (
          <Badge variant={pnl >= 0 ? "success" : "destructive"}>{pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}%</Badge>
        ) : <span className="text-sm text-muted-foreground">—</span>}
      </div>

      {/* Analysis verdict */}
      {reco && (
        <div className="mt-3 rounded-lg border border-border/40 bg-muted/30 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={RECO_VARIANT[reco] ?? "outline"}>{reco.replace("_", " ")}</Badge>
            {target != null && (
              <span className="flex items-center gap-1 text-[11px] text-accent"><Target className="h-3 w-3" /> {formatMoney(target, displayCurrency)}</span>
            )}
            {stop != null && (
              <span className="flex items-center gap-1 text-[11px] text-destructive"><ShieldAlert className="h-3 w-3" /> {formatMoney(stop, displayCurrency)}</span>
            )}
          </div>
          {summary && <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">{summary}</p>}
          {whyBuy.length > 0 && (
            <ul className="mt-2 space-y-1">
              {whyBuy.slice(0, 3).map((r, i) => (
                <li key={i} className="flex gap-1.5 text-[11px] text-muted-foreground"><span className="text-accent">▸</span>{r}</li>
              ))}
            </ul>
          )}
          {whyNot.length > 0 && (
            <ul className="mt-1.5 space-y-1">
              {whyNot.slice(0, 2).map((r, i) => (
                <li key={i} className="flex gap-1.5 text-[11px] text-muted-foreground"><span className="text-amber-500">▸</span>{r}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Run analysis */}
      <Button variant="outline" size="sm" onClick={runAnalysis} disabled={analyzing}
        className="mt-3 w-full gap-2 text-xs">
        {analyzing ? <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Analysing…</>
                   : <><Sparkles className="h-3.5 w-3.5" /> {reco ? "Re-run Analysis" : "Run Analysis"}</>}
      </Button>
    </div>
  )
}

function Cell({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="text-sm font-semibold">{value}</span>
    </div>
  )
}
