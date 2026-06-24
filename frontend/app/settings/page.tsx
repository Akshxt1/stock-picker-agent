"use client"

import { useState } from "react"
import { useTheme } from "next-themes"
import { useAuth, type AccountType } from "@/lib/auth-context"
import { useSettings, type AccentColor, type AppSettings } from "@/lib/settings-context"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Settings, LogOut, User, Zap, Shield, Clock,
  Sun, Moon, Palette, TrendingUp, Globe, Eye,
  Info, BarChart2,
} from "lucide-react"
import { cn } from "@/lib/utils"

// ── Section nav ────────────────────────────────────────────────────────────────

type SectionId = "account" | "appearance" | "analysis" | "display" | "plan" | "about"

const SECTIONS: { id: SectionId; label: string; icon: React.ElementType }[] = [
  { id: "account",    label: "Account",     icon: User      },
  { id: "appearance", label: "Appearance",  icon: Palette   },
  { id: "analysis",   label: "Analysis",    icon: TrendingUp },
  { id: "display",    label: "Display",     icon: Eye       },
  { id: "plan",       label: "Plan & Usage", icon: BarChart2 },
  { id: "about",      label: "About",       icon: Info      },
]

// ── Plan metadata ──────────────────────────────────────────────────────────────

const PLAN_INFO: Record<AccountType, {
  label: string; color: string; icon: React.ReactNode; perks: string[]; limit: string
}> = {
  admin:   { label: "Admin",   color: "text-primary",         icon: <Shield className="h-4 w-4" />, perks: ["Unlimited runs", "Full admin panel", "All user controls", "App logs"], limit: "Unlimited" },
  premium: { label: "Premium", color: "text-accent",          icon: <Zap className="h-4 w-4" />,    perks: ["5 agent runs/week", "5 portfolio analyses/week", "Priority support"], limit: "5 runs/week" },
  trial:   { label: "Trial",   color: "text-amber-500",       icon: <Clock className="h-4 w-4" />,  perks: ["2 agent runs/week", "3 portfolio analyses/week", "Basic support"],    limit: "2 runs/week" },
  guest:   { label: "Guest",   color: "text-muted-foreground", icon: <User className="h-4 w-4" />,  perks: ["View demo only", "No real-time data", "No analysis runs"],           limit: "0 runs" },
}

// ── Accent swatches ────────────────────────────────────────────────────────────

const ACCENT_SWATCHES: { id: AccentColor; label: string; bg: string; ring: string }[] = [
  { id: "gold",   label: "Gold",   bg: "bg-amber-500",  ring: "ring-amber-400" },
  { id: "indigo", label: "Indigo", bg: "bg-indigo-500", ring: "ring-indigo-400" },
  { id: "teal",   label: "Teal",   bg: "bg-teal-500",   ring: "ring-teal-400" },
  { id: "rose",   label: "Rose",   bg: "bg-rose-500",   ring: "ring-rose-400" },
]

