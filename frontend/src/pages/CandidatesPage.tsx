import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import {
  Loader2, Search as SearchIcon, AlertTriangle, ChevronRight,
  Building2, MapPin, Users, Sparkles, ArrowUpDown,
} from "lucide-react"
import { api } from "@/lib/api"
import type { CandidateResult, Company, ScoreDistribution } from "@/lib/types"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { CompanyCard } from "@/components/CompanyCard"
import { CompanyCardSkeleton } from "@/components/CompanyCardSkeleton"
import { QUICK_SCORE_RANGES, SCORE_RANGES, rangeBounds } from "@/components/FiltersBar"
import { Trophy } from "lucide-react"
import { cn } from "@/lib/utils"

const SECTORS = [
  "transportes",
  "construcciones",
  "alimentacion",
  "industrial",
]

function fitBadge(fit: "ALTO" | "MEDIO" | "BAJO") {
  if (fit === "ALTO")
    return <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400">Alineación Alta</Badge>
  if (fit === "MEDIO")
    return <Badge className="bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400">Alineación Media</Badge>
  return <Badge className="bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400">Alineación Baja</Badge>
}

function CandidateCard({ item }: { item: CandidateResult }) {
  const navigate = useNavigate()
  const c = item.company

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      role="button"
      tabIndex={0}
      aria-label={`Ver ficha de ${c.name}`}
      onClick={() => navigate(`/empresa/${c.slug}`)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          navigate(`/empresa/${c.slug}`)
        }
      }}
    >
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <div className="flex flex-col items-center">
            <div
              className={cn(
                "flex size-14 items-center justify-center rounded-full text-lg font-bold",
                item.fit_score >= 70
                  ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400"
                  : item.fit_score >= 40
                    ? "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-400"
                    : "bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-400",
              )}
            >
              {item.fit_score}
            </div>
            <span className="mt-1 text-[10px] text-muted-foreground">/100</span>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="truncate font-semibold">{c.name}</h3>
              {fitBadge(item.fit_label)}
              {item.succession_signal && (
                <Badge variant="outline" className="border-orange-300 text-orange-600">
                  Relevo generacional
                </Badge>
              )}
            </div>

            <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Building2 className="size-3" />
                {c.cif}
              </span>
              {(c.province || c.city) && (
                <span className="flex items-center gap-1">
                  <MapPin className="size-3" />
                  {c.city ? `${c.city}, ` : ""}{c.province}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Users className="size-3" />
                {c.administrators?.length ?? 0} Administradores
              </span>
              <span className="flex items-center gap-1">
                <ArrowUpDown className="size-3" />
                {c.borme_acts_count} Actos en BORME
              </span>
            </div>

            {item.rationale && (
              <p className="mt-2 text-sm text-muted-foreground">
                {item.rationale}
              </p>
            )}

            <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
              <Sparkles className="size-3" />
              Indicador BORME: {item.borme_score}
              <ChevronRight className="size-3" />
              <span className="font-medium text-foreground">Fit: {item.fit_score}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function CandidatesPage() {
  // Ranking completo de la BD, cargado al entrar (ordenado por score DESC)
  const [rank, setRank] = useState<Company[]>([])
  const [rankLoading, setRankLoading] = useState(true)
  const [activeChip, setActiveChip] = useState<string | null>(null)
  const [results, setResults] = useState<CandidateResult[]>([])
  const [warnings, setWarnings] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [totalCompanies, setTotalCompanies] = useState(0)
  const [llmOk, setLlmOk] = useState<boolean | null>(null)
  const [selectedSectors, setSelectedSectors] = useState<string[]>(SECTORS)
  const [maxAnalyze, setMaxAnalyze] = useState(10)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    api.llmHealth({ signal: ctrl.signal }).then((r) => setLlmOk(r.llm.configured)).catch(() => setLlmOk(false))
    return () => ctrl.abort()
  }, [])

  useEffect(() => {
    const ctrl = new AbortController()
    api.getCompanies({ limit: 500 }, { signal: ctrl.signal })
      .then((res) => setRank(res.companies))
      .catch(() => setRank([]))
      .finally(() => setRankLoading(false))
    return () => ctrl.abort()
  }, [])

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  async function handleSearch() {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    setLoading(true)
    setWarnings([])
    try {
      const res = await api.searchCandidates({
        sectors: selectedSectors.length > 0 ? selectedSectors : undefined,
        max_analyze: maxAnalyze,
      }, { signal: ctrl.signal })
      setResults(res.results)
      setTotalCompanies(res.total_companies)
      setWarnings(res.warnings)
      setSearched(true)
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      setWarnings([err instanceof Error ? err.message : "Error desconocido"])
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  function toggleSector(s: string) {
    setSelectedSectors((prev) =>
      prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s],
    )
  }

  // Distribución y filtro del ranking en cliente (la lista ya está cargada)
  const dist: ScoreDistribution | null = rank
    ? {
        alto: rank.filter((c) => (c.score ?? 0) >= 60).length,
        medio: rank.filter((c) => (c.score ?? 0) >= 40 && (c.score ?? 0) < 60).length,
        bajo: rank.filter((c) => (c.score ?? 0) < 40).length,
      }
    : null

  const bounds = rangeBounds(SCORE_RANGES, activeChip ?? "all")
  const visibleRank =
    bounds.min !== undefined || bounds.max !== undefined
      ? rank.filter((c) => {
          const s = c.score ?? 0
          if (bounds.min !== undefined && s < bounds.min) return false
          if (bounds.max !== undefined && s > bounds.max) return false
          return true
        })
      : rank

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">Candidatas</h1>
        <p className="text-muted-foreground">
          Todas las empresas encontradas, ranqueadas de mejor a peor. Usa el Agente para un análisis profundo de las mejores.
        </p>
      </header>

      {rankLoading ? (
        <div className="grid grid-cols-1 gap-3">
          {[...Array(6)].map((_, i) => (
            <CompanyCardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Ranking de adquisición
            </span>
            {QUICK_SCORE_RANGES.map((r) => {
              const active = activeChip === r.value
              const count = dist ? dist[r.value as keyof ScoreDistribution] : undefined
              const tone =
                r.tone === "red"
                  ? { idle: "bg-red-400 text-black hover:bg-red-300", active: "bg-red-500 text-black ring-1 ring-red-600" }
                  : r.tone === "orange"
                    ? { idle: "bg-orange-400 text-black hover:bg-orange-300", active: "bg-orange-500 text-black ring-1 ring-orange-600" }
                    : { idle: "bg-green-400 text-black hover:bg-green-300", active: "bg-green-500 text-black ring-1 ring-green-600" }
              return (
                <button
                  key={r.value}
                  onClick={() => setActiveChip(active ? null : r.value)}
                  aria-pressed={active}
                  className={`rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
                    active ? `border-transparent ${tone.active}` : `border-transparent ${tone.idle}`
                  }`}
                >
                  {r.label}
                  {count !== undefined && (
                    <span className="ml-0.5 rounded-full bg-white px-1.5 text-[10px] font-bold text-black">{count}</span>
                  )}
                </button>
              )
            })}
            <span className="text-xs text-muted-foreground">
              {visibleRank.length} de {rank.length} empresas · score ↓
            </span>
          </div>

          {visibleRank.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
              <Trophy className="mb-4 size-12 opacity-30" />
              <p className="text-lg font-medium">Aún no hay empresas en el ranking</p>
              <p className="mt-1 text-sm">Haz una búsqueda para empezar a poblarlo.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {visibleRank.map((c) => (
                <CompanyCard key={c.cif ?? c.slug} company={c} />
              ))}
            </div>
          )}
        </>
      )}

      <div className="flex items-center gap-2 pt-2">
        <Sparkles className="size-4 text-muted-foreground" />
        <h2 className="text-lg font-semibold">Análisis del Agente</h2>
      </div>

      {llmOk === false && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          <AlertTriangle className="size-4" />
          El motor de análisis (Ollama) no está disponible. Por favor, verifique que el servicio esté activo.
        </div>
      )}

      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-muted-foreground">
                Sectores
              </label>
              <div className="flex gap-1.5">
                {SECTORS.map((s) => (
                  <Button
                    key={s}
                    variant={selectedSectors.includes(s) ? "default" : "outline"}
                    size="sm"
                    onClick={() => toggleSector(s)}
                    className="h-7 text-xs"
                  >
                    {s}
                  </Button>
                ))}
              </div>
            </div>
            <div>
              <label htmlFor="max-analyze" className="mb-1 block text-xs font-medium text-muted-foreground">
                Muestra de Análisis
              </label>
              <select
                id="max-analyze"
                onChange={(e) => setMaxAnalyze(Number(e.target.value))}
                className="h-7 rounded-md border bg-background px-2 text-xs"
              >
                {[5, 10, 20, 50].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
            <Button
              onClick={handleSearch}
              disabled={loading || llmOk === false}
            >
              {loading ? <Loader2 className="animate-spin" /> : <SearchIcon />}
              Iniciar Análisis de Candidatos
            </Button>
          </div>
        </CardContent>
      </Card>

      {warnings.length > 0 && (
        <div className="space-y-1">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-center gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
              <AlertTriangle className="size-4 shrink-0" />
              {w}
            </div>
          ))}
        </div>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
          <Loader2 className="size-8 animate-spin" />
          <p className="text-sm">El Agente está evaluando la viabilidad de las empresas...</p>
          <p className="text-xs">Este proceso de análisis cualitativo puede demorar unos minutos.</p>
          <Button variant="outline" size="sm" onClick={() => { abortRef.current?.abort(); setLoading(false); }}>
            Cancelar
          </Button>
        </div>
      ) : searched ? (
        <>
          <p className="text-sm text-muted-foreground">
            {results.length === 0
              ? "No se encontraron candidatas."
              : `${results.length} candidata${results.length === 1 ? "" : "s"} de ${totalCompanies} empresa${totalCompanies === 1 ? "" : "s"} analizadas`}
          </p>
          <div className="space-y-3">
            {results.map((item) => (
              <CandidateCard key={item.company.cif} item={item} />
            ))}
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <Sparkles className="mb-4 size-12 opacity-30" />
          <p className="text-lg font-medium">Configuración de Análisis</p>
          <p className="mt-1 text-sm">
            Defina los sectores objetivo para que el Agente identifique y puntúe las mejores oportunidades.
          </p>
        </div>
      )}
    </div>
  )
}
