"use client"

import { useEffect, useState } from "react"
import { AlertTriangle, Loader2, ShieldCheck, Sparkles } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import {
  forecast as forecastApi,
  type AssetClass, type Forecast, type ForecastBacktest, type ForecastExplanation, type ForecastHorizon, type ScenarioKey,
} from "@/lib/api"
import { formatPct } from "@/lib/utils"

const HORIZONS: { key: ForecastHorizon; label: string }[] = [
  { key: "3m", label: "3 months" },
  { key: "1y", label: "1 year" },
]

const BAR: Record<ScenarioKey, string> = {
  CRASH:         "bg-[hsl(var(--loss))]",
  DECLINE:       "bg-[hsl(var(--loss))]/55",
  STEADY:        "bg-muted-foreground/45",
  STRONG_GROWTH: "bg-[hsl(var(--gain))]/65",
  MULTIBAGGER:   "bg-[hsl(var(--gain))]",
}

function range(min: number | null, max: number | null): string {
  const pct = (v: number) => `${v > 0 ? "+" : ""}${Math.round(v * 100)}%`
  if (min == null && max != null) return `${pct(max)} or worse`
  if (max == null && min != null) return `${pct(min)} or better`
  if (min != null && max != null) return `${pct(min)} to ${pct(max)}`
  return ""
}

function skillText(b: ForecastBacktest): { tone: string; text: string } {
  if (b.status !== "ok" || b.skill == null) return { tone: "", text: b.detail ?? "Not enough history to test this model." }
  const pct = Math.round(b.skill * 100)
  if (pct > 3)  return { tone: "gain", text: `Beat the historical base rate by ${pct}% on past forecasts.` }
  if (pct < -3) return { tone: "loss", text: `Did worse than the historical base rate (${pct}%) here — treat these odds with extra caution.` }
  return { tone: "", text: "No clear edge over the historical base rate on this asset. Across ~250 assets the model's edge is small (a few percent), mostly in judging how wide outcomes can be." }
}

