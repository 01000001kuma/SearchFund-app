import { useState, useEffect, useRef, type FormEvent } from "react"
import { Search, Loader2, Inbox } from "lucide-react"
import { api } from "@/lib/api"
import type { Company } from "@/lib/types"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { CompanyCard } from "@/components/CompanyCard"
import { CompanyCardSkeleton } from "@/components/CompanyCardSkeleton"
import { FiltersBar, type Filters } from "@/components/FiltersBar"

const EMPTY_FILTERS: Filters = { province: "", minScore: "", maxScore: "", hasFinancial: "" }

export function SearchPage() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<Company[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [warning, setWarning] = useState<string | null>(null)
  const [searched, setSearched] = useState(false)
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS)
  const abortRef = useRef<AbortController | null>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      abortRef.current?.abort()
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  async function doSearch(q: string, f: Filters) {
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    setLoading(true)
    setError(null)
    setWarning(null)
    try {
      const res = await api.search(q, {
        province: f.province || undefined,
        min_score: f.minScore ? Number(f.minScore) : undefined,
        max_score: f.maxScore ? Number(f.maxScore) : undefined,
        has_financial_data: f.hasFinancial === "true" ? true : f.hasFinancial === "false" ? false : undefined,
      }, { signal: ctrl.signal })
      setResults(res.results)
      setTotal(res.total)
      setWarning(res.warning ?? null)
      setSearched(true)
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      setError(err instanceof Error ? err.message : "Error en la búsqueda")
      setResults([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
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

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold tracking-tight">Filtrar empresas</h1>
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
          Filtrar
        </Button>
      </form>

      <FiltersBar
        filters={filters}
        onChange={handleFiltersChange}
        resultCount={searched ? total : null}
      />

      {error && (
        <div className="flex items-center justify-between rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={() => setError(null)}>
            Cerrar
          </Button>
        </div>
      )}

      {warning && !error && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
          {warning}
        </div>
      )}

      {searched && !loading && !error && total === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="mb-4 rounded-full bg-muted p-4">
            <Inbox className="size-10 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold">No se encontraron resultados</h3>
          <p className="text-muted-foreground max-w-xs">
            Intenta ampliar los filtros o cambiar la palabra de búsqueda.
          </p>
        </div>
      )}

      {searched && !loading && !error && total > 0 && (
        <p className="text-sm text-muted-foreground">
          {total} resultado{total === 1 ? "" : "s"} para "{query.trim()}"
        </p>
      )}

      {loading ? (
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
