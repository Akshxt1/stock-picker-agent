"use client"

import { createContext, useContext, useEffect, useState, ReactNode } from "react"
import { useAuth } from "@/lib/auth-context"

export type AccentColor      = "gold" | "indigo" | "teal" | "rose"
export type ChartPeriod      = "1mo" | "3mo" | "6mo" | "1y"
export type DefaultMarket    = "INDIA" | "US"
export type RiskTolerance    = "conservative" | "moderate" | "aggressive"
export type SortOrder        = "confidence" | "sector" | "date" | "price"
export type CardViewMode     = "compact" | "expanded"

export interface AppSettings {
  // existing
  defaultMarket:      DefaultMarket
  defaultCapSize:     string
  showTickerTape:     boolean
  defaultChartPeriod: ChartPeriod
  accentColor:        AccentColor
  // analysis
  defaultSectors:     string[]
  riskTolerance:      RiskTolerance
  minConfidence:      number        // 0–100
  defaultNumPicks:    number        // 5–20
  // display
  defaultSortOrder:   SortOrder
  cardViewMode:       CardViewMode
}

export const SETTINGS_DEFAULTS: AppSettings = {
  defaultMarket:      "INDIA",
  defaultCapSize:     "Mid",
  showTickerTape:     true,
  defaultChartPeriod: "6mo",
  accentColor:        "gold",
  defaultSectors:     [],
  riskTolerance:      "moderate",
  minConfidence:      0,
  defaultNumPicks:    10,
  defaultSortOrder:   "confidence",
  cardViewMode:       "expanded",
}

interface SettingsCtx {
  settings: AppSettings
  update:   <K extends keyof AppSettings>(key: K, val: AppSettings[K]) => void
  reset:    () => void
}

const Ctx = createContext<SettingsCtx>({
  settings: SETTINGS_DEFAULTS,
  update: () => {},
  reset:  () => {},
})

export function SettingsProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const storageKey = user?.user_id ? `app_settings_${user.user_id}` : "app_settings"

  const [settings, setSettings] = useState<AppSettings>(SETTINGS_DEFAULTS)

  // Reload settings whenever the active user changes (login / logout)
  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey)
      if (raw) setSettings({ ...SETTINGS_DEFAULTS, ...JSON.parse(raw) })
      else setSettings(SETTINGS_DEFAULTS)
    } catch {}
  }, [storageKey])

  // Reflect accent color as a data attribute on <html> so CSS vars can target it
  useEffect(() => {
    const el = document.documentElement
    if (settings.accentColor === "gold") {
      el.removeAttribute("data-accent")
    } else {
      el.setAttribute("data-accent", settings.accentColor)
    }
  }, [settings.accentColor])

  function update<K extends keyof AppSettings>(key: K, val: AppSettings[K]) {
    setSettings(prev => {
      const next = { ...prev, [key]: val }
      try { localStorage.setItem(storageKey, JSON.stringify(next)) } catch {}
      return next
    })
  }

  function reset() {
    setSettings(SETTINGS_DEFAULTS)
    document.documentElement.removeAttribute("data-accent")
    try { localStorage.removeItem(storageKey) } catch {}
  }

  return <Ctx.Provider value={{ settings, update, reset }}>{children}</Ctx.Provider>
}

export const useSettings = () => useContext(Ctx)

/** Read a single setting synchronously from localStorage (avoids one-render lag in useState initialisers). */
export function readSettingSync<K extends keyof AppSettings>(key: K): AppSettings[K] {
  if (typeof window === "undefined") return SETTINGS_DEFAULTS[key]
  try {
    const raw = localStorage.getItem("app_settings")
    if (raw) {
      const parsed = JSON.parse(raw)
      if (key in parsed) return parsed[key] as AppSettings[K]
    }
  } catch {}
  return SETTINGS_DEFAULTS[key]
}
