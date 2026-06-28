"use client"

import { useState } from "react"
import { useAuth }  from "@/lib/auth-context"
import { api }      from "@/lib/api"
import { Input }    from "@/components/ui/input"
import { Button }   from "@/components/ui/button"
import Image from "next/image"
import { Loader2, Eye, KeyRound, ArrowLeft, CheckCircle2, UserPlus } from "lucide-react"

type View = "login" | "signup" | "forgot" | "forgot-sent" | "signup-sent"

export default function LoginPage() {
  const { login, loginAsGuest, forgotPassword } = useAuth()
  const [view,     setView]     = useState<View>("login")
  const [email,    setEmail]    = useState("")
  const [password, setPassword] = useState("")
  const [username, setUsername] = useState("")
  const [confirm,  setConfirm]  = useState("")
  const [error,    setError]    = useState<string | null>(null)
  const [loading,  setLoading]  = useState(false)

  function reset(v: View) { setView(v); setError(null) }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault(); setError(null); setLoading(true)
    try { await login(email, password) }
    catch (err: unknown) { setError((err as Error).message ?? "Login failed") }
    finally { setLoading(false) }
  }

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault(); setError(null)
    if (password !== confirm) { setError("Passwords don't match"); return }
    if (password.length < 6)  { setError("Password must be at least 6 characters"); return }
    setLoading(true)
    try {
      await api.auth.signup(email, password, username)
      setView("signup-sent")
    } catch (err: unknown) { setError((err as Error).message ?? "Signup failed") }
    finally { setLoading(false) }
  }

  async function handleForgot(e: React.FormEvent) {
    e.preventDefault(); setError(null); setLoading(true)
    try { await forgotPassword(email); setView("forgot-sent") }
    catch (err: unknown) { setError((err as Error).message ?? "Failed to send reset email") }
    finally { setLoading(false) }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-40 -left-40 h-96 w-96 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 h-96 w-96 rounded-full bg-accent/10 blur-3xl" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full bg-primary/5 blur-3xl" />
      </div>

      <div className="relative z-10 w-full max-w-sm mx-4">
        <div className="mb-8 flex justify-center">
          <div className="rounded-2xl overflow-hidden shadow-2xl ring-1 ring-white/10" style={{ width: "200px", background: "white" }}>
            <Image
              src="/logo.png"
              alt="The Great Ponzi"
              width={1536}
              height={1024}
              className="w-full h-auto block"
              priority
            />
          </div>
        </div>

        <div className="rounded-2xl border border-border/60 bg-card/80 backdrop-blur-md p-6 shadow-2xl">

          {/* ── LOGIN / SIGNUP tabs ── */}
          {(view === "login" || view === "signup") && (
            <>
              <div className="flex rounded-lg bg-muted/50 p-1 mb-5">
                {(["login", "signup"] as View[]).map(v => (
                  <button key={v} onClick={() => reset(v)}
                    className={`flex-1 rounded-md py-1.5 text-sm font-medium transition-all capitalize ${
                      view === v ? "bg-background shadow-sm text-foreground" : "text-muted-foreground"
                    }`}
                  >
                    {v === "login" ? "Sign In" : "Sign Up"}
                  </button>
                ))}
              </div>

              {view === "login" ? (
                <form onSubmit={handleLogin} className="space-y-3">
                  <Input type="email" placeholder="Email address" value={email}
                    onChange={e => setEmail(e.target.value)} required className="bg-muted/50 border-border/60 h-11" />
                  <Input type="password" placeholder="Password" value={password}
                    onChange={e => setPassword(e.target.value)} required className="bg-muted/50 border-border/60 h-11" />
                  <div className="flex justify-end">
                    <button type="button" onClick={() => reset("forgot")}
                      className="text-xs text-muted-foreground hover:text-primary transition-colors">
                      Forgot password?
                    </button>
                  </div>
                  {error && <p className="rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">{error}</p>}
                  <Button type="submit" className="w-full h-11 font-semibold" disabled={loading}>
                    {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />} Sign In
                  </Button>
                </form>
              ) : (
                <form onSubmit={handleSignup} className="space-y-3">
                  <Input placeholder="Username" value={username}
                    onChange={e => setUsername(e.target.value)} required className="bg-muted/50 border-border/60 h-11" />
                  <Input type="email" placeholder="Email address" value={email}
                    onChange={e => setEmail(e.target.value)} required className="bg-muted/50 border-border/60 h-11" />
                  <Input type="password" placeholder="Password (min 6 chars)" value={password}
                    onChange={e => setPassword(e.target.value)} required className="bg-muted/50 border-border/60 h-11" />
                  <Input type="password" placeholder="Confirm password" value={confirm}
                    onChange={e => setConfirm(e.target.value)} required className="bg-muted/50 border-border/60 h-11" />
                  <p className="text-[11px] text-muted-foreground">New accounts start on the <strong>Trial</strong> plan (2 runs/week).</p>
                  {error && <p className="rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">{error}</p>}
                  <Button type="submit" className="w-full h-11 font-semibold" disabled={loading}>
                    {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UserPlus className="h-4 w-4 mr-2" />}
                    Create Account
                  </Button>
                </form>
              )}

              <div className="mt-4 flex items-center gap-3">
                <div className="h-px flex-1 bg-border/60" />
                <span className="text-xs text-muted-foreground">or</span>
                <div className="h-px flex-1 bg-border/60" />
              </div>
              <Button variant="outline" className="mt-4 w-full h-11 border-border/60 hover:bg-muted/60 font-medium gap-2" onClick={loginAsGuest}>
                <Eye className="h-4 w-4" /> View as Guest
              </Button>
              <p className="mt-2 text-center text-xs text-muted-foreground">No account needed · demo access only</p>
            </>
          )}

          {/* ── FORGOT ── */}
          {view === "forgot" && (
            <>
              <button onClick={() => reset("login")} className="mb-4 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
                <ArrowLeft className="h-4 w-4" /> Back
              </button>
              <div className="mb-5 flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                  <KeyRound className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <h2 className="text-base font-semibold">Reset password</h2>
                  <p className="text-xs text-muted-foreground">We'll email you a reset link</p>
                </div>
              </div>
              <form onSubmit={handleForgot} className="space-y-3">
                <Input type="email" placeholder="Your email" value={email}
                  onChange={e => setEmail(e.target.value)} required className="bg-muted/50 border-border/60 h-11" />
                {error && <p className="rounded-lg bg-destructive/10 border border-destructive/20 px-3 py-2 text-sm text-destructive">{error}</p>}
                <Button type="submit" className="w-full h-11 font-semibold" disabled={loading}>
                  {loading && <Loader2 className="h-4 w-4 animate-spin mr-2" />} Send Reset Link
                </Button>
              </form>
            </>
          )}

          {/* ── CONFIRMATIONS ── */}
          {(view === "forgot-sent" || view === "signup-sent") && (
            <div className="py-4 text-center">
              <CheckCircle2 className="mx-auto mb-3 h-10 w-10 text-accent" />
              <h2 className="text-base font-semibold">
                {view === "signup-sent" ? "Check your email" : "Reset link sent"}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {view === "signup-sent"
                  ? <>Confirm your email at <strong>{email}</strong> to activate your account.</>
                  : <>A reset link was sent to <strong>{email}</strong>.</>
                }
              </p>
              <Button variant="ghost" className="mt-5 w-full" onClick={() => reset("login")}>
                Back to sign in
              </Button>
            </div>
          )}
        </div>

        <p className="mt-6 text-center text-xs text-muted-foreground">
          Not financial advice. Do your own research.
        </p>
      </div>
    </div>
  )
}
