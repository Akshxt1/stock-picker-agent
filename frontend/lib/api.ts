/**
 * lib/api.ts — typed API client for the FastAPI backend
 *
 * Usage:
 *   import { api } from "@/lib/api"
 *   const picks = await api.picks.list()
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem("access_token")
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error((body as any).detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface AuthUser {
  user_id:            string
  email:              string
  name:               string
  account_type:       string
  weekly_runs:        number
  limits:             { crew_runs: number; portfolio_runs: number }
  notification_email?: string | null
}

export const auth = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: AuthUser }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  signup: (email: string, password: string, username: string) =>
    request<{ message: string }>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, username }),
    }),

  me: () => request<AuthUser>("/api/auth/me"),

  forgotPassword: (email: string) =>
    request<{ message: string }>("/api/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  updateProfile: (fields: { username?: string; notification_email?: string; tutorial_seen?: boolean }) =>
    request<{ name?: string; notification_email?: string; tutorial_seen?: boolean; email: string; user_id: string }>("/api/auth/profile", {
      method: "PATCH",
      body: JSON.stringify(fields),
    }),

  clearPicks: () =>
    request<{ ok: boolean; deleted: number }>("/api/auth/picks/all", { method: "DELETE" }),
}

// ── Picks ─────────────────────────────────────────────────────────────────────

export interface Pick {
  id: number
  ticker: string
  company_name: string
  market: string
  sector: string
  size: string
  current_price: number | null
  currency: string | null
  recommendation: string
  technical_signal: string
  sentiment: string
  confidence: string
  roe: string | null
  debt_to_equity: string | null
  revenue_growth: string | null
  pe_ratio: string | null
  why_buy: string[]
  why_not_buy: string[]
  stop_loss_pct: number | null
  target_pct: number | null
  analysis_date: string
  run_by_username?: string | null
  reasoning: string
}

export const picks = {
  list: (market?: string) =>
    request<Pick[]>(`/api/picks${market ? `?market=${market}` : ""}`),
  get:  (id: number) => request<Pick>(`/api/picks/${id}`),
  del:  (id: number) => request<{ ok: boolean }>(`/api/picks/${id}`, { method: "DELETE" }),
}

// ── Portfolio ─────────────────────────────────────────────────────────────────

export interface Holding {
  id: number
  ticker: string
  market: string | null
  currency: string | null
  quantity: number
  buy_price: number
  current_price?: number | null
  pnl_pct?: number | null
  pe_ratio?: number | null
  target_price?: number | null
  stop_loss?: number | null
  recommendation?: string | null
  analysis_summary?: string | null
  why_buy?: string[] | null
  why_not_buy?: string[] | null
  analyzed_at?: string | null
}

export interface HoldingVerdict {
  ok: boolean
  recommendation: string
  target_price: number | null
  stop_loss: number | null
  summary: string
  why_buy?: string[]
  why_not_buy?: string[]
}

export const portfolio = {
  list: (market?: string) =>
    request<Holding[]>(`/api/portfolio${market ? `?market=${market}` : ""}`),
  add:  (ticker: string, quantity: number, buy_price: number) =>
    request<{ ok: boolean }>("/api/portfolio", {
      method: "POST",
      body: JSON.stringify({ ticker, quantity, buy_price }),
    }),
  del:  (id: number) => request<{ ok: boolean }>(`/api/portfolio/${id}`, { method: "DELETE" }),
  analyze: (id: number) =>
    request<HoldingVerdict>(`/api/portfolio/${id}/analyze`, { method: "POST" }),
  analyzeAll: (market?: string) =>
    request<{ ok: boolean; analyzed: number }>(
      `/api/portfolio/analyze-all${market ? `?market=${market}` : ""}`, { method: "POST" }),
}

// ── Market ────────────────────────────────────────────────────────────────────

export interface NewsItem {
  title:     string
  publisher: string
  link:      string
  published: string
}

export interface Mover {
  symbol:     string
  price:      number
  change_pct: number
  currency?:  string
  display?:   string
}

export interface IndexQuote {
  key:        string
  label:      string
  currency:   string
  value:      number | null
  change_pct: number | null
  group?:     "india" | "us"
}

export const market = {
  status: () => request<Record<string, { open: boolean; tz: string; hours: string }>>("/api/market/status"),
  indices: () => request<IndexQuote[]>("/api/market/indices"),
  ticker: (symbols: string[]) =>
    request<Array<{ symbol: string; price: number | null; change_pct: number | null }>>(
      `/api/market/ticker?symbols=${symbols.join(",")}`
    ),
  news:     (market: string) =>
    request<NewsItem[]>(`/api/market/news?market=${market}`),
  movers:   (market: string) =>
    request<{ gainers: Mover[]; losers: Mover[] }>(`/api/market/movers?market=${market}`),
  holidays: (exchange = "NSE") =>
    request<MarketHoliday[]>(`/api/market/holidays?exchange=${exchange}`),
  fiiDii:   () => request<FiiDiiFlow[]>(`/api/market/fii-dii`),
  sectorHeatmap: () => request<{ sectors: SectorHeat[] }>(`/api/market/sector-heatmap`),
}

// ── Universe ──────────────────────────────────────────────────────────────────

export interface StockSearchResult {
  ticker:       string
  company_name: string
  sector:       string
  size:         string
  market:       string
}

export const universe = {
  sectors: (market: string) => request<string[]>(`/api/universe/sectors?market=${market}`),
  sizes:   (market: string) => request<string[]>(`/api/universe/sizes?market=${market}`),
  search:  (q: string, market: string) =>
    request<StockSearchResult[]>(
      `/api/universe/search?q=${encodeURIComponent(q)}&market=${market}`
    ),
}

// ── FX ────────────────────────────────────────────────────────────────────────

export const fx = {
  rate: (pair = "USDINR") =>
    request<{ pair: string; rate: number; usd_inr: number }>(`/api/market/fx?pair=${pair}`),
}

// ── Stock detail ───────────────────────────────────────────────────────────────

export interface StockQuote {
  ticker: string
  currency: string
  company_name?: string
  price?: number | null
  previous_close?: number | null
  day_change_pct?: number | null
  sector?: string | null
  industry?: string | null
  market_cap?: number | null
  pe_ratio?: number | null
  pb_ratio?: number | null
  eps?: number | null
  roe?: string | null
  debt_to_equity?: string | null
  revenue_growth?: string | null
  dividend_yield?: string | null
  fifty_two_week_high?: number | null
  fifty_two_week_low?: number | null
  // Upstox-only (India tickers)
  upper_circuit?: number | null
  lower_circuit?: number | null
  vwap?: number | null
  oi?: number | null
}

export interface Candle {
  date: string
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  volume: number | null
}

export interface Technicals {
  ticker: string
  price: number | null
  rsi: number | null;  rsi_label: string | null
  macd: number | null; macd_signal: number | null; macd_hist: number | null; macd_label: string | null
  ema20: number | null; ema50: number | null; trend: string | null
  atr: number | null
  bb_lower: number | null; bb_mid: number | null; bb_upper: number | null
}

export interface StockNews {
  ticker: string
  sentiment: string
  items: Array<{ title: string; publisher: string; link: string; published: string }>
}

export interface StockEvents {
  ticker: string
  dividends: Array<{ date: string; amount: number; label?: string | null }>
  upcoming: Array<{ label: string; date: string }>
  corporate_actions?: Array<{ type: string; label: string; date: string; details: string; upcoming: boolean }>
  dividend_rate?: number
}

export interface ShareholdingQuarter {
  date: string
  promoter: number
  fii: number
  dii: number
  public: number
}
export interface ShareholdingData {
  ticker: string
  quarters: ShareholdingQuarter[]
  india_only?: boolean
}

export interface IncomeEntry {
  period: string
  revenue: number | null
  pat: number | null
  ebitda: number | null
}
export interface FinancialsData {
  ticker: string
  income: IncomeEntry[]
  balance_sheet: {
    total_assets: number | null
    total_debt: number | null
    cash: number | null
    networth: number | null
  }
  ratios: {
    pe: number | null
    pb: number | null
    roe: number | null
    ev_ebitda: number | null
    roce: number | null
    roa: number | null
    quick: number | null
  }
  india_only?: boolean
}

export interface Peer {
  ticker: string
  name: string
  price: number | null
  pe: number | null
}
export interface PeersData {
  ticker: string
  peers: Peer[]
  india_only?: boolean
}

export interface MarketHoliday {
  date: string
  description?: string
  holiday_type?: string
}

export interface FiiDiiFlow {
  category: string          // "FII" | "DII"
  date: string
  buy_value: number | null
  sell_value: number | null
  net_value: number | null
}

export interface SectorHeat {
  sector: string
  change_pct: number
  count: number
}

export const stock = {
  quote:        (t: string) => request<StockQuote>(`/api/stock/${encodeURIComponent(t)}/quote`),
  history:      (t: string, period = "6mo") =>
    request<{ ticker: string; period: string; currency: string; candles: Candle[] }>(
      `/api/stock/${encodeURIComponent(t)}/history?period=${period}`),
  intraday:     (t: string) =>
    request<{ ticker: string; currency: string; candles: Candle[] }>(
      `/api/stock/${encodeURIComponent(t)}/intraday`),
  technicals:   (t: string) => request<Technicals>(`/api/stock/${encodeURIComponent(t)}/technicals`),
  news:         (t: string) => request<StockNews>(`/api/stock/${encodeURIComponent(t)}/news`),
  events:       (t: string) => request<StockEvents>(`/api/stock/${encodeURIComponent(t)}/events`),
  ai:           (t: string) => request<Pick & { has_pick: boolean }>(`/api/stock/${encodeURIComponent(t)}/ai`),
  shareholding: (t: string) => request<ShareholdingData>(`/api/stock/${encodeURIComponent(t)}/shareholding`),
  financials:   (t: string) => request<FinancialsData>(`/api/stock/${encodeURIComponent(t)}/financials`),
  peers:        (t: string) => request<PeersData>(`/api/stock/${encodeURIComponent(t)}/peers`),
}

// ── SSE crew stream ───────────────────────────────────────────────────────────

export type StreamEvent =
  | { type: "step"; agent: string; text: string; kind?: "tool" | "thought" | "answer"; tool?: string | null }
  | { type: "task"; text: string; agent?: string }
  | { type: "done"; result: unknown }
  | { type: "error"; text: string }

/**
 * Connects to the crew SSE stream and calls onEvent for each message.
 * Returns a cleanup function that closes the connection.
 */
