"use client"

import { useEffect, useState, useRef, useCallback } from "react"
import { TrendingUp, TrendingDown } from "lucide-react"

interface Tick {
  symbol:     string
  display:    string
  price:      number | null
  change_pct: number | null
  currency:   "INR" | "USD"
}

function marketStatus(): { nse: boolean; nyse: boolean } {
  const now = new Date()
  const IST = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }))
  const EST = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }))

  const nseDay = IST.getDay(), nyseDay = EST.getDay()
  const nseMins  = IST.getHours()  * 60 + IST.getMinutes()
  const nyseMins = EST.getHours()  * 60 + EST.getMinutes()

  const nse  = nseDay  > 0 && nseDay  < 6 && nseMins  >= 9*60+15 && nseMins  <= 15*60+30
  const nyse = nyseDay > 0 && nyseDay < 6 && nyseMins >= 9*60+30 && nyseMins <  16*60

  return { nse, nyse }
}

const INDIA = ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
               "WIPRO.NS","TATAMOTORS.NS","SBIN.NS","BAJFINANCE.NS","HCLTECH.NS"]
const US    = ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","JPM","V","NFLX"]

function currSym(tick: Tick): string {
  // Prefer explicit field, but derive from symbol as fallback
  if (tick.currency === "INR") return "₹"
  if (tick.currency === "USD") return "$"
  return tick.symbol.endsWith(".NS") || tick.symbol.endsWith(".BO") ? "₹" : "$"
}

function displayName(tick: Tick): string {
  return (tick.display || tick.symbol)
    .replace(".NS", "")
    .replace(".BO", "")
}

export default function TickerTape() {
  const [ticks,   setTicks]   = useState<Tick[]>([])
  const [label,   setLabel]   = useState("")
  const [live,    setLive]    = useState(true)
  const [loading, setLoading] = useState(true)
  const lastTicks = useRef<Tick[]>([])    // persist across market-closed gaps

  const refresh = useCallback(async () => {
    const { nse, nyse } = marketStatus()

    // When no market is live, keep showing last known data
    if (!nse && !nyse) {
      if (lastTicks.current.length > 0) {
        setTicks(lastTicks.current)
        // Label shows which market's data we're displaying
        const hasIndia = lastTicks.current.some(t => t.symbol.endsWith(".NS"))
        setLabel(hasIndia ? "India Market (Closed)" : "US Market (Closed)")
        setLive(false)
        setLoading(false)
      } else {
        setLoading(false)
      }
      return
    }

    // Decide which symbols to fetch — India takes priority when both open
    const syms  = nse ? INDIA : US
    const lbl   = nse ? "India Market" : "US Market"
    setLabel(lbl)
    setLive(true)

    try {
      const BASE  = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
      const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null
      const res   = await fetch(`${BASE}/api/market/ticker?symbols=${syms.join(",")}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!res.ok) return
      const data: Tick[] = await res.json()
      const valid = data.filter(t => t.price !== null)
      if (valid.length > 0) {
        setTicks(valid)
        lastTicks.current = valid
      }
    } catch {
      // silent — keep last known data
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 60_000)
    return () => clearInterval(id)
  }, [refresh])

  if (loading) {
    return (
      <div className="h-8 border-b border-border/40 bg-card/60 flex items-center px-4 gap-6 overflow-hidden shrink-0">
        <span className="text-[10px] font-bold text-primary/60 shrink-0 mr-2">LOADING</span>
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-2.5 w-24 rounded bg-muted/60 animate-shimmer" />
        ))}
      </div>
    )
  }

  if (ticks.length === 0) return null

  const doubled = [...ticks, ...ticks]

  return (
    <div className="h-8 border-b border-border/40 bg-card/60 flex items-center overflow-hidden select-none shrink-0">
      <div className="shrink-0 px-3 border-r border-border/40 flex items-center gap-1.5 h-full">
        <span className="text-[10px] font-bold text-primary tracking-widest uppercase">{label}</span>
        {live
          ? <span className="h-1.5 w-1.5 rounded-full bg-green-500 animate-pulse" />
          : <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground/50" />
        }
      </div>
      <div className="flex-1 overflow-hidden">
        <div className="flex items-center gap-5 ticker-track whitespace-nowrap">
          {doubled.map((t, i) => {
            const up  = (t.change_pct ?? 0) >= 0
            const cs  = currSym(t)
            const dn  = displayName(t)
            return (
              <span key={i} className="inline-flex items-center gap-1.5 text-[11px] font-medium shrink-0">
                <span className="text-primary/90 font-mono font-bold tracking-tight">{dn}</span>
                <span className="text-foreground font-semibold">
                  {cs}{t.price?.toLocaleString("en-IN", { maximumFractionDigits: 2 })}
                </span>
                <span className={`flex items-center gap-0.5 font-semibold ${up ? "gain" : "loss"}`}>
                  {up
                    ? <TrendingUp   className="h-2.5 w-2.5" />
                    : <TrendingDown className="h-2.5 w-2.5" />
                  }
                  {up ? "+" : ""}{t.change_pct?.toFixed(2)}%
                </span>
              </span>
            )
          })}
        </div>
      </div>
    </div>
  )
}
