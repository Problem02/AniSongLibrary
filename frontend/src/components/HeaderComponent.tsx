import React from "react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Music2 } from "lucide-react"

/**
 * Header
 *
 * Minimal, reusable site header for AniSongLibrary.
 * - Left: brand (clickable, routes to "/").
 * - Right: Login button (routes to `/login` by default).
 *
 * Swap routes or wire callbacks via props as your app evolves.
 */

export type HeaderProps = {
  /** Path for the brand/home link. */
  homePath?: string
  /** Path for the login button. */
  signInPath?: string
  /** Optional: render a separator between nav items (kept for parity with design language). */
  showSeparator?: boolean
  /** Optional: right-aligned slot (e.g., user avatar when authenticated). */
  rightSlot?: React.ReactNode
}

export function LogoMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <div className={`rounded-xl bg-indigo-600 text-white grid place-items-center shadow ${className}`} aria-hidden>
      <Music2 className="h-4 w-4" />
    </div>
  )
}

export default function Header({
  homePath = "/",
  signInPath = "/login",
  showSeparator = false,
  rightSlot,
}: HeaderProps) {
  return (
    <header className="w-full border-b bg-background/60 backdrop-blur supports-[backdrop-filter]:bg-background/40">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4 sm:h-16 sm:px-6 md:px-8">
        {/* Brand */}
        <Link
          to={homePath}
          className="group inline-flex items-center gap-2 outline-none"
          aria-label="Go to AniSongLibrary home"
          data-testid="brand-link"
        >
          <LogoMark />
          <span className="font-semibold tracking-tight group-hover:underline">
            AniSongLibrary
          </span>
        </Link>

        {/* Right side */}
        <div className="flex items-center gap-3">
          {showSeparator && <Separator orientation="vertical" className="h-6" />}
          {rightSlot ? (
            rightSlot
          ) : (
            <Button asChild size="sm" data-testid="login-button">
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
