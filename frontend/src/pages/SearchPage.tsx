import { useState, useEffect, useRef, type FormEvent } from "react"
import { useSearchParams } from "react-router-dom"
import { Search, Loader2, Inbox, Trophy } from "lucide-react"
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

  // Vista "ranking": lista de empresas en caché de una banda de score
  const [activeChip, setActiveChip] = useState<string | null>(
    () => searchParams.get("rango"),
  )
  const [rankCompanies, setRankCompanies] = useState<Company[] | null>(null)
  const [rankTotal, setRankTotal] = useState(0)
  const [rankLoading, setRankLoading] = useState(false)

  const abortRef = useRef<AbortController | null>(null)
  const rankAbortRef = useRef<AbortController | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
      rankAbortRef.current?.abort()
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

  // Distribución del ranking completo + vista de ranking desde la URL
  const mountedRef = useRef(false)
  useEffect(() => {
    if (mountedRef.current) return
    mountedRef.current = true
    void loadDistribution()
    const rango = searchParams.get("rango")
    if (rango && rango !== "all") {
      void loadRanking(rango, filters)
    } else {
      const q = searchParams.get("q")
      if (q) void doSearch(q, filters)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function syncUrl(q: string, f: Filters, rango: string | null = activeChip) {
    const params = new URLSearchParams()
    if (rango && rango !== "all") params.set("rango", rango)
    if (q) params.set("q", q)
    if (f.province !== "all") params.set("provincia", f.province)
    if (f.scoreRange !== "all") params.set("score", f.scoreRange)
    if (f.hasFinancial !== "all") params.set("fin", f.hasFinancial)
    if (f.ebitdaRange !== "all") params.set("ebitda", f.ebitdaRange)
    if (f.revenueRange !== "all") params.set("rev", f.revenueRange)
    setSearchParams(params, { replace: true })
  }

  async function doSearch(q: string, f: Filters) {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    // Una búsqueda de texto sustituye la vista de ranking
    setActiveChip(null)
    setRankCompanies(null)

    setLoading(true)
    setError(null)
    setWarning(null)
    syncUrl(q, f, null)
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
    // La búsqueda pudo añadir empresas al caché: refresca los conteos del ranking
    void loadDistribution()
  }

  async function loadRanking(range: string, f: Filters) {
    rankAbortRef.current?.abort()
    const ctrl = new AbortController()
    rankAbortRef.current = ctrl

    setRankLoading(true)
    setError(null)
    const bounds = rangeBounds(SCORE_RANGES, range)
    const ebitdaBounds = rangeBounds(EBITDA_RANGES, f.ebitdaRange)
    const revenueBounds = rangeBounds(REVENUE_RANGES, f.revenueRange)
    try {
      const res = await api.getCompanies({
        min_score: bounds.min,
        max_score: bounds.max,
        province: f.province !== "all" ? f.province : undefined,
        has_financial_data:
          f.hasFinancial === "true" ? true : f.hasFinancial === "false" ? false : undefined,
        limit: 500,
      }, { signal: ctrl.signal })
      // Rangos EBITDA/facturación se aplican en cliente (la BD no filtra por JSON)
      let list = res.companies
      if (ebitdaBounds.min !== undefined)
        list = list.filter((c) => (c.financial?.ebitda ?? -Infinity) >= ebitdaBounds.min!)
      if (ebitdaBounds.max !== undefined)
        list = list.filter((c) => c.financial?.ebitda != null && c.financial.ebitda <= ebitdaBounds.max!)
      if (revenueBounds.min !== undefined)
        list = list.filter((c) => (c.financial?.revenue ?? -Infinity) >= revenueBounds.min!)
      if (revenueBounds.max !== undefined)
        list = list.filter((c) => c.financial?.revenue != null && c.financial.revenue <= revenueBounds.max!)
      setRankCompanies(list)
      setRankTotal(list.length)
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      setError(err instanceof Error ? err.message : "Error al cargar el ranking")
      setRankCompanies([])
      setRankTotal(0)
    } finally {
      setRankLoading(false)
    }
  }

  function handleQuickFilter(value: string) {
    if (value === "all") {
      setActiveChip(null)
      setRankCompanies(null)
      syncUrl(query.trim(), filters, null)
      return
    }
    setActiveChip(value)
    syncUrl(query.trim(), filters, value)
    void loadRanking(value, filters)
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    doSearch(q, filters)
  }

  function handleFiltersChange(f: Filters) {
    setFilters(f)
    if (activeChip) {
      // La vista de ranking respeta provincia/datos financieros
      void loadRanking(activeChip, f)
    } else if (query.trim()) {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => {
        doSearch(query.trim(), f)
      }, 400)
    }
  }

  const chipLabel = QUICK_SCORE_RANGES.find((r) => r.value === activeChip)?.label
  const chipBounds = chipChipBounds(activeChip)

  function chipChipBounds(range: string | null): string {
    if (!range) return ""
    const found = SCORE_RANGES.find((r) => r.value === range)
    if (!found) return ""
    if (found.min !== undefined && found.max !== undefined) return `${found.min}–${found.max}`
    if (found.min !== undefined) return `≥ ${found.min}`
    return ""
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Filtrar Empresas</h1>
        <p className="text-muted-foreground">
          Introduce un nombre o sector para encontrar PYMES en el Registro
          Mercantil.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="flex gap-2" role="search">
        <Input
          placeholder="Ej: industrial, alimentación, transporte..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="max-w-lg"
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
        onQuickFilter={handleQuickFilter}
      />

      {error && (
        <div className="flex items-center justify-between rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={() => setError(null)}>
            Cerrar
          </Button>
        </div>
      )}

      {warning && !error && !activeChip && (
        <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-700 dark:text-amber-400">
          {warning}
        </div>
      )}

      {activeChip && (
        <p className="text-sm text-muted-foreground">
          Ranking <span className="font-medium text-foreground">{chipLabel}</span>
          {chipBounds && ` · score ${chipBounds}`}
          {rankTotal > 0 && ` · ${rankTotal} empresa${rankTotal === 1 ? "" : "s"}`}
        </p>
      )}

      {!activeChip && searched && !loading && !error && total === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="mb-4 rounded-full bg-muted p-4">
            <Inbox className="size-10 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No se encontraron resultados</h3>
          <p className="text-muted-foreground max-w-xs">
            Prueba a ampliar los filtros o cambiar la palabra de búsqueda.
          </p>
        </div>
      )}

      {!activeChip && searched && !loading && !error && total > 0 && (
        <p className="text-sm text-muted-foreground">
          {total} resultado{total === 1 ? "" : "s"} para "{query.trim()}"
          {total > results.length && ` · mostrando ${results.length}`}
        </p>
      )}

      {rankLoading ? (
        <div className="grid grid-cols-1 gap-3">
          {[...Array(6)].map((_, i) => (
            <CompanyCardSkeleton key={i} />
          ))}
        </div>
      ) : activeChip && rankCompanies && rankCompanies.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="mb-4 rounded-full bg-muted p-4">
            <Trophy className="size-10 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">Sin empresas en este rango</h3>
          <p className="text-muted-foreground max-w-xs">
            Haz búsquedas para poblar el ranking con candidatas.
          </p>
        </div>
      ) : rankCompanies ? (
        <div className="grid grid-cols-1 gap-3">
          {rankCompanies.map((c) => (
            <CompanyCard key={c.cif ?? c.slug} company={c} />
          ))}
        </div>
      ) : loading ? (
        <div className="grid grid-cols-1 gap-3">
          {[...Array(6)].map((_, i) => (
            <CompanyCardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {results.map((c) => (
            <CompanyCard key={c.cif ?? c.slug} company={c} />
          ))}
        </div>
      )}
    </div>
  )
}
