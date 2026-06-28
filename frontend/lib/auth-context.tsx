"use client"

import { createContext, useContext, useEffect, useState, ReactNode } from "react"
import { api, type AuthUser } from "@/lib/api"

export const ADMIN_EMAIL = process.env.NEXT_PUBLIC_ADMIN_EMAIL ?? "akshatgupta428@gmail.com"

export type AccountType = "admin" | "premium" | "trial" | "guest"

export interface ExtendedUser extends AuthUser {
  account_type:       AccountType
  weekly_runs:        number
  limits:             { crew_runs: number; portfolio_runs: number }
  notification_email?: string | null
}

interface AuthContextValue {
  user:           ExtendedUser | null
  token:          string | null
  isGuest:        boolean
  isAdmin:        boolean
  login:          (email: string, password: string) => Promise<void>
  loginAsGuest:   () => void
  logout:         () => void
  forgotPassword: (email: string) => Promise<void>
  updateUser:     (updates: Partial<ExtendedUser>) => void
  loading:        boolean
}

const AuthContext = createContext<AuthContextValue>({
  user: null, token: null, isGuest: false, isAdmin: false,
  login: async () => {}, loginAsGuest: () => {}, logout: () => {},
  forgotPassword: async () => {}, updateUser: () => {}, loading: true,
})

const GUEST_USER: ExtendedUser = {
  user_id: "guest", email: "guest@demo.com", name: "Guest",
  account_type: "guest", weekly_runs: 0,
  limits: { crew_runs: 0, portfolio_runs: 0 },
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user,    setUser]    = useState<ExtendedUser | null>(null)
  const [token,   setToken]   = useState<string | null>(null)
  const [isGuest, setIsGuest] = useState(false)
  const [loading, setLoading] = useState(true)

  const isAdmin = user?.account_type === "admin" || user?.email === ADMIN_EMAIL

  useEffect(() => {
    const stored      = localStorage.getItem("access_token")
    const guestStored = localStorage.getItem("is_guest")
    if (guestStored === "true") {
      setIsGuest(true); setUser(GUEST_USER); setLoading(false); return
    }
    if (stored) {
      setToken(stored)
      api.auth.me()
        .then(u => setUser(u as ExtendedUser))
        .catch(() => { localStorage.removeItem("access_token"); setToken(null) })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  async function login(email: string, password: string) {
    const { access_token, user } = await api.auth.login(email, password)
    localStorage.removeItem("is_guest")
    localStorage.removeItem("last_run_result")   // never carry a prior account's run over
    localStorage.setItem("access_token", access_token)
    setToken(access_token)
    setUser(user as ExtendedUser)
    setIsGuest(false)
  }

  function loginAsGuest() {
    localStorage.removeItem("access_token")
    localStorage.setItem("is_guest", "true")
    setIsGuest(true); setUser(GUEST_USER); setToken(null)
  }

  function logout() {
    localStorage.removeItem("access_token")
    localStorage.removeItem("is_guest")
    localStorage.removeItem("last_run_result")
    setToken(null); setUser(null); setIsGuest(false)
  }

  async function forgotPassword(email: string) {
    await api.auth.forgotPassword(email)
  }

  function updateUser(updates: Partial<ExtendedUser>) {
    setUser(prev => prev ? { ...prev, ...updates } : null)
  }

  return (
    <AuthContext.Provider value={{ user, token, isGuest, isAdmin, login, loginAsGuest, logout, forgotPassword, updateUser, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