/** Shared fetch-based SSE reader (EventSource can't send the Bearer header). */
function streamSSE(path: string, onEvent: (e: StreamEvent) => void): () => void {
  const token = getToken()
  const controller = new AbortController()

  ;(async () => {
    try {
      const res = await fetch(`${BASE}${path}`, {
        headers: { Authorization: `Bearer ${token}` },
        signal:  controller.signal,
      })

      if (!res.ok || !res.body) {
        let detail = `HTTP ${res.status}`
        try { const b = await res.json(); if (b?.detail) detail = b.detail } catch { /* keep default */ }
        onEvent({ type: "error", text: detail })
        return
      }

      const reader  = res.body.getReader()
      const decoder = new TextDecoder()
      let   buffer  = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split("\n\n")
        buffer = parts.pop() ?? ""

        for (const part of parts) {
          const line = part.replace(/^data: /, "").trim()
          if (!line) continue
          try {
            onEvent(JSON.parse(line) as StreamEvent)
          } catch {
            // ignore malformed lines
          }
        }
      }
    } catch (err: unknown) {
      if ((err as Error)?.name !== "AbortError") {
        onEvent({ type: "error", text: String(err) })
      }
    }
  })()

  return () => controller.abort()
}

export function streamCrew(
  params: { market: string; sector: string; size: string },
  onEvent: (e: StreamEvent) => void
): () => void {
  const qs = new URLSearchParams(params)
  return streamSSE(`/api/crew/stream?${qs}`, onEvent)
}

/** Full 4-agent Deep Analysis for one ticker. Streams the same StreamEvent shape. */
export function streamStockAnalysis(
  ticker: string,
  onEvent: (e: StreamEvent) => void
): () => void {
  return streamSSE(`/api/crew/stock-stream?ticker=${encodeURIComponent(ticker)}`, onEvent)
}

// ── Convenience re-export ─────────────────────────────────────────────────────

export const api = { auth, picks, portfolio, market, universe, stock, fx }