// ── Page ───────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [active, setActive] = useState<SectionId>("account")
  const { user, logout, isAdmin } = useAuth()
  const { settings, update, reset } = useSettings()
  const { theme, setTheme } = useTheme()

  const acct = (isAdmin ? "admin" : (user?.account_type ?? "guest")) as AccountType
  const plan = PLAN_INFO[acct]
  const runsUsed  = user?.weekly_runs ?? 0
  const runsLimit = user?.limits?.crew_runs ?? 0
  const pct = runsLimit > 0 && runsLimit < 9999 ? Math.min((runsUsed / runsLimit) * 100, 100) : 0

  return (
    <div className="space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold flex items-center gap-2">
        <Settings className="h-6 w-6" /> Settings
      </h1>

      <div className="flex flex-col md:flex-row gap-6">

        {/* ── Left nav ── */}
        <nav className="flex md:flex-col gap-1 md:w-48 shrink-0 overflow-x-auto md:overflow-visible pb-1 md:pb-0">
          {SECTIONS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActive(id)}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm font-medium transition-all whitespace-nowrap",
                active === id
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </button>
          ))}
        </nav>

        {/* ── Content panel ── */}
        <div className="flex-1 min-w-0 max-w-lg">

          {/* ── Account ── */}
          {active === "account" && (
            <Section title="Account" desc="Your profile and session">
              <Card className="border-border/60">
                <CardContent className="pt-5 space-y-4">
                  <div className="flex items-center gap-4">
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary/15 border border-primary/20 text-xl font-bold text-primary">
                      {(user?.name || user?.email || "?")[0].toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold truncate">{user?.name || "—"}</p>
                      <p className="text-sm text-muted-foreground truncate">{user?.email || "—"}</p>
                    </div>
                  </div>
                  <div className="rounded-lg bg-muted/50 px-3 py-2">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">User ID</p>
                    <p className="font-mono text-xs text-muted-foreground select-all break-all">{user?.user_id || "—"}</p>
                  </div>
                  <div className="rounded-lg bg-muted/50 px-3 py-2">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">Account Type</p>
                    <p className={`text-sm font-semibold ${plan.color}`}>{plan.label}</p>
                  </div>
                  <Button variant="destructive" onClick={logout} size="sm" className="gap-2">
                    <LogOut className="h-4 w-4" /> Sign Out
                  </Button>
                </CardContent>
              </Card>
            </Section>
          )}

          {/* ── Appearance ── */}
          {active === "appearance" && (
            <Section title="Appearance" desc="Theme and color preferences">
              <Card className="border-border/60">
                <CardContent className="pt-5 space-y-6">

                  {/* Theme */}
                  <div>
                    <p className="text-sm font-medium mb-3">Theme</p>
                    <div className="grid grid-cols-2 gap-2">
                      {(["dark", "light"] as const).map(t => (
                        <button
                          key={t}
                          onClick={() => setTheme(t)}
                          className={cn(
                            "flex items-center gap-2.5 rounded-lg border px-4 py-3 text-sm font-medium transition-all",
                            theme === t
                              ? "border-primary/40 bg-primary/10 text-primary"
                              : "border-border/60 text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                          )}
                        >
                          {t === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                          {t === "dark" ? "Dark" : "Light"}
                          {theme === t && <span className="ml-auto text-[10px] opacity-60">Active</span>}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Accent color */}
                  <div>
                    <p className="text-sm font-medium mb-1">Accent Color</p>
                    <p className="text-xs text-muted-foreground mb-3">
                      Changes buttons, highlights, and active states across the app
                    </p>
                    <div className="flex gap-3 flex-wrap">
                      {ACCENT_SWATCHES.map(s => (
                        <button
                          key={s.id}
                          onClick={() => update("accentColor", s.id)}
                          title={s.label}
                          className={cn(
                            "flex flex-col items-center gap-1.5 rounded-xl p-2.5 transition-all",
                            settings.accentColor === s.id
                              ? `ring-2 ring-offset-2 ring-offset-card ${s.ring}`
                              : "opacity-60 hover:opacity-90"
                          )}
                        >
                          <span className={cn("h-9 w-9 rounded-full", s.bg)} />
                          <span className="text-[10px] text-muted-foreground">{s.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Live preview */}
                  <div className="rounded-lg border border-border/60 bg-muted/30 p-3">
                    <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-2">Preview</p>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="rounded-md bg-primary/15 text-primary text-xs font-semibold px-3 py-1.5">Active nav</span>
                      <span className="rounded-full bg-primary h-2.5 w-2.5" />
                      <span className="text-primary text-sm font-semibold">Primary text</span>
                      <span className="h-px w-4 bg-border/60" />
                      <span className="rounded-md bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground">Button</span>
                    </div>
                  </div>

                </CardContent>
              </Card>
            </Section>
          )}

          {/* ── Analysis Defaults ── */}
          {active === "analysis" && (
            <Section title="Analysis Defaults" desc="Pre-fill values when you open a new analysis run">
              <Card className="border-border/60">
                <CardContent className="pt-5 space-y-5">

                  {/* Default Market */}
                  <div>
                    <p className="text-sm font-medium mb-3">Default Market</p>
                    <div className="grid grid-cols-2 gap-2">
                      {(["INDIA", "US"] as const).map(m => (
                        <button
                          key={m}
                          onClick={() => update("defaultMarket", m)}
                          className={cn(
                            "flex items-center gap-2.5 rounded-lg border px-4 py-3 text-sm font-medium transition-all",
                            settings.defaultMarket === m
                              ? "border-primary/40 bg-primary/10 text-primary"
                              : "border-border/60 text-muted-foreground hover:bg-muted/40 hover:text-foreground"
                          )}
                        >
                          {m === "INDIA" ? <TrendingUp className="h-4 w-4" /> : <Globe className="h-4 w-4" />}
                          {m === "INDIA" ? "India (NSE)" : "US (NYSE)"}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Default Cap Size */}
                  <div>
                    <p className="text-sm font-medium mb-1.5">Default Cap Size</p>
                    <p className="text-xs text-muted-foreground mb-3">
                      Applied when the cap size dropdown loads for the selected market
                    </p>
                    <Select
                      value={settings.defaultCapSize}
                      onValueChange={v => update("defaultCapSize", v as AppSettings["defaultCapSize"])}
                    >
                      <SelectTrigger className="w-40 bg-muted/40 border-border/60">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(settings.defaultMarket === "US"
                          ? ["Mega", "Large", "Mid", "Small"]
                          : ["Large", "Mid", "Small"]
                        ).map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>

                  <p className="text-xs text-muted-foreground rounded-lg bg-muted/40 px-3 py-2.5">
                    These are starting values only — you can change them before each run without affecting this default.
                  </p>

                </CardContent>
              </Card>
            </Section>
          )}

          {/* ── Display ── */}
          {active === "display" && (
            <Section title="Display" desc="Customise what you see across the app">
              <Card className="border-border/60">
                <CardContent className="pt-5 space-y-6">

                  <SettingRow
                    label="Ticker Tape"
                    desc="Live price scroll at the top of every page"
                    control={
                      <Toggle
                        checked={settings.showTickerTape}
                        onChange={v => update("showTickerTape", v)}
                      />
                    }
                  />

                  <div className="h-px bg-border/60" />

                  <div>
                    <p className="text-sm font-medium mb-1">Default Chart Period</p>
                    <p className="text-xs text-muted-foreground mb-3">
                      Initial time range when opening a stock&apos;s price chart
                    </p>
                    <div className="flex gap-1.5 flex-wrap">
                      {(["1mo", "3mo", "6mo", "1y"] as const).map(p => (
                        <button
                          key={p}
                          onClick={() => update("defaultChartPeriod", p)}
                          className={cn(
                            "rounded-lg border px-4 py-1.5 text-xs font-medium transition-all",
                            settings.defaultChartPeriod === p
                              ? "border-primary/40 bg-primary/10 text-primary"
                              : "border-border/60 text-muted-foreground hover:bg-muted/40"
                          )}
                        >
                          {p}
                        </button>
                      ))}
                    </div>
                  </div>

                </CardContent>
              </Card>
            </Section>
          )}

          {/* ── Plan & Usage ── */}
          {active === "plan" && (
            <Section title="Plan & Usage" desc="Your subscription and weekly limits">
              <Card className="border-border/60">
                <CardHeader className="pb-3">
                  <CardTitle className={`flex items-center gap-2 text-base ${plan.color}`}>
                    {plan.icon} {plan.label} Plan
                  </CardTitle>
                  <CardDescription>{plan.limit}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2">
                    {plan.perks.map(p => (
                      <li key={p} className="flex items-center gap-2 text-sm text-muted-foreground">
                        <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${plan.color.replace("text-", "bg-")}`} />
                        {p}
                      </li>
                    ))}
                  </ul>

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
            </Section>
          )}

          {/* ── About ── */}
          {active === "about" && (
            <Section title="About" desc="App version and system info">
              <Card className="border-border/60">
                <CardContent className="pt-5 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/15 border border-primary/20">
                      <TrendingUp className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-semibold text-sm">The Great Ponzi</p>
                      <p className="text-xs text-muted-foreground">AI Stock Analysis · v0.1.0</p>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <InfoRow label="API Backend"   value={process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"} mono />
                    <InfoRow label="Markets"        value="NSE India · NYSE / NASDAQ" />
                    <InfoRow label="Data Sources"   value="yfinance · Finnhub · Google News" />
                    <InfoRow label="AI Engine"      value="Claude + CrewAI" />
                  </div>

                  <div className="pt-2 border-t border-border/60">
                    <button
                      onClick={reset}
                      className="text-xs text-muted-foreground hover:text-destructive transition-colors"
                    >
                      Reset all settings to defaults
                    </button>
                  </div>
                </CardContent>
              </Card>
            </Section>
          )}

        </div>
      </div>
    </div>
  )
}

// ── Shared sub-components ──────────────────────────────────────────────────────

function Section({ title, desc, children }: { title: string; desc: string; children: React.ReactNode }) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="text-sm text-muted-foreground">{desc}</p>
      </div>
      {children}
    </div>
  )
}

function SettingRow({ label, desc, control }: { label: string; desc?: string; control: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <div>
        <p className="text-sm font-medium">{label}</p>
        {desc && <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>}
      </div>
      {control}
    </div>
  )
}

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={cn(
        "relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
        checked ? "bg-primary" : "bg-muted-foreground/30"
      )}
    >
      <span className={cn(
        "inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform",
        checked ? "translate-x-4" : "translate-x-0.5"
      )} />
    </button>
  )
}

function InfoRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg bg-muted/40 px-3 py-2">
      <span className="text-xs text-muted-foreground shrink-0">{label}</span>
      <span className={cn("text-xs font-medium text-right", mono && "font-mono")}>{value}</span>
    </div>
  )
}
