import React from "react"
import ReactDOM from "react-dom"
import { Button } from "@/ui/button"
import { X } from "lucide-react"

type CreditRole = "artist" | "composer" | "arranger"

export type SongDetail = {
  id: string
  name: string
  audio?: string
  credits: { role: CreditRole; people: { id: string; primary_name: string } }[]
  anime_links: {
    id: string
    use_type: "OP" | "ED" | "IN"
    sequence?: number | null
    is_dub: boolean
    is_rebroadcast: boolean
    anime: { id: string; title_en?: string | null; title_jp?: string | null; title_romaji?: string | null }
  }[]
}

export type BasicTrack = {
  id: string
  title: string
  artist: string
  anime?: string
}

const UUIDish = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
const SONGS_API_BASE = import.meta.env.VITE_CATALOG_API_BASE ?? "http://localhost:8001"

type Props = {
  open: boolean
  onClose: () => void
  track?: BasicTrack
}

export default function SongInfoPanel({ open, onClose, track }: Props) {
  // Portal mount
  const [mounted, setMounted] = React.useState(false)
  React.useEffect(() => setMounted(true), [])

  // Live header bottom (in viewport px). Panel's top will be pinned here.
  const [headerBottom, setHeaderBottom] = React.useState<number>(measureHeaderBottom())

  React.useEffect(() => {
    const header = document.querySelector("header") as HTMLElement | null
    if (!header) return

    // Update fn reads the current header bottom relative to viewport
    let raf = 0
    const update = () => {
      cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => setHeaderBottom(measureHeaderBottom()))
    }

    // ResizeObserver for header height changes (responsive)
    const ro = new ResizeObserver(update)
    ro.observe(header)

    // Scroll + resize listeners (header may be sticky/fixed)
    window.addEventListener("scroll", update, { passive: true })
    window.addEventListener("resize", update)

    // Initial couple of ticks to catch CSS transitions
    update()
    const t1 = setTimeout(update, 50)
    const t2 = setTimeout(update, 200)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      cancelAnimationFrame(raf)
      ro.disconnect()
      window.removeEventListener("scroll", update)
      window.removeEventListener("resize", update)
    }
  }, [])

  // Load details only when opening (and only if id looks like a UUID)
  const [loading, setLoading] = React.useState(false)
  const [detail, setDetail] = React.useState<SongDetail | null>(null)
  const [error, setError] = React.useState<string | null>(null)

  const load = React.useCallback(async () => {
    if (!track?.id || !UUIDish.test(track.id)) {
      setDetail(null)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${SONGS_API_BASE}/songs/${track.id}`)
      if (!res.ok) throw new Error(`Failed to load song (${res.status})`)
      const json = (await res.json()) as SongDetail
      setDetail(json)
    } catch (e: any) {
      setError(e?.message ?? "Failed to load song")
      setDetail(null)
    } finally {
      setLoading(false)
    }
  }, [track?.id])

  React.useEffect(() => {
    if (open) load()
  }, [open, load])

  // Close on ESC only (persistent, no backdrop)
  React.useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  if (!mounted) return null

  // Panel: fixed left, bottom:0, top: headerBottom. Lower z-index than header/footer.
  const panelBase =
    "fixed left-0 z-[60] w-full md:w-[480px] border-r bg-background/95 backdrop-blur shadow-xl " +
    "transition-transform duration-300 will-change-transform overflow-auto"

  return ReactDOM.createPortal(
    <section
      role="dialog"
      aria-modal="false"
      aria-label="Song details"
      style={{ top: headerBottom, bottom: 0 }}
      className={`${panelBase} ${open ? "translate-y-0" : "translate-y-full"}`}
      onClick={(e) => e.stopPropagation()} // persistent; outside clicks do nothing
    >
      {/* Sticky panel header */}
      <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b bg-background/95 p-4 backdrop-blur">
        <div className="min-w-0">
          <div className="truncate text-base font-semibold">{detail?.name ?? track?.title ?? "Song"}</div>
          <div className="truncate text-sm text-muted-foreground">
            {detail
              ? detail.credits
                  .filter((c) => c.role === "artist")
                  .map((c) => c.people.primary_name)
                  .join(", ") || track?.artist
              : track?.artist}
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close">
          <X className="h-5 w-5" />
        </Button>
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {/* Appearances */}
        <div className="rounded-xl border bg-card p-3">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Anime Appearances
          </div>
          {loading ? (
            <div className="text-sm text-muted-foreground">Loading…</div>
          ) : error ? (
            <div className="text-sm text-rose-500">{error}</div>
          ) : detail?.anime_links?.length ? (
            <ul className="space-y-1 text-sm">
              {detail.anime_links.map((ln) => {
                const seq = ln.sequence != null ? `${ln.use_type}${ln.sequence}` : ln.use_type
                const at = ln.anime.title_en || ln.anime.title_romaji || ln.anime.title_jp || "Unknown Anime"
                return (
                  <li key={ln.id} className="flex items-center justify-between gap-3">
                    <span className="truncate">{at}</span>
                    <span className="text-xs text-muted-foreground">{seq}</span>
                  </li>
                )
              })}
            </ul>
          ) : (
            <div className="text-sm text-muted-foreground">
              {track?.anime ? track.anime : "No appearances found."}
            </div>
          )}
        </div>

        {/* Credits */}
        <div className="rounded-xl border bg-card p-3">
          <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Credits</div>
          {loading ? (
            <div className="text-sm text-muted-foreground">Loading…</div>
          ) : error ? (
            <div className="text-sm text-rose-500">{error}</div>
          ) : detail?.credits?.length ? (
            <div className="space-y-2 text-sm">
              {(["artist", "composer", "arranger"] as const).map((role) => {
                const list = detail.credits.filter((c) => c.role === role)
                if (!list.length) return null
                return (
                  <div key={role} className="flex items-start gap-2">
                    <span className="w-20 shrink-0 text-xs uppercase text-muted-foreground">{role}</span>
                    <span className="truncate">{list.map((c) => c.people.primary_name).join(", ")}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">No credits available.</div>
          )}
        </div>
      </div>
    </section>,
    document.body
  )
}

function measureHeaderBottom(): number {
  const h = document.querySelector("header") as HTMLElement | null
  if (!h) return 0
  const r = h.getBoundingClientRect()
  // Use the current bottom edge in the viewport; ensures the panel never overlaps the header
  return Math.max(0, Math.floor(r.bottom))
}
