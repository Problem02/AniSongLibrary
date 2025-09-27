import React from "react"
import { Link, useNavigate } from "react-router-dom"

// If your UI components live at "@/components/ui/*", adjust these paths.
import { Button } from "@/ui/button"
import { Separator } from "@/ui/separator"
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/ui/dropdown-menu"
import { Avatar, AvatarImage, AvatarFallback } from "@/ui/avatar"

import { Music2 } from "lucide-react"
import { useAuth, DEFAULT_AVATAR_URL, getStoredAvatar } from "@/services/auth"

export type HeaderProps = {
  homePath?: string
  signInPath?: string
  showSeparator?: boolean
  rightSlot?: React.ReactNode
}

export function LogoMark({ className = "h-10 w-10" }: { className?: string }) {
  return (
    <div
      className={`rounded-2xl bg-indigo-600 text-white grid place-items-center shadow ${className}`}
      aria-hidden
    >
      <Music2 className="h-5 w-5" />
    </div>
  )
}

function getInitials(nameOrEmail?: string) {
  if (!nameOrEmail) return "U"
  const s = nameOrEmail.trim()
  if (!s.includes(" ")) {
    const token = s.includes("@") ? s.split("@")[0] : s
    return token.slice(0, 2).toUpperCase()
  }
  const [a, b] = s.split(/\s+/, 2)
  return (a[0] + (b?.[0] ?? "")).toUpperCase()
}

export default function Header({
  homePath = "/",
  signInPath = "/login",
  showSeparator = false,
  rightSlot,
}: HeaderProps) {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const displayName =
    (user as any)?.display_name ||
    (user as any)?.name ||
    (user as any)?.username ||
    (user as any)?.email ||
    ""

  const backendAvatar =
    (user as any)?.avatar_url ||
    (user as any)?.picture ||
    (user as any)?.image ||
    ""

  // Prefer backend -> stored(previous) -> default
  const storedAvatar = getStoredAvatar()
  const initialAvatarSrc =
    (backendAvatar && backendAvatar.trim() !== "" ? backendAvatar : null) ||
    storedAvatar ||
    DEFAULT_AVATAR_URL

  const [imgOk, setImgOk] = React.useState(true)
  React.useEffect(() => {
    setImgOk(true)
  }, [initialAvatarSrc])

  const onLogout = async () => {
    try {
      await logout()
    } finally {
      navigate("/login", { replace: true })
    }
  }

  return (
    <header className="w-full border-b bg-background/60 backdrop-blur supports-[backdrop-filter]:bg-background/40">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-5 px-5 sm:h-20 sm:px-8 md:px-10">
        {/* Brand */}
        <Link
          to={homePath}
          className="group inline-flex items-center gap-3 outline-none"
          aria-label="Go to AniSongLibrary home"
          data-testid="brand-link"
        >
          <LogoMark />
          <span className="text-lg sm:text-xl font-semibold tracking-tight hover:no-underline">
            AniSongLibrary
          </span>
        </Link>

        {/* Right side */}
        <div className="flex items-center gap-4">
          {showSeparator && <Separator orientation="vertical" className="h-7" />}

          {rightSlot ? (
            rightSlot
          ) : user ? (
            // Logged-in: bigger avatar + dropdown
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  className="inline-flex items-center gap-3 rounded-full focus:outline-none focus:ring-2 focus:ring-ring"
                  aria-label="Open account menu"
                >
                  <Avatar className="h-12 w-12">
                    {imgOk && initialAvatarSrc ? (
                      <AvatarImage
                        src={initialAvatarSrc}
                        alt={displayName || "Profile"}
                        onError={() => setImgOk(false)}
                      />
                    ) : (
                      <AvatarFallback className="text-base">
                        {getInitials(displayName)}
                      </AvatarFallback>
                    )}
                  </Avatar>
                </button>
              </DropdownMenuTrigger>

              <DropdownMenuContent align="end" className="w-52">
                <div className="px-3 py-2 text-sm text-muted-foreground truncate">
                  {displayName || "Signed in"}
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild className="text-sm">
                  <Link to="/account" aria-label="Profile">
                    Profile
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem className="text-sm" onClick={onLogout}>
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button asChild className="h-10 px-5 text-sm">
              <Link to={signInPath} aria-label="Sign in">
                Sign in
              </Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  )
}
