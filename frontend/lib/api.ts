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
  if (typeof FormData !== "undefined" && options.body instanceof FormData) delete headers["Content-Type"]

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = (body as any).detail
    // FastAPI validation errors (422) arrive as a list of {msg, loc}.
    const message = Array.isArray(detail)
      ? detail.map((d: any) => d?.msg).filter(Boolean).join("; ")
      : detail
    throw new Error(message || `HTTP ${res.status}`)
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
  asset_class?: AssetClass
  name?: string | null
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
  add:  (ticker: string, quantity: number, buy_price: number,
          opts: { assetClass?: AssetClass; name?: string } = {}) =>
    request<{ ok: boolean }>("/api/portfolio", {
      method: "POST",
      body: JSON.stringify({
        ticker, quantity, buy_price,
        asset_class: opts.assetClass, name: opts.name,
      }),
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

// ── Crypto & funds ────────────────────────────────────────────────────────────

export type AssetClass = "EQUITY" | "CRYPTO" | "FUND"

export interface AssetSearchResult {
  symbol:      string          // canonical: CRYPTO:bitcoin, MF:118989, VTSAX
  ticker:      string
  name:        string | null
  asset_class: AssetClass
  market:      "INDIA" | "US" | "CRYPTO"
  rank?:       number | null
  fund_type?:  string
}

export interface AssetQuote {
  symbol:          string
  price:           number
  day_change_pct?: number | null
  market_cap?:     number | null
  volume_24h?:     number | null
  as_of?:          string
  currency:        string
  source?:         string
}

export interface AssetInfo {
  symbol: string; asset_class: AssetClass; market: string; currency: string
  name?: string | null; fund_house?: string | null; category?: string | null
  type?: string | null; isin?: string | null
}

export interface AssetCandle { date: string; close: number }

export interface AssetMetrics {
  observations: number
  start?: string; end?: string
  total_return?: number | null; cagr?: number | null
  annual_volatility?: number | null; sharpe?: number | null
  max_drawdown?: number | null; current_drawdown?: number | null
  best_day?: number | null; worst_day?: number | null
  rolling_returns?: Record<"1m" | "3m" | "6m" | "1y", number | null>
}

const assetQs = (symbol: string, assetClass?: AssetClass, extra = "") =>
  `symbol=${encodeURIComponent(symbol)}${assetClass ? `&asset_class=${assetClass}` : ""}${extra}`

export const assets = {
  search: (q: string, assetClass?: "CRYPTO" | "FUND", market?: "INDIA" | "US" | "CRYPTO", limit = 12) =>
    request<AssetSearchResult[]>(
      `/api/assets/search?q=${encodeURIComponent(q)}&limit=${limit}` +
      `${assetClass ? `&asset_class=${assetClass}` : ""}${market ? `&market=${market}` : ""}`),
  info:    (symbol: string, c?: AssetClass) => request<AssetInfo>(`/api/assets/info?${assetQs(symbol, c)}`),
  quote:   (symbol: string, c?: AssetClass) => request<AssetQuote>(`/api/assets/quote?${assetQs(symbol, c)}`),
  history: (symbol: string, period = "1y", c?: AssetClass) =>
    request<{ candles: AssetCandle[]; currency: string }>(
      `/api/assets/history?${assetQs(symbol, c, `&period=${period}`)}`),
  metrics: (symbol: string, period = "1y", c?: AssetClass) =>
    request<AssetMetrics>(`/api/assets/metrics?${assetQs(symbol, c, `&period=${period}`)}`),
}

// ── Scenario forecasts ────────────────────────────────────────────────────────

export type ScenarioKey = "CRASH" | "DECLINE" | "STEADY" | "STRONG_GROWTH" | "MULTIBAGGER"
export type ForecastHorizon = "3m" | "1y"

export interface ScenarioBucket { scenario: ScenarioKey; label: string; min: number | null; max: number | null }

export interface Forecast {
  symbol: string; asset_class: AssetClass; horizon: ForecastHorizon; horizon_days: number
  as_of: string; price: number; currency: string
  probs: Record<ScenarioKey, number>
  base_rate: Record<ScenarioKey, number>
  quantiles: Record<"p5" | "p25" | "p50" | "p75" | "p95", number>
  expected_return: number; daily_vol: number; n_samples: number; model_version: string
  low_volatility?: boolean
  scenarios: ScenarioBucket[]
}

export interface Reliability { bin: [number, number]; predicted: number; observed: number; count: number }

export interface ForecastScore {
  n?: number; brier?: number; brier_base_rate?: number; skill?: number | null
  log_loss?: number; log_loss_base_rate?: number; reliability?: Reliability[]
}

export interface ForecastBacktest extends ForecastScore {
  status: "ok" | "insufficient_history"; detail?: string
  first?: string; last?: string; model_version: string
}

export interface TrackRecord extends ForecastScore {
  total: number; resolved: number; pending: number; model_version: string
  actual_distribution?: Record<ScenarioKey, number>
  mean_predicted?: Record<ScenarioKey, number>
}

export interface ForecastExplanation {
  summary: string; bull_case: string[]; bear_case: string[]; watch: string[]
  model: string; generated_at: string; headlines_used: number
}

export const forecast = {
  get: (symbol: string, horizon: ForecastHorizon = "3m", c?: AssetClass) =>
    request<Forecast>(`/api/forecast?${assetQs(symbol, c, `&horizon=${horizon}`)}`),
  backtest: (symbol: string, horizon: ForecastHorizon = "3m", c?: AssetClass) =>
    request<ForecastBacktest>(`/api/forecast/backtest?${assetQs(symbol, c, `&horizon=${horizon}`)}`),
  explain: (symbol: string, horizon: ForecastHorizon = "3m", c?: AssetClass) =>
    request<ForecastExplanation>(`/api/forecast/explain?${assetQs(symbol, c, `&horizon=${horizon}`)}`),
  trackRecord: (horizon?: ForecastHorizon) =>
    request<TrackRecord>(`/api/forecast/track-record${horizon ? `?horizon=${horizon}` : ""}`),
}

// ── Portfolio agent (upload -> review -> analysis -> strategy) ───────────────────

export type AgentClassHint = "stock" | "crypto" | "mutual_fund" | "etf" | "other"

export interface AgentCandidate { symbol: string; name: string; asset_class: AssetClass; market: string; score: number }

export interface AgentRow {
  name: string | null; symbol: string | null; asset_class: AgentClassHint; exchange: string | null
  quantity: number | null; avg_price: number | null; last_price: number | null
  current_value: number | null; invested: number | null; pnl_pct: number | null
  candidates: AgentCandidate[]; match: string | null; status: "matched" | "review" | "unmatched"
}

export interface AgentParse { source: string; portfolio_currency: string | null; notes: string | null; rows: AgentRow[] }

export interface AgentHoldingIn {
  symbol: string; quantity: number; avg_price?: number | null; asset_class?: AssetClass | null; name?: string | null
}

export interface AgentHolding {
  symbol: string; name?: string | null; display: string; asset_class: AssetClass; market: string; currency: string
  price: number; quantity: number; avg_price?: number | null; value: number; weight: number
  pnl_pct?: number | null; risk_share?: number | null
  metrics?: { annual_volatility?: number | null; max_drawdown?: number | null }
  outlook_3m?: { downside: number; upside: number; p5: number; p50: number; p95: number } | null
}

export interface AgentSimHorizon {
  days: number; paths: number
  quantiles: Record<"p5" | "p25" | "p50" | "p75" | "p95", number>
  prob_at_least: Record<string, number>; prob_loss: number
}

export interface AgentAnalysis {
  base_currency: string; fx_usd_inr: number | null
  portfolio: {
    value: number; cost_known: number | null; pnl_pct: number | null; pnl_amount: number | null
    cost_coverage: number; breakeven_return: number | null; n_holdings: number; top3_weight: number
    effective_n: number; annual_volatility?: number; diversification_ratio?: number | null
    avg_correlation?: number; most_correlated?: { a: string; b: string; corr: number }[]
    by_asset_class: Record<string, number>; by_market: Record<string, number>
  }
  holdings: AgentHolding[]
  simulation: { horizons: Record<string, AgentSimHorizon>; breakeven_return: number | null; common_days: number } | null
  failed: string[]; notes: string[]
}

export interface AgentStep { action: string; symbol: string | null; what: string; why: string | null }

export interface AgentStrategy {
  headline: string; goal_feasibility: string | null; diagnosis: string[]; plan: AgentStep[]
  if_markets: { rise: string | null; flat: string | null; fall: string | null }
  risks: string[]; next_steps: string[]; goal: string; risk: string
}

export interface AgentJob {
  status: "queued" | "running" | "done" | "error"; progress: string | null
  result: { analysis: AgentAnalysis; strategy: AgentStrategy } | null; error: string | null
}

export const portfolioAgent = {
  parse: (file: File) => {
    const fd = new FormData()
    fd.append("file", file)
    return request<AgentParse>("/api/portfolio-agent/parse", { method: "POST", body: fd })
  },
  analyze: (holdings: AgentHoldingIn[]) =>
    request<AgentAnalysis>("/api/portfolio-agent/analyze", { method: "POST", body: JSON.stringify({ holdings }) }),
  startStrategy: (holdings: AgentHoldingIn[], goal: string, risk: string) =>
    request<{ job_id: string }>("/api/portfolio-agent/strategy", {
      method: "POST", body: JSON.stringify({ holdings, goal, risk }) }),
  job: (id: string) => request<AgentJob>(`/api/portfolio-agent/jobs/${id}`),
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

export const api = { auth, picks, portfolio, market, universe, stock, fx, assets, forecast, portfolioAgent }
