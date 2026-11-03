"use client"

import { useState } from "react"
import Link from "next/link"
import { ArrowLeft, Sparkles } from "lucide-react"
import UploadStep from "@/components/portfolio-agent/upload-step"
import ReviewStep, { readyHoldings, toReviewRows, type ReviewRow } from "@/components/portfolio-agent/review-step"
import ResultsStep from "@/components/portfolio-agent/results-step"
import { useAuth } from "@/lib/auth-context"
import { portfolioAgent, type AgentAnalysis, type AgentHoldingIn, type AgentParse } from "@/lib/api"

type Step = "upload" | "review" | "results"
const STEPS: { key: Step; label: string }[] = [
  { key: "upload", label: "Upload" }, { key: "review", label: "Check" }, { key: "results", label: "Strategy" },
]

export default function PortfolioStrategyPage() {
  const { isGuest } = useAuth()
  const [step, setStep] = useState<Step>("upload")
  const [goal, setGoal] = useState("")
  const [risk, setRisk] = useState("moderate")
  const [parse, setParse] = useState<AgentParse | null>(null)
  const [rows, setRows] = useState<ReviewRow[]>([])
  const [analysis, setAnalysis] = useState<AgentAnalysis | null>(null)
  const [confirmed, setConfirmed] = useState<AgentHoldingIn[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function analyse() {
    const holdings = readyHoldings(rows)
    setBusy(true); setErr(null)
    try {
      setAnalysis(await portfolioAgent.analyze(holdings))
      setConfirmed(holdings)
      setStep("results")
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Couldn't analyse these holdings.")
    } finally {
      setBusy(false)
    }
  }

  function restart() {
    setStep("upload"); setParse(null); setRows([]); setAnalysis(null); setConfirmed([]); setErr(null)
  }

  const idx = STEPS.findIndex(s => s.key === step)
  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <Link href="/portfolio" className="mb-3 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-3 w-3" /> Portfolio
        </Link>
        <h1 className="flex items-center gap-2 text-xl font-bold"><Sparkles className="h-5 w-5 text-primary" /> Portfolio strategy</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload your holdings, tell us your goal, and get a realistic plan based on your actual numbers, including how likely the goal really is.
        </p>
      </div>

      <ol className="flex items-center gap-2 text-xs">
        {STEPS.map((s, i) => (
          <li key={s.key} className="flex items-center gap-2">
            <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
              i <= idx ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"}`}>{i + 1}</span>
            <span className={i === idx ? "font-semibold" : "text-muted-foreground"}>{s.label}</span>
            {i < STEPS.length - 1 && <span className="mx-1 h-px w-6 bg-border" />}
          </li>
        ))}
      </ol>

      {isGuest ? (
        <div className="rounded-lg border border-border/60 bg-card p-6 text-center text-sm text-muted-foreground">
          Portfolio strategy is available to signed-in accounts. Please sign up or log in to use it.
        </div>
      ) : step === "upload" ? (
        <UploadStep goal={goal} setGoal={setGoal} risk={risk} setRisk={setRisk}
          onParsed={p => { setParse(p); setRows(toReviewRows(p)); setErr(null); setStep("review") }} />
      ) : step === "review" && parse ? (
        <ReviewStep parse={parse} rows={rows} setRows={setRows} busy={busy} error={err}
          onBack={() => setStep("upload")} onAnalyze={analyse} />
      ) : step === "results" && analysis ? (
        <ResultsStep analysis={analysis} holdings={confirmed} goal={goal} risk={risk} onRestart={restart} />
      ) : null}
    </div>
  )
}
