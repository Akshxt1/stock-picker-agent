"use client"

import { useState } from "react"
import * as Dialog from "@radix-ui/react-dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { portfolio } from "@/lib/api"
import { Plus, Loader2, Check, X } from "lucide-react"
import { currencySymbol } from "@/lib/utils"

interface Props {
  ticker: string
  defaultPrice?: number | null
  currency?: string | null
  /** Render-prop trigger; defaults to a small "Add" button. */
  trigger?: React.ReactNode
  onAdded?: () => void
}

export default function AddToPortfolio({ ticker, defaultPrice, currency, trigger, onAdded }: Props) {
  const [open,  setOpen]  = useState(false)
  const [qty,   setQty]   = useState("")
  const [price, setPrice] = useState(defaultPrice ? String(defaultPrice) : "")
  const [busy,  setBusy]  = useState(false)
  const [done,  setDone]  = useState(false)
  const [err,   setErr]   = useState<string | null>(null)

  const sym = currencySymbol(currency)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    e.stopPropagation()
    if (!qty || !price) return
    setBusy(true); setErr(null)
    try {
      await portfolio.add(ticker.toUpperCase(), parseFloat(qty), parseFloat(price))
      setDone(true)
      onAdded?.()
      setTimeout(() => { setOpen(false); setDone(false); setQty("") }, 900)
    } catch (e: any) {
      setErr(e.message ?? "Failed to add")
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild onClick={(e) => e.stopPropagation()}>
        {trigger ?? (
          <button
            className="inline-flex items-center gap-1 rounded-lg border border-border/60 bg-muted/40 px-2.5 py-1 text-xs font-medium hover:bg-muted transition-colors"
            onClick={(e) => e.stopPropagation()}
          >
            <Plus className="h-3 w-3" /> Add
          </button>
        )}
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in" />
        <Dialog.Content
          onClick={(e) => e.stopPropagation()}
          className="fixed left-1/2 top-1/2 z-50 w-[90vw] max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border/60 bg-background p-5 shadow-2xl"
        >
          <div className="flex items-center justify-between mb-4">
            <Dialog.Title className="text-base font-bold">Add to Portfolio</Dialog.Title>
            <Dialog.Close className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></Dialog.Close>
          </div>
          <p className="text-xs text-muted-foreground mb-4 font-mono">{ticker}</p>

          <form onSubmit={submit} className="space-y-3">
            <div>
              <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">Quantity</label>
              <Input type="number" step="any" min="0" value={qty} autoFocus
                     onChange={(e) => setQty(e.target.value)} placeholder="e.g. 10" className="mt-1" />
            </div>
            <div>
              <label className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">
                Buy Price {sym && `(${sym})`}
              </label>
              <Input type="number" step="any" min="0" value={price}
                     onChange={(e) => setPrice(e.target.value)} placeholder="0.00" className="mt-1" />
            </div>

            {err && <p className="text-xs text-destructive">{err}</p>}

            <Button type="submit" disabled={busy || done || !qty || !price} className="w-full gap-2">
              {done ? <><Check className="h-4 w-4" /> Added</>
                    : busy ? <><Loader2 className="h-4 w-4 animate-spin" /> Adding…</>
                    : <><Plus className="h-4 w-4" /> Add Position</>}
            </Button>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
