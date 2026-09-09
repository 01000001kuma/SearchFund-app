import { useState, useEffect, useRef, useMemo, type FormEvent } from "react"
import { useSearchParams } from "react-router-dom"
import { Search, Loader2, Inbox, Trophy, Building2 } from "lucide-react"
import { api } from "@/lib/api"
import type { Company, ScoreDistribution } from "@/lib/types"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { CompanyCard } from "@/components/CompanyCard"
import { CompanyCardSkeleton } from "@/components/CompanyCardSkeleton"
import {
  FiltersBar,
  rangeBounds,
  SCORE_RANGES,
  EBITDA_RANGES,
  REVENUE_RANGES,
  QUICK_SCORE_RANGES,
  type Filters,
} from "@/components/FiltersBar"

// Sección CNAE (letra) → sector legible
const CNAE_SECTORS: Record<string, string> = {
  A: "Agroalimentario",
  B: "Industria extractiva",
  C: "Industria manufacturera",
  D: "Energía",
  E: "Agua y residuos",
  F: "Construcción",
  G: "Comercio",
  H: "Transporte y logística",
  I: "Hostelería",
  J: "Tecnología",
  K: "Financiero",
  L: "Inmobiliario",
  M: "Servicios B2B",
  N: "Servicios operativos",
  O: "Sector público",
  P: "Educación",
  Q: "Salud",
  R: "Cultura",
  S: "Otros servicios",
}

function sectorOf(c: Company): string | null {
  const section = c.cnae?.split("·")[0]?.trim()?.toUpperCase()
  return section ? (CNAE_SECTORS[section] ?? null) : null
}

