"use client"

import { useState, useRef, useEffect } from "react"
import { universe }  from "@/lib/api"
import { useAuth }   from "@/lib/auth-context"
import { useRun }    from "@/lib/run-context"
import { Button }    from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge }     from "@/components/ui/badge"
import PickCard      from "@/components/pick-card"
import {
  Bot, AlertCircle,
  CheckCircle2, Loader2, Play, Square, Sparkles, RotateCcw,
} from "lucide-react"
import { cn } from "@/lib/utils"

const MARKETS = ["INDIA", "US"]

export default function AgentStream({ lockedMarket }: { lockedMarket?: string } = {}) {
  const { user, isGuest } = useAuth()
  const { state, start, stop, reset } = useRun()

  const [market,  setMarket]  = useState(lockedMarket ?? "INDIA")
  const [sector,  setSector]  = useState("")
  const [size,    setSize]    = useState("")
  const [sectors, setSectors] = useState<string[]>([])
  const [sizes,   setSizes]   = useState<string[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  const atLimit   = !isGuest && user?.limits && user.limits.crew_runs < 9999
    && (user.weekly_runs ?? 0) >= user.limits.crew_runs

  // When a market is locked (India/US page), only surface picks if the LAST RUN
  // was for that same market. Gating on the run's market (not each pick's field)
  // is bulletproof — an India run never leaks onto the US page and vice-versa.
  const runMarket = state.params?.market
  const visiblePicks = lockedMarket
    ? (runMarket === lockedMarket
        ? state.picks.filter(p => !p.market || p.market === lockedMarket)
        : [])
    : state.picks

  useEffect(() => {
    universe.sectors(market).then(s => { setSectors(s); if (!state.params) setSector(s[0] ?? "") })
    universe.sizes(market).then(s   => { setSizes(s);   if (!state.params) setSize(s[2] ?? "Mid") })
  }, [market])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [state.lines])

  function handleStart() {
    if (!sector || !size || isGuest || atLimit) return
    start({ market, sector, size })
  }

  return (
    <div className="space-y-4">

      {/* ── Controls ── */}
      <Card className="border-border/60 overflow-hidden">
        <div className="h-0.5 w-full bg-gradient-to-r from-primary via-amber-400 to-transparent" />
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center justify-between text-base">
            <span className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/10">
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              AI Stock Picker
            </span>
            {(state.lines.length > 0 || state.picks.length > 0) && !state.running && (
              <button onClick={reset} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors">
                <RotateCcw className="h-3 w-3" /> New Run
              </button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 items-end">
            {!lockedMarket && (
              <div className="flex flex-col gap-1.5">
                <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Market</label>
                <Select value={market} onValueChange={setMarket} disabled={state.running}>
                  <SelectTrigger className="w-28 h-9 bg-muted/40 border-border/60"><SelectValue /></SelectTrigger>
                  <SelectContent>{MARKETS.map(m => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            )}
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Sector</label>
              <Select value={sector} onValueChange={setSector} disabled={state.running}>
                <SelectTrigger className="w-44 h-9 bg-muted/40 border-border/60"><SelectValue /></SelectTrigger>
                <SelectContent>{sectors.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Cap Size</label>
              <Select value={size} onValueChange={setSize} disabled={state.running}>
                <SelectTrigger className="w-28 h-9 bg-muted/40 border-border/60"><SelectValue /></SelectTrigger>
                <SelectContent>{sizes.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            {state.running ? (
              <Button variant="destructive" size="sm" onClick={stop} className="h-9 gap-2">
                <Square className="h-3.5 w-3.5" /> Stop
              </Button>
            ) : (
              <Button size="sm" onClick={handleStart}
                disabled={!sector || !size || isGuest || !!atLimit}
                className="h-9 gap-2 font-semibold"
              >
                <Play className="h-3.5 w-3.5" /> Run Analysis
              </Button>
            )}
          </div>

          {isGuest && (
            <p className="mt-3 text-xs text-amber-500">Guest mode — <a href="/login" className="underline">sign in</a> to run analysis.</p>
          )}
          {atLimit && !isGuest && (
            <p className="mt-3 text-xs text-destructive">
              Weekly limit reached ({user?.limits?.crew_runs} runs for {user?.account_type} plan). Resets next Monday.
            </p>
          )}
          {state.params && !state.running && (
            <p className="mt-3 text-xs text-muted-foreground">
              Last run: {state.params.market} · {state.params.sector} · {state.params.size}
            </p>
          )}
        </CardContent>
      </Card>

      {/* ── Stream log ── */}
      {state.lines.length > 0 && (
        <Card className="border-border/60">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Bot className="h-4 w-4 text-muted-foreground" />
              Agent Activity
              {state.running && <Loader2 className="h-3.5 w-3.5 animate-spin text-primary ml-1" />}
              {state.lastDone && <CheckCircle2 className="h-3.5 w-3.5 text-accent ml-1" />}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
              {state.lines.map(line => <ActivityRow key={line.id} line={line} />)}
              {state.running && (
                <div className="flex items-center gap-2 pl-1 text-xs text-muted-foreground">
                  <Loader2 className="h-3 w-3 animate-spin" /> working…
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Results ── */}
      {visiblePicks.length > 0 && (
        <Card className="border-border/60 overflow-hidden">
          <div className="h-0.5 w-full bg-gradient-to-r from-accent via-emerald-400 to-transparent" />
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="h-5 w-5 text-accent" />
              {visiblePicks.length} Pick{visiblePicks.length !== 1 ? "s" : ""} Found
              <Badge variant="outline" className="ml-auto text-[10px]">
                {state.params?.market} · {state.params?.sector} · {state.params?.size}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-xs text-muted-foreground">Tap a card for the full chart, AI analysis, technicals, news &amp; events.</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {visiblePicks.map((p, i) => <PickCard key={p.id ?? i} pick={p} />)}
            </div>
          </CardContent>
        </Card>
      )}

      {state.error && state.picks.length === 0 && (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {state.error}
        </div>
      )}
    </div>
  )
}

// ── Agent activity row ──────────────────────────────────────────────────────────

const AGENT_STYLE: Record<string, { dot: string; chip: string; emoji: string }> = {
  "Researcher":        { dot: "bg-sky-500",     chip: "text-sky-500",     emoji: "🔍" },
  "Data Analyst":      { dot: "bg-violet-500",  chip: "text-violet-500",  emoji: "📊" },
  "Sentiment Analyst": { dot: "bg-amber-500",   chip: "text-amber-500",   emoji: "📰" },
  "Master Analyst":    { dot: "bg-emerald-500", chip: "text-emerald-500", emoji: "🎯" },
}

function ActivityRow({ line }: { line: { type: string; agent?: string; text: string; kind?: string; tool?: string | null } }) {
  if (line.type === "error") {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
        <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" /> {line.text}
      </div>
    )
  }
  if (line.type === "done") {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-accent/10 px-3 py-2 text-xs font-medium text-accent">
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0" /> {line.text}
      </div>
    )
  }

  const style = AGENT_STYLE[line.agent ?? ""] ?? { dot: "bg-muted-foreground", chip: "text-muted-foreground", emoji: "🤖" }

  if (line.type === "task") {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-border/50 bg-muted/30 px-3 py-2">
        <CheckCircle2 className={cn("h-3.5 w-3.5 shrink-0", style.chip)} />
        <span className="text-xs font-semibold">{line.text}</span>
      </div>
    )
  }

  // step: tool / thought / answer
  return (
    <div className="flex gap-2.5 pl-1">
      <div className="flex flex-col items-center pt-1">
        <span className={cn("h-2 w-2 rounded-full shrink-0", style.dot)} />
        <span className="mt-1 w-px flex-1 bg-border/50" />
      </div>
      <div className="min-w-0 flex-1 pb-1">
        <div className="flex items-center gap-1.5">
          <span className={cn("text-[11px] font-semibold", style.chip)}>{style.emoji} {line.agent}</span>
          {line.kind === "tool" && line.tool && (
            <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">🔧 {line.tool}</span>
          )}
          {line.kind === "answer" && (
            <span className="rounded bg-accent/10 px-1.5 py-0.5 text-[10px] font-medium text-accent">summary</span>
          )}
        </div>
        {line.text && (
          <p className={cn(
            "mt-0.5 text-xs leading-relaxed break-words",
            line.kind === "thought" ? "italic text-muted-foreground" : "text-foreground/75"
          )}>
            {line.text}
          </p>
        )}
      </div>
    </div>
  )
}
