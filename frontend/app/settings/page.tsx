"use client"

import { useState } from "react"
import { useTheme } from "next-themes"
import { useAuth, type AccountType } from "@/lib/auth-context"
import { useSettings, type AccentColor, type AppSettings, type RiskTolerance, type SortOrder, type CardViewMode } from "@/lib/settings-context"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Settings, LogOut, User, Zap, Shield, Clock,
  Sun, Moon, Palette, TrendingUp, Globe, Eye,
  Info, BarChart2, Pencil, Check, X, Lock,
  Download, Trash2, KeyRound, Mail,
  LayoutGrid, List, SlidersHorizontal, AlertTriangle,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"
import type { Pick } from "@/lib/api"

// ── Section nav ────────────────────────────────────────────────────────────────

type SectionId = "account" | "appearance" | "analysis" | "display" | "privacy" | "plan" | "about"

const SECTIONS: { id: SectionId; label: string; icon: React.ElementType }[] = [
  { id: "account",    label: "Account",      icon: User          },
  { id: "appearance", label: "Appearance",   icon: Palette       },
  { id: "analysis",   label: "Analysis",     icon: TrendingUp    },
  { id: "display",    label: "Display",      icon: Eye           },
  { id: "privacy",    label: "Privacy",      icon: Lock          },
  { id: "plan",       label: "Plan & Usage", icon: BarChart2     },
  { id: "about",      label: "About",        icon: Info          },
]

// ── Plan metadata ──────────────────────────────────────────────────────────────

const PLAN_INFO: Record<AccountType, {
  label: string; color: string; icon: React.ReactNode; perks: string[]; limit: string
}> = {
  admin:   { label: "Admin",   color: "text-primary",          icon: <Shield className="h-4 w-4" />, perks: ["Unlimited runs", "Full admin panel", "All user controls", "App logs"], limit: "Unlimited" },
  premium: { label: "Premium", color: "text-accent",           icon: <Zap className="h-4 w-4" />,    perks: ["5 agent runs/week", "5 portfolio analyses/week", "Priority support"],  limit: "5 runs/week" },
  trial:   { label: "Trial",   color: "text-amber-500",        icon: <Clock className="h-4 w-4" />,  perks: ["2 agent runs/week", "3 portfolio analyses/week", "Basic support"],      limit: "2 runs/week" },
  guest:   { label: "Guest",   color: "text-muted-foreground", icon: <User className="h-4 w-4" />,   perks: ["View demo only", "No real-time data", "No analysis runs"],             limit: "0 runs" },
}

// ── Accent swatches ────────────────────────────────────────────────────────────

const ACCENT_SWATCHES: { id: AccentColor; label: string; bg: string; ring: string }[] = [
  { id: "gold",   label: "Gold",   bg: "bg-amber-500",  ring: "ring-amber-400"  },
  { id: "indigo", label: "Indigo", bg: "bg-indigo-500", ring: "ring-indigo-400" },
  { id: "teal",   label: "Teal",   bg: "bg-teal-500",   ring: "ring-teal-400"   },
  { id: "rose",   label: "Rose",   bg: "bg-rose-500",   ring: "ring-rose-400"   },
]

// ── Sectors ───────────────────────────────────────────────────────────────────

const SECTORS_INDIA = ["Banking", "IT", "Pharma", "FMCG", "Auto", "Energy", "Metals", "Realty", "Infrastructure", "Telecom", "Chemicals", "Consumer Discretionary"]
const SECTORS_US    = ["Technology", "Healthcare", "Financials", "Energy", "Consumer Staples", "Consumer Discretionary", "Industrials", "Materials", "Utilities", "Real Estate", "Communication Services"]

