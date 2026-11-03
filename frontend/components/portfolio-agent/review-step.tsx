"use client"

import { AlertTriangle, CheckCircle2, HelpCircle, Loader2, Trash2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import type { AgentHoldingIn, AgentParse, AgentRow } from "@/lib/api"

export interface ReviewRow {
  id: number
  row: AgentRow
  selected: string          // chosen symbol; "" = skip this row
  qty: string
  avg: string
}

export function toReviewRows(p: AgentParse): ReviewRow[] {
  return p.rows.map((row, id) => ({
    id, row, selected: row.match ?? "",
    qty: row.quantity != null ? String(row.quantity) : "",
    avg: row.avg_price != null ? String(Math.round(row.avg_price * 10000) / 10000) : "",
  }))
}

/** Rows that are ready to analyse: a chosen symbol and a positive quantity. */
export function readyHoldings(rows: ReviewRow[]): AgentHoldingIn[] {
  const out: AgentHoldingIn[] = []
  for (const r of rows) {
    const qty = parseFloat(r.qty)
    const cand = r.row.candidates.find(c => c.symbol === r.selected)
    if (!r.selected || !cand || !(qty > 0)) continue
    const avg = parseFloat(r.avg)
    out.push({ symbol: r.selected, quantity: qty, avg_price: avg > 0 ? avg : null, asset_class: cand.asset_class, name: r.row.name })
  }
  return out
}

const STATUS = {
  matched:   { label: "Matched",      variant: "success" as const, Icon: CheckCircle2 },
  review:    { label: "Please check", variant: "warning" as const, Icon: HelpCircle },
  unmatched: { label: "Not found",    variant: "destructive" as const, Icon: AlertTriangle },
}

const field = "h-9 w-full rounded-md border border-input bg-background px-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"

export default function ReviewStep({ parse, rows, setRows, busy, error, onBack, onAnalyze }: {
  parse: AgentParse
  rows: ReviewRow[]
  setRows: (r: ReviewRow[]) => void
  busy: boolean
  error: string | null
  onBack: () => void
  onAnalyze: () => void
}) {
  const ready = readyHoldings(rows)
  const needsAttention = rows.filter(r => r.row.status !== "matched" && !r.selected).length
  const update = (id: number, patch: Partial<ReviewRow>) => setRows(rows.map(r => r.id === id ? { ...r, ...patch } : r))

  return (
    <div className="space-y-4">
      <Card className="border-border/60">
        <CardContent className="pt-5">
          <h3 className="mb-1 text-sm font-semibold">3 · Check what we read</h3>
          <p className="text-xs text-muted-foreground">
            AI can misread a screenshot, so please confirm each row before we analyse it. Wrong symbols or numbers would give you a wrong plan.
          </p>
          {parse.notes && (
            <p className="mt-3 rounded-lg border border-border/50 bg-muted/20 p-2.5 text-[11px] text-muted-foreground">Note from the reader: {parse.notes}</p>
          )}
        </CardContent>
      </Card>

      <div className="space-y-3">
        {rows.map(r => {
          const s = STATUS[r.row.status]
          const qtyBad = !(parseFloat(r.qty) > 0)
          return (
            <Card key={r.id} className={`border-border/60 ${r.selected ? "" : "opacity-70"}`}>
              <CardContent className="space-y-3 py-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold">{r.row.name ?? r.row.symbol ?? "Unnamed row"}</p>
                    <p className="text-[11px] text-muted-foreground">
                      Read as {r.row.symbol ? `“${r.row.symbol}” · ` : ""}{r.row.asset_class.replace("_", " ")}
                      {r.row.pnl_pct != null && <> · shown P&amp;L {r.row.pnl_pct > 0 ? "+" : ""}{r.row.pnl_pct}%</>}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={s.variant} className="gap-1"><s.Icon className="h-3 w-3" />{s.label}</Badge>
                    <button aria-label="Remove row" onClick={() => setRows(rows.filter(x => x.id !== r.id))}
                      className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-destructive">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-[1fr_8rem_9rem]">
                  <label className="text-[11px] text-muted-foreground">
                    Which instrument is this?
                    <select value={r.selected} onChange={e => update(r.id, { selected: e.target.value })} className={`${field} mt-1`}>
                      <option value="">Skip this row</option>
                      {r.row.candidates.map(c => (
                        <option key={c.symbol} value={c.symbol}>
                          {c.name} · {c.symbol.replace(/^(CRYPTO|MF):/, "")} · {c.market === "CRYPTO" ? "Crypto" : c.market === "INDIA" ? "India" : "US"}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="text-[11px] text-muted-foreground">
                    Quantity
                    <input inputMode="decimal" value={r.qty} onChange={e => update(r.id, { qty: e.target.value })}
                      className={`${field} mt-1 ${qtyBad && r.selected ? "border-destructive" : ""}`} />
                  </label>
                  <label className="text-[11px] text-muted-foreground">
                    Avg buy price
                    <input inputMode="decimal" value={r.avg} placeholder="unknown" onChange={e => update(r.id, { avg: e.target.value })}
                      className={`${field} mt-1`} />
                  </label>
                </div>
                {r.row.status === "unmatched" && r.row.candidates.length === 0 && (
                  <p className="text-[11px] text-destructive">We couldn&apos;t find this one. It will be skipped; you can add it manually from the Portfolio page.</p>
                )}
              </CardContent>
            </Card>
          )
        })}
        {rows.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">No rows left. Go back and upload again.</p>
        )}
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {error}
        </div>
      )}
      {needsAttention > 0 && (
        <p className="text-[11px] text-amber-600 dark:text-amber-400">
          {needsAttention} row{needsAttention > 1 ? "s" : ""} need an instrument chosen, or will be skipped.
        </p>
      )}
      <div className="flex gap-2">
        <Button variant="outline" onClick={onBack} disabled={busy}>Back</Button>
        <Button onClick={onAnalyze} disabled={busy || ready.length === 0} className="flex-1 gap-2">
          {busy ? <><Loader2 className="h-4 w-4 animate-spin" /> Analysing…</> : `Analyse ${ready.length} holding${ready.length === 1 ? "" : "s"}`}
        </Button>
      </div>
    </div>
  )
}