export function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  // Estado inicial hidratado desde la URL (persistente al recargar y compartible)
  const [query, setQuery] = useState(() => searchParams.get("q") ?? "")
  const [filters, setFilters] = useState<Filters>(() => ({
    province: searchParams.get("provincia") ?? "all",
    scoreRange: searchParams.get("score") ?? "all",
    hasFinancial: searchParams.get("fin") ?? "all",
    ebitdaRange: searchParams.get("ebitda") ?? "all",
    revenueRange: searchParams.get("rev") ?? "all",
  }))
  const [results, setResults] = useState<Company[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)
  const [distribution, setDistribution] = useState<ScoreDistribution | null>(null)

  // Ranking completo de la BD (vista por defecto) + chips de banda y sector
  const [allRank, setAllRank] = useState<Company[]>([])
  const [allRankLoading, setAllRankLoading] = useState(true)
  const [activeChip, setActiveChip] = useState<string | null>(
    () => searchParams.get("rango"),
  )
  const [sectorFilter, setSectorFilter] = useState<string | null>(
    () => searchParams.get("sector"),
  )

  const abortRef = useRef<AbortController | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  async function loadDistribution() {
    try {
      const stats = await api.getStats()
      setDistribution(stats.score_distribution ?? null)
    } catch {
      // silencioso: los chips quedan sin conteo
    }
  }

  // Caché completo al montar: sectores + vista por defecto + chip de banda
  const mountedRef = useRef(false)
  useEffect(() => {
    if (mountedRef.current) return
    mountedRef.current = true
    void loadDistribution()
    api
      .getCompanies({ limit: 500 })
      .then((res) => setAllRank(res.companies))
      .catch(() => setAllRank([]))
      .finally(() => setAllRankLoading(false))
    const q = searchParams.get("q")
    if (q) void doSearch(q, filters)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function syncUrl(q: string, f: Filters, rango: string | null, sector: string | null) {
    const params = new URLSearchParams()
    if (rango && rango !== "all") params.set("rango", rango)
    if (sector) params.set("sector", sector)
    if (q) params.set("q", q)
    if (f.province !== "all") params.set("provincia", f.province)
    if (f.scoreRange !== "all") params.set("score", f.scoreRange)
    if (f.hasFinancial !== "all") params.set("fin", f.hasFinancial)
    if (f.ebitdaRange !== "all") params.set("ebitda", f.ebitdaRange)
    if (f.revenueRange !== "all") params.set("rev", f.revenueRange)
    setSearchParams(params, { replace: true })
  }

  function updateUrl(partial: { rango?: string | null; sector?: string | null }) {
    const params = new URLSearchParams(searchParams)
    const setOrDelete = (key: string, value?: string | null) => {
      if (value && value !== "all") params.set(key, value)
      else params.delete(key)
    }
    if (partial.rango !== undefined) setOrDelete("rango", partial.rango)
    if (partial.sector !== undefined) setOrDelete("sector", partial.sector)
    const q = searchParams.get("q")
    if (q) params.set("q", q)
    setSearchParams(params, { replace: true })
  }

  async function doSearch(q: string, f: Filters) {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    setLoading(true)
    setError(null)
    setWarning(null)
    syncUrl(q, f, activeChip, sectorFilter)
    const scoreBounds = rangeBounds(SCORE_RANGES, f.scoreRange)
    const ebitdaBounds = rangeBounds(EBITDA_RANGES, f.ebitdaRange)
    const revenueBounds = rangeBounds(REVENUE_RANGES, f.revenueRange)
    try {
      const res = await api.search(q, {
        province: f.province !== "all" ? f.province : undefined,
        min_score: scoreBounds.min,
        max_score: scoreBounds.max,
        has_financial_data:
          f.hasFinancial === "true" ? true : f.hasFinancial === "false" ? false : undefined,
        ebitda_min: ebitdaBounds.min,
        ebitda_max: ebitdaBounds.max,
        revenue_min: revenueBounds.min,
        revenue_max: revenueBounds.max,
      }, { signal: ctrl.signal })
      setResults(res.results)
      setTotal(res.total)
      setWarning(res.warning ?? null)
      setDistribution(res.score_distribution ?? null)
      setSearched(true)
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      setError(err instanceof Error ? err.message : "Error en la búsqueda")
      setResults([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
    // La búsqueda pudo añadir empresas al caché: refresca datos del ranking
    api.getCompanies({ limit: 500 })
      .then((res) => setAllRank(res.companies))
      .catch(() => setAllRank([]))
      .finally(() => setAllRankLoading(false))
    void loadDistribution()
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    doSearch(q, filters)
  }

  function handleFiltersChange(f: Filters) {
    setFilters(f)
    if (searched && query.trim()) {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => {
        doSearch(query.trim(), f)
      }, 400)
    }
  }

  // Filtros combinables en cliente: banda de score + sector
  const bandBounds = rangeBounds(SCORE_RANGES, activeChip ?? "all")
  const shownList = useMemo(() => {
    const base = searched ? results : allRank
    let list = base
    if (bandBounds.min !== undefined || bandBounds.max !== undefined) {
      list = list.filter((c) => {
        const s = c.score ?? 0
        if (bandBounds.min !== undefined && s < bandBounds.min) return false
        if (bandBounds.max !== undefined && s > bandBounds.max) return false
        return true
      })
    }
    if (sectorFilter) {
      list = list.filter((c) => sectorOf(c) === sectorFilter)
    }
    return list
  }, [searched, results, allRank, activeChip, sectorFilter, bandBounds.min, bandBounds.max])

  // Sectores presentes en el caché con su número de empresas
  const sectorCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const c of allRank) {
      const s = sectorOf(c)
      if (s) counts.set(s, (counts.get(s) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [allRank])

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Filtrar Empresas</h1>
        <p className="text-muted-foreground">
          Filtra por sector y puntuación, o busca nuevas empresas en el Registro Mercantil.
        </p>
      </header>

      {/* Filtro por sectores (CNAE de las empresas en caché) */}
      {allRank.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Sectores
          </span>
          {sectorCounts.map(([name, count]) => {
            const active = sectorFilter === name
            return (
              <Button
                key={name}
                variant="outline"
                size="sm"
                aria-pressed={active}
                onClick={() => {
                  const next = active ? null : name
                  setSectorFilter(next)
                  updateUrl({ sector: next })
                }}
                className={
                  active
                    ? "border-primary bg-primary/10 font-medium text-primary"
                    : "text-muted-foreground"
                }
              >
                {name}
                <span
                  className={`ml-0.5 rounded-full px-1.5 text-[10px] font-semibold ${
                    active ? "bg-primary/15" : "bg-muted text-muted-foreground"
                  }`}
                >
                  {count}
                </span>
              </Button>
            )
          })}
          {sectorFilter && (
            <Button
              variant="ghost"
              size="sm"
              className="text-xs"
              onClick={() => {
                setSectorFilter(null)
                updateUrl({ sector: null })
              }}
            >
              Todos los sectores
            </Button>
          )}
        </div>
      )}

      {/* Búsqueda compacta: descubre nuevas empresas en el Registro Mercantil */}
      <form onSubmit={handleSubmit} className="flex gap-2" role="search">
        <Input
          placeholder="Buscar nuevas empresas: industrial, alimentación, transporte..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="max-w-md"
          aria-label="Texto de búsqueda"
        />
        <Button type="submit" disabled={loading || !query.trim()}>
          {loading ? <Loader2 className="animate-spin" /> : <Search />}
          Buscar
        </Button>
      </form>

      <FiltersBar
        filters={filters}
        onChange={handleFiltersChange}
        activeQuick={activeChip}
        counts={distribution}
        onQuickFilter={(v) => {
          const next = v === "all" ? null : v
          setActiveChip(next)
          updateUrl({ rango: next })
        }}
      />

      {error && (
        <div className="flex items-center justify-between rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={() => setError(null)}>
            Cerrar
          </Button>
        </div>
      )}

      {warning && !error && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
          {warning}
        </div>
      )}

      {searched && !loading && !error && total > 0 && (
        <p className="text-sm text-muted-foreground">
          {total} resultado{total === 1 ? "" : "s"} para "{query.trim()}"
          {total > results.length && ` · mostrando ${results.length}`}
        </p>
      )}

      {loading || allRankLoading ? (
        <div className="grid grid-cols-1 gap-3">
          {[...Array(6)].map((_, i) => (
            <CompanyCardSkeleton key={i} />
          ))}
        </div>
      ) : shownList.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="mb-4 rounded-full bg-muted p-4">
            {searched ? (
              <Inbox className="size-10 text-muted-foreground" />
            ) : (
              <Building2 className="size-10 text-muted-foreground" />
            )}
          </div>
          <h3 className="text-lg font-semibold">
            {searched ? "No se encontraron resultados" : "Aún no hay empresas en el ranking"}
          </h3>
          <p className="text-muted-foreground max-w-xs">
            {searched
              ? "Prueba a ampliar los filtros o cambiar la palabra de búsqueda."
              : "Haz una búsqueda para empezar a poblarlo."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {shownList.map((c) => (
            <CompanyCard key={c.cif ?? c.slug} company={c} />
          ))}
        </div>
      )}
    </div>
  )
}
