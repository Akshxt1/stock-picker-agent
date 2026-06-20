"use client"

import { useEffect, useState } from "react"
import { picks, type Pick } from "@/lib/api"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart2, TrendingUp, Trash2, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"

export default function MetricsPage() {
  const [data,    setData]    = useState<Pick[]>([])
  const [loading, setLoading] = useState(true)

  async function load() {
    try { setData(await picks.list()) }
    catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function handleDelete(id: number) {
    await picks.del(id)
    await load()
  }

  const isBuy = (p: Pick) => {
    const r = (p.recommendation || p.technical_signal || "").toUpperCase()
    return r === "BUY" || r.includes("BULL")
  }
  const buyCount   = data.filter(isBuy).length
  const watchCount = data.length - buyCount
  const highConf   = data.filter(p => (p.confidence || "").toLowerCase() === "high").length

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold flex items-center gap-2">
        <BarChart2 className="h-6 w-6" />
        Metrics & History
      </h2>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Picks",  value: data.length  },
          { label: "Buy Signals",  value: buyCount      },
          { label: "Watch / Hold", value: watchCount    },
          { label: "High Confidence", value: highConf },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardContent className="pt-6">
              <p className="text-3xl font-bold">{value}</p>
              <p className="text-sm text-muted-foreground">{label}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* History table */}
      <Card>
        <CardHeader><CardTitle className="text-base flex items-center gap-2"><TrendingUp className="h-4 w-4" />All Picks</CardTitle></CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : data.length === 0 ? (
            <p className="text-muted-foreground text-sm py-4 text-center">No picks yet — run an analysis first.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground text-left">
                    <th className="pb-2 pr-3">Date</th>
                    <th className="pb-2 pr-3">Ticker</th>
                    <th className="pb-2 pr-3">Market</th>
                    <th className="pb-2 pr-3">Sector</th>
                    <th className="pb-2 pr-3">Signal</th>
                    <th className="pb-2 pr-3">Conf.</th>
                    <th className="pb-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {data.map(p => (
                    <tr key={p.id} className="border-b last:border-0 hover:bg-muted/50">
                      <td className="py-2 pr-3 text-muted-foreground">{p.analysis_date}</td>
                      <td className="py-2 pr-3 font-semibold">
                        <a href={`/stock/${encodeURIComponent(p.ticker)}`} className="font-mono hover:text-primary transition-colors">
                          {p.ticker}
                        </a>
                      </td>
                      <td className="py-2 pr-3">{p.market}</td>
                      <td className="py-2 pr-3">{p.sector}</td>
                      <td className="py-2 pr-3">
                        <Badge variant={isBuy(p) ? "success" : "warning"}>
                          {p.recommendation || p.technical_signal}
                        </Badge>
                      </td>
                      <td className="py-2 pr-3">{p.confidence || "—"}</td>
                      <td className="py-2">
                        <Button variant="ghost" size="icon" onClick={() => handleDelete(p.id)}>
                          <Trash2 className="h-4 w-4 text-muted-foreground" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
