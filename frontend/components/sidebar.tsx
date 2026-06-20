"use client"

import Link           from "next/link"
import { usePathname } from "next/navigation"
import { cn }          from "@/lib/utils"
import { useAuth }     from "@/lib/auth-context"
import { useRun }      from "@/lib/run-context"
import ThemeToggle     from "@/components/ui/theme-toggle"
import {
  LayoutDashboard, TrendingUp, Globe, Briefcase,
  BarChart2, Settings, LogOut, Shield, Eye, Loader2,
} from "lucide-react"

const NAV = [
  { href: "/",          label: "Dashboard", icon: LayoutDashboard },
  { href: "/india",     label: "IND Market", icon: TrendingUp      },
  { href: "/us",        label: "US Market", icon: Globe           },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase       },
  { href: "/metrics",   label: "Metrics",   icon: BarChart2       },
  { href: "/settings",  label: "Settings",  icon: Settings        },
]

const ACCOUNT_BADGE: Record<string, { label: string; cls: string }> = {
  admin:   { label: "Admin",   cls: "bg-primary/15 text-primary border-primary/20" },
  premium: { label: "Premium", cls: "bg-accent/15 text-accent border-accent/20" },
  trial:   { label: "Trial",   cls: "bg-amber-500/15 text-amber-500 border-amber-500/20" },
  guest:   { label: "Guest",   cls: "bg-muted text-muted-foreground border-border" },
}

export default function Sidebar() {
  const pathname              = usePathname()
  const { user, isGuest, isAdmin, logout } = useAuth()
  const { state: runState }   = useRun()

  const acct   = (isAdmin ? "admin" : user?.account_type) ?? "guest"
  const badge  = ACCOUNT_BADGE[acct] ?? ACCOUNT_BADGE.guest
  const limits = user?.limits

  return (
    <aside className="flex flex-col w-56 min-h-screen bg-card border-r border-border/60 px-3 py-5 gap-1 shrink-0">

      {/* ── Logo ── */}
      <div className="px-2 mb-5">
        <div className="flex items-center gap-2 mb-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 border border-primary/20">
            <TrendingUp className="h-3.5 w-3.5 text-primary" />
          </div>
          <span className="font-bold text-sm gradient-text">The Great Ponzi</span>
        </div>
        {user && (
          <>
            <p className="text-[11px] text-muted-foreground truncate pl-0.5">
              {isGuest ? "Viewing as guest" : (user.name || user.email)}
            </p>
            <div className="mt-1.5 flex items-center gap-1.5">
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${badge.cls}`}>
                {badge.label}
              </span>
              {!isGuest && limits && limits.crew_runs < 9999 && (
                <span className="text-[10px] text-muted-foreground">
                  {user.weekly_runs ?? 0}/{limits.crew_runs} runs
                </span>
              )}
            </div>
          </>
        )}
      </div>

      {/* ── Nav ── */}
      <nav className="flex-1 space-y-0.5">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-all duration-150",
                active
                  ? "bg-primary/10 text-primary border border-primary/20"
                  : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
              )}
            >
              <Icon className={cn("h-4 w-4 shrink-0", active && "text-primary")} />
              {label}
              {/* Show running badge on Dashboard when a run is active */}
              {href === "/" && runState.running && (
                <span className="ml-auto flex items-center gap-1 text-[10px] font-semibold text-primary">
                  <Loader2 className="h-2.5 w-2.5 animate-spin" />
                  LIVE
                </span>
              )}
            </Link>
          )
        })}

        {isAdmin && (
          <Link
            href="/admin"
            className={cn(
              "flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-all duration-150",
              pathname === "/admin"
                ? "bg-primary/10 text-primary border border-primary/20"
                : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
            )}
          >
            <Shield className="h-4 w-4 shrink-0" />
            Admin
          </Link>
        )}
      </nav>

      {/* ── Bottom ── */}
      <div className="border-t border-border/60 pt-3 mt-2 space-y-1">
        <div className="flex items-center justify-between px-2.5 py-1">
          <span className="text-xs text-muted-foreground">Appearance</span>
          <ThemeToggle />
        </div>
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium text-muted-foreground hover:bg-muted/60 hover:text-foreground transition-all"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          {isGuest ? "Sign In" : "Log Out"}
        </button>
      </div>
    </aside>
  )
}