// ── Page ───────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [active, setActive] = useState<SectionId>("account")
  const { user, logout, isAdmin, updateUser } = useAuth()
  const { settings, update, reset } = useSettings()
  const { theme, setTheme } = useTheme()

  // ── account: username
  const [editingName,  setEditingName]  = useState(false)
  const [nameInput,    setNameInput]    = useState(user?.name ?? "")
  const [nameSaving,   setNameSaving]   = useState(false)
  const [nameError,    setNameError]    = useState("")

  async function saveName() {
    const trimmed = nameInput.trim()
    if (!trimmed || trimmed === user?.name) { setEditingName(false); return }
    setNameSaving(true); setNameError("")
    try {
      const res = await api.auth.updateProfile({ username: trimmed })
      updateUser({ name: res.name ?? trimmed })
      setEditingName(false)
    } catch (e: any) { setNameError(e.message ?? "Failed to save") }
    finally { setNameSaving(false) }
  }

  // ── account: notification email
  const [editingNE,   setEditingNE]   = useState(false)
  const [neInput,     setNeInput]     = useState(user?.notification_email ?? "")
  const [neSaving,    setNeSaving]    = useState(false)
  const [neError,     setNeError]     = useState("")

  async function saveNE() {
    const trimmed = neInput.trim()
    if (trimmed === (user?.notification_email ?? "")) { setEditingNE(false); return }
    setNeSaving(true); setNeError("")
    try {
      const res = await api.auth.updateProfile({ notification_email: trimmed })
      updateUser({ notification_email: res.notification_email ?? null })
      setEditingNE(false)
    } catch (e: any) { setNeError(e.message ?? "Failed to save") }
    finally { setNeSaving(false) }
  }

  // ── account: change password
  const [pwSent,   setPwSent]   = useState(false)
  const [pwSaving, setPwSaving] = useState(false)
  const [pwError,  setPwError]  = useState("")

  async function sendPasswordReset() {
    if (!user?.email) return
    setPwSaving(true); setPwError("")
    try {
      await api.auth.forgotPassword(user.email)
      setPwSent(true)
    } catch (e: any) { setPwError(e.message ?? "Failed to send") }
    finally { setPwSaving(false) }
  }

  // ── privacy: export CSV
  const [exporting, setExporting] = useState(false)

  async function exportCsv() {
    setExporting(true)
    try {
      const picks: Pick[] = await api.picks.list()
      const headers = ["Ticker", "Company", "Market", "Sector", "Size", "Signal", "Confidence", "Sentiment", "Price", "Currency", "Target%", "StopLoss%", "ROE", "D/E", "Revenue Growth", "PE Ratio", "Date", "Run By"]
      const rows = picks.map(p => [
        p.ticker, `"${(p.company_name ?? "").replace(/"/g, '""')}"`,
        p.market, p.sector, p.size,
        p.technical_signal, p.confidence, p.sentiment,
        p.current_price ?? "", p.currency ?? "",
        p.target_pct ?? "", p.stop_loss_pct ?? "",
        p.roe ?? "", p.debt_to_equity ?? "", p.revenue_growth ?? "", p.pe_ratio ?? "",
        p.analysis_date, p.run_by_username ?? "",
      ])
      const csv = [headers, ...rows].map(r => r.join(",")).join("\n")
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
      const url  = URL.createObjectURL(blob)
      const a    = document.createElement("a")
      a.href = url; a.download = "my-picks.csv"; a.click()
      URL.revokeObjectURL(url)
    } catch (e: any) { alert(e.message ?? "Export failed") }
    finally { setExporting(false) }
  }

  // ── privacy: clear history
  const [confirmClear, setConfirmClear] = useState(false)
  const [clearing,     setClearing]     = useState(false)

  async function clearHistory() {
    setClearing(true)
    try {
      await api.auth.clearPicks()
      setConfirmClear(false)
    } catch (e: any) { alert(e.message ?? "Failed to clear") }
    finally { setClearing(false) }
  }

  const acct = (isAdmin ? "admin" : (user?.account_type ?? "guest")) as AccountType
  const plan = PLAN_INFO[acct]
  const runsUsed  = user?.weekly_runs ?? 0
  const runsLimit = user?.limits?.crew_runs ?? 0
  const pct = runsLimit > 0 && runsLimit < 9999 ? Math.min((runsUsed / runsLimit) * 100, 100) : 0

  const allSectors = settings.defaultMarket === "US" ? SECTORS_US : SECTORS_INDIA

  function toggleSector(s: string) {
    const next = settings.defaultSectors.includes(s)
      ? settings.defaultSectors.filter(x => x !== s)
      : [...settings.defaultSectors, s]
    update("defaultSectors", next)
  }

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
        <div className="flex-1 min-w-0 space-y-4">

          {/* ════════════════════════════════════════
              ACCOUNT
          ════════════════════════════════════════ */}
          {active === "account" && (
            <Section title="Account" desc="Your profile and session">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">

                {/* Left: Avatar + username + email + meta */}
                <Card className="border-border/60">
                  <CardContent className="pt-5 space-y-4">
                    <div className="flex items-center gap-4">
                      <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary/15 border border-primary/20 text-xl font-bold text-primary">
                        {(user?.name || user?.email || "?")[0].toUpperCase()}
                      </div>
                      <div className="min-w-0 flex-1">
                        {editingName ? (
                          <div className="space-y-1.5">
                            <div className="flex items-center gap-2">
                              <Input value={nameInput} onChange={e => setNameInput(e.target.value)}
                                onKeyDown={e => { if (e.key === "Enter") saveName(); if (e.key === "Escape") setEditingName(false) }}
                                maxLength={50} className="h-8 text-sm" autoFocus />
                              <button onClick={saveName} disabled={nameSaving} className="text-primary hover:text-primary/80 disabled:opacity-40"><Check className="h-4 w-4" /></button>
                              <button onClick={() => { setEditingName(false); setNameInput(user?.name ?? "") }} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
                            </div>
                            {nameError && <p className="text-xs text-destructive">{nameError}</p>}
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <p className="font-semibold truncate">{user?.name || "—"}</p>
                            <button onClick={() => { setNameInput(user?.name ?? ""); setEditingName(true) }} className="text-muted-foreground hover:text-foreground transition-colors" title="Edit username">
                              <Pencil className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        )}
                        <p className="text-sm text-muted-foreground truncate">{user?.email || "—"}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-2">
                      <div className="rounded-lg bg-muted/50 px-3 py-2.5">
                        <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">Account Type</p>
                        <p className={`text-sm font-semibold ${plan.color}`}>{plan.label}</p>
                      </div>
                      <div className="rounded-lg bg-muted/50 px-3 py-2.5">
                        <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">Weekly Runs</p>
                        <p className="text-sm font-semibold">{runsLimit < 9999 ? `${runsUsed} / ${runsLimit}` : "Unlimited"}</p>
                      </div>
                    </div>

                    <div className="rounded-lg bg-muted/50 px-3 py-2">
                      <p className="text-[10px] uppercase tracking-wide text-muted-foreground mb-0.5">User ID</p>
                      <p className="font-mono text-xs text-muted-foreground select-all break-all">{user?.user_id || "—"}</p>
                    </div>

                    <Button variant="destructive" onClick={logout} size="sm" className="gap-2 w-full sm:w-auto">
                      <LogOut className="h-4 w-4" /> Sign Out
                    </Button>
                  </CardContent>
                </Card>

                {/* Right: Notification email + Change password */}
                <div className="space-y-4">
                  <Card className="border-border/60">
                    <CardContent className="pt-5 space-y-3">
                      <div className="flex items-center gap-2 mb-1">
                        <Mail className="h-4 w-4 text-muted-foreground" />
                        <p className="text-sm font-medium">Notification Email</p>
                      </div>
                      <p className="text-xs text-muted-foreground">Separate email for alerts and digests. Defaults to your login email if blank.</p>
                      {editingNE ? (
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-2">
                            <Input value={neInput} onChange={e => setNeInput(e.target.value)}
                              onKeyDown={e => { if (e.key === "Enter") saveNE(); if (e.key === "Escape") setEditingNE(false) }}
                              placeholder="alerts@example.com" type="email" className="h-8 text-sm" autoFocus />
                            <button onClick={saveNE} disabled={neSaving} className="text-primary hover:text-primary/80 disabled:opacity-40"><Check className="h-4 w-4" /></button>
                            <button onClick={() => { setEditingNE(false); setNeInput(user?.notification_email ?? "") }} className="text-muted-foreground hover:text-foreground"><X className="h-4 w-4" /></button>
                          </div>
                          {neError && <p className="text-xs text-destructive">{neError}</p>}
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <p className="text-sm text-muted-foreground truncate">
                            {user?.notification_email || <span className="italic">Same as login email</span>}
                          </p>
                          <button onClick={() => { setNeInput(user?.notification_email ?? ""); setEditingNE(true) }} className="text-muted-foreground hover:text-foreground transition-colors shrink-0">
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="border-border/60">
                    <CardContent className="pt-5 space-y-3">
                      <div className="flex items-center gap-2 mb-1">
                        <KeyRound className="h-4 w-4 text-muted-foreground" />
                        <p className="text-sm font-medium">Change Password</p>
                      </div>
                      <p className="text-xs text-muted-foreground">We'll send a reset link to <span className="font-medium text-foreground">{user?.email}</span>.</p>
                      {pwSent ? (
                        <div className="flex items-center gap-2 text-sm text-primary">
                          <Check className="h-4 w-4" /> Reset link sent — check your inbox.
                        </div>
                      ) : (
                        <>
                          <Button size="sm" variant="outline" onClick={sendPasswordReset} disabled={pwSaving} className="gap-2">
                            <KeyRound className="h-3.5 w-3.5" />
                            {pwSaving ? "Sending…" : "Send reset email"}
                          </Button>
                          {pwError && <p className="text-xs text-destructive">{pwError}</p>}
                        </>
                      )}
                    </CardContent>
                  </Card>
                </div>

              </div>
            </Section>
          )}

          {/* ════════════════════════════════════════
              APPEARANCE
          ════════════════════════════════════════ */}
          {active === "appearance" && (
            <Section title="Appearance" desc="Theme and color preferences">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">

                {/* Left: Theme */}
                <Card className="border-border/60">
                  <CardContent className="pt-5 space-y-4">
                    <div>
                      <p className="text-sm font-medium mb-1">Theme</p>
                      <p className="text-xs text-muted-foreground mb-3">Controls the overall color scheme of the app</p>
                      <div className="grid grid-cols-2 gap-2">
                        {(["dark", "light"] as const).map(t => (
                          <button key={t} onClick={() => setTheme(t)}
                            className={cn("flex flex-col items-center gap-2 rounded-lg border px-4 py-4 text-sm font-medium transition-all",
                              theme === t ? "border-primary/40 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-muted/40 hover:text-foreground")}>
                            {t === "dark" ? <Moon className="h-5 w-5" /> : <Sun className="h-5 w-5" />}
                            {t === "dark" ? "Dark" : "Light"}
                            {theme === t && <span className="text-[10px] opacity-60">Active</span>}
                          </button>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Right: Accent Color + Preview */}
                <Card className="border-border/60">
                  <CardContent className="pt-5 space-y-4">
                    <div>
                      <p className="text-sm font-medium mb-1">Accent Color</p>
                      <p className="text-xs text-muted-foreground mb-3">Changes buttons, highlights, and active states across the app</p>
                      <div className="grid grid-cols-4 gap-2">
                        {ACCENT_SWATCHES.map(s => (
                          <button key={s.id} onClick={() => update("accentColor", s.id)} title={s.label}
                            className={cn("flex flex-col items-center gap-1.5 rounded-xl py-3 transition-all",
                              settings.accentColor === s.id ? `ring-2 ring-offset-2 ring-offset-card ${s.ring}` : "opacity-60 hover:opacity-90")}>
                            <span className={cn("h-9 w-9 rounded-full", s.bg)} />
                            <span className="text-[10px] text-muted-foreground">{s.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>
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

              </div>
            </Section>
          )}

          {/* ════════════════════════════════════════
              ANALYSIS
          ════════════════════════════════════════ */}
          {active === "analysis" && (
            <Section title="Analysis Defaults" desc="Pre-fill values and filters for every run">

              {/* Row 1: Market+Cap (left) | Sectors (right) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">

                <Card className="border-border/60">
                  <CardContent className="pt-5 space-y-5">
                    <div>
                      <p className="text-sm font-medium mb-3">Default Market</p>
                      <div className="grid grid-cols-2 gap-2">
                        {(["INDIA", "US"] as const).map(m => (
                          <button key={m} onClick={() => { update("defaultMarket", m); update("defaultSectors", []) }}
                            className={cn("flex items-center gap-2.5 rounded-lg border px-4 py-3 text-sm font-medium transition-all",
                              settings.defaultMarket === m ? "border-primary/40 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-muted/40 hover:text-foreground")}>
                            {m === "INDIA" ? <TrendingUp className="h-4 w-4" /> : <Globe className="h-4 w-4" />}
                            {m === "INDIA" ? "India (NSE)" : "US (NYSE)"}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <p className="text-sm font-medium mb-1.5">Default Cap Size</p>
                      <Select value={settings.defaultCapSize} onValueChange={v => update("defaultCapSize", v)}>
                        <SelectTrigger className="w-full bg-muted/40 border-border/60"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {(settings.defaultMarket === "US" ? ["Mega", "Large", "Mid", "Small"] : ["Large", "Mid", "Small"])
                            .map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-border/60">
                  <CardContent className="pt-5 space-y-3">
                    <div>
                      <p className="text-sm font-medium mb-1">Default Sectors</p>
                      <p className="text-xs text-muted-foreground mb-3">Pre-selected when you open a new run. Leave blank to pick manually each time.</p>
                      <div className="flex flex-wrap gap-2">
                        {allSectors.map(s => {
                          const selected = settings.defaultSectors.includes(s)
                          return (
                            <button key={s} onClick={() => toggleSector(s)}
                              className={cn("rounded-full border px-3 py-1 text-xs font-medium transition-all",
                                selected ? "border-primary/50 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:border-border hover:text-foreground")}>
                              {s}
                            </button>
                          )
                        })}
                      </div>
                      {settings.defaultSectors.length > 0 && (
                        <button onClick={() => update("defaultSectors", [])} className="mt-2 text-xs text-muted-foreground hover:text-destructive transition-colors">Clear all</button>
                      )}
                    </div>
                  </CardContent>
                </Card>

              </div>

              {/* Row 2: Risk + Confidence + Num Picks (full width) */}
              <Card className="border-border/60">
                <CardContent className="pt-5">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

                    {/* Risk tolerance */}
                    <div>
                      <p className="text-sm font-medium mb-1">Risk Tolerance</p>
                      <p className="text-xs text-muted-foreground mb-3">Filters which pick signals are shown</p>
                      <div className="flex flex-col gap-2">
                        {([
                          { id: "conservative", label: "Conservative", desc: "Strong Buy only" },
                          { id: "moderate",     label: "Moderate",     desc: "Buy & above"     },
                          { id: "aggressive",   label: "Aggressive",   desc: "All signals"     },
                        ] as { id: RiskTolerance; label: string; desc: string }[]).map(r => (
                          <button key={r.id} onClick={() => update("riskTolerance", r.id)}
                            className={cn("flex items-center justify-between rounded-lg border px-3 py-2.5 text-left transition-all",
                              settings.riskTolerance === r.id ? "border-primary/40 bg-primary/10" : "border-border/60 hover:bg-muted/40")}>
                            <span className={cn("text-xs font-semibold", settings.riskTolerance === r.id ? "text-primary" : "text-foreground")}>{r.label}</span>
                            <span className="text-[10px] text-muted-foreground">{r.desc}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Min confidence */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <p className="text-sm font-medium">Min Confidence</p>
                        <span className="text-sm font-semibold text-primary">
                          {settings.minConfidence === 0 ? "Off" : `${settings.minConfidence}%+`}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mb-3">Hide picks below this score</p>
                      <input type="range" min={0} max={90} step={10} value={settings.minConfidence}
                        onChange={e => update("minConfidence", Number(e.target.value))}
                        className="w-full accent-primary cursor-pointer" />
                      <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                        <span>Off</span><span>50%</span><span>90%</span>
                      </div>
                    </div>

                    {/* Default num picks */}
                    <div>
                      <p className="text-sm font-medium mb-1">Picks per Run</p>
                      <p className="text-xs text-muted-foreground mb-3">Top picks shown after each run</p>
                      <div className="grid grid-cols-2 gap-2">
                        {[5, 10, 15, 20].map(n => (
                          <button key={n} onClick={() => update("defaultNumPicks", n)}
                            className={cn("rounded-lg border py-2 text-sm font-medium transition-all",
                              settings.defaultNumPicks === n ? "border-primary/40 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-muted/40")}>
                            {n}
                          </button>
                        ))}
                      </div>
                    </div>

                  </div>
                </CardContent>
              </Card>

              <p className="text-xs text-muted-foreground rounded-lg bg-muted/40 px-3 py-2.5">
                These are starting values — you can still change them before each individual run.
              </p>
            </Section>
          )}

          {/* ════════════════════════════════════════
              DISPLAY
          ════════════════════════════════════════ */}
          {active === "display" && (
            <Section title="Display" desc="Customise what you see across the app">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">

                {/* Left: Ticker Tape + Chart Period */}
                <Card className="border-border/60">
                  <CardContent className="pt-5 space-y-6">
                    <SettingRow label="Ticker Tape" desc="Live price scroll at the top of every page"
                      control={<Toggle checked={settings.showTickerTape} onChange={v => update("showTickerTape", v)} />} />

                    <div className="h-px bg-border/60" />

                    <div>
                      <p className="text-sm font-medium mb-1">Default Chart Period</p>
                      <p className="text-xs text-muted-foreground mb-3">Initial time range when opening a stock chart</p>
                      <div className="grid grid-cols-4 gap-1.5">
                        {(["1mo", "3mo", "6mo", "1y"] as const).map(p => (
                          <button key={p} onClick={() => update("defaultChartPeriod", p)}
                            className={cn("rounded-lg border py-2 text-xs font-medium transition-all",
                              settings.defaultChartPeriod === p ? "border-primary/40 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-muted/40")}>
                            {p}
                          </button>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Right: Sort Order + Card View */}
                <Card className="border-border/60">
                  <CardContent className="pt-5 space-y-6">
                    <div>
                      <p className="text-sm font-medium mb-1">Default Sort Order</p>
                      <p className="text-xs text-muted-foreground mb-3">How picks are ordered when a run completes</p>
                      <div className="grid grid-cols-2 gap-2">
                        {([
                          { id: "confidence", label: "Confidence", icon: SlidersHorizontal },
                          { id: "sector",     label: "Sector",     icon: LayoutGrid       },
                          { id: "date",       label: "Date",       icon: Clock            },
                          { id: "price",      label: "Price",      icon: BarChart2        },
                        ] as { id: SortOrder; label: string; icon: React.ElementType }[]).map(o => (
                          <button key={o.id} onClick={() => update("defaultSortOrder", o.id)}
                            className={cn("flex items-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium transition-all",
                              settings.defaultSortOrder === o.id ? "border-primary/40 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-muted/40 hover:text-foreground")}>
                            <o.icon className="h-3.5 w-3.5" /> {o.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="h-px bg-border/60" />

                    <div>
                      <p className="text-sm font-medium mb-1">Card View</p>
                      <p className="text-xs text-muted-foreground mb-3">How stock cards are displayed in results</p>
                      <div className="grid grid-cols-2 gap-2">
                        {([
                          { id: "expanded", label: "Expanded", icon: LayoutGrid, desc: "Full card with rationale" },
                          { id: "compact",  label: "Compact",  icon: List,       desc: "Dense table-style rows"  },
                        ] as { id: CardViewMode; label: string; icon: React.ElementType; desc: string }[]).map(v => (
                          <button key={v.id} onClick={() => update("cardViewMode", v.id)}
                            className={cn("flex flex-col items-start rounded-lg border px-3 py-2.5 text-left transition-all",
                              settings.cardViewMode === v.id ? "border-primary/40 bg-primary/10" : "border-border/60 hover:bg-muted/40")}>
                            <div className="flex items-center gap-2 mb-0.5">
                              <v.icon className="h-3.5 w-3.5" />
                              <span className={cn("text-xs font-semibold", settings.cardViewMode === v.id ? "text-primary" : "text-foreground")}>{v.label}</span>
                            </div>
                            <span className="text-[10px] text-muted-foreground">{v.desc}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>

              </div>
            </Section>
          )}

          {/* ════════════════════════════════════════
              PRIVACY
          ════════════════════════════════════════ */}
          {active === "privacy" && (
            <Section title="Privacy & Data" desc="Manage your data and history">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">

                {/* Export */}
                <Card className="border-border/60">
                  <CardContent className="pt-5 space-y-3">
                    <div className="flex items-center gap-2">
                      <Download className="h-4 w-4 text-muted-foreground" />
                      <p className="text-sm font-medium">Export Pick History</p>
                    </div>
                    <p className="text-xs text-muted-foreground">Download all your saved picks as a CSV file. Includes all analysis data, prices, and signals.</p>
                    <Button size="sm" variant="outline" onClick={exportCsv} disabled={exporting} className="gap-2 w-full sm:w-auto">
                      <Download className="h-3.5 w-3.5" />
                      {exporting ? "Exporting…" : "Download CSV"}
                    </Button>
                  </CardContent>
                </Card>

                {/* Clear history */}
                <Card className="border-border/60 border-destructive/20">
                  <CardContent className="pt-5 space-y-3">
                    <div className="flex items-center gap-2">
                      <Trash2 className="h-4 w-4 text-destructive" />
                      <p className="text-sm font-medium text-destructive">Clear Run History</p>
                    </div>
                    <p className="text-xs text-muted-foreground">Permanently delete all your saved picks and analysis history. This cannot be undone.</p>
                    {confirmClear ? (
                      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 space-y-3">
                        <div className="flex items-start gap-2 text-xs text-destructive">
                          <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                          <span>This will permanently delete all your picks. Are you sure?</span>
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="destructive" onClick={clearHistory} disabled={clearing} className="gap-1.5">
                            <Trash2 className="h-3.5 w-3.5" />
                            {clearing ? "Deleting…" : "Yes, delete all"}
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => setConfirmClear(false)}>Cancel</Button>
                        </div>
                      </div>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => setConfirmClear(true)} className="gap-2 w-full sm:w-auto border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive">
                        <Trash2 className="h-3.5 w-3.5" /> Clear History
                      </Button>
                    )}
                  </CardContent>
                </Card>

              </div>
            </Section>
          )}

          {/* ════════════════════════════════════════
              PLAN & USAGE
          ════════════════════════════════════════ */}
          {active === "plan" && (
            <Section title="Plan & Usage" desc="Your subscription and weekly limits">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">

                <Card className="border-border/60">
                  <CardHeader className="pb-3">
                    <CardTitle className={`flex items-center gap-2 text-base ${plan.color}`}>
                      {plan.icon} {plan.label} Plan
                    </CardTitle>
                    <CardDescription>{plan.limit}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ul className="space-y-2">
                      {plan.perks.map(p => (
                        <li key={p} className="flex items-center gap-2 text-sm text-muted-foreground">
                          <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${plan.color.replace("text-", "bg-")}`} />
                          {p}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>

                <Card className="border-border/60">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-base">Usage This Week</CardTitle>
                    <CardDescription>Resets every Monday</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {runsLimit > 0 && runsLimit < 9999 ? (
                      <div>
                        <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
                          <span>Crew runs</span>
                          <span className={runsUsed >= runsLimit ? "text-destructive font-semibold" : ""}>{runsUsed} / {runsLimit}</span>
                        </div>
                        <div className="h-2.5 rounded-full bg-muted overflow-hidden">
                          <div className={`h-full rounded-full transition-all ${pct >= 100 ? "bg-destructive" : "bg-primary"}`} style={{ width: `${pct}%` }} />
                        </div>
                        {runsUsed >= runsLimit && <p className="mt-2 text-xs text-destructive">Limit reached — resets next Monday.</p>}
                      </div>
                    ) : (
                      <p className="text-sm text-muted-foreground">Unlimited runs — no weekly cap.</p>
                    )}
                    {acct !== "admin" && (
                      <div className="rounded-lg border border-border/60 bg-muted/30 p-3 text-xs text-muted-foreground">
                        Want more runs? Contact admin to upgrade your plan.
                      </div>
                    )}
                  </CardContent>
                </Card>

              </div>
            </Section>
          )}

          {/* ════════════════════════════════════════
              ABOUT
          ════════════════════════════════════════ */}
          {active === "about" && (
            <Section title="About" desc="App version and system info">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-start">

                <Card className="border-border/60">
                  <CardContent className="pt-5 space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/15 border border-primary/20">
                        <TrendingUp className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <p className="font-semibold">The Great Ponzi</p>
                        <p className="text-xs text-muted-foreground">AI Stock Analysis · v0.1.0</p>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <InfoRow label="API Backend"  value={process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"} mono />
                      <InfoRow label="Markets"      value="NSE India · NYSE / NASDAQ" />
                      <InfoRow label="Data Sources" value="yfinance · Finnhub · Google News" />
                      <InfoRow label="AI Engine"    value="Claude + CrewAI" />
                    </div>
                  </CardContent>
                </Card>

                <Card className="border-border/60">
                  <CardContent className="pt-5 space-y-4">
                    <p className="text-sm font-medium">Settings</p>
                    <p className="text-xs text-muted-foreground">Your preferences are stored locally per account and sync automatically when you log in on any device sharing the same browser.</p>
                    <div className="pt-2 border-t border-border/60">
                      <button onClick={reset} className="text-xs text-muted-foreground hover:text-destructive transition-colors">
                        Reset all settings to defaults
                      </button>
                    </div>
                  </CardContent>
                </Card>

              </div>
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
    <button role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
      className={cn("relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary",
        checked ? "bg-primary" : "bg-muted-foreground/30")}>
      <span className={cn("inline-block h-4 w-4 transform rounded-full bg-white shadow-sm transition-transform",
        checked ? "translate-x-4" : "translate-x-0.5")} />
    </button>
  )
}

function InfoRow({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg bg-muted/40 px-3 py-2">
      <span className="text-xs text-muted-foreground shrink-0">{label}</span>
      <span className={cn("text-xs font-medium text-right break-all", mono && "font-mono")}>{value}</span>
    </div>
  )
}
