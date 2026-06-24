import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

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
