"use client"

import { useEffect, useMemo, useState } from "react"
import { portfolio, fx, type Holding } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input }  from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import HoldingRow from "@/components/holding-row"
import {
  Plus, Loader2, ArrowLeftRight, TrendingUp, TrendingDown, Sparkles, Wallet,
} from "lucide-react"
import { isIndianTicker, formatMoney } from "@/lib/utils"

type DisplayCcy = "INR" | "USD"

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [loading,  setLoading]  = useState(true)
  const [market,   setMarket]   = useState<"INDIA" | "US">("INDIA")
  const [ticker,   setTicker]   = useState("")
  const [qty,      setQty]      = useState("")
  const [price,    setPrice]    = useState("")
  const [adding,   setAdding]   = useState(false)
  const [showAdd,  setShowAdd]  = useState(false)
  const [usdInr,   setUsdInr]   = useState<number | null>(null)
  const [allCcy,   setAllCcy]   = useState<DisplayCcy>("INR")
  const [analyzing, setAnalyzing] = useState(false)
  const [tab,      setTab]      = useState<"ind" | "us" | "all">("all")

  async function load() {
    try { setHoldings(await portfolio.list()) }
    catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])
  useEffect(() => { fx.rate("USDINR").then(r => setUsdInr(r.rate)).catch(() => {}) }, [])

  function normalizeTicker(raw: string, mkt: "INDIA" | "US"): string {
    const t = raw.trim().toUpperCase()
    if (mkt === "INDIA" && !t.endsWith(".NS") && !t.endsWith(".BO")) return `${t}.NS`
    if (mkt === "US") return t.replace(/\.(NS|BO)$/i, "")
    return t
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault()
    const parsedQty = parseFloat(qty)
    const parsedPrice = parseFloat(price)
    if (!ticker || !qty || !price || parsedQty <= 0 || parsedPrice <= 0 || isNaN(parsedQty) || isNaN(parsedPrice)) return
    setAdding(true)
    try {
      await portfolio.add(normalizeTicker(ticker, market), parsedQty, parsedPrice)
      setTicker(""); setQty(""); setPrice(""); setShowAdd(false)
      await load()
    } finally { setAdding(false) }
  }

  async function analyzePortfolio() {
    setAnalyzing(true)
    try {
      const mkt = tab === "ind" ? "INDIA" : tab === "us" ? "US" : undefined
      await portfolio.analyzeAll(mkt)
      await load()
    } catch (e: any) {
      alert(e?.message || "Analysis failed")
    } finally { setAnalyzing(false) }
  }

  const ind = useMemo(() => holdings.filter(h => h.market === "INDIA"), [holdings])
  const us  = useMemo(() => holdings.filter(h => h.market === "US"),    [holdings])

  const noConvert = (v: number | null | undefined) => (v == null ? null : v)
  function convertTo(target: DisplayCcy) {
    return (v: number | null | undefined, from: string | null | undefined): number | null => {
      if (v == null) return null
      if (!usdInr || !from || from === target) return v
      if (from === "USD" && target === "INR") return v * usdInr
      if (from === "INR" && target === "USD") return v / usdInr
      return v
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Wallet className="h-6 w-6" /> Portfolio
        </h2>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={analyzePortfolio} disabled={analyzing || holdings.length === 0} className="gap-2">
            {analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
            Analyze Portfolio
          </Button>
          <Button size="sm" onClick={() => setShowAdd(v => !v)} className="gap-2">
            <Plus className="h-4 w-4" /> Add
          </Button>
        </div>
      </div>

      {/* Add position (collapsible) */}
      {showAdd && (
        <div className="rounded-xl border border-border/60 bg-card p-4">
          <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-3">
            <div className="flex flex-col gap-1">
              <label className="text-[11px] text-muted-foreground uppercase tracking-wide">Market</label>
              <Select value={market} onValueChange={v => setMarket(v as "INDIA" | "US")}>
                <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="INDIA">🇮🇳 India</SelectItem>
                  <SelectItem value="US">🇺🇸 US</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[11px] text-muted-foreground uppercase tracking-wide">Ticker</label>
              <Input placeholder={market === "INDIA" ? "e.g. TATATECH" : "e.g. AAPL"} value={ticker}
                     onChange={e => setTicker(e.target.value)} className="w-44" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[11px] text-muted-foreground uppercase tracking-wide">Quantity</label>
              <Input placeholder="10" type="number" step="any" value={qty}
                     onChange={e => setQty(e.target.value)} className="w-28" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[11px] text-muted-foreground uppercase tracking-wide">
                Buy Price {market === "INDIA" ? "(₹)" : "($)"}
              </label>
              <Input placeholder="0.00" type="number" step="any" value={price}
                     onChange={e => setPrice(e.target.value)} className="w-32" />
            </div>
            <Button type="submit" disabled={adding} className="gap-2">
              {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />} Add
            </Button>
          </form>
          {(() => {
            const parsedQty = parseFloat(qty)
            const parsedPrice = parseFloat(price)
            const totalCost = !isNaN(parsedQty) && !isNaN(parsedPrice) && parsedQty > 0 && parsedPrice > 0
              ? parsedQty * parsedPrice : null
            return totalCost != null ? (
              <p className="mt-2 text-[11px] text-muted-foreground">
                Total cost: <span className="font-semibold text-foreground">
                  {market === "INDIA" ? "₹" : "$"}{totalCost.toLocaleString(market === "INDIA" ? "en-IN" : "en-US", { maximumFractionDigits: 2 })}
                </span>
                {market === "INDIA" && ticker && !isIndianTicker(ticker) && (
                  <> · will be saved as <span className="font-mono text-foreground">{ticker.toUpperCase()}.NS</span> (NSE)</>
                )}
              </p>
            ) : market === "INDIA" && ticker && !isIndianTicker(ticker) ? (
              <p className="mt-2 text-[11px] text-muted-foreground">
                Will be saved as <span className="font-mono text-foreground">{ticker.toUpperCase()}.NS</span> (NSE)
              </p>
            ) : null
          })()}
        </div>
      )}

      <Tabs value={tab} onValueChange={v => setTab(v as any)}>
        <TabsList>
          <TabsTrigger value="all">All ({holdings.length})</TabsTrigger>
          <TabsTrigger value="ind">🇮🇳 IND ({ind.length})</TabsTrigger>
          <TabsTrigger value="us">🇺🇸 US ({us.length})</TabsTrigger>
        </TabsList>

        {loading ? (
          <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : (
          <>
            <TabsContent value="all">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  {usdInr ? `Live FX · $1 = ₹${usdInr.toFixed(2)}` : "Fetching live FX rate…"}
                </p>
                <Button variant="outline" size="sm" onClick={() => setAllCcy(c => c === "INR" ? "USD" : "INR")}
                  disabled={!usdInr} className="gap-2 text-xs">
                  <ArrowLeftRight className="h-3.5 w-3.5" /> Show in {allCcy === "INR" ? "USD ($)" : "INR (₹)"}
                </Button>
              </div>
              <HoldingSection items={holdings} displayCurrency={allCcy} convert={convertTo(allCcy)} onChanged={load}
                empty="No holdings yet. Add a position or pick a stock from a run." />
            </TabsContent>
            <TabsContent value="ind">
              <HoldingSection items={ind} displayCurrency="INR" convert={(v) => noConvert(v)} onChanged={load}
                empty="No Indian holdings yet." />
            </TabsContent>
            <TabsContent value="us">
              <HoldingSection items={us} displayCurrency="USD" convert={(v) => noConvert(v)} onChanged={load}
                empty="No US holdings yet." />
            </TabsContent>
          </>
        )}
      </Tabs>
    </div>
  )
}

function HoldingSection({ items, displayCurrency, convert, onChanged, empty }: {
  items: Holding[]
  displayCurrency: string
  convert: (v: number | null | undefined, from: string | null | undefined) => number | null
  onChanged: () => void
  empty: string
}) {
  if (items.length === 0)
    return <p className="py-12 text-center text-sm text-muted-foreground">{empty}</p>

  let invested = 0, current = 0
  for (const h of items) {
    const native = h.currency || "INR"
    const buy = convert(h.buy_price, native)
    const cur = convert(h.current_price ?? h.buy_price, native)
    if (buy != null && h.quantity) invested += buy * h.quantity
    if (cur != null && h.quantity) current += cur * h.quantity
  }
  const pnl    = current - invested
  const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0
  const up     = pnl >= 0

  return (
    <div className="space-y-4">
      {/* Hero summary — Groww/INDmoney style */}
      <div className="rounded-2xl border border-border/60 bg-gradient-to-br from-card to-muted/20 p-5">
        <p className="text-xs text-muted-foreground">Current Value</p>
        <p className="mt-1 text-3xl font-bold tracking-tight">{formatMoney(current, displayCurrency)}</p>
        <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-2">
          <div>
            <p className="text-[11px] text-muted-foreground">Invested</p>
            <p className="text-sm font-semibold">{formatMoney(invested, displayCurrency)}</p>
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground">Total Returns</p>
            <p className={`flex items-center gap-1 text-sm font-semibold ${up ? "gain" : "loss"}`}>
              {up ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
              {up ? "+" : "−"}{formatMoney(Math.abs(pnl), displayCurrency).replace(/^[₹$]/, displayCurrency === "USD" ? "$" : "₹")} ({up ? "+" : ""}{pnlPct.toFixed(2)}%)
            </p>
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground">Holdings</p>
            <p className="text-sm font-semibold">{items.length}</p>
          </div>
        </div>
      </div>

      {/* Holdings list */}
      <div className="space-y-2">
        {items.map(h => (
          <HoldingRow key={h.id} holding={h} displayCurrency={displayCurrency} convert={convert} onChanged={onChanged} />
        ))}
      </div>
    </div>
  )
}
