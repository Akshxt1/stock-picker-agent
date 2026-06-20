"use client"

import { useEffect, useState } from "react"
import AgentStream from "@/components/agent-stream"
import PickCard from "@/components/pick-card"
import { picks as picksApi, type Pick } from "@/lib/api"
import { useRun } from "@/lib/run-context"
import { History, Loader2 } from "lucide-react"

export default function IndiaPage() {
  const { state } = useRun()
  const [saved, setSaved] = useState<Pick[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    try { setSaved(await picksApi.list("INDIA")) }
    catch { /* ignore */ }
    finally { setLoading(false) }
  }

  // Refresh saved picks on mount and whenever a run finishes.
  useEffect(() => { load() }, [state.lastDone])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-1">India Markets</h2>
        <p className="text-muted-foreground text-sm">NSE-listed stocks · SEBI market cap definitions</p>
      </div>

      <AgentStream lockedMarket="INDIA" />

      {/* Saved India picks (history) */}
      <div>
        <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
          <History className="h-4 w-4" /> Saved India Picks
        </h3>
        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
        ) : saved.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4">No saved India picks yet. Run an analysis above.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {saved.map(p => <PickCard key={p.id} pick={p} />)}
          </div>
        )}
      </div>
    </div>
  )
}
