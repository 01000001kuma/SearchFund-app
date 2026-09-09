import { cn } from "@/lib/utils"

// Bandas alineadas con el algoritmo de score (backend/engines/score.py):
// 80-100 muy bueno, 60-79 bueno, 40-59 moderado, 20-39 bajo, 0-19 no recomendado
function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-muted-foreground"
  if (score >= 80) return "text-emerald-600"
  if (score >= 60) return "text-green-600"
  if (score >= 40) return "text-amber-600"
  if (score >= 20) return "text-orange-600"
  return "text-red-600"
}

function scoreLabel(score: number | null | undefined): {
  text: string
  color: string
  bg: string
} {
  if (score == null)
    return { text: "Sin datos", color: "text-muted-foreground", bg: "bg-muted" }
  if (score >= 80)
    return {
      text: "Muy bueno",
      color: "text-emerald-700 dark:text-emerald-400",
      bg: "bg-emerald-100 dark:bg-emerald-500/15",
    }
  if (score >= 60)
    return {
      text: "Bueno",
      color: "text-green-700 dark:text-green-400",
      bg: "bg-green-100 dark:bg-green-500/15",
    }
  if (score >= 40)
    return {
      text: "Moderado",
      color: "text-amber-700 dark:text-amber-400",
      bg: "bg-amber-100 dark:bg-amber-500/15",
    }
  if (score >= 20)
    return {
      text: "Bajo",
      color: "text-orange-700 dark:text-orange-400",
      bg: "bg-orange-100 dark:bg-orange-500/15",
    }
  return {
    text: "No recomendado",
    color: "text-red-700 dark:text-red-400",
    bg: "bg-red-100 dark:bg-red-500/15",
  }
}

export function ScoreCircle({
  score,
  size = 72,
}: {
  score: number | null | undefined
  size?: number
}) {
  const pct = score == null ? 0 : Math.max(0, Math.min(100, score))
  const strokeWidth = Math.max(5, Math.round(size / 18))
  const r = (size - strokeWidth - 6) / 2
  const c = 2 * Math.PI * r
  const offset = c - (pct / 100) * c

  return (
    <div
      className="relative inline-flex shrink-0 items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Puntuación ${score == null ? "sin datos" : Math.round(score)} de 100`}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          strokeWidth={strokeWidth}
          className="fill-background stroke-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          className={cn("transition-all duration-500", scoreColor(score))}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className={cn("font-bold leading-none tracking-tight", scoreColor(score))}
          style={{ fontSize: Math.round(size * 0.3) }}
        >
          {score == null ? "—" : Math.round(score)}
        </span>
        <span
          className="text-muted-foreground"
          style={{ fontSize: Math.max(9, Math.round(size * 0.075)), marginTop: Math.round(size * 0.02) }}
        >
          de 100
        </span>
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