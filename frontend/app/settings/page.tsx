"use client"

import { useAuth, type AccountType } from "@/lib/auth-context"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Settings, LogOut, User, Zap, Shield, Clock } from "lucide-react"

const PLAN_INFO: Record<AccountType, {
  label: string; color: string; icon: React.ReactNode
  perks: string[]; limit: string
}> = {
  admin: {
    label: "Admin", color: "text-primary", icon: <Shield className="h-4 w-4" />,
    perks: ["Unlimited runs", "Full admin panel", "All user controls", "App logs"],
    limit: "Unlimited",
  },
  premium: {
    label: "Premium", color: "text-accent", icon: <Zap className="h-4 w-4" />,
    perks: ["5 agent runs/week", "5 portfolio analyses/week", "Priority support"],
    limit: "5 runs/week",
  },
  trial: {
    label: "Trial", color: "text-amber-500", icon: <Clock className="h-4 w-4" />,
    perks: ["2 agent runs/week", "3 portfolio analyses/week", "Basic support"],
    limit: "2 runs/week",
  },
  guest: {
    label: "Guest", color: "text-muted-foreground", icon: <User className="h-4 w-4" />,
    perks: ["View demo only", "No real-time data", "No analysis runs"],
    limit: "0 runs",
  },
}

export default function SettingsPage() {
  const { user, logout, isAdmin } = useAuth()
  const acct = (isAdmin ? "admin" : (user?.account_type ?? "guest")) as AccountType
  const plan = PLAN_INFO[acct]

  const runsUsed  = user?.weekly_runs ?? 0
  const runsLimit = user?.limits?.crew_runs ?? 0
  const pct       = runsLimit > 0 && runsLimit < 9999 ? Math.min((runsUsed / runsLimit) * 100, 100) : 0

  return (
    <div className="space-y-6 max-w-xl animate-fade-in">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <Settings className="h-6 w-6" /> Settings
      </h1>

      {/* ── Account info ── */}
      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <User className="h-4 w-4" /> Account
          </CardTitle>
          <CardDescription>Your profile details</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-1">Name</p>
              <p className="font-semibold">{user?.name ?? "—"}</p>
            </div>
            <div>
              <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-1">Email</p>
              <p className="font-semibold text-sm">{user?.email ?? "—"}</p>
            </div>
          </div>
          <div>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-1">User ID</p>
            <p className="font-mono text-xs text-muted-foreground">{user?.user_id ?? "—"}</p>
          </div>
          <Button variant="destructive" onClick={logout} size="sm" className="gap-2">
            <LogOut className="h-4 w-4" /> Sign Out
          </Button>
        </CardContent>
      </Card>

      {/* ── Plan ── */}
      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className={`flex items-center gap-2 text-base ${plan.color}`}>
            {plan.icon} {plan.label} Plan
          </CardTitle>
          <CardDescription>{plan.limit}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <ul className="space-y-1.5">
            {plan.perks.map(p => (
              <li key={p} className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className={`h-1.5 w-1.5 rounded-full ${plan.color.replace("text-", "bg-")}`} />
                {p}
              </li>
            ))}
          </ul>

          {/* Weekly usage bar */}
          {runsLimit > 0 && runsLimit < 9999 && (
            <div>
              <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
                <span>Crew runs this week</span>
                <span className={runsUsed >= runsLimit ? "text-destructive font-semibold" : ""}>
                  {runsUsed} / {runsLimit}
                </span>
              </div>
              <div className="h-2 rounded-full bg-muted overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${pct >= 100 ? "bg-destructive" : "bg-primary"}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              {runsUsed >= runsLimit && (
                <p className="mt-1.5 text-xs text-destructive">Limit reached — resets next Monday.</p>
              )}
            </div>
          )}

          {acct !== "admin" && (
            <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground">
              Want more runs? Contact admin to upgrade your plan.
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── API Backend ── */}
      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="text-base">API Backend</CardTitle>
          <CardDescription>Connected FastAPI server</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-sm text-muted-foreground">
            {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
