import React, { useEffect, createContext, useCallback, useContext, useMemo, useRef, useState } from "react"
import { Button } from "@/ui/button"
import { Slider } from "@/ui/slider"
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Music2, ChevronUp } from "lucide-react"
import SongInfoPanel from "@/components/SongInfoPanel"

export type Track = {
  id: string
  title: string
  artist: string
  anime?: string
  audioUrl?: string
}

type PlayerState = {
  queue: Track[]
  index: number
  isPlaying: boolean
  volume: number
  progress: number
  duration: number
}

type PlayerApi = PlayerState & {
  current?: Track
  setQueue: (tracks: Track[], startIndex?: number) => void
  play: () => void
  pause: () => void
  toggle: () => void
  next: () => void
  prev: () => void
  seek: (seconds: number) => void
  setVolume: (v: number) => void
}

const PlayerCtx = createContext<PlayerApi | null>(null)
export function usePlayer() {
  const ctx = useContext(PlayerCtx)
  if (!ctx) throw new Error("usePlayer must be used within <PlayerProvider>")
  return ctx
}

export function PlayerProvider({ children }: { children: React.ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [state, setState] = useState<PlayerState>({
    queue: [
      { id: "demo-1", title: "again", artist: "YUI", anime: "Fullmetal Alchemist: Brotherhood", audioUrl: "" },
      { id: "demo-2", title: "unravel", artist: "TK from Ling tosite sigure", anime: "Tokyo Ghoul", audioUrl: "" },
    ],
    index: 0,
    isPlaying: false,
    volume: 0.8,
    progress: 0,
    duration: 0,
  })

  const current = state.queue[state.index]

  const setQueue = useCallback((tracks: Track[], startIndex = 0) => {
    setState((s) => ({
      ...s,
      queue: tracks,
      index: Math.max(0, Math.min(startIndex, tracks.length - 1)),
      progress: 0,
    }))
  }, [])

  const play = useCallback(() => {
    setState((s) => ({ ...s, isPlaying: true }))
    audioRef.current?.play().catch(() => void 0)
  }, [])

  const pause = useCallback(() => {
    setState((s) => ({ ...s, isPlaying: false }))
    audioRef.current?.pause()
  }, [])

  const toggle = useCallback(() => {
    setState((s) => ({ ...s, isPlaying: !s.isPlaying }))
    const a = audioRef.current
    if (!a) return
    if (a.paused) a.play().catch(() => void 0)
    else a.pause()
  }, [])

  const next = useCallback(() => {
    setState((s) => {
      if (s.queue.length === 0) return s
      return { ...s, index: (s.index + 1) % s.queue.length, progress: 0 }
    })
  }, [])

  const prev = useCallback(() => {
    setState((s) => {
      if (s.queue.length === 0) return s
      return { ...s, index: (s.index - 1 + s.queue.length) % s.queue.length, progress: 0 }
    })
  }, [])

  const seek = useCallback((seconds: number) => {
    const a = audioRef.current
    if (!a) return
    a.currentTime = Math.max(0, Math.min(seconds, a.duration || seconds))
  }, [])

  const setVolume = useCallback((v: number) => {
    const vol = Math.max(0, Math.min(v, 1))
    setState((s) => ({ ...s, volume: vol }))
    if (audioRef.current) audioRef.current.volume = vol
  }, [])

  useEffect(() => {
    const a = audioRef.current
    if (!a) return
    if (state.isPlaying) {
      a.play().catch(() => void 0)
    }
  }, [state.index, state.isPlaying])

  const value: PlayerApi = useMemo(
    () => ({
      ...state,
      current,
      setQueue,
      play,
      pause,
      toggle,
      next,
      prev,
      seek,
      setVolume,
    }),
    [state, current, setQueue, play, pause, toggle, next, prev, seek, setVolume]
  )

  return (
    <PlayerCtx.Provider value={value}>
      {children}
      <audio
        ref={audioRef}
        src={current?.audioUrl || undefined}
        onTimeUpdate={(e) => setState((s) => ({ ...s, progress: (e.target as HTMLAudioElement).currentTime }))}
        onLoadedMetadata={(e) => setState((s) => ({ ...s, duration: (e.target as HTMLAudioElement).duration }))}
        onEnded={next}
        autoPlay={state.isPlaying}
      />
      <PlayerBar />
    </PlayerCtx.Provider>
  )
}

// --- UI ---
export function PlayerBar() {
  const { current, isPlaying, toggle, next, prev, progress, duration, volume, setVolume, seek } = usePlayer()
  const [panelOpen, setPanelOpen] = useState(true)

  React.useEffect(() => {
    // close panel on track change
    setPanelOpen(false)
  }, [current?.id])

  const fmt = (t: number) => {
    if (!isFinite(t)) return "0:00"
    const m = Math.floor(t / 60)
    const s = Math.floor(t % 60)
    return `${m}:${s.toString().padStart(2, "0")}`
  }

  return (
    <>
  <footer
  role="contentinfo"
  className="sticky bottom-0 z-[1000] w-screen mx-[calc(50%-50vw)] border-t
             bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60 p-0 m-0"
  >
  {/* Full-bleed bar; no max-width container */}
  <div className="flex w-full items-center gap-4 py-2 px-4 sm:px-5">
    {/* Left: song meta (click to toggle panel) */}
    <button
      className="flex min-w-0 flex-1 items-center gap-2 text-left"
      onClick={() => setPanelOpen((v) => !v)}
      aria-haspopup="dialog"
      aria-expanded={panelOpen}
      title={panelOpen ? "Hide song details" : "Show song details"}
    >
      {/* Up arrow that animates toward the panel when opening */}
      <span
        className={[
          "inline-flex items-center justify-center",
          "transition-transform transition-opacity duration-300",
          panelOpen ? "-translate-y-1 opacity-0" : "translate-y-0 opacity-100",
        ].join(" ")}
        aria-hidden
      >
        <ChevronUp className="h-4 w-4 text-muted-foreground" />
      </span>

      {/* Small note glyph (kept) */}
      <span className="hidden sm:inline text-muted-foreground" aria-hidden>
        <Music2 className="h-5 w-5" />
      </span>

      <span className="min-w-0">
        <span className="block truncate text-sm font-medium">
          {current?.title ?? "No track selected"}
        </span>
        <span className="block truncate text-xs text-muted-foreground">
          {current ? `${current.artist}${current.anime ? " • " + current.anime : ""}` : "Pick a song to start"}
        </span>
      </span>
    </button>


    {/* Center: transport + progress */}
    <div className="flex flex-1 flex-col items-center gap-2">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={prev} aria-label="Previous">
          <SkipBack className="h-5 w-5" />
        </Button>
        <Button size="icon" onClick={toggle} aria-label={isPlaying ? "Pause" : "Play"}>
          {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
        </Button>
        <Button variant="ghost" size="icon" onClick={next} aria-label="Next">
          <SkipForward className="h-5 w-5" />
        </Button>
      </div>
      <div className="flex w-full max-w-xl items-center gap-2">
        <span className="w-10 text-right text-[10px] tabular-nums text-muted-foreground">{fmt(progress)}</span>
        <Slider
          value={[duration ? Math.min(progress, duration) : 0]}
          max={duration || 0}
          step={1}
          onValueChange={(v) => seek(v[0] ?? 0)}
          aria-label="Seek"
        />
        <span className="w-10 text-[10px] tabular-nums text-muted-foreground">{fmt(duration)}</span>
      </div>
    </div>

    {/* Right: volume */}
    <div className="flex flex-1 items-center justify-end gap-2">
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setVolume(volume > 0 ? 0 : 0.8)}
        aria-label={volume > 0 ? "Mute" : "Unmute"}
        title={volume > 0 ? "Mute" : "Unmute"}
      >
        {volume > 0 ? <Volume2 className="h-5 w-5" /> : <VolumeX className="h-5 w-5" />}
      </Button>
      <div className="w-32">
        <Slider
          value={[Math.round(volume * 100)]}
          max={100}
          step={1}
          onValueChange={(v) => setVolume((v[0] ?? 0) / 100)}
          aria-label="Volume"
        />
      </div>
    </div>
  </div>
</footer>


      {/* Slide-up panel (portal) */}
      <SongInfoPanel open={panelOpen} onClose={() => setPanelOpen(false)} track={current} />
    </>
  )
}
