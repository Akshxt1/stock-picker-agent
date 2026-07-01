"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  X, Sparkles, LayoutDashboard, TrendingUp, Briefcase,
  BarChart2, Settings, ChevronLeft, ChevronRight, Globe,
} from "lucide-react"

interface Step {
  icon:        React.ReactNode
  title:       string
  description: string
  detail:      string
}

const STEPS: Step[] = [
  {
    icon:        <Sparkles className="h-10 w-10 text-primary" />,
    title:       "Welcome to The Great Ponzi",
    description: "Your AI-powered stock analysis platform for India & US markets.",
    detail:      "We'll give you a quick tour of the key features so you can hit the ground running. You can replay this tour anytime from Settings.",
  },
  {
    icon:        <LayoutDashboard className="h-10 w-10 text-primary" />,
    title:       "Dashboard",
    description: "Your market command centre.",
    detail:      "Live indices (Nifty, Sensex, S&P 500, Nasdaq), top movers, FII/DII smart-money flows, sector heatmap, and curated market news — all updated in real time. The AI agent stream shows your latest stock picks right here.",
  },
  {
    icon:        (
      <div className="flex gap-2">
        <TrendingUp className="h-10 w-10 text-primary" />
        <Globe className="h-10 w-10 text-primary" />
      </div>
    ),
    title:       "India & US Markets",
    description: "Run AI-powered stock picks with a single click.",
    detail:      "Configure cap size, sectors, number of picks, and risk tolerance — then let the AI crew analyse fundamentals, technicals, and news to surface the best opportunities. Results stream in live.",
  },
  {
    icon:        <Briefcase className="h-10 w-10 text-primary" />,
    title:       "Portfolio",
    description: "Track your holdings and P&L in real time.",
    detail:      "Add Indian (NSE/BSE) and US positions. See current value, total returns, and per-holding gain/loss with live FX conversion between INR and USD. Hit 'Analyze Portfolio' to get AI commentary on your specific positions.",
  },
  {
    icon:        <BarChart2 className="h-10 w-10 text-primary" />,
    title:       "Metrics",
    description: "Measure how your picks are performing over time.",
    detail:      "Review every stock the AI has ever recommended for you — win rate, average return, and sector breakdown. Useful for tuning your filters and building conviction.",
  },
  {
    icon:        <Settings className="h-10 w-10 text-primary" />,
    title:       "You're all set!",
    description: "Customise the app to match your style in Settings.",
    detail:      "Change your default market, accent colour, chart period, minimum confidence threshold, and more. Your preferences are saved per account so they follow you across devices.",
  },
]

interface Props {
  onDismiss: () => void
}

export default function OnboardingTutorial({ onDismiss }: Props) {
  const [step, setStep] = useState(0)

  const isFirst = step === 0
  const isLast  = step === STEPS.length - 1
  const current = STEPS[step]

  function next() {
    if (isLast) { onDismiss(); return }
    setStep(s => s + 1)
  }

  function prev() {
    if (!isFirst) setStep(s => s - 1)
  }

  return (
    /* Backdrop */
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">

      {/* Card */}
      <div className="relative w-full max-w-lg mx-4 rounded-2xl border border-border/60 bg-card shadow-2xl">

        {/* Skip button */}
        <button
          onClick={onDismiss}
          className="absolute right-4 top-4 text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Skip tutorial"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Content */}
        <div className="px-8 pb-6 pt-8 text-center">
          {/* Icon */}
          <div className="flex justify-center mb-5">
            {current.icon}
          </div>

          {/* Text */}
          <h2 className="text-xl font-bold tracking-tight mb-2">{current.title}</h2>
          <p className="text-sm font-semibold text-primary mb-3">{current.description}</p>
          <p className="text-sm text-muted-foreground leading-relaxed">{current.detail}</p>
        </div>

        {/* Progress dots */}
        <div className="flex justify-center gap-1.5 pb-4">
          {STEPS.map((_, i) => (
            <button
              key={i}
              onClick={() => setStep(i)}
              className={cn(
                "h-1.5 rounded-full transition-all duration-200",
                i === step ? "w-6 bg-primary" : "w-1.5 bg-border hover:bg-muted-foreground"
              )}
              aria-label={`Go to step ${i + 1}`}
            />
          ))}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between border-t border-border/60 px-6 py-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={prev}
            disabled={isFirst}
            className="gap-1"
          >
            <ChevronLeft className="h-4 w-4" /> Back
          </Button>

          <span className="text-xs text-muted-foreground">
            {step + 1} / {STEPS.length}
          </span>

          <Button size="sm" onClick={next} className="gap-1">
            {isLast ? "Get Started" : <>Next <ChevronRight className="h-4 w-4" /></>}
          </Button>
        </div>
      </div>
    </div>
  )
}
