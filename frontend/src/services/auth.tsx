import React from "react"

export type User = {
  id: string
  email: string
  display_name: string
  avatar_url?: string | null
  role: string
  created_at: string
  updated_at: string
  last_login_at?: string | null
}

type AuthContextType = {
  user: User | null
  token: string | null
  login: (p: { email: string; password: string }) => Promise<void>
  register: (p: { email: string; password: string; display_name?: string }) => Promise<void>
  logout: () => Promise<void>
  refreshMe: () => Promise<void>
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined)

// ---- config ----
const API_BASE = import.meta.env.VITE_ACCOUNT_API_BASE ?? "http://localhost:8003"
export const DEFAULT_AVATAR_URL = "/default-avatar.png" // put a file in /public, or change path

// ---- storage helpers ----
const TOKEN_KEY = "asl_token"
const AVATAR_KEY = "asl_avatar_url"

function getStoredToken(): string | null {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}
function setStoredToken(v: string | null) {
  try { v ? localStorage.setItem(TOKEN_KEY, v) : localStorage.removeItem(TOKEN_KEY) } catch {}
}
export function getStoredAvatar(): string | null {
  try { return localStorage.getItem(AVATAR_KEY) || null } catch { return null }
}
function setStoredAvatar(url: string | null) {
  try {
    if (url && url.trim() !== "") localStorage.setItem(AVATAR_KEY, url)
    // NOTE: intentionally do NOT clear on null/empty – keeps last good avatar
  } catch {}
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = React.useState<string | null>(getStoredToken())
  const [user, setUser] = React.useState<User | null>(null)
  const [bootstrapped, setBootstrapped] = React.useState(false)

  const authFetch = React.useCallback(
    async (path: string, init?: RequestInit) => {
      const headers: Record<string, string> = { "Content-Type": "application/json" }
      if (token) headers.Authorization = `Bearer ${token}`
      const res = await fetch(`${API_BASE}${path}`, { ...init, headers: { ...headers, ...(init?.headers as any) } })
      if (!res.ok) {
        const txt = await res.text().catch(() => "")
        throw new Error(txt || `HTTP ${res.status}`)
      }
      return res
    },
    [token]
  )

  const refreshMe = React.useCallback(async () => {
    if (!token) { setUser(null); return }
    const res = await authFetch("/user/me")
    const me = (await res.json()) as User
    // persist a new avatar only if backend provided one
    if (me.avatar_url && me.avatar_url.trim() !== "") {
      setStoredAvatar(me.avatar_url)
    }
    setUser(me)
  }, [token, authFetch])

  const login = React.useCallback(
    async ({ email, password }: { email: string; password: string }) => {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) {
        const txt = await res.text().catch(() => "")
        throw new Error(txt || "Login failed")
      }
      const data = (await res.json()) as { access_token: string }
      setToken(data.access_token)
      setStoredToken(data.access_token)
      await refreshMe()
    },
    [refreshMe]
  )

  const register = React.useCallback(
    async ({ email, password, display_name }: { email: string; password: string; display_name?: string }) => {
      const res = await fetch(`${API_BASE}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, display_name: display_name ?? "" }),
      })
      if (!res.ok) {
        const txt = await res.text().catch(() => "")
        throw new Error(txt || "Registration failed")
      }
      await login({ email, password })
    },
    [login]
  )

  const logout = React.useCallback(async () => {
    setToken(null)
    setStoredToken(null)
    setUser(null)
    // keep stored avatar so the old one can still show if future profiles have none
  }, [])

  React.useEffect(() => {
    (async () => {
      try { if (token) await refreshMe() } finally { setBootstrapped(true) }
    })()
  }, [token, refreshMe])

  const value: AuthContextType = { user, token, login, register, logout, refreshMe }
  if (!bootstrapped) return null
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = React.useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>")
  return ctx
}

export function isUserLoggedIn() {
  return !!getStoredToken()
}
