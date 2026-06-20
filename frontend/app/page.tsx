"use client"

import { useEffect, useState } from "react"
import { useAuth }             from "@/lib/auth-context"
import { market, type NewsItem, type IndexQuote } from "@/lib/api"
import AgentStream             from "@/components/agent-stream"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge }               from "@/components/ui/badge"
import {
  TrendingUp, TrendingDown, Globe, Activity,
  Newspaper, Clock, ExternalLink, Briefcase,
  Zap, BarChart2,
} from "lucide-react"

interface MarketStatus {
  open:  boolean
  tz:    string
  hours: string
}

interface Mover {
  symbol:     string
  price:      number
  change_pct: number
  currency?:  string
}

export default function Dashboard() {
  const { user, isGuest } = useAuth()
  const firstName = user?.name?.split(" ")[0] ?? user?.email?.split("@")[0] ?? "there"

  const [status,       setStatus]       = useState<Record<string, MarketStatus>>({})
  const [news,         setNews]         = useState<NewsItem[]>([])
  const [gainers,      setGainers]      = useState<Mover[]>([])
  const [losers,       setLosers]       = useState<Mover[]>([])
  const [newsLoading,  setNewsLoading]  = useState(true)
  const [moversLoading,setMoversLoading]= useState(true)
  const [indices,      setIndices]      = useState<IndexQuote[]>([])
  const [mkt,          setMkt]          = useState<"INDIA" | "US" | "BOTH">("INDIA")

  // Pick the default market based on which exchange is live.
  useEffect(() => {
    market.status().then(s => {
      setStatus(s)
      if (s?.NSE?.open && s?.NYSE?.open) setMkt("BOTH")
      else if (s?.NYSE?.open && !s?.NSE?.open) setMkt("US")
      else setMkt("INDIA")
    }).catch(() => {})
    market.indices().then(setIndices).catch(() => {})
  }, [])

  // Re-fetch movers + news whenever the selected market changes.
  useEffect(() => {
    setNewsLoading(true); setMoversLoading(true)
    market.news(mkt)
      .then(setNews)
      .catch(() => {})
      .finally(() => setNewsLoading(false))
    market.movers(mkt)
      .then(d => { setGainers(d.gainers ?? []); setLosers(d.losers ?? []) })
      .catch(() => {})
      .finally(() => setMoversLoading(false))
  }, [mkt])

  const hour = new Date().getHours()
  const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening"

  return (
    <div className="space-y-6 animate-fade-in">

      {/* ── Guest banner ── */}
      {isGuest && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3">
          <Zap className="h-4 w-4 text-amber-500 shrink-0" />
          <p className="text-sm text-amber-600 dark:text-amber-400">
            You're viewing as a guest. <a href="/login" className="font-semibold underline">Sign in</a> to run AI analysis.
          </p>
        </div>
      )}

      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {greeting}, <span className="gradient-text capitalize">{firstName}</span>
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
          </p>
        </div>
        <div className="flex gap-2">
          {Object.entries(status).map(([name, s]) => (
            <div
              key={name}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${
                s.open
                  ? "bg-accent/10 border-accent/30 text-accent"
                  : "bg-muted/60 border-border/60 text-muted-foreground"
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${s.open ? "bg-accent animate-pulse" : "bg-muted-foreground"}`} />
              {name} {s.open ? "OPEN" : "CLOSED"}
            </div>
          ))}
        </div>
      </div>

      {/* ── Live index cards ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {indices.length === 0
          ? [0,1,2,3].map(i => <IndexCard key={i} loading />)
          : indices.map(ix => (
              <IndexCard
                key={ix.key}
                label={ix.label}
                value={ix.value}
                changePct={ix.change_pct}
                currency={ix.currency}
                live={ix.currency === "INR" ? status.NSE?.open : status.NYSE?.open}
              />
            ))}
      </div>

      {/* ── Main 2-col grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

        {/* Left: Agent stream (3/5) */}
        <div className="lg:col-span-3">
          <AgentStream />
        </div>

        {/* Right: News + Movers (2/5) */}
        <div className="lg:col-span-2 space-y-4">

          {/* Market toggle */}
          <div className="flex items-center justify-end">
            <div className="flex gap-1 rounded-lg bg-muted/50 p-0.5">
              {(["INDIA", "US", "BOTH"] as const).map(m => (
                <button key={m} onClick={() => setMkt(m)}
                  className={`rounded-md px-3 py-1 text-xs font-semibold transition-all ${
                    mkt === m ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"
                  }`}>
                  {m === "INDIA" ? "🇮🇳 IND" : m === "US" ? "🇺🇸 US" : "🌐 Both"}
                </button>
              ))}
            </div>
          </div>

          {/* Movers */}
          <Card className="border-border/60">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-accent" />
                Top Movers · {mkt === "INDIA" ? "India" : mkt === "US" ? "US" : "India + US"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 pt-0">
              {moversLoading ? (
                <p className="text-xs text-muted-foreground py-2">Loading market data…</p>
              ) : gainers.length === 0 && losers.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2">No movers data available.</p>
              ) : (
                <>
                  {gainers.slice(0, 3).map(m => (
                    <MoverRow key={m.symbol} {...m} up ccy={m.currency === "USD" ? "$" : "₹"} />
                  ))}
                  <div className="my-2 h-px bg-border/40" />
                  {losers.slice(0, 3).map(m => (
                    <MoverRow key={m.symbol} {...m} up={false} ccy={m.currency === "USD" ? "$" : "₹"} />
                  ))}
                </>
              )}
            </CardContent>
          </Card>

          {/* News */}
          <Card className="border-border/60">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Newspaper className="h-4 w-4 text-primary" />
                Market News · {mkt === "INDIA" ? "India" : mkt === "US" ? "US" : "Global"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 pt-0">
              {newsLoading ? (
                <p className="text-xs text-muted-foreground py-2">Loading news…</p>
              ) : news.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2">No news available.</p>
              ) : (
                news.slice(0, 6).map((item, i) => (
                  <a
                    key={i}
                    href={item.link || "#"}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group flex flex-col gap-0.5 hover:bg-muted/40 rounded-lg p-1.5 -mx-1.5 transition-colors"
                  >
                    <p className="text-xs font-medium leading-snug line-clamp-2 group-hover:text-primary transition-colors">
                      {item.title}
                      <ExternalLink className="inline-block ml-1 h-2.5 w-2.5 opacity-0 group-hover:opacity-60 transition-opacity" />
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px] text-muted-foreground">{item.publisher}</span>
                      {item.published && (
                        <>
                          <span className="text-[10px] text-border">·</span>
                          <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                            <Clock className="h-2.5 w-2.5" />
                            {item.published}
                          </span>
                        </>
                      )}
                    </div>
                  </a>
                ))
              )}
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  )
}

function IndexCard({ label, value, changePct, currency, live, loading }: {
  label?:     string
  value?:     number | null
  changePct?: number | null
  currency?:  string
  live?:      boolean
  loading?:   boolean
}) {
  const sym = currency === "USD" ? "$" : "₹"
  const up  = (changePct ?? 0) >= 0
  return (
    <Card className="border-border/60 shine overflow-hidden">
      <CardContent className="pt-5 pb-4 px-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wide">
            {loading ? "—" : label}
          </p>
          {!loading && live !== undefined && (
            <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full ${
              live ? "bg-accent/15 text-accent" : "bg-muted text-muted-foreground"
            }`}>
              {live ? "LIVE" : "CLOSED"}
            </span>
          )}
        </div>
        {loading ? (
          <div className="h-6 w-20 rounded bg-muted/50 animate-pulse" />
        ) : (
          <>
            <p className="text-xl font-bold leading-none">
              {value != null ? `${sym}${value.toLocaleString(currency === "USD" ? "en-US" : "en-IN")}` : "—"}
            </p>
            {changePct != null && (
              <p className={`mt-1 flex items-center gap-1 text-[11px] font-semibold ${up ? "gain" : "loss"}`}>
                {up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                {up ? "+" : ""}{changePct.toFixed(2)}%
              </p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

function MoverRow({ symbol, price, change_pct, up, ccy }: {
  symbol: string; price: number; change_pct: number; up: boolean; ccy: string
}) {
  const locale = ccy === "₹" ? "en-IN" : "en-US"
  return (
    <div className="flex items-center justify-between py-1">
      <div className="flex items-center gap-2">
        <div className={`flex h-6 w-6 items-center justify-center rounded-md ${
          up ? "bg-accent/10" : "bg-destructive/10"
        }`}>
          {up
            ? <TrendingUp   className="h-3 w-3 text-accent" />
            : <TrendingDown className="h-3 w-3 text-destructive" />
          }
        </div>
        <span className="text-xs font-semibold">{symbol.replace(".NS", "")}</span>
      </div>
      <div className="text-right">
        <p className="text-xs font-medium">{ccy}{price.toLocaleString(locale)}</p>
        <p className={`text-[10px] font-semibold ${up ? "gain" : "loss"}`}>
          {up ? "+" : ""}{change_pct.toFixed(2)}%
        </p>
      </div>
    </div>
  )
}
