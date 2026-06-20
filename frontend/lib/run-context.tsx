"use client"

/**
 * RunContext — global crew run state.
 * Lives at the app level so navigating between pages doesn't kill the run.
 * The sidebar shows a live "Running..." badge using this context.
 */

import { createContext, useContext, useReducer, useRef, useEffect, ReactNode } from "react"
import { streamCrew, type StreamEvent, type Pick } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"

export type { Pick }

export type RunLine = {
  id:    number
  type:  StreamEvent["type"]
  agent?: string
  text:  string
  kind?: "tool" | "thought" | "answer"
  tool?: string | null
}

type RunState = {
  running:  boolean
  lines:    RunLine[]
  picks:    Pick[]
  error:    string | null
  params:   { market: string; sector: string; size: string } | null
  lastDone: boolean
}

type Action =
  | { type: "START";  params: RunState["params"] }
  | { type: "LINE";   line: Omit<RunLine, "id"> }
  | { type: "DONE";   picks: Pick[] }
  | { type: "RESTORE"; picks: Pick[]; params: RunState["params"] }
  | { type: "ERROR";  text: string }
  | { type: "STOP" }
  | { type: "RESET" }

const INITIAL: RunState = {
  running: false, lines: [], picks: [], error: null, params: null, lastDone: false,
}

function reducer(state: RunState, action: Action): RunState {
  switch (action.type) {
    case "START":  return { ...INITIAL, running: true, params: action.params }
    case "LINE":   return { ...state, lines: [...state.lines, { ...action.line, id: state.lines.length }] }
    case "DONE":   return { ...state, running: false, picks: action.picks, lastDone: true }
    case "RESTORE":return { ...state, picks: action.picks, params: action.params, lastDone: true }
    case "ERROR":  return { ...state, running: false, error: action.text }
    case "STOP":   return { ...state, running: false }
    case "RESET":  return INITIAL
    default:       return state
  }
}

interface RunContextValue {
  state:  RunState
  start:  (params: { market: string; sector: string; size: string }) => void
  stop:   () => void
  reset:  () => void
}

const Ctx = createContext<RunContextValue>({
  state: INITIAL, start: () => {}, stop: () => {}, reset: () => {},
})

export function RunProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, INITIAL)
  const stopRef = useRef<(() => void) | null>(null)
  const { user, loading } = useAuth()
  const ownerId = user?.user_id ?? null

  // Restore the last run ONLY if it belongs to the currently signed-in user.
  // When the account changes (or signs out), wipe any run state so one user's
  // runs never bleed into another's session on a shared browser.
  useEffect(() => {
    if (loading) return   // wait until auth resolves so we don't clear prematurely
    try {
      const saved = localStorage.getItem("last_run_result")
      const parsed = saved ? JSON.parse(saved) : null
      if (parsed?.picks?.length && parsed.userId && parsed.userId === ownerId) {
        dispatch({ type: "RESET" })
        dispatch({ type: "RESTORE", picks: parsed.picks, params: parsed.params ?? null })
        if (parsed.lines) parsed.lines.forEach((l: RunLine) => dispatch({ type: "LINE", line: l }))
      } else {
        // Different owner (or none) → clear it out.
        dispatch({ type: "RESET" })
        if (parsed && parsed.userId !== ownerId) localStorage.removeItem("last_run_result")
      }
    } catch {
      // ignore corrupt storage
    }
    // Re-run whenever the signed-in user changes or auth finishes loading.
  }, [ownerId, loading])

  // Save completed runs to localStorage, tagged with the owner.
  useEffect(() => {
    if (state.lastDone && state.picks.length > 0 && ownerId) {
      try {
        localStorage.setItem("last_run_result", JSON.stringify({
          userId: ownerId,
          picks:  state.picks,
          params: state.params,
          ts:     Date.now(),
        }))
      } catch {}
    }
  }, [state.lastDone, state.picks, state.params, ownerId])

  function start(params: { market: string; sector: string; size: string }) {
    stopRef.current?.()
    localStorage.removeItem("last_run_result")
    dispatch({ type: "START", params })

    const stop = streamCrew(params, (evt) => {
      switch (evt.type) {
        case "step":
          dispatch({ type: "LINE", line: { type: "step", agent: evt.agent, text: evt.text, kind: evt.kind, tool: evt.tool } })
          break
        case "task":
          dispatch({ type: "LINE", line: { type: "task", text: evt.text, agent: evt.agent } })
          break
        case "done":
          dispatch({ type: "LINE", line: { type: "done", text: "Analysis complete." } })
          dispatch({ type: "DONE", picks: ((evt.result as any)?.picks ?? []) as Pick[] })
          break
        case "error":
          dispatch({ type: "LINE", line: { type: "error", text: evt.text } })
          dispatch({ type: "ERROR", text: evt.text })
          break
      }
    })
    stopRef.current = stop
  }

  function stop() {
    stopRef.current?.()
    stopRef.current = null
    dispatch({ type: "STOP" })
  }

  function reset() {
    stopRef.current?.()
    stopRef.current = null
    dispatch({ type: "RESET" })
    localStorage.removeItem("last_run_result")
  }

  return <Ctx.Provider value={{ state, start, stop, reset }}>{children}</Ctx.Provider>
}

export const useRun = () => useContext(Ctx)
