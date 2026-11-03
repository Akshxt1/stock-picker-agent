"use client"

import { Suspense, useEffect, useMemo, useState } from "react"
import { useParams, useSearchParams, useRouter } from "next/navigation"
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts"
import { ArrowLeft, Loader2, TrendingUp, TrendingDown, Plus, AlertTriangle } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import AddToPortfolio from "@/components/add-to-portfolio"
import ScenarioOutlook from "@/components/scenario-outlook"
import { assets, type AssetCandle, type AssetClass, type AssetInfo, type AssetMetrics, type AssetQuote } from "@/lib/api"
import { formatMoney, formatPct, shortSymbol } from "@/lib/utils"

const PERIODS_ALL    = ["1mo", "3mo", "6mo", "1y", "5y"] as const
const PERIODS_CRYPTO = ["1mo", "3mo", "6mo", "1y"] as const   // CoinGecko public history is capped at 1y

function safeDecode(s: string): string {
  try { return decodeURIComponent(s) } catch { return s }
}

function toAssetClass(symbol: string, hint: string | null): AssetClass {
  if (symbol.startsWith("CRYPTO:")) return "CRYPTO"
  if (symbol.startsWith("MF:") || hint === "FUND") return "FUND"
  return "EQUITY"
}

export default function AssetDetailPage() {
  return (
    <Suspense fallback={<div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>}>
      <AssetDetail />
    </Suspense>
  )
}

