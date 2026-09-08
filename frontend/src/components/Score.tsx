import { cn } from "@/lib/utils"

function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-muted-foreground"
  if (score >= 70) return "text-emerald-600"
  if (score >= 50) return "text-amber-600"
  if (score >= 30) return "text-orange-600"
  return "text-red-600"
}

function scoreLabel(score: number | null | undefined): {
  text: string
  color: string
  bg: string
} {
  if (score == null)
    return { text: "Sin datos", color: "text-muted-foreground", bg: "bg-muted" }
  if (score >= 70)
    return { text: "Alto", color: "text-emerald-700", bg: "bg-emerald-100" }
  if (score >= 50)
    return { text: "Medio", color: "text-amber-700", bg: "bg-amber-100" }
  if (score >= 30)
    return { text: "Medio-bajo", color: "text-orange-700", bg: "bg-orange-100" }
  return { text: "Bajo", color: "text-red-700", bg: "bg-red-100" }
}

export function ScoreCircle({
  score,
  size = 72,
}: {
  score: number | null | undefined
  size?: number
}) {
  const pct = score == null ? 0 : Math.max(0, Math.min(100, score))
  const r = (size - 10) / 2
  const c = 2 * Math.PI * r
  const offset = c - (pct / 100) * c

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth="6"
          className="stroke-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          className={cn("transition-all duration-500", scoreColor(score))}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={cn("text-lg font-bold leading-none", scoreColor(score))}>
          {score == null ? "—" : Math.round(score)}
        </span>
        <span className="text-[10px] text-muted-foreground">/100</span>
      </div>
    </div>
  )
}

export function ScoreBadge({ score }: { score: number | null | undefined }) {
  const label = scoreLabel(score)
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        label.color,
        label.bg,
      )}
    >
      {score == null ? "Sin datos" : `${Math.round(score)} · ${label.text}`}
    </span>
  )
}