import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"
import type { Pick } from "@/lib/api"
import type { AppSettings } from "@/lib/settings-context"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Sanitize an externally-supplied URL (e.g. a news link) before using it in an
 * href. Only http(s) links are allowed through; anything else (javascript:,
 * data:, etc.) falls back to "#" to avoid an XSS / scheme-injection vector.
 */
export function safeUrl(url?: string | null): string {
  if (!url) return "#"
  try {
    const u = new URL(url, "https://example.com")
    return u.protocol === "http:" || u.protocol === "https:" ? url : "#"
  } catch {
    return "#"
  }
}

/** True for NSE/BSE tickers. */
export function isIndianTicker(ticker: string): boolean {
  const t = ticker.toUpperCase()
  return t.endsWith(".NS") || t.endsWith(".BO")
}

/** Currency symbol for a market/currency/ticker. */
export function currencySymbol(code?: string | null): string {
  return code === "INR" ? "₹" : code === "USD" ? "$" : code ?? ""
}

/** Format a number as money in the given currency (₹ / $). */
export function formatMoney(value?: number | null, currency: string = "INR"): string {
  if (value == null || Number.isNaN(value)) return "—"
  const sym = currencySymbol(currency)
  const locale = currency === "INR" ? "en-IN" : "en-US"
  return `${sym}${value.toLocaleString(locale, { maximumFractionDigits: 2 })}`
}

/** Parse a confidence string like "85%", "85", or 85 into a number 0–100. */
function parseConfidence(raw?: string | number | null): number {
  if (raw == null) return 0
  return parseFloat(raw.toString().replace("%", "").trim()) || 0
}

/**
 * Filter, sort, and optionally cap a list of picks according to AppSettings.
 * Pass `capToNumPicks = true` only for live run results (not saved history).
 */
export function applyPickSettings(
  picks: Pick[],
  settings: AppSettings,
  capToNumPicks = false,
): Pick[] {
  let result = [...picks]

  // Confidence threshold
  if (settings.minConfidence > 0) {
    result = result.filter(p => parseConfidence(p.confidence) >= settings.minConfidence)
  }

  // Risk tolerance
  if (settings.riskTolerance !== "aggressive") {
    result = result.filter(p => {
      const sig = (p.technical_signal || p.recommendation || "").toUpperCase()
      if (settings.riskTolerance === "conservative") return sig.includes("STRONG") && sig.includes("BUY")
      // moderate: any buy/bull signal
      return sig.includes("BUY") || sig.includes("BULL")
    })
  }

  // Sort
  switch (settings.defaultSortOrder) {
    case "confidence":
      result.sort((a, b) => parseConfidence(b.confidence) - parseConfidence(a.confidence))
      break
    case "sector":
      result.sort((a, b) => (a.sector || "").localeCompare(b.sector || ""))
      break
    case "date":
      result.sort((a, b) => (b.analysis_date || "").localeCompare(a.analysis_date || ""))
      break
    case "price":
      result.sort((a, b) => (b.current_price ?? 0) - (a.current_price ?? 0))
      break
  }

  // Cap to defaultNumPicks (only for run results)
  if (capToNumPicks && settings.defaultNumPicks > 0) {
    result = result.slice(0, settings.defaultNumPicks)
  }

  return result
}

/** Compact display of a large number (market cap). */
export function formatCompact(value?: number | null, currency: string = "INR"): string {
  if (value == null || Number.isNaN(value)) return "—"
  const sym = currencySymbol(currency)
  const abs = Math.abs(value)
  if (currency === "INR") {
    if (abs >= 1e7) return `${sym}${(value / 1e7).toFixed(2)} Cr`
    if (abs >= 1e5) return `${sym}${(value / 1e5).toFixed(2)} L`
  } else {
    if (abs >= 1e12) return `${sym}${(value / 1e12).toFixed(2)}T`
    if (abs >= 1e9)  return `${sym}${(value / 1e9).toFixed(2)}B`
    if (abs >= 1e6)  return `${sym}${(value / 1e6).toFixed(2)}M`
  }
  return `${sym}${value.toLocaleString()}`
}
