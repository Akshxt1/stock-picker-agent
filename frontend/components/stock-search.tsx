"use client"

import { useState, useRef, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { Search, Loader2, TrendingUp } from "lucide-react"
import { universe, type StockSearchResult } from "@/lib/api"

interface StockSearchProps {
  market: "INDIA" | "US"
}

export default function StockSearch({ market }: StockSearchProps) {
  const router = useRouter()
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<StockSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const doSearch = useCallback(
    async (q: string) => {
      setLoading(true)
      try {
        const data = await universe.search(q, market)
        setResults(data)
        setOpen(data.length > 0)
        setHighlighted(-1)
      } catch {
        setResults([])
        setOpen(false)
      } finally {
        setLoading(false)
      }
    },
    [market]
  )

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!query.trim()) {
      setResults([])
      setOpen(false)
      return
    }
    debounceRef.current = setTimeout(() => doSearch(query.trim()), 300)
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current) }
  }, [query, doSearch])

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      const target = e.target as Node
      if (
        !inputRef.current?.contains(target) &&
        !dropdownRef.current?.contains(target)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener("mousedown", onClickOutside)
    return () => document.removeEventListener("mousedown", onClickOutside)
  }, [])

  function navigate(ticker: string) {
    setOpen(false)
    setQuery("")
    router.push(`/stock/${encodeURIComponent(ticker)}`)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault()
      setHighlighted(h => Math.min(h + 1, results.length - 1))
    } else if (e.key === "ArrowUp") {
      e.preventDefault()
      setHighlighted(h => Math.max(h - 1, -1))
    } else if (e.key === "Enter") {
      e.preventDefault()
      if (highlighted >= 0 && results[highlighted]) {
        navigate(results[highlighted].ticker)
      } else if (query.trim()) {
        // Allow direct navigation even for out-of-universe tickers
        const raw = query.trim()
        const ticker = market === "INDIA" && !raw.includes(".")
          ? `${raw.toUpperCase()}.NS`
          : raw.toUpperCase()
        navigate(ticker)
      }
    } else if (e.key === "Escape") {
      setOpen(false)
    }
  }

  const placeholder =
    market === "INDIA"
      ? "Search NSE stocks — ticker or company name"
      : "Search US stocks — ticker or company name"

  return (
    <div className="relative w-full max-w-lg">
      <div className="relative flex items-center">
        <Search className="pointer-events-none absolute left-3 h-4 w-4 text-muted-foreground" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => { if (results.length > 0) setOpen(true) }}
          placeholder={placeholder}
          className="h-9 w-full rounded-md border border-border bg-background pl-9 pr-9 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
        {loading && (
          <Loader2 className="pointer-events-none absolute right-3 h-4 w-4 animate-spin text-muted-foreground" />
        )}
      </div>

      {open && results.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 mt-1 w-full overflow-hidden rounded-md border border-border bg-popover shadow-lg"
        >
          {results.map((r, i) => {
            const displayTicker = r.ticker.replace(".NS", "")
            return (
              <button
                key={r.ticker}
                onMouseDown={() => navigate(r.ticker)}
                onMouseEnter={() => setHighlighted(i)}
                className={`flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition-colors ${
                  highlighted === i ? "bg-accent text-accent-foreground" : "text-foreground hover:bg-accent/50"
                }`}
              >
                <TrendingUp className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                <span className="w-24 shrink-0 font-mono font-semibold">{displayTicker}</span>
                <span className="min-w-0 flex-1 truncate text-muted-foreground">{r.company_name}</span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {r.sector} · {r.size}
                </span>
              </button>
            )
          })}
          <div className="border-t border-border px-3 py-1.5 text-xs text-muted-foreground">
            Press <kbd className="rounded border border-border px-1 py-0.5 font-mono text-[10px]">Enter</kbd> to navigate directly by ticker
          </div>
        </div>
      )}
    </div>
  )
}
