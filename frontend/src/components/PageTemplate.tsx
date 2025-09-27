import React from "react"

/**
 * PageTemplate — drop-in placeholder page for routing previews
 *
 * Keep this super light so it compiles everywhere. No external UI deps.
 * Use it in each page file while you wire real content.
 *
 * Example:
 * export default function LoginPage() {
 *   return <PageTemplate title="Login" description="Sign in to AniSongLibrary" />
 * }
 */

export type PageTemplateProps = {
  /** Big page title */
  title: string
  /** Optional subtitle/description */
  description?: string
  /** Optional actions (e.g., buttons) shown on the right */
  actions?: React.ReactNode
  /** Optional slot for content (center panel) */
  children?: React.ReactNode
  /** Optional test id for e2e */
  "data-testid"?: string
}

export function PageTemplate({ title, description, actions, children, ...rest }: PageTemplateProps) {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 md:px-8" {...rest}>
      {/* Header row */}
      <div className="flex flex-col gap-2 py-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          {description ? (
            <p className="text-sm text-muted-foreground">{description}</p>
          ) : null}
        </div>
        {actions ? <div className="flex items-center gap-2">{actions}</div> : null}
      </div>

      {/* Content area */}
      <div className="rounded-xl border bg-background p-6">
        {children ? (
          children
        ) : (
          <EmptyState title="Nothing here yet" subtitle="This page is wired up correctly. Add content when ready." />
        )}
      </div>
    </div>
  )
}

export function EmptyState({ title, subtitle, icon }: { title: string; subtitle?: string; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-12 text-center">
      <div className="text-4xl" aria-hidden>
        {icon ?? "🎵"}
      </div>
      <div className="text-base font-medium">{title}</div>
      {subtitle ? <div className="text-sm text-muted-foreground">{subtitle}</div> : null}
    </div>
  )
}

// Convenience: set document.title when mounted
export function usePageTitle(title: string) {
  React.useEffect(() => {
    const prev = document.title
    document.title = title ? `${title} • AniSongLibrary` : "AniSongLibrary"
    return () => {
      document.title = prev
    }
  }, [title])
}

// Default export for easy imports
export default PageTemplate
