import React from "react"
import { useNavigate, Link } from "react-router-dom"
import { useAuth } from "@/services/auth"

function cx(...cls: Array<string | false | undefined | null>) {
  return cls.filter(Boolean).join(" ")
}

// =====================
// Login Page
// =====================
export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()

  const [email, setEmail] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [submitting, setSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!email.includes("@")) return setError("Please enter a valid email address.")
    if (password.length < 6) return setError("Password must be at least 6 characters.")

    try {
      setSubmitting(true)
      await login({ email, password })
      navigate("/", { replace: true })
    } catch (err: any) {
      setError(typeof err?.message === "string" ? err.message : "Something went wrong.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="rounded-2xl shadow-xl bg-[#1a1023]/90 ring-1 ring-white/5 backdrop-blur p-6">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-3xl font-semibold tracking-tight text-white">Sign in</h1>
          <p className="mt-2 text-sm text-violet-200">Welcome back to AniSongLibrary</p>
        </div>

        <div className="rounded-2xl shadow-xl bg-[#1a1023]/90 ring-1 ring-white/5 backdrop-blur p-6">
          <form onSubmit={onSubmit} className="space-y-4">
            {error && (
              <div className="text-sm text-rose-300 bg-rose-900/30 border border-rose-900/50 p-2 rounded">{error}</div>
            )}

            <label className="block text-sm">
              <span className="text-violet-200">Email</span>
              <input
                type="email"
                autoComplete="email"
                className="mt-1 w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-white placeholder-violet-300/60 focus:outline-none focus:ring-2 focus:ring-violet-500"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </label>

            <label className="block text-sm">
              <span className="text-violet-200">Password</span>
              <input
                type="password"
                autoComplete="current-password"
                className="mt-1 w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-white placeholder-violet-300/60 focus:outline-none focus:ring-2 focus:ring-violet-500"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </label>

            <button
              type="submit"
              disabled={submitting}
              className={cx(
                "w-full rounded-xl py-2.5 text-sm font-medium transition",
                submitting ? "bg-violet-700/60 text-violet-100" : "bg-violet-600 hover:bg-violet-500 text-white"
              )}
            >
              {submitting ? "Signing in…" : "Sign in"}
            </button>

            <p className="text-center text-xs text-violet-300">
              New here?{' '}
              <Link to="/register" className="underline hover:no-underline">Create an account</Link>
            </p>
          </form>
        </div>
      </div>
    </main>
  )
}

// =====================
// Register Page
// =====================
export function RegisterPage() {
  const navigate = useNavigate()
  const { register, login } = useAuth()

  const [email, setEmail] = React.useState("")
  const [password, setPassword] = React.useState("")
  const [displayName, setDisplayName] = React.useState("")
  const [submitting, setSubmitting] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!email.includes("@")) return setError("Please enter a valid email address.")
    if (password.length < 6) return setError("Password must be at least 6 characters.")

    try {
      setSubmitting(true)
      await register({ email, password, display_name: displayName || undefined })
      await login({ email, password }) // auto sign-in after registration
      navigate("/", { replace: true })
    } catch (err: any) {
      setError(typeof err?.message === "string" ? err.message : "Something went wrong.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="rounded-2xl shadow-xl bg-[#1a1023]/90 ring-1 ring-white/5 backdrop-blur p-6">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <h1 className="text-3xl font-semibold tracking-tight text-white">Create account</h1>
          <p className="mt-2 text-sm text-violet-200">Join AniSongLibrary</p>
        </div>

        <div className="rounded-2xl shadow-xl bg-[#1a1023]/90 ring-1 ring-white/5 backdrop-blur p-6">
          <form onSubmit={onSubmit} className="space-y-4">
            {error && (
              <div className="text-sm text-rose-300 bg-rose-900/30 border border-rose-900/50 p-2 rounded">{error}</div>
            )}

            <label className="block text-sm">
              <span className="text-violet-200">Username</span>
              <input
                type="text"
                className="mt-1 w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-white placeholder-violet-300/60 focus:outline-none focus:ring-2 focus:ring-violet-500"
                placeholder="username"
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
              />
            </label>

            <label className="block text-sm">
              <span className="text-violet-200">Email</span>
              <input
                type="email"
                autoComplete="email"
                className="mt-1 w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-white placeholder-violet-300/60 focus:outline-none focus:ring-2 focus:ring-violet-500"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </label>

            <label className="block text-sm">
              <span className="text-violet-200">Password</span>
              <input
                type="password"
                autoComplete="new-password"
                className="mt-1 w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-white placeholder-violet-300/60 focus:outline-none focus:ring-2 focus:ring-violet-500"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </label>

            <button
              type="submit"
              disabled={submitting}
              className={cx(
                "w-full rounded-xl py-2.5 text-sm font-medium transition",
                submitting ? "bg-violet-700/60 text-violet-100" : "bg-violet-600 hover:bg-violet-500 text-white"
              )}
            >
              {submitting ? "Creating account…" : "Create account"}
            </button>

            <p className="text-center text-xs text-violet-300">
              Already have an account?{' '}
              <Link to="/login" className="underline hover:no-underline">Sign in</Link>
            </p>
          </form>
        </div>
      </div>
    </main>
  )
}

// Optional: a simple protected route helper you can use in your router
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#12051a] text-violet-200">
        <div className="space-y-4 text-center">
          <p className="text-sm">You must sign in to access this page.</p>
          <Link
            to="/login"
            className="inline-flex items-center justify-center rounded-lg px-4 py-2 bg-violet-600 text-white hover:bg-violet-500"
          >
            Go to sign in
          </Link>
        </div>
      </div>
    )}
  return <>{children}</>
}
