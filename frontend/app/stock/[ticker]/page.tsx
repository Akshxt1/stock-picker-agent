"use client"

import { useEffect, useState, useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { readSettingSync } from "@/lib/settings-context"
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from "recharts"
import {
  stock, streamStockAnalysis,
  type StockQuote, type Candle, type Technicals, type StockNews, type StockEvents, type Pick,
} from "@/lib/api"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import AddToPortfolio from "@/components/add-to-portfolio"
import {
  ArrowLeft, TrendingUp, TrendingDown, Loader2, ExternalLink,
  Sparkles, BarChart3, Newspaper, CalendarDays, Check, X,
} from "lucide-react"
import { formatMoney, formatCompact } from "@/lib/utils"

const PERIODS = ["1mo", "3mo", "6mo", "1y"]

export default function StockDetailPage() {
  const params = useParams()
  const router = useRouter()
  const ticker = decodeURIComponent(String(params.ticker))

  const [quote,   setQuote]   = useState<StockQuote | null>(null)
  const [candles, setCandles] = useState<Candle[]>([])
  const [period,  setPeriod]  = useState<string>(() => readSettingSync("defaultChartPeriod"))
  const [chartLoading, setChartLoading] = useState(true)

  useEffect(() => {
    stock.quote(ticker).then(setQuote).catch(() => {})
  }, [ticker])

  useEffect(() => {
    setChartLoading(true)
    stock.history(ticker, period)
      .then(d => setCandles(d.candles))
      .catch(() => setCandles([]))
      .finally(() => setChartLoading(false))
  }, [ticker, period])

  const cur = quote?.currency || "INR"
  const change = quote?.day_change_pct ?? null
  const up = (change ?? 0) >= 0

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Back */}
      <button onClick={() => router.back()}
        className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold">{quote?.company_name || ticker}</h1>
            <Badge variant="outline" className="font-mono text-[11px]">{ticker}</Badge>
          </div>
          {quote?.sector && (
            <p className="mt-1 text-sm text-muted-foreground">{quote.sector}{quote.industry ? ` · ${quote.industry}` : ""}</p>
          )}
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="text-2xl font-bold">{formatMoney(quote?.price, cur)}</p>
            {change != null && (
              <p className={`flex items-center justify-end gap-1 text-sm font-semibold ${up ? "gain" : "loss"}`}>
                {up ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
                {up ? "+" : ""}{change.toFixed(2)}%
              </p>
            )}
          </div>
          <AddToPortfolio ticker={ticker} defaultPrice={quote?.price} currency={cur}
            trigger={
              <button className="rounded-lg bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 transition-opacity">
                + Portfolio
              </button>} />
        </div>
      </div>

      {/* Key stats strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <Stat label="Market Cap" value={formatCompact(quote?.market_cap, cur)} />
        <Stat label="P/E" value={quote?.pe_ratio != null ? quote.pe_ratio.toFixed(2) : "—"} />
        <Stat label="ROE" value={quote?.roe ?? "—"} />
        <Stat label="D/E" value={quote?.debt_to_equity ?? "—"} />
        <Stat label="52w High" value={formatMoney(quote?.fifty_two_week_high, cur)} />
        <Stat label="52w Low" value={formatMoney(quote?.fifty_two_week_low, cur)} />
      </div>

      {/* Chart */}
      <Card className="border-border/60">
        <CardContent className="pt-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Price Chart</h3>
            <div className="flex gap-1 rounded-lg bg-muted/50 p-0.5">
              {PERIODS.map(p => (
                <button key={p} onClick={() => setPeriod(p)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-all ${
                    period === p ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"
                  }`}>{p}</button>
              ))}
            </div>
          </div>
          {chartLoading ? (
            <div className="flex h-64 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          ) : candles.length === 0 ? (
            <div className="flex h-64 items-center justify-center text-sm text-muted-foreground">No price data available.</div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={candles} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} vertical={false} />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={40}
                  stroke="hsl(var(--muted-foreground))" tickFormatter={(d) => String(d).slice(5)} />
                <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10 }} width={55}
                  stroke="hsl(var(--muted-foreground))"
                  tickFormatter={(v) => formatMoney(v, cur)} />
                <Tooltip
                  contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }}
                  formatter={(v: any) => [formatMoney(Number(v), cur), "Close"]} />
                <Area type="monotone" dataKey="close" stroke="hsl(var(--primary))" strokeWidth={2} fill="url(#g)" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="ai">
        <TabsList className="w-full justify-start overflow-x-auto">
          <TabsTrigger value="ai"><Sparkles className="h-4 w-4" /> AI Analysis</TabsTrigger>
          <TabsTrigger value="tech"><BarChart3 className="h-4 w-4" /> Technicals</TabsTrigger>
          <TabsTrigger value="news"><Newspaper className="h-4 w-4" /> News</TabsTrigger>
          <TabsTrigger value="events"><CalendarDays className="h-4 w-4" /> Events</TabsTrigger>
        </TabsList>

        <TabsContent value="ai"><AITab ticker={ticker} currency={cur} /></TabsContent>
        <TabsContent value="tech"><TechTab ticker={ticker} currency={cur} /></TabsContent>
        <TabsContent value="news"><NewsTab ticker={ticker} /></TabsContent>
        <TabsContent value="events"><EventsTab ticker={ticker} currency={cur} /></TabsContent>
      </Tabs>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Card className="border-border/60">
      <CardContent className="px-3 py-3">
        <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
        <p className="mt-0.5 text-sm font-bold">{value}</p>
      </CardContent>
    </Card>
  )
}

// ── AI tab ─────────────────────────────────────────────────────────────────────
const DEEP_STAGES = [
  { agent: "Researcher",        emoji: "🔍", label: "Research" },
  { agent: "Data Analyst",      emoji: "📊", label: "Technicals" },
  { agent: "Sentiment Analyst", emoji: "📰", label: "Sentiment" },
  { agent: "Master Analyst",    emoji: "🎯", label: "Decision" },
]

function AITab({ ticker, currency }: { ticker: string; currency: string }) {
  const [data, setData] = useState<(Pick & { has_pick: boolean }) | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [lines, setLines] = useState<{ agent?: string; text: string; kind?: string; tool?: string | null }[]>([])
  const [doneStages, setDoneStages] = useState(0)
  const [showLog, setShowLog] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const stopRef = useRef<(() => void) | null>(null)

  function loadAI() {
    return stock.ai(ticker).then(setData).catch(() => setData(null))
  }
  useEffect(() => { loadAI().finally(() => setLoading(false)) }, [ticker])
  useEffect(() => () => stopRef.current?.(), [])

  function runDeep() {
    setRunning(true); setLines([]); setDoneStages(0); setErr(null); setShowLog(true)
    stopRef.current = streamStockAnalysis(ticker, (evt) => {
      if (evt.type === "step")  setLines(l => [...l, { agent: evt.agent, text: evt.text, kind: evt.kind, tool: evt.tool }])
      else if (evt.type === "task") { setDoneStages(s => s + 1); setLines(l => [...l, { agent: evt.agent, text: evt.text, kind: "task" }]) }
      else if (evt.type === "done") { setRunning(false); setShowLog(false); loadAI() }
      else if (evt.type === "error") { setRunning(false); setErr(evt.text) }
    })
  }

  const anyData = data as any
  const isHolding = anyData?.source === "holding"
  const isCrew    = anyData?.source === "crew"
  const activeStage = running ? Math.min(doneStages, DEEP_STAGES.length - 1) : -1

  if (loading) return <Spinner />

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">Full Crew Analysis</h3>
          <p className="text-xs text-muted-foreground">Researcher → Technicals → Sentiment → CEO decision · ~1–2 min · counts as 1 analysis run</p>
        </div>
        <button onClick={runDeep} disabled={running}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-3.5 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-60 transition-opacity">
          {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {running ? "Analysing…" : data?.has_pick ? "Re-run Deep Analysis" : "Run Deep Analysis"}
        </button>
      </div>

      {err && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <X className="h-4 w-4 shrink-0" /> {err}
        </div>
      )}

      {/* Stage tracker (while running or just after) */}
      {(running || lines.length > 0) && (
        <Card className="border-border/60 overflow-hidden">
          <div className="h-0.5 w-full bg-gradient-to-r from-primary via-amber-400 to-transparent" />
          <CardContent className="pt-4">
            <div className="grid grid-cols-4 gap-2">
              {DEEP_STAGES.map((s, i) => {
                const done = i < doneStages
                const active = i === activeStage
                return (
                  <div key={s.agent} className={`rounded-lg border px-2 py-2 text-center transition-colors ${
                    done ? "border-accent/40 bg-accent/10" : active ? "border-primary/50 bg-primary/10" : "border-border/50 bg-muted/20"
                  }`}>
                    <div className="flex items-center justify-center gap-1">
                      {done ? <Check className="h-3.5 w-3.5 text-accent" />
                            : active ? <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                            : <span className="text-sm opacity-50">{s.emoji}</span>}
                    </div>
                    <p className={`mt-1 text-[10px] font-medium ${done ? "text-accent" : active ? "text-primary" : "text-muted-foreground"}`}>{s.label}</p>
                  </div>
                )
              })}
            </div>

            {/* Collapsible live log */}
            {lines.length > 0 && (
              <>
                <button onClick={() => setShowLog(v => !v)}
                  className="mt-3 text-[11px] font-medium text-muted-foreground hover:text-foreground transition-colors">
                  {showLog ? "▾ Hide" : "▸ Show"} agent activity ({lines.length})
                </button>
                {showLog && (
                  <div className="mt-2 max-h-56 space-y-1.5 overflow-y-auto rounded-lg bg-muted/20 p-3">
                    {lines.map((l, i) => (
                      <div key={i} className="flex items-start gap-2 text-[11px]">
                        {l.kind === "task"
                          ? <Check className="h-3 w-3 text-accent mt-0.5 shrink-0" />
                          : <span className="shrink-0 text-[11px]">{DEEP_STAGES.find(s => s.agent === l.agent)?.emoji ?? "🤖"}</span>}
                        <div className="min-w-0">
                          {l.kind === "tool" && l.tool && <span className="text-primary font-medium">{l.tool}: </span>}
                          <span className={l.kind === "thought" ? "italic text-muted-foreground" : "text-foreground/70"}>{l.text}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {!data?.has_pick && !running && lines.length === 0 && !err && (
        <Empty text="No AI analysis yet. Hit 'Run Deep Analysis' — the full agent crew will research this stock and produce a clear buy / hold / avoid brief." />
      )}

      {/* Saved brief */}
      {data?.has_pick && (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="success">{data.recommendation || data.technical_signal}</Badge>
            {data.confidence && <Badge variant="outline">Confidence: {data.confidence}</Badge>}
            {data.sentiment && <Badge variant="outline">Sentiment: {data.sentiment}</Badge>}
            {data.target_pct != null && <Badge variant="outline">Target +{data.target_pct}%</Badge>}
            {data.stop_loss_pct != null && <Badge variant="destructive">Stop −{data.stop_loss_pct}%</Badge>}
            {anyData.target_price != null && <Badge variant="outline">Target {formatMoney(anyData.target_price, currency)}</Badge>}
            {anyData.stop_loss != null && <Badge variant="destructive">Stop {formatMoney(anyData.stop_loss, currency)}</Badge>}
            {isCrew && <Badge variant="outline">Full crew brief</Badge>}
            {isHolding && <Badge variant="outline">Portfolio verdict</Badge>}
          </div>
          {anyData.analysis_summary && (
            <Card className="border-border/60">
              <CardContent className="pt-4">
                <p className="text-sm leading-relaxed text-muted-foreground">{anyData.analysis_summary}</p>
              </CardContent>
            </Card>
          )}
          <div className="grid gap-4 md:grid-cols-2">
            <Card className="border-border/60">
              <CardContent className="pt-4">
                <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-accent"><Check className="h-4 w-4" /> Why Buy</h4>
                <ul className="space-y-1.5">
                  {(data.why_buy ?? []).map((r, i) => (
                    <li key={i} className="flex gap-2 text-sm text-muted-foreground"><span className="text-accent">▸</span>{r}</li>
                  ))}
                  {(!data.why_buy || data.why_buy.length === 0) && <li className="text-sm text-muted-foreground">—</li>}
                </ul>
              </CardContent>
            </Card>
            <Card className="border-border/60">
              <CardContent className="pt-4">
                <h4 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-amber-500"><X className="h-4 w-4" /> Why Not Buy</h4>
                <ul className="space-y-1.5">
                  {(data.why_not_buy ?? []).map((r, i) => (
                    <li key={i} className="flex gap-2 text-sm text-muted-foreground"><span className="text-amber-500">▸</span>{r}</li>
                  ))}
                  {(!data.why_not_buy || data.why_not_buy.length === 0) && <li className="text-sm text-muted-foreground">—</li>}
                </ul>
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}

// ── Technicals tab ─────────────────────────────────────────────────────────────
function TechTab({ ticker, currency }: { ticker: string; currency: string }) {
  const [data, setData] = useState<Technicals | null>(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(false)
  useEffect(() => {
    stock.technicals(ticker).then(setData).catch(() => setErr(true)).finally(() => setLoading(false))
  }, [ticker])

  if (loading) return <Spinner />
  if (err || !data) return <Empty text="Technical indicators unavailable for this stock." />

  const rows: Array<[string, string, string?]> = [
    ["RSI (14)", data.rsi != null ? String(data.rsi) : "—", data.rsi_label ?? undefined],
    ["MACD", data.macd != null ? String(data.macd) : "—", data.macd_label ?? undefined],
    ["MACD Signal", data.macd_signal != null ? String(data.macd_signal) : "—"],
    ["EMA 20", formatMoney(data.ema20, currency)],
    ["EMA 50", formatMoney(data.ema50, currency)],
    ["Trend", data.trend ?? "—"],
    ["ATR (14)", data.atr != null ? String(data.atr) : "—"],
    ["Bollinger Upper", formatMoney(data.bb_upper, currency)],
    ["Bollinger Mid", formatMoney(data.bb_mid, currency)],
    ["Bollinger Lower", formatMoney(data.bb_lower, currency)],
  ]
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {rows.map(([label, value, tag]) => (
        <div key={label} className="flex items-center justify-between rounded-lg border border-border/50 bg-card px-4 py-2.5">
          <span className="text-sm text-muted-foreground">{label}</span>
          <span className="flex items-center gap-2 text-sm font-semibold">
            {value}
            {tag && <Badge variant="outline" className="text-[10px]">{tag}</Badge>}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── News tab ───────────────────────────────────────────────────────────────────
function NewsTab({ ticker }: { ticker: string }) {
  const [data, setData] = useState<StockNews | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    stock.news(ticker).then(setData).catch(() => setData(null)).finally(() => setLoading(false))
  }, [ticker])

  if (loading) return <Spinner />
  if (!data || data.items.length === 0) return <Empty text="No recent news found." />

  return (
    <div className="space-y-3">
      <Badge variant="outline">Overall sentiment: {data.sentiment}</Badge>
      <div className="space-y-2">
        {data.items.map((n, i) => (
          <a key={i} href={n.link || "#"} target="_blank" rel="noopener noreferrer"
            className="group flex items-start justify-between gap-3 rounded-lg border border-border/50 bg-card px-4 py-3 hover:border-primary/40 transition-colors">
            <div className="min-w-0">
              <p className="text-sm font-medium leading-snug group-hover:text-primary transition-colors">{n.title}</p>
              <p className="mt-1 text-[11px] text-muted-foreground">
                {n.publisher}{n.published ? ` · ${n.published}` : ""}
              </p>
            </div>
            <ExternalLink className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
          </a>
        ))}
      </div>
    </div>
  )
}

// ── Events tab ─────────────────────────────────────────────────────────────────
function EventsTab({ ticker, currency }: { ticker: string; currency: string }) {
  const [data, setData] = useState<StockEvents | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    stock.events(ticker).then(setData).catch(() => setData(null)).finally(() => setLoading(false))
  }, [ticker])

  if (loading) return <Spinner />
  if (!data || (data.dividends.length === 0 && data.upcoming.length === 0))
    return <Empty text="No upcoming events or dividend history available." />

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card className="border-border/60">
        <CardContent className="pt-4">
          <h4 className="mb-3 text-sm font-semibold">Upcoming</h4>
          {data.upcoming.length === 0 ? <p className="text-sm text-muted-foreground">None scheduled.</p> : (
            <ul className="space-y-2">
              {data.upcoming.map((e, i) => (
                <li key={i} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{e.label}</span>
                  <span className="font-semibold">{e.date}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
      <Card className="border-border/60">
        <CardContent className="pt-4">
          <h4 className="mb-3 text-sm font-semibold">Recent Dividends</h4>
          {data.dividends.length === 0 ? <p className="text-sm text-muted-foreground">No dividend history.</p> : (
            <ul className="space-y-2">
              {data.dividends.map((d, i) => (
                <li key={i} className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{d.date}</span>
                  <span className="font-semibold">{formatMoney(d.amount, currency)}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function Spinner() {
  return <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
}
function Empty({ text }: { text: string }) {
  return <p className="py-8 text-center text-sm text-muted-foreground">{text}</p>
}
