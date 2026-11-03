"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Coins } from "lucide-react"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import AssetSearch from "@/components/asset-search"
import { assetHref } from "@/lib/utils"
import type { AssetSearchResult } from "@/lib/api"

type Kind = "crypto" | "in-funds" | "us-funds"

const KINDS: Record<Kind, {
  label: string
  assetClass: "CRYPTO" | "FUND"
  market: "INDIA" | "US" | "CRYPTO"
  placeholder: string
  blurb: string
  presets: string[]
}> = {
  crypto: {
    label: "🪙 Crypto", assetClass: "CRYPTO", market: "CRYPTO",
    placeholder: "Search coins — Bitcoin, Ethereum, Solana…",
    blurb: "Prices and history from CoinGecko, in USD. Crypto trades 24/7 and is far more volatile than stocks.",
    presets: ["Bitcoin", "Ethereum", "Solana", "XRP", "Cardano", "Chainlink"],
  },
  "in-funds": {
    label: "🇮🇳 India Funds", assetClass: "FUND", market: "INDIA",
    placeholder: "Search mutual funds — e.g. Nifty 50 index, flexi cap",
    blurb: "Daily NAVs for AMFI-registered schemes. Pick the Direct – Growth variant to compare returns fairly.",
    presets: ["Nifty 50 index direct growth", "flexi cap direct growth", "small cap direct growth", "liquid direct growth", "ELSS direct growth"],
  },
  "us-funds": {
    label: "🇺🇸 US Funds & ETFs", assetClass: "FUND", market: "US",
    placeholder: "Search US mutual funds & ETFs — e.g. S&P 500, Vanguard",
    blurb: "US mutual funds and ETFs, priced in USD.",
    presets: ["S&P 500", "Total market", "Nasdaq 100", "Treasury bond", "Dividend"],
  },
}

export default function AssetsPage() {
  const router = useRouter()
  const [kind, setKind] = useState<Kind>("crypto")
  const [queries, setQueries] = useState<Record<Kind, string>>({ crypto: "", "in-funds": "", "us-funds": "" })

  function open(a: AssetSearchResult) {
    router.push(assetHref(a.symbol, a.asset_class))
  }

  return (
    <div className="space-y-5">
      <div>
        <h2 className="flex items-center gap-2 text-2xl font-bold"><Coins className="h-6 w-6" /> Crypto &amp; Funds</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Look up any coin, mutual fund or ETF — see its price history and risk profile, then add it to your portfolio.
        </p>
      </div>

      <Tabs value={kind} onValueChange={v => setKind(v as Kind)}>
        <TabsList>
          {(Object.keys(KINDS) as Kind[]).map(k => (
            <TabsTrigger key={k} value={k}>{KINDS[k].label}</TabsTrigger>
          ))}
        </TabsList>

        {(Object.keys(KINDS) as Kind[]).map(k => {
          const cfg = KINDS[k]
          return (
            <TabsContent key={k} value={k} className="space-y-4">
              <p className="text-xs text-muted-foreground">{cfg.blurb}</p>
              <AssetSearch
                className="max-w-xl"
                assetClass={cfg.assetClass}
                market={cfg.market}
                placeholder={cfg.placeholder}
                query={queries[k]}
                onQueryChange={q => setQueries(s => ({ ...s, [k]: q }))}
                onSelect={open}
              />
              <div>
                <p className="mb-2 text-[11px] uppercase tracking-wide text-muted-foreground">Try</p>
                <div className="flex flex-wrap gap-2">
                  {cfg.presets.map(p => (
                    <button key={p}
                      onClick={() => setQueries(s => ({ ...s, [k]: p }))}
                      className="rounded-full border border-border/60 bg-muted/40 px-3 py-1 text-xs hover:bg-muted transition-colors">
                      {p}
                    </button>
                  ))}
                </div>
              </div>
              {k !== "crypto" && (
                <p className="text-[11px] text-muted-foreground">
                  Looking for an Indian ETF like NIFTYBEES? Those trade on NSE like stocks — find them with the{" "}
                  <Link href="/india" className="underline">IND Market</Link> search.
                </p>
              )}
            </TabsContent>
          )
        })}
      </Tabs>
    </div>
  )
}
