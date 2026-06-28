"use client"

import { useEffect, useState } from "react"
import AgentStream from "@/components/agent-stream"
import PickCard from "@/components/pick-card"
import StockSearch from "@/components/stock-search"
import { picks as picksApi, type Pick } from "@/lib/api"
import { useRun } from "@/lib/run-context"
import { useSettings } from "@/lib/settings-context"
import { applyPickSettings, cn } from "@/lib/utils"
import { History, Loader2, SlidersHorizontal } from "lucide-react"

export default function IndiaPage() {
  const { state } = useRun()
  const { settings } = useSettings()
  const [saved, setSaved] = useState<Pick[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    try { setSaved(await picksApi.list("INDIA")) }
    catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [state.lastDone])

  // Apply sort + confidence + risk filters to saved picks (no numPicks cap on history)
  const filtered = applyPickSettings(saved, settings, false)
  const isFiltered = filtered.length < saved.length

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold mb-1">India Markets</h2>
          <p className="text-muted-foreground text-sm">NSE-listed stocks · SEBI market cap definitions</p>
        </div>
        <StockSearch market="INDIA" />
      </div>

      <AgentStream lockedMarket="INDIA" />

      {/* Saved India picks (history) */}
      <div>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
          <History className="h-4 w-4" /> Saved India Picks
          {isFiltered && (
            <span className="flex items-center gap-1 text-[11px] font-normal">
              <SlidersHorizontal className="h-3 w-3" />
              {filtered.length} of {saved.length} shown
            </span>
          )}
        </h3>
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">
            {saved.length === 0
              ? "No saved India picks yet. Run an analysis above."
              : "All picks filtered out by your Analysis settings. Adjust confidence or risk tolerance in Settings."}
          </p>
        ) : (
          <div className={cn(
            settings.cardViewMode === "compact"
              ? "flex flex-col gap-1.5"
              : "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
          )}>
            {filtered.map(p => <PickCard key={p.id} pick={p} />)}
          </div>
        )}
      </div>
    </div>
  )
}