function AssetDetail() {
  const router  = useRouter()
  const params  = useParams<{ symbol: string }>()
  const search  = useSearchParams()
  const symbol  = safeDecode(String(params.symbol ?? ""))
  const aclass  = toAssetClass(symbol, search.get("class"))
  const periods = aclass === "CRYPTO" ? PERIODS_CRYPTO : PERIODS_ALL

  const [period,  setPeriod]  = useState<string>("1y")
  const [info,    setInfo]    = useState<AssetInfo | null>(null)
  const [quote,   setQuote]   = useState<AssetQuote | null>(null)
  const [quoteErr, setQuoteErr] = useState(false)
  const [candles, setCandles] = useState<AssetCandle[]>([])
  const [metrics, setMetrics] = useState<AssetMetrics | null>(null)
  const [chartLoading, setChartLoading] = useState(true)
  const [chartErr, setChartErr] = useState(false)

  // Identity + live quote: once per symbol.
  useEffect(() => {
    let live = true
    setInfo(null); setQuote(null); setQuoteErr(false)
    assets.info(symbol, aclass).then(r => live && setInfo(r)).catch(() => {})
    assets.quote(symbol, aclass).then(r => live && setQuote(r)).catch(() => live && setQuoteErr(true))
    return () => { live = false }
  }, [symbol, aclass])

  // History + metrics: whenever the period changes.
  useEffect(() => {
    let live = true
    setChartLoading(true); setChartErr(false)
    Promise.allSettled([assets.history(symbol, period, aclass), assets.metrics(symbol, period, aclass)])
      .then(([h, m]) => {
        if (!live) return
        if (h.status === "fulfilled") setCandles(h.value.candles); else { setCandles([]); setChartErr(true) }
        setMetrics(m.status === "fulfilled" ? m.value : null)
        setChartLoading(false)
      })
    return () => { live = false }
  }, [symbol, aclass, period])

  const cur   = quote?.currency ?? info?.currency ?? (aclass === "FUND" && symbol.startsWith("MF:") ? "INR" : "USD")
  const name  = info?.name ?? shortSymbol(symbol)
  const chg   = quote?.day_change_pct ?? null
  const up    = (chg ?? 0) >= 0
  const first = candles[0]?.close
  const last  = candles[candles.length - 1]?.close
  const rangeUp = first != null && last != null ? last >= first : true

  const stats = useMemo(() => !metrics || metrics.observations < 2 ? [] : [
    { label: "Total return",    value: formatPct(metrics.total_return),      tone: metrics.total_return },
    { label: "CAGR",            value: formatPct(metrics.cagr),              tone: metrics.cagr },
    { label: "Volatility (ann.)", value: formatPct(metrics.annual_volatility).replace("+", "") },
    { label: "Sharpe ratio",    value: metrics.sharpe != null ? metrics.sharpe.toFixed(2) : "—" },
    { label: "Max drawdown",    value: formatPct(metrics.max_drawdown),      tone: metrics.max_drawdown },
    { label: "Now vs peak",     value: formatPct(metrics.current_drawdown),  tone: metrics.current_drawdown },
    { label: "Best day",        value: formatPct(metrics.best_day),          tone: metrics.best_day },
    { label: "Worst day",       value: formatPct(metrics.worst_day),         tone: metrics.worst_day },
  ], [metrics])

  return (
    <div className="space-y-5">
      <button onClick={() => router.push("/assets")}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-3.5 w-3.5" /> Crypto &amp; Funds
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-2xl font-bold leading-tight">{name}</h2>
            <Badge variant="outline" className="text-[10px]">{aclass === "CRYPTO" ? "Crypto" : "Fund"}</Badge>
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{symbol}</p>
          {(info?.fund_house || info?.category) && (
            <p className="mt-1 text-xs text-muted-foreground">
              {[info.fund_house, info.category].filter(Boolean).join(" · ")}
            </p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            {quote ? (
              <>
                <p className="text-3xl font-bold tracking-tight">{formatMoney(quote.price, cur)}</p>
                {chg != null && (
                  <p className={`flex items-center justify-end gap-1 text-sm font-semibold ${up ? "gain" : "loss"}`}>
                    {up ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                    {up ? "+" : ""}{chg.toFixed(2)}% {aclass === "CRYPTO" ? "24h" : "1d"}
                  </p>
                )}
                {quote.as_of && <p className="text-[11px] text-muted-foreground">NAV as of {quote.as_of}</p>}
              </>
            ) : quoteErr ? (
              <p className="text-sm text-muted-foreground">Price unavailable</p>
            ) : (
              <Loader2 className="ml-auto h-5 w-5 animate-spin text-muted-foreground" />
            )}
          </div>
          {quote && (
            <AddToPortfolio
              ticker={symbol}
              assetClass={aclass}
              name={info?.name ?? undefined}
              label={name}
              defaultPrice={quote.price}
              currency={cur}
              trigger={
                <button className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-xs font-semibold text-primary-foreground hover:opacity-90 transition-opacity">
                  <Plus className="h-3.5 w-3.5" /> Add to Portfolio
                </button>
              }
            />
          )}
        </div>
      </div>

      {/* Chart */}
      <Card className="border-border/60">
        <CardContent className="pt-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">{aclass === "FUND" && symbol.startsWith("MF:") ? "NAV history" : "Price history"}</h3>
            <div className="flex gap-1 rounded-lg bg-muted/50 p-0.5">
              {periods.map(p => (
                <button key={p} onClick={() => setPeriod(p)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all ${
                    period === p ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                  {p}
                </button>
              ))}
            </div>
          </div>
          {chartLoading ? (
            <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : candles.length === 0 ? (
            <div className="flex h-64 items-center justify-center gap-2 text-sm text-muted-foreground">
              {chartErr && <AlertTriangle className="h-4 w-4" />}
              {chartErr ? "Price history is temporarily unavailable." : "No price data available."}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={candles} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="assetFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={`hsl(var(--${rangeUp ? "gain" : "loss"}))`} stopOpacity={0.35} />
                    <stop offset="100%" stopColor={`hsl(var(--${rangeUp ? "gain" : "loss"}))`} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={40} stroke="hsl(var(--muted-foreground))" />
                <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10 }} width={62}
                  stroke="hsl(var(--muted-foreground))" tickFormatter={v => formatMoney(v, cur)} />
                <Tooltip
                  contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
                  formatter={(v: any) => [formatMoney(Number(v), cur), "Close"]} />
                <Area type="monotone" dataKey="close" strokeWidth={2}
                  stroke={`hsl(var(--${rangeUp ? "gain" : "loss"}))`} fill="url(#assetFill)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      <ScenarioOutlook symbol={symbol} assetClass={aclass} />

      {/* Risk & return */}
      <Card className="border-border/60">
        <CardContent className="pt-5">
          <div className="mb-3 flex items-baseline justify-between">
            <h3 className="text-sm font-semibold">Risk &amp; return · {period}</h3>
            {metrics?.start && <span className="text-[11px] text-muted-foreground">{metrics.start} → {metrics.end}</span>}
          </div>
          {chartLoading ? (
            <div className="flex h-24 items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
          ) : stats.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">Not enough data to compute risk metrics.</p>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {stats.map(s => (
                  <div key={s.label} className="rounded-lg border border-border/50 bg-muted/20 p-3">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{s.label}</p>
                    <p className={`mt-1 text-base font-semibold ${
                      s.tone == null ? "" : s.tone >= 0 ? "gain" : "loss"}`}>{s.value}</p>
                  </div>
                ))}
              </div>
              {metrics?.rolling_returns && (
                <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs">
                  <span className="text-muted-foreground">Rolling returns</span>
                  {(["1m", "3m", "6m", "1y"] as const).map(k => {
                    const v = metrics.rolling_returns?.[k]
                    return (
                      <span key={k}>
                        <span className="text-muted-foreground">{k} </span>
                        <span className={`font-semibold ${v == null ? "" : v >= 0 ? "gain" : "loss"}`}>{formatPct(v)}</span>
                      </span>
                    )
                  })}
                </div>
              )}
            </>
          )}
          <p className="mt-4 text-[11px] leading-relaxed text-muted-foreground">
            Volatility is the annualised swing in daily returns; max drawdown is the worst peak-to-trough fall in the window.
            Past performance does not predict future returns — this is information, not investment advice.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