export default function ScenarioOutlook({ symbol, assetClass }: { symbol: string; assetClass?: AssetClass }) {
  const [horizon, setHorizon] = useState<ForecastHorizon>("3m")
  const [data, setData] = useState<Forecast | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [proof, setProof] = useState<ForecastBacktest | null>(null)
  const [proofLoading, setProofLoading] = useState(false)
  const [proofErr, setProofErr] = useState(false)
  const [why, setWhy] = useState<ForecastExplanation | null>(null)
  const [whyLoading, setWhyLoading] = useState(false)
  const [whyErr, setWhyErr] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    setLoading(true); setErr(null); setProof(null); setProofErr(false); setWhy(null); setWhyErr(null)
    forecastApi.get(symbol, horizon, assetClass)
      .then(r => live && setData(r))
      .catch(e => { if (live) { setData(null); setErr(e instanceof Error ? e.message : "Forecast unavailable.") } })
      .finally(() => live && setLoading(false))
    return () => { live = false }
  }, [symbol, assetClass, horizon])

  function loadProof() {
    setProofLoading(true); setProofErr(false)
    forecastApi.backtest(symbol, horizon, assetClass)
      .then(setProof)
      .catch(() => setProofErr(true))
      .finally(() => setProofLoading(false))
  }

  function loadWhy() {
    setWhyLoading(true); setWhyErr(null)
    forecastApi.explain(symbol, horizon, assetClass)
      .then(setWhy)
      .catch(e => setWhyErr(e instanceof Error ? e.message : "Could not generate an explanation."))
      .finally(() => setWhyLoading(false))
  }

  const top = data ? Math.max(...Object.values(data.probs)) : 0
  const verdict = proof ? skillText(proof) : null

  return (
    <Card className="border-border/60">
      <CardContent className="pt-5">
        <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-semibold">Scenario outlook</h3>
          <div className="flex gap-1 rounded-lg bg-muted/50 p-0.5">
            {HORIZONS.map(h => (
              <button key={h.key} onClick={() => setHorizon(h.key)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all ${
                  horizon === h.key ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                {h.label}
              </button>
            ))}
          </div>
        </div>
        <p className="mb-4 text-xs text-muted-foreground">
          How often each outcome has followed conditions like today&apos;s in this asset&apos;s own history.
        </p>

        {loading ? (
          <div className="flex h-40 items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
        ) : err || !data ? (
          <div className="flex h-24 items-center justify-center gap-2 px-4 text-center text-sm text-muted-foreground">
            <AlertTriangle className="h-4 w-4 shrink-0" /> {err ?? "Forecast unavailable."}
          </div>
        ) : (
          <>
            <div className="space-y-2.5">
              {data.scenarios.map(b => {
                const p = data.probs[b.scenario]
                const base = data.base_rate[b.scenario]
                return (
                  <div key={b.scenario}>
                    <div className="mb-1 flex items-baseline justify-between text-xs">
                      <span className="font-medium">
                        {b.label} <span className="font-normal text-muted-foreground">· {range(b.min, b.max)}</span>
                      </span>
                      <span className={`tabular-nums ${p === top ? "font-semibold" : ""}`}>{(p * 100).toFixed(0)}%</span>
                    </div>
                    <div className="relative h-2.5 overflow-hidden rounded-full bg-muted/40">
                      <div className={`h-full rounded-full ${BAR[b.scenario]}`} style={{ width: `${Math.max(p * 100, 1)}%` }} />
                      <div className="absolute inset-y-0 w-0.5 bg-foreground/60" style={{ left: `${Math.min(base * 100, 99)}%` }}
                        title={`Historical base rate: ${(base * 100).toFixed(0)}%`} />
                    </div>
                  </div>
                )
              })}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">The thin marker on each bar is how often that outcome happened historically, unconditionally.</p>

            {data.low_volatility && (
              <p className="mt-3 rounded-lg border border-border/50 bg-muted/20 p-2.5 text-[11px] text-muted-foreground">
                This is a very low-volatility asset, so outcomes are almost always &ldquo;steady&rdquo;. The odds shown are just
                how often each outcome happened historically, with no model adjustment.
              </p>
            )}

            <div className="mt-4 grid grid-cols-3 gap-3 text-center">
              {([["Bad case", data.quantiles.p5], ["Middle", data.quantiles.p50], ["Good case", data.quantiles.p95]] as const).map(([label, v]) => (
                <div key={label} className="rounded-lg border border-border/50 bg-muted/20 p-3">
                  <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
                  <p className={`mt-1 text-base font-semibold ${v >= 0 ? "gain" : "loss"}`}>{formatPct(v, 1)}</p>
                </div>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">
              Return after {data.horizon_days} days, as of {data.as_of}. About a 1-in-20 chance of doing worse than the bad case, and 1-in-20 of beating the good case.
            </p>

            <div className="mt-4 rounded-lg border border-border/50 bg-muted/20 p-3">
              {proof ? (
                <div className="space-y-1.5 text-xs">
                  <p className={`flex items-center gap-1.5 font-medium ${verdict?.tone}`}>
                    <ShieldCheck className="h-3.5 w-3.5 shrink-0" /> {verdict?.text}
                  </p>
                  {proof.status === "ok" && (
                    <p className="text-muted-foreground">
                      Tested on {proof.n} past forecasts ({proof.first} → {proof.last}). Error score {proof.brier?.toFixed(3)} vs{" "}
                      {proof.brier_base_rate?.toFixed(3)} for the base rate (lower is better). Past forecasts overlap, so small
                      differences are noise.
                    </p>
                  )}
                </div>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                  <span className="text-muted-foreground">How reliable has this model been on {data.symbol.replace(/^(CRYPTO|MF):/, "")}?</span>
                  <button onClick={loadProof} disabled={proofLoading}
                    className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 font-medium hover:bg-muted disabled:opacity-60">
                    {proofLoading && <Loader2 className="h-3 w-3 animate-spin" />} {proofErr ? "Retry check" : "Check track record"}
                  </button>
                </div>
              )}
            </div>
          </>
        )}

        {data && (
          <div className="mt-3 rounded-lg border border-border/50 p-3">
            {why ? (
              <div className="space-y-3 text-xs">
                <p className="font-medium">{why.summary}</p>
                {([["Could be better", why.bull_case, "gain"], ["Could be worse", why.bear_case, "loss"], ["Watch for", why.watch, ""]] as const)
                  .filter(([, items]) => items.length > 0)
                  .map(([title, items, tone]) => (
                    <div key={title}>
                      <p className={`mb-1 text-[10px] font-semibold uppercase tracking-wide ${tone}`}>{title}</p>
                      <ul className="list-disc space-y-1 pl-4 text-muted-foreground">
                        {items.map((t, i) => <li key={i}>{t}</li>)}
                      </ul>
                    </div>
                  ))}
                <p className="text-[10px] text-muted-foreground">
                  Written by AI from the numbers above{why.headlines_used > 0 ? ` and ${why.headlines_used} recent headlines` : ""}. It can be wrong. Not advice.
                </p>
              </div>
            ) : (
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                <span className="text-muted-foreground">
                  {whyErr ?? "Want the odds explained in plain words, with the case for and against?"}
                </span>
                <button onClick={loadWhy} disabled={whyLoading}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border px-2.5 py-1 font-medium hover:bg-muted disabled:opacity-60">
                  {whyLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Sparkles className="h-3 w-3" />}
                  {whyErr ? "Try again" : "Explain this outlook"}
                </button>
              </div>
            )}
          </div>
        )}

        <p className="mt-4 text-[11px] leading-relaxed text-muted-foreground">
          Statistical estimates from past price behaviour, not predictions or investment advice. Real outcomes can fall outside
          any range shown, especially during crises.
        </p>
      </CardContent>
    </Card>
  )
}
