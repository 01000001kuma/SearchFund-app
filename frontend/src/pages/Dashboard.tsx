import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Building2, ListChecks, Search, FileText, BarChart3, Sparkles, Loader2, CheckCircle2, TrendingUp } from "lucide-react"
import { api } from "@/lib/api"
import type { Stats, DailyStats } from "@/lib/types"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

export function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [daily, setDaily] = useState<DailyStats[]>([])
  const [loading, setLoading] = useState(true)
  const [isSearchingDaily, setIsSearchingDaily] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    Promise.all([
      api.getStats({ signal: ctrl.signal }),
      api.getDailyStats(14, { signal: ctrl.signal }),
    ])
      .then(([s, d]) => {
        setStats(s)
        setDaily(d.daily)
      })
      .catch(() => {
        setStats(null)
        setDaily([])
      })
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [])

  async function handleDailySearch() {
    setIsSearchingDaily(true)
    try {
      const res = await api.searchDaily()
      toast.success(`Búsqueda completada. ${res.new_count} nuevas candidatas añadidas.`)
      const s = await api.getStats()
      setStats(s)
    } catch {
      toast.error("Error al realizar la búsqueda diaria")
    } finally {
      setIsSearchingDaily(false)
    }
  }

  const cards = [
    {
      label: "Empresas Encontradas",
      value: stats?.total_companies ?? 0,
      today: stats?.companies_today ?? 0,
      icon: Building2,
      to: "/candidatas",
      color: "text-blue-500",
    },
    {
      label: "EBITDA Disponibles",
      value: stats?.companies_with_financial_data ?? 0,
      today: stats?.financial_today ?? 0,
      icon: FileText,
      to: "/candidatas",
      color: "text-emerald-500",
    },
    {
      label: "Listas por Sector",
      value: stats?.total_lists ?? 0,
      today: stats?.lists_today ?? 0,
      icon: ListChecks,
      to: "/listas",
      color: "text-amber-500",
    },
    {
      label: "Búsquedas Totales",
      value: stats?.total_searches ?? 0,
      today: stats?.searches_today ?? 0,
      icon: Search,
      to: "/buscar",
      color: "text-purple-500",
    },
  ]

  const maxSearches = Math.max(...daily.map((d) => d.searches), 1)

  return (
    <div className="space-y-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Panel de Control</h1>
        </div>
        <Button 
          onClick={handleDailySearch} 
          disabled={isSearchingDaily}
          className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm"
        >
          {isSearchingDaily ? (
            <><Loader2 className="mr-2 size-4 animate-spin" /> Buscando...</>
          ) : (
            <><Sparkles className="mr-2 size-4" /> Búsqueda Diaria</>
          )}
        </Button>
      </header>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <Link to={c.to} key={c.label}>
            <Card className="group relative overflow-hidden transition-all hover:shadow-md hover:-translate-y-1">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">{c.label}</span>
                  <c.icon className={`size-6 ${c.color}`} />
                </div>
                <p className="mt-2 text-3xl font-bold tracking-tight">
                  {loading ? "…" : c.value}
                </p>
                {(c.today ?? 0) > 0 ? (
                  <span className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400">
                    <TrendingUp className="size-3" />+{c.today} hoy
                  </span>
                ) : (
                  <span className="mt-1.5 inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                    +0 hoy
                  </span>
                )}
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardContent className="p-6">
            <div className="mb-6 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BarChart3 className="size-5 text-muted-foreground" />
                <h2 className="text-lg font-semibold">Actividad Reciente</h2>
              </div>
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="size-2 rounded-full bg-primary" /> Búsquedas
                </span>
                <span className="flex items-center gap-1">
                  <span className="size-2 rounded-full bg-emerald-500" /> Empresas
                </span>
                <span className="flex items-center gap-1">
                  <span className="size-2 rounded-full bg-amber-500" /> Listas
                </span>
              </div>
            </div>
            {loading ? (
              <div className="flex h-32 items-center justify-center text-muted-foreground">
                <Loader2 className="size-6 animate-spin" />
              </div>
            ) : daily.length === 0 ? (
              <p className="text-center py-10 text-muted-foreground">Sin datos de actividad</p>
            ) : (
              <div className="flex items-end gap-2" style={{ height: 160 }}>
                {daily.map((d) => (
                  <div key={d.day} className="group relative flex flex-1 flex-col items-center gap-1">
                    <div className="flex w-full flex-col items-center gap-1" style={{ height: 140 }}>
                      {d.searches > 0 && (
                        <div
                          className="w-full rounded-t-sm bg-primary/80 transition-all hover:bg-primary"
                          style={{ height: `${(d.searches / maxSearches) * 100}%`, minHeight: 2 }}
                        />
                      )}
                      {d.companies > 0 && (
                        <div
                          className="w-full rounded-t-sm bg-emerald-500/80 transition-all hover:bg-emerald-500"
                          style={{ height: `${(d.companies / maxSearches) * 100}%`, minHeight: 2 }}
                        />
                      )}
                      {d.lists > 0 && (
                        <div
                          className="w-full rounded-t-sm bg-amber-500/80 transition-all hover:bg-amber-500"
                          style={{ height: `${(d.lists / maxSearches) * 100}%`, minHeight: 2 }}
                        />
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground font-medium">
                      {d.day.slice(5)}
                    </span>
                    <div className="pointer-events-none absolute bottom-full mb-2 hidden rounded bg-popover p-2 text-xs shadow-lg group-hover:block z-10 border">
                      <p className="font-bold mb-1">{d.day}</p>
                      <p className="text-muted-foreground">Búsquedas: {d.searches}</p>
                      <p className="text-muted-foreground">Empresas: {d.companies}</p>
                      <p className="text-muted-foreground">Listas: {d.lists}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle2 className="size-5 text-primary" />
              <h2 className="text-lg font-semibold">Guía Rápida</h2>
            </div>
            <div className="space-y-4">
              <div className="rounded-lg border bg-muted/30 p-3">
                <h3 className="text-sm font-medium">Búsqueda Diaria</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  En el panel de control sincroniza el registro mercantil y encuentra nuevas candidatas automáticamente.
                </p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-3">
                <h3 className="text-sm font-medium">Análisis junto con el Agente</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Utiliza el agente para analizar empresas detalladamente
                </p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-3">
                <h3 className="text-sm font-medium">Candidatas</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Accede al listado completo de empresas detectadas, filtradas y priorizadas por su probabilidad de compra.
                </p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-3">
                <h3 className="text-sm font-medium">Búsqueda Inteligente</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Explora Las empresas encontradas, filtralas y detecta candidatas con el algoritmo de puntuacion automático.
                </p>
              </div>
              <div className="rounded-lg border bg-muted/30 p-3">
                <h3 className="text-sm font-medium">Listas</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  Organiza tus candidatas en grupos personalizados y expórtalas en PDFs o tablas de EXCEL para su análisis financiero.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
