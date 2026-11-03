"use client"

import { useEffect, useState } from "react"
import { AlertTriangle, Loader2, Target } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { forecast, type ForecastHorizon, type ScenarioKey, type TrackRecord } from "@/lib/api"

const ORDER: { key: ScenarioKey; label: string }[] = [
  { key: "CRASH", label: "Crash" },
  { key: "DECLINE", label: "Decline" },
  { key: "STEADY", label: "Steady" },
  { key: "STRONG_GROWTH", label: "Strong growth" },
  { key: "MULTIBAGGER", label: "Multi-bagger" },
]

export default function TrackRecordPage() {
  const [horizon, setHorizon] = useState<ForecastHorizon | "all">("all")
  const [data, setData] = useState<TrackRecord | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(false)

  useEffect(() => {
    let live = true
    setLoading(true); setErr(false)
    forecast.trackRecord(horizon === "all" ? undefined : horizon)
      .then(r => live && setData(r))
      .catch(() => live && setErr(true))
      .finally(() => live && setLoading(false))
    return () => { live = false }
  }, [horizon])

  const skill = data?.skill
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-bold"><Target className="h-5 w-5 text-primary" /> Forecast track record</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Every scenario forecast is logged when it is made and scored once its horizon has passed. Nothing here is edited afterwards.
          </p>
        </div>
        <div className="flex gap-1 rounded-lg bg-muted/50 p-0.5">
          {(["all", "3m", "1y"] as const).map(h => (
            <button key={h} onClick={() => setHorizon(h)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all ${
                horizon === h ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
              {h === "all" ? "All" : h === "3m" ? "3 months" : "1 year"}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : err || !data ? (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
          <AlertTriangle className="h-4 w-4" /> Could not load the track record.
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-3">
            {[["Logged", data.total], ["Scored", data.resolved], ["Waiting", data.pending]].map(([label, v]) => (
              <Card key={label as string} className="border-border/60">
                <CardContent className="py-4 text-center">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
                  <p className="mt-1 text-2xl font-bold tabular-nums">{v}</p>
                </CardContent>
              </Card>
            ))}
          </div>

          {data.resolved === 0 ? (
            <Card className="border-border/60">
              <CardContent className="py-8 text-center text-sm text-muted-foreground">
                No forecast has reached its horizon yet, so there is nothing to score. 3-month forecasts are scored after about
                91 days; 1-year forecasts after a year. Open any stock, coin or fund&apos;s <b>Scenarios</b> section to start
                logging forecasts. Until then, the &ldquo;Check track record&rdquo; button on each asset shows how the model would
                have done on that asset&apos;s past.
              </CardContent>
            </Card>
          ) : (
            <>
              <Card className="border-border/60">
                <CardContent className="pt-5">
                  <h3 className="mb-3 text-sm font-semibold">Live accuracy vs the historical base rate</h3>
                  <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                    {[
                      ["Error score", data.brier?.toFixed(3)],
                      ["Base-rate error", data.brier_base_rate?.toFixed(3)],
                      ["Skill", skill == null ? "—" : `${skill > 0 ? "+" : ""}${(skill * 100).toFixed(1)}%`],
                      ["Scored", String(data.n)],
                    ].map(([label, v]) => (
                      <div key={label} className="rounded-lg border border-border/50 bg-muted/20 p-3">
                        <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
                        <p className={`mt-1 text-base font-semibold ${label === "Skill" && skill != null ? (skill >= 0 ? "gain" : "loss") : ""}`}>{v}</p>
                      </div>
                    ))}
                  </div>
                  <p className="mt-3 text-[11px] text-muted-foreground">
                    Error score is the Brier score (0 is perfect, lower is better). Skill above 0% means the model beat simply
                    assuming past frequencies. Few scored forecasts means a noisy number.
                  </p>
                </CardContent>
              </Card>

              {data.actual_distribution && data.mean_predicted && (
                <Card className="border-border/60">
                  <CardContent className="pt-5">
                    <h3 className="mb-3 text-sm font-semibold">What happened vs what was expected</h3>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                          <th className="pb-2 font-medium">Scenario</th>
                          <th className="pb-2 text-right font-medium">Expected</th>
                          <th className="pb-2 text-right font-medium">Actual</th>
                        </tr>
                      </thead>
                      <tbody>
                        {ORDER.map(o => (
                          <tr key={o.key} className="border-t border-border/40">
                            <td className="py-2">{o.label}</td>
                            <td className="py-2 text-right tabular-nums">{(data.mean_predicted![o.key] * 100).toFixed(0)}%</td>
                            <td className="py-2 text-right tabular-nums">
                              {((data.actual_distribution![o.key] / Math.max(data.resolved, 1)) * 100).toFixed(0)}%
                              <span className="ml-1 text-xs text-muted-foreground">({data.actual_distribution![o.key]})</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </CardContent>
                </Card>
              )}

              {data.reliability && data.reliability.length > 0 && (
                <Card className="border-border/60">
                  <CardContent className="pt-5">
                    <h3 className="mb-1 text-sm font-semibold">Calibration</h3>
                    <p className="mb-3 text-xs text-muted-foreground">
                      When the model said X%, how often did it happen? A well-calibrated model sits on the diagonal.
                    </p>
                    <div className="space-y-2">
                      {data.reliability.map(r => (
                        <div key={r.bin[0]} className="grid grid-cols-[5.5rem_1fr_7rem] items-center gap-3 text-xs">
                          <span className="text-muted-foreground">said {Math.round(r.bin[0] * 100)}–{Math.round(r.bin[1] * 100)}%</span>
                          <div className="relative h-2 rounded-full bg-muted/40">
                            <div className="h-full rounded-full bg-primary/70" style={{ width: `${r.observed * 100}%` }} />
                            <div className="absolute -top-0.5 h-3 w-0.5 bg-foreground/70" style={{ left: `${Math.min(r.predicted * 100, 99)}%` }}
                              title={`Average predicted ${(r.predicted * 100).toFixed(0)}%`} />
                          </div>
                          <span className="text-right tabular-nums">happened {(r.observed * 100).toFixed(0)}% <span className="text-muted-foreground">({r.count})</span></span>
                        </div>
                      ))}
                    </div>
                    <p className="mt-3 text-[11px] text-muted-foreground">Bar = how often it happened; marker = what the model predicted on average.</p>
                  </CardContent>
                </Card>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
