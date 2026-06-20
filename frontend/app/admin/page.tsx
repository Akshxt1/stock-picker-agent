"use client"

import { useEffect, useState, useCallback } from "react"
import { useAuth }  from "@/lib/auth-context"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge }    from "@/components/ui/badge"
import { Button }   from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Shield, Lock, Users, Zap, Activity, ScrollText, RefreshCw, Loader2 } from "lucide-react"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

async function adminFetch(path: string) {
  const token = localStorage.getItem("access_token")
  const res = await fetch(`${BASE}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

async function adminPatch(path: string, body: object) {
  const token = localStorage.getItem("access_token")
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

type Tab = "users" | "usage" | "runs" | "logs"

const ACCOUNT_TYPES = ["admin", "premium", "trial", "guest"]
const BADGE_MAP: Record<string, string> = {
  admin:   "bg-primary/15 text-primary",
  premium: "bg-accent/15 text-accent",
  trial:   "bg-amber-500/15 text-amber-500",
  guest:   "bg-muted text-muted-foreground",
}

export default function AdminPage() {
  const { isAdmin } = useAuth()
  const [tab,     setTab]     = useState<Tab>("users")
  const [loading, setLoading] = useState(false)
  const [data,    setData]    = useState<any>(null)
  const [error,   setError]   = useState<string | null>(null)
  const [updating, setUpdating] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const paths: Record<Tab, string> = {
        users: "/api/admin/users",
        usage: "/api/admin/usage",
        runs:  "/api/admin/runs",
        logs:  "/api/admin/logs?lines=150",
      }
      const d = await adminFetch(paths[tab])
      setData(d)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [tab])

  useEffect(() => { if (isAdmin) load() }, [tab, isAdmin, load])

  async function handleAccountTypeChange(userId: string, accountType: string) {
    setUpdating(userId)
    try {
      await adminPatch(`/api/admin/users/${userId}/account-type`, { account_type: accountType })
      await load()
    } catch (e: any) {
      setError(e.message)
    } finally {
      setUpdating(null)
    }
  }

  if (!isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground">
        <Lock className="h-8 w-8 opacity-40" />
        <p className="text-sm">Admin access only.</p>
      </div>
    )
  }

  const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "users", label: "Users",     icon: <Users     className="h-4 w-4" /> },
    { id: "usage", label: "Usage",     icon: <Zap       className="h-4 w-4" /> },
    { id: "runs",  label: "Run Logs",  icon: <Activity  className="h-4 w-4" /> },
    { id: "logs",  label: "App Logs",  icon: <ScrollText className="h-4 w-4" /> },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6 text-primary" /> Admin Panel
          </h1>
          <p className="text-sm text-muted-foreground mt-1">System control centre</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading} className="gap-2">
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>

      {/* ── Tabs ── */}
      <div className="flex gap-1 rounded-xl bg-muted/50 p-1 w-fit">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === t.id ? "bg-background shadow-sm text-foreground" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/20 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="h-7 w-7 animate-spin text-muted-foreground" /></div>
      ) : (

        /* ── Users ── */
        tab === "users" && Array.isArray(data) && (
          <Card className="border-border/60">
            <CardHeader><CardTitle className="text-base">All Users ({data.length})</CardTitle></CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border/60">
                      {["Username","Email","Account","Runs/Limit","Last Seen","Change Plan"].map(h => (
                        <th key={h} className="pb-2 pr-4 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    {data.map((u: any) => (
                      <tr key={u.user_id} className="hover:bg-muted/30">
                        <td className="py-2.5 pr-4 font-semibold">{u.username || "—"}</td>
                        <td className="py-2.5 pr-4 text-muted-foreground text-xs">{u.email}</td>
                        <td className="py-2.5 pr-4">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${BADGE_MAP[u.account_type] || ""}`}>
                            {u.account_type}
                          </span>
                        </td>
                        <td className="py-2.5 pr-4 text-xs">{u.weekly_runs} / {u.limits?.crew_runs}</td>
                        <td className="py-2.5 pr-4 text-xs text-muted-foreground">
                          {u.last_seen ? new Date(u.last_seen).toLocaleDateString() : "—"}
                        </td>
                        <td className="py-2.5 pr-4">
                          <Select
                            value={u.account_type}
                            onValueChange={v => handleAccountTypeChange(u.user_id, v)}
                            disabled={updating === u.user_id}
                          >
                            <SelectTrigger className="h-7 w-24 text-xs bg-muted/40 border-border/60">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {ACCOUNT_TYPES.map(t => <SelectItem key={t} value={t} className="text-xs">{t}</SelectItem>)}
                            </SelectContent>
                          </Select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )
      )}

      {/* ── Usage ── */}
      {!loading && tab === "usage" && data && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Total Runs",   value: data.total_calls },
              { label: "Input Tokens", value: data.total_input_tokens?.toLocaleString() },
              { label: "Output Tokens",value: data.total_output_tokens?.toLocaleString() },
              { label: "Total Cost",   value: `$${data.total_cost_usd?.toFixed(4)}` },
            ].map(s => (
              <Card key={s.label} className="border-border/60">
                <CardContent className="pt-5 pb-4">
                  <p className="text-2xl font-bold">{s.value}</p>
                  <p className="text-xs text-muted-foreground mt-1">{s.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>
          {data.by_user && Object.keys(data.by_user).length > 0 && (
            <Card className="border-border/60">
              <CardHeader><CardTitle className="text-sm">Usage by User</CardTitle></CardHeader>
              <CardContent>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border/60">
                      {["User","Calls","Tokens","Cost"].map(h => (
                        <th key={h} className="pb-2 pr-4 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    {Object.entries(data.by_user).map(([user, stats]: [string, any]) => (
                      <tr key={user} className="hover:bg-muted/30">
                        <td className="py-2 pr-4 font-medium">{user}</td>
                        <td className="py-2 pr-4">{stats.calls}</td>
                        <td className="py-2 pr-4">{stats.tokens?.toLocaleString()}</td>
                        <td className="py-2">${stats.cost?.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* ── Runs ── */}
      {!loading && tab === "runs" && Array.isArray(data) && (
        <Card className="border-border/60">
          <CardHeader><CardTitle className="text-sm">Recent Crew Runs ({data.length})</CardTitle></CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/60">
                    {["Time","User","Context","Tokens In","Tokens Out","Cost"].map(h => (
                      <th key={h} className="pb-2 pr-4 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {data.map((r: any) => (
                    <tr key={r.id} className="hover:bg-muted/30">
                      <td className="py-2 pr-4 text-xs text-muted-foreground whitespace-nowrap">{r.timestamp ? new Date(r.timestamp).toLocaleString() : "—"}</td>
                      <td className="py-2 pr-4 text-xs font-medium">{r.user}</td>
                      <td className="py-2 pr-4 text-xs">{r.context}</td>
                      <td className="py-2 pr-4 text-xs">{r.input_tokens?.toLocaleString()}</td>
                      <td className="py-2 pr-4 text-xs">{r.output_tokens?.toLocaleString()}</td>
                      <td className="py-2 text-xs">${r.cost_usd}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Logs ── */}
      {!loading && tab === "logs" && data && (
        <Card className="border-border/60">
          <CardHeader>
            <CardTitle className="text-sm flex items-center justify-between">
              App Logs
              <span className="text-xs text-muted-foreground font-normal">{data.path}</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data.lines?.length === 0 ? (
              <p className="text-sm text-muted-foreground">No logs yet. Logs appear here after the first crew run.</p>
            ) : (
              <div className="font-mono text-[11px] bg-muted/30 rounded-lg p-3 max-h-96 overflow-y-auto space-y-0.5">
                {data.lines?.map((line: string, i: number) => {
                  const isError = line.includes("[ERROR]") || line.includes("Error") || line.includes("error")
                  const isWarn  = line.includes("[WARNING]") || line.includes("WARN")
                  return (
                    <div key={i} className={`leading-relaxed ${isError ? "text-destructive" : isWarn ? "text-amber-500" : "text-foreground/70"}`}>
                      {line}
                    </div>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
