"use client"

import { useState, useRef, useEffect } from "react"
import { Search, Loader2, Coins, Landmark } from "lucide-react"
import { assets, type AssetSearchResult } from "@/lib/api"

interface Props {
  assetClass: "CRYPTO" | "FUND"
  market?: "INDIA" | "US" | "CRYPTO"
  placeholder: string
  onSelect: (asset: AssetSearchResult) => void
  /** Seed the box (e.g. from a preset chip); changing it triggers a search. */
  query?: string
  onQueryChange?: (q: string) => void
  className?: string
}

export default function AssetSearch({
  assetClass, market, placeholder, onSelect, query: controlled, onQueryChange, className,
}: Props) {
  const [inner, setInner]       = useState("")
  const query                   = controlled ?? inner
  const [results, setResults]   = useState<AssetSearchResult[]>([])
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState(false)
  const [open, setOpen]         = useState(false)
  const [hi, setHi]             = useState(-1)
  const wrapRef                 = useRef<HTMLDivElement>(null)
  const reqId                   = useRef(0)

  function setQuery(q: string) {
    setInner(q)
    onQueryChange?.(q)
  }

  useEffect(() => {
    const q = query.trim()
    if (q.length < 2) { setResults([]); setOpen(false); setError(false); return }
    const id = ++reqId.current
    const t = setTimeout(async () => {
      setLoading(true); setError(false)
      try {
        const data = await assets.search(q, assetClass, market)
        if (id !== reqId.current) return           // a newer search superseded this one
        setResults(data); setOpen(true); setHi(-1)
      } catch {
        if (id !== reqId.current) return
        setResults([]); setError(true); setOpen(true)
      } finally {
        if (id === reqId.current) setLoading(false)
      }
    }, 350)
    return () => clearTimeout(t)
  }, [query, assetClass, market])

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener("mousedown", close)
    return () => document.removeEventListener("mousedown", close)
  }, [])

  function pick(r: AssetSearchResult) {
    setOpen(false)
    onSelect(r)
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") { e.preventDefault(); setHi(h => Math.min(h + 1, results.length - 1)) }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi(h => Math.max(h - 1, -1)) }
    else if (e.key === "Enter") { e.preventDefault(); if (results[hi]) pick(results[hi]) }
    else if (e.key === "Escape") setOpen(false)
  }

  const Icon = assetClass === "CRYPTO" ? Coins : Landmark

  return (
    <div ref={wrapRef} className={`relative w-full ${className ?? ""}`}>
      <div className="relative flex items-center">
        <Search className="pointer-events-none absolute left-3 h-4 w-4 text-muted-foreground" />
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={onKeyDown}
          onFocus={() => { if (results.length || error) setOpen(true) }}
          placeholder={placeholder}
          aria-label={placeholder}
          className="h-9 w-full rounded-md border border-border bg-background pl-9 pr-9 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
        {loading && <Loader2 className="pointer-events-none absolute right-3 h-4 w-4 animate-spin text-muted-foreground" />}
      </div>

      {open && (
        <div className="absolute z-50 mt-1 max-h-80 w-full overflow-y-auto rounded-md border border-border bg-popover shadow-lg">
          {error ? (
            <p className="px-3 py-3 text-xs text-muted-foreground">Search is unavailable right now. Try again in a moment.</p>
          ) : results.length === 0 ? (
            <p className="px-3 py-3 text-xs text-muted-foreground">No matches.</p>
          ) : results.map((r, i) => (
            <button
              key={r.symbol}
              onMouseDown={() => pick(r)}
              onMouseEnter={() => setHi(i)}
              className={`flex w-full items-center gap-3 px-3 py-2 text-left text-sm transition-colors ${
                hi === i ? "bg-accent text-accent-foreground" : "hover:bg-accent/50"}`}
            >
              <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1 truncate">{r.name ?? r.ticker}</span>
              <span className="shrink-0 font-mono text-xs text-muted-foreground">
                {r.asset_class === "CRYPTO" ? r.ticker : r.market === "US" ? r.ticker : `#${r.ticker}`}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
