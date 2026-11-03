"use client"

import { useEffect, useRef, useState } from "react"
import { AlertTriangle, Check, Download, Info, Loader2, Sparkles } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  portfolio, portfolioAgent,
  type AgentAnalysis, type AgentHoldingIn, type AgentSimHorizon, type AgentStrategy,
} from "@/lib/api"
import { formatMoney, formatPct } from "@/lib/utils"

const ACTION_STYLE: Record<string, string> = {
  exit: "bg-[hsl(var(--loss))]/15 text-[hsl(var(--loss))]",
  trim: "bg-[hsl(var(--loss))]/10 text-[hsl(var(--loss))]",
  hedge: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  add: "bg-[hsl(var(--gain))]/15 text-[hsl(var(--gain))]",
  rebalance: "bg-primary/15 text-primary",
  hold: "bg-muted text-muted-foreground",
  review: "bg-muted text-muted-foreground",
}

const tone = (v?: number | null) => (v == null ? "" : v >= 0 ? "gain" : "loss")

function Stat({ label, value, sub, cls = "" }: { label: string; value: string; sub?: string; cls?: string }) {
  return (
    <div className="rounded-lg border border-border/50 bg-muted/20 p-3">
      <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={`mt-1 text-base font-semibold ${cls}`}>{value}</p>
      {sub && <p className="mt-0.5 text-[10px] text-muted-foreground">{sub}</p>}
    </div>
  )
}

function breakevenKey(be: number | null): string | null {
  return be != null && be > 0 && be < 2 ? `+${(be * 100).toFixed(1)}%` : null
}

