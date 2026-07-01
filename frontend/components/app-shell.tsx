"use client"

import { useEffect, useState } from "react"
import { useAuth }             from "@/lib/auth-context"
import { useSettings }         from "@/lib/settings-context"
import Sidebar                 from "@/components/sidebar"
import TickerTape              from "@/components/ticker-tape"
import LoginPage               from "@/app/login/page"
import OnboardingTutorial      from "@/components/onboarding-tutorial"
import { api }                 from "@/lib/api"
import { Loader2 }             from "lucide-react"

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, updateUser } = useAuth()
  const { settings }                  = useSettings()
  const [showTutorial, setShowTutorial] = useState(false)

  useEffect(() => {
    if (!user) return
    if (!user.tutorial_seen) setShowTutorial(true)
  }, [user?.user_id])

  async function dismissTutorial() {
    setShowTutorial(false)
    try {
      await api.auth.updateProfile({ tutorial_seen: true })
      updateUser({ tutorial_seen: true })
    } catch { /* best-effort — next login will retry */ }
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-7 w-7 animate-spin text-primary" />
          <p className="text-xs text-muted-foreground">Loading…</p>
        </div>
      </div>
    )
  }

  if (!user) return <LoginPage />

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        {settings.showTickerTape && <TickerTape />}
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
      {showTutorial && <OnboardingTutorial onDismiss={dismissTutorial} />}
    </div>
  )
}
