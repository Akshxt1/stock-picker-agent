"use client"

import { useRef, useState } from "react"
import { AlertTriangle, FileSpreadsheet, FileText, ImageIcon, Loader2, Lock, UploadCloud } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { portfolioAgent, type AgentParse } from "@/lib/api"

const ACCEPT = ".png,.jpg,.jpeg,.webp,.gif,.pdf,.csv,.xlsx"
const MAX_MB = 8

export const RISKS = [
  { key: "conservative", label: "Conservative", hint: "Protect capital first" },
  { key: "moderate", label: "Moderate", hint: "Balanced" },
  { key: "aggressive", label: "Aggressive", hint: "Accept bigger swings" },
] as const

export const GOAL_EXAMPLES = [
  "Make this portfolio profitable within 1–2 months",
  "Reduce my risk without selling everything",
  "Recover my losses over the next year",
]

function iconFor(name: string) {
  if (/\.(png|jpe?g|webp|gif)$/i.test(name)) return <ImageIcon className="h-5 w-5" />
  if (/\.(csv|xlsx)$/i.test(name)) return <FileSpreadsheet className="h-5 w-5" />
  return <FileText className="h-5 w-5" />
}

export default function UploadStep({ goal, setGoal, risk, setRisk, onParsed }: {
  goal: string; setGoal: (v: string) => void
  risk: string; setRisk: (v: string) => void
  onParsed: (p: AgentParse) => void
}) {
  const input = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [drag, setDrag] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  function pick(f: File | undefined | null) {
    if (!f) return
    setErr(null)
    if (f.size > MAX_MB * 1024 * 1024) { setErr(`That file is over ${MAX_MB} MB.`); return }
    setFile(f)
  }

  async function read() {
    if (!file) return
    setBusy(true); setErr(null)
    try {
      onParsed(await portfolioAgent.parse(file))
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Couldn't read that file.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-5">
      <Card className="border-border/60">
        <CardContent className="pt-5">
          <h3 className="mb-1 text-sm font-semibold">1 · Upload your portfolio</h3>
          <p className="mb-4 text-xs text-muted-foreground">
            A screenshot from your broker app, a PDF statement, or a CSV / Excel export. Any broker, any layout.
          </p>
          <div
            onDragOver={e => { e.preventDefault(); setDrag(true) }}
            onDragLeave={() => setDrag(false)}
            onDrop={e => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]) }}
            onClick={() => input.current?.click()}
            role="button" tabIndex={0}
            onKeyDown={e => (e.key === "Enter" || e.key === " ") && input.current?.click()}
            className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
              drag ? "border-primary bg-primary/5" : "border-border hover:border-primary/50 hover:bg-muted/30"}`}
          >
            {file ? (
              <>
                <span className="text-primary">{iconFor(file.name)}</span>
                <p className="text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(0)} KB · click to choose a different file</p>
              </>
            ) : (
              <>
                <UploadCloud className="h-8 w-8 text-muted-foreground" />
                <p className="text-sm font-medium">Drop a file here, or click to browse</p>
                <p className="text-xs text-muted-foreground">PNG, JPG, PDF, CSV or XLSX · up to {MAX_MB} MB</p>
              </>
            )}
            <input ref={input} type="file" accept={ACCEPT} className="hidden" onChange={e => pick(e.target.files?.[0])} />
          </div>
          <p className="mt-3 flex items-start gap-1.5 text-[11px] text-muted-foreground">
            <Lock className="mt-0.5 h-3 w-3 shrink-0" />
            Your file is read once to extract the holdings and is not stored. The extracted text is sent to an AI model to read it.
          </p>
        </CardContent>
      </Card>

      <Card className="border-border/60">
        <CardContent className="pt-5">
          <h3 className="mb-1 text-sm font-semibold">2 · What do you want?</h3>
          <textarea
            value={goal} onChange={e => setGoal(e.target.value.slice(0, 600))} rows={3}
            placeholder="e.g. Make this portfolio profitable within 1–2 months"
            className="mt-2 w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <div className="mt-2 flex flex-wrap gap-1.5">
            {GOAL_EXAMPLES.map(g => (
              <button key={g} onClick={() => setGoal(g)}
                className="rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground">
                {g}
              </button>
            ))}
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            {RISKS.map(r => (
              <button key={r.key} onClick={() => setRisk(r.key)}
                className={`rounded-lg border px-3 py-2 text-left transition-colors ${
                  risk === r.key ? "border-primary bg-primary/10" : "border-border hover:bg-muted/40"}`}>
                <p className="text-xs font-semibold">{r.label}</p>
                <p className="text-[10px] text-muted-foreground">{r.hint}</p>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {err && (
        <div className="flex items-start gap-2 rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /> {err}
        </div>
      )}
      <Button onClick={read} disabled={!file || busy} className="w-full gap-2">
        {busy ? <><Loader2 className="h-4 w-4 animate-spin" /> Reading your portfolio…</> : "Read my portfolio"}
      </Button>
    </div>
  )
}