function Feasibility({ a }: { a: AgentAnalysis }) {
  const sim = a.simulation
  if (!sim) return (
    <p className="text-sm text-muted-foreground">There isn&apos;t enough shared price history across these holdings to simulate the portfolio as a whole.</p>
  )
  const entries = Object.entries(sim.horizons)
  const be = a.portfolio.breakeven_return
  const key = breakevenKey(be)
  const two = (sim.horizons["2 months"] ?? entries[entries.length - 1]?.[1]) as AgentSimHorizon | undefined
  const beChance = key && two ? two.prob_at_least[key] : null
  return (
    <div className="space-y-3">
      {be != null && be > 0 && beChance != null && (
        <p className="rounded-lg border border-border/50 bg-muted/20 p-3 text-sm">
          To get back to break-even this portfolio needs <b className="loss">{formatPct(be, 1)}</b>. In{" "}
          {two ? entries.find(([, v]) => v === two)?.[0] : "the period"}, it got there in{" "}
          <b>{(beChance * 100).toFixed(beChance < 0.01 && beChance > 0 ? 1 : 0)}%</b> of simulated paths.
        </p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-wide text-muted-foreground">
              <th className="pb-2 font-medium">Over</th>
              <th className="pb-2 font-medium">Chance of a loss</th>
              <th className="pb-2 font-medium">Bad / typical / good case</th>
              <th className="pb-2 font-medium">Chance of gaining at least…</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(([label, h]) => (
              <tr key={label} className="border-t border-border/40 align-top">
                <td className="py-2 font-medium">{label}</td>
                <td className="py-2 tabular-nums">{(h.prob_loss * 100).toFixed(0)}%</td>
                <td className="py-2 tabular-nums">
                  <span className="loss">{formatPct(h.quantiles.p5, 1)}</span> / {formatPct(h.quantiles.p50, 1)} /{" "}
                  <span className="gain">{formatPct(h.quantiles.p95, 1)}</span>
                </td>
                <td className="py-2">
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(h.prob_at_least).map(([t, p]) => (
                      <span key={t} className={`rounded px-1.5 py-0.5 tabular-nums ${t === key ? "border border-primary/60" : ""} bg-muted/50`}>
                        {t === "+0.0%" ? "any gain" : t}{t === key ? " (break-even)" : ""}: <b>{(p * 100).toFixed(p > 0 && p < 0.01 ? 1 : 0)}%</b>
                      </span>
                    ))}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-muted-foreground">
        Simulated from how these exact holdings moved together over the last {sim.common_days} trading days, with past
        gains or losses removed so the past isn&apos;t assumed to repeat. It shows how wide the outcomes can be, not a forecast.
      </p>
    </div>
  )
}

function StrategyView({ s }: { s: AgentStrategy }) {
  return (
    <div className="space-y-5 text-sm">
      <div className="rounded-lg border border-primary/30 bg-primary/5 p-4">
        <p className="font-semibold">{s.headline}</p>
        {s.goal_feasibility && <p className="mt-2 text-muted-foreground">{s.goal_feasibility}</p>}
      </div>
      {s.diagnosis.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">What the numbers show</h4>
          <ul className="list-disc space-y-1.5 pl-5 text-muted-foreground">{s.diagnosis.map((d, i) => <li key={i}>{d}</li>)}</ul>
        </div>
      )}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Suggested plan</h4>
        <ol className="space-y-2.5">
          {s.plan.map((p, i) => (
            <li key={i} className="rounded-lg border border-border/50 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${ACTION_STYLE[p.action] ?? ACTION_STYLE.review}`}>{p.action}</span>
                {p.symbol && <Badge variant="outline">{p.symbol.replace(/^(CRYPTO|MF):/, "")}</Badge>}
              </div>
              <p className="mt-1.5 font-medium">{p.what}</p>
              {p.why && <p className="mt-0.5 text-xs text-muted-foreground">{p.why}</p>}
            </li>
          ))}
        </ol>
      </div>
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">If markets…</h4>
        <div className="grid gap-2 sm:grid-cols-3">
          {([["rise", "Rise", "gain"], ["flat", "Stay flat", ""], ["fall", "Fall", "loss"]] as const).map(([k, label, c]) =>
            s.if_markets[k] ? (
              <div key={k} className="rounded-lg border border-border/50 bg-muted/20 p-3">
                <p className={`mb-1 text-[10px] font-semibold uppercase tracking-wide ${c}`}>{label}</p>
                <p className="text-xs text-muted-foreground">{s.if_markets[k]}</p>
              </div>
            ) : null)}
        </div>
      </div>
      {s.risks.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">What could go wrong</h4>
          <ul className="list-disc space-y-1.5 pl-5 text-muted-foreground">{s.risks.map((d, i) => <li key={i}>{d}</li>)}</ul>
        </div>
      )}
      {s.next_steps.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Next steps</h4>
          <ul className="list-disc space-y-1.5 pl-5 text-muted-foreground">{s.next_steps.map((d, i) => <li key={i}>{d}</li>)}</ul>
        </div>
      )}
    </div>
  )
}

export default function ResultsStep({ analysis, holdings, goal, risk, onRestart }: {
  analysis: AgentAnalysis
  holdings: AgentHoldingIn[]
  goal: string
  risk: string
  onRestart: () => void
}) {
  const p = analysis.portfolio
  const cur = analysis.base_currency
  const [phase, setPhase] = useState<"idle" | "running" | "done" | "error">("idle")
  const [progress, setProgress] = useState<string | null>(null)
  const [strategy, setStrategy] = useState<AgentStrategy | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)
  const [imp, setImp] = useState<{ done: number; total: number; failed: number; finished: boolean } | null>(null)

  useEffect(() => () => { if (timer.current) clearInterval(timer.current) }, [])

  async function generate() {
    setPhase("running"); setErr(null); setProgress("Starting…")
    try {
      const { job_id } = await portfolioAgent.startStrategy(holdings, goal, risk)
      const started = Date.now()
      timer.current = setInterval(async () => {
        try {
          const j = await portfolioAgent.job(job_id)
          setProgress(j.progress)
          if (j.status === "done" && j.result) {
            clearInterval(timer.current!); setStrategy(j.result.strategy); setPhase("done")
          } else if (j.status === "error") {
            clearInterval(timer.current!); setErr(j.error ?? "Something went wrong."); setPhase("error")
          } else if (Date.now() - started > 6 * 60 * 1000) {
            clearInterval(timer.current!); setErr("This is taking too long. Please try again."); setPhase("error")
          }
        } catch { /* transient network error: keep polling */ }
      }, 3000)
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Couldn't start."); setPhase("error")
    }
  }

  async function importAll() {
    const byPrice = new Map(analysis.holdings.map(h => [h.symbol.toUpperCase(), h]))
    setImp({ done: 0, total: holdings.length, failed: 0, finished: false })
    let done = 0, failed = 0
    for (const h of holdings) {
      const live = byPrice.get(h.symbol.toUpperCase())
      const price = h.avg_price ?? live?.price
      try {
        if (!price) throw new Error("no price")
        await portfolio.add(h.symbol, h.quantity, price, { assetClass: h.asset_class ?? undefined, name: h.name ?? undefined })
        done++
      } catch { failed++ }
      setImp({ done, total: holdings.length, failed, finished: false })
    }
    setImp({ done, total: holdings.length, failed, finished: true })
  }

  return (
    <div className="space-y-4">
      <Card className="border-border/60">
        <CardContent className="pt-5">
          <h3 className="mb-3 text-sm font-semibold">Your portfolio today</h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat label="Value" value={formatMoney(p.value, cur)} sub={`${p.n_holdings} holdings`} />
            <Stat label="Profit / loss" value={p.pnl_pct == null ? "—" : formatPct(p.pnl_pct, 1)} cls={tone(p.pnl_pct)}
              sub={p.pnl_amount == null ? "no buy prices" : `${p.pnl_amount < 0 ? "-" : "+"}${formatMoney(Math.round(Math.abs(p.pnl_amount)), cur)}`} />
            <Stat label="Gain needed to break even" value={p.breakeven_return != null && p.breakeven_return > 0 ? formatPct(p.breakeven_return, 1) : "—"} />
            <Stat label="Volatility (yearly)" value={p.annual_volatility != null ? formatPct(p.annual_volatility, 0).replace("+", "") : "—"}
              sub={p.diversification_ratio ? `diversification ${p.diversification_ratio.toFixed(2)}×` : undefined} />
            <Stat label="Top 3 holdings" value={`${(p.top3_weight * 100).toFixed(0)}%`} sub="of portfolio value" />
            <Stat label="Effective holdings" value={p.effective_n.toFixed(1)} sub={`of ${p.n_holdings} held`} />
            <Stat label="Avg correlation" value={p.avg_correlation != null ? p.avg_correlation.toFixed(2) : "—"} sub="1 = move together" />
            <Stat label="Mix" value={Object.entries(p.by_asset_class).map(([k, v]) => `${Math.round(v * 100)}% ${k === "EQUITY" ? "stocks" : k.toLowerCase()}`).join(" · ")} />
          </div>
          {analysis.notes.length > 0 && (
            <ul className="mt-3 space-y-1 text-[11px] text-muted-foreground">
              {analysis.notes.map((n, i) => <li key={i} className="flex gap-1.5"><Info className="mt-0.5 h-3 w-3 shrink-0" />{n}</li>)}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="border-border/60">
        <CardContent className="pt-5">
          <h3 className="mb-3 text-sm font-semibold">How realistic is your goal?</h3>
          <Feasibility a={analysis} />
        </CardContent>
      </Card>

      <Card className="border-border/60">
        <CardContent className="pt-5">
          <h3 className="mb-3 text-sm font-semibold">Holding by holding</h3>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[34rem] text-xs">
              <thead>
                <tr className="text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                  <th className="pb-2 font-medium">Holding</th>
                  <th className="pb-2 text-right font-medium">Weight</th>
                  <th className="pb-2 text-right font-medium">P&amp;L</th>
                  <th className="pb-2 text-right font-medium" title="Share of the portfolio's total risk">Risk share</th>
                  <th className="pb-2 text-right font-medium">Volatility</th>
                  <th className="pb-2 text-right font-medium" title="Chance of falling more than 5% over 3 months">Chance of −5%+ (3m)</th>
                </tr>
              </thead>
              <tbody>
                {analysis.holdings.map(h => (
                  <tr key={h.symbol} className="border-t border-border/40">
                    <td className="py-2"><p className="font-medium">{h.name ?? h.display}</p><p className="text-[10px] text-muted-foreground">{h.symbol.replace(/^(CRYPTO|MF):/, "")}</p></td>
                    <td className="py-2 text-right tabular-nums">{(h.weight * 100).toFixed(1)}%</td>
                    <td className={`py-2 text-right tabular-nums ${tone(h.pnl_pct)}`}>{h.pnl_pct == null ? "—" : formatPct(h.pnl_pct, 1)}</td>
                    <td className={`py-2 text-right tabular-nums ${h.risk_share != null && h.risk_share > h.weight * 1.3 ? "loss" : ""}`}>{h.risk_share == null ? "—" : `${(h.risk_share * 100).toFixed(0)}%`}</td>
                    <td className="py-2 text-right tabular-nums">{h.metrics?.annual_volatility == null ? "—" : `${(h.metrics.annual_volatility * 100).toFixed(0)}%`}</td>
                    <td className="py-2 text-right tabular-nums">{h.outlook_3m ? `${(h.outlook_3m.downside * 100).toFixed(0)}%` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/60">
        <CardContent className="pt-5">
          <h3 className="mb-1 flex items-center gap-2 text-sm font-semibold"><Sparkles className="h-4 w-4 text-primary" /> AI strategy</h3>
          {goal && <p className="mb-3 text-xs text-muted-foreground">For: “{goal}” · {risk} risk</p>}
          {phase === "idle" && (
            <>
              <p className="mb-3 text-xs text-muted-foreground">
                Writes a plan grounded in the numbers above. It takes about a minute and uses 1 of your weekly portfolio analyses.
              </p>
              <Button onClick={generate} className="gap-2"><Sparkles className="h-4 w-4" /> Write my strategy</Button>
            </>
          )}
          {phase === "running" && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /> {progress ?? "Working…"}</p>
          )}
          {phase === "error" && (
            <div className="space-y-3">
              <div className="flex items-start gap-2 rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {err}
              </div>
              <Button variant="outline" onClick={generate}>Try again</Button>
            </div>
          )}
          {phase === "done" && strategy && <StrategyView s={strategy} />}
          <p className="mt-5 text-[11px] leading-relaxed text-muted-foreground">
            Educational analysis based on your numbers and past market behaviour. It is not personalised financial advice, can be wrong,
            and no outcome is guaranteed. Consider taxes and trading costs, and speak to a licensed adviser before acting.
          </p>
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" onClick={onRestart}>Start over</Button>
        <Button variant="outline" onClick={importAll} disabled={!!imp && !imp.finished} className="gap-2">
          {imp && !imp.finished ? <Loader2 className="h-4 w-4 animate-spin" /> : imp?.finished ? <Check className="h-4 w-4" /> : <Download className="h-4 w-4" />}
          {imp?.finished ? `Imported ${imp.done}${imp.failed ? ` (${imp.failed} failed)` : ""}` : imp ? `Importing ${imp.done}/${imp.total}…` : "Import into my portfolio"}
        </Button>
        {imp?.finished && imp.done > 0 && <a href="/portfolio" className="text-xs text-primary underline">View portfolio</a>}
      </div>
      <p className="text-[11px] text-muted-foreground">Import adds these holdings to your Portfolio page; any without a buy price use today&apos;s price.</p>
    </div>
  )
}
