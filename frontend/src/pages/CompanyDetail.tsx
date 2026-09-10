import { useEffect, useState } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  ArrowLeft,
  Building2,
  Loader2,
  CalendarDays,
  Activity,
  Users,
  FileText,
  Globe,
  Phone,
  Mail,
  MapPin,
  Download,
  TrendingUp,
  ShieldCheck,
  Zap,
} from "lucide-react"
import { api, getExportUrl } from "@/lib/api"
import type { Company } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScoreCircle, ScoreBadge } from "@/components/Score"
import { AddToListDialog } from "@/components/AddToListDialog"
import { formatEuro } from "@/lib/utils"

function parseNum(value: string): number | null {
  const n = parseFloat(value)
  if (isNaN(n)) return null
  return Number.isInteger(n) ? n : Math.round(n * 100) / 100
}

function parseYear(value: string): number | null {
  const n = parseInt(value, 10)
  if (isNaN(n) || n < 1900 || n > 2100) return null
  return n
}

export function CompanyDetail() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  const [company, setCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [revenue, setRevenue] = useState("")
  const [ebitda, setEbitda] = useState("")
  const [margin, setMargin] = useState("")
  const [year, setYear] = useState("")
  const [savingFinance, setSavingFinance] = useState(false)
  const [financeMsg, setFinanceMsg] = useState<string | null>(null)
  const [financeIsError, setFinanceIsError] = useState(false)

  useEffect(() => {
    if (!slug) return
    const ctrl = new AbortController()
    setLoading(true)
    setError(null)
    api
      .getCompany(slug, { signal: ctrl.signal })
      .then((c) => {
        setCompany(c)
        setRevenue(c.financial?.revenue != null ? String(c.financial.revenue) : "")
        setEbitda(c.financial?.ebitda != null ? String(c.financial.ebitda) : "")
        setMargin(
          c.financial?.ebitda_margin != null
            ? String(c.financial.ebitda_margin)
            : "",
        )
        setYear(c.financial?.year != null ? String(c.financial.year) : "")
      })
      .catch((err) => {
        if (err instanceof DOMException && err.name === "AbortError") return
        setError(err instanceof Error ? err.message : "Error al cargar")
      })
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [slug])

  async function saveFinancial() {
    if (!company) return
    const payload: Record<string, number> = {}
    const rv = parseNum(revenue)
    const ev = parseNum(ebitda)
    const mv = margin ? parseNum(margin) : null
    const yv = parseYear(year)
    if (rv != null) payload.revenue = rv
    if (ev != null) payload.ebitda = ev
    if (mv != null) payload.ebitda_margin = mv
    if (yv != null) payload.year = yv
    if (Object.keys(payload).length === 0) {
      setFinanceMsg("Introduce al menos un valor financiero")
      setFinanceIsError(true)
      return
    }
    setSavingFinance(true)
    setFinanceMsg(null)
    setFinanceIsError(false)
    try {
      const res = await api.updateFinancial(company.cif, payload)
      const updated = await api.getCompany(company.slug)
      setCompany(updated)
      if (res.new_score != null) {
        setFinanceMsg(`Guardado. Nuevo score: ${Math.round(res.new_score.total)}`)
        setFinanceIsError(false)
      } else {
        setFinanceMsg("Datos financieros guardados")
        setFinanceIsError(false)
      }
    } catch (err) {
      setFinanceMsg(err instanceof Error ? err.message : "Error al guardar")
      setFinanceIsError(true)
    } finally {
      setSavingFinance(false)
    }
  }

  async function handleExportPdf() {
    if (!company) return
    try {
      const url = await getExportUrl(`/api/company/${company.cif}/export/pdf`)
      const res = await fetch(url)
      const blob = await res.blob()
      const a = document.createElement("a")
      a.href = URL.createObjectURL(blob)
      a.download = `informe_${company.cif}.pdf`
      a.click()
      URL.revokeObjectURL(a.href)
    } catch {
      const url = await getExportUrl(`/api/company/${company.cif}/export/pdf`)
      window.open(url, "_blank")
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" />
        Cargando empresa...
      </div>
    )
  }

  if (error || !company) {
    return (
      <div className="py-16 text-center">
        <p className="text-destructive">{error ?? "Empresa no encontrada"}</p>
        <Button variant="outline" className="mt-4" onClick={() => navigate(-1)}>
          <ArrowLeft /> Volver
        </Button>
      </div>
    )
  }

  const fin = company.financial
  const borme_breakdown = company.score_breakdown?.breakdown?.borme

  // Criterios BORME: puntos obtenidos / máximo posible (score.py)
  const BORME_CRITERIA: Record<string, { label: string; max: number }> = {
    admin_age: { label: "Edad del administrador", max: 40 },
    stability: { label: "Estabilidad BORME", max: 15 },
    family: { label: "Empresa familiar", max: 20 },
    no_council: { label: "Sin consejo externo", max: 10 },
    cnae: { label: "Sector compatible", max: 10 },
    recent_activity: { label: "Actividad reciente", max: 25 },
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{company.name}</h1>
            <p className="text-sm text-muted-foreground">
              {company.cif} {company.legal_form ? `· ${company.legal_form}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleExportPdf}>
            <Download className="size-4 mr-2" />
            Exportar Informe
          </Button>
          <ScoreBadge score={company.score} />
          <AddToListDialog company={company} />
        </div>
      </div>

      {/* Medidor de probabilidad (tira compacta de cabecera) */}
      <Card className="border-primary/20">
        <CardContent className="flex flex-wrap items-center gap-5 p-5">
          <ScoreCircle score={company.score} size={110} />
          <div className="min-w-0 flex-1 space-y-2">
            <p className="text-sm font-semibold leading-snug">
              {company.score_breakdown?.interpretation ?? "Sin evaluar"}
            </p>
            <p className="text-xs text-muted-foreground">
              Probabilidad de adquisición según las señales del Registro Mercantil y los datos financieros.
            </p>
            <div className="flex items-center gap-4 pt-1">
              <div className="min-w-[140px] flex-1">
                <div className="flex justify-between text-[10px] text-muted-foreground">
                  <span>Señales BORME</span>
                  <span className="font-semibold">{company.score_breakdown?.borme?.toFixed(0) ?? 0}%</span>
                </div>
                <div className="mt-0.5 h-1.5 w-full bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-primary" style={{ width: `${company.score_breakdown?.borme ?? 0}%` }} />
                </div>
              </div>
              <div className="min-w-[140px] flex-1">
                <div className="flex justify-between text-[10px] text-muted-foreground">
                  <span>Sólidez financiera</span>
                  <span className="font-semibold">
                    {company.score_breakdown?.financial != null
                      ? `${company.score_breakdown.financial.toFixed(0)}%`
                      : "sin datos"}
                  </span>
                </div>
                <div className="mt-0.5 h-1.5 w-full bg-muted rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500" style={{ width: `${company.score_breakdown?.financial ?? 0}%` }} />
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="space-y-6 lg:col-span-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Building2 className="size-4" /> Datos Corporativos
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">CIF</span>
                <span className="font-medium">{company.cif}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Provincia</span>
                <span className="font-medium">{company.province ?? "—"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Sede</span>
                <span className="font-medium truncate max-w-[150px]">{company.city ?? "—"}</span>
              </div>
              <Separator />
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Globe className="size-4" />
                  <a href={company.website} target="_blank" rel="noreferrer" className="text-primary hover:underline truncate">
                    {company.website ? company.website.replace(/^https?:\/\/(www\.)?/, "") : "Sin web"}
                  </a>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Phone className="size-4" />
                  <span>{company.phone ?? "Sin teléfono"}</span>
                </div>
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Mail className="size-4" />
                  {company.email ? (
                    <a href={`mailto:${company.email}`} className="truncate text-primary hover:underline">
                      {company.email}
                    </a>
                  ) : (
                    <span>Sin email</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6 lg:col-span-8">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <Zap className="size-4 text-amber-500" /> Análisis de Fit (base del Score)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {borme_breakdown && (
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {Object.entries(borme_breakdown).map(([key, val]) => {
                    const meta = BORME_CRITERIA[key]
                    if (!meta) return null
                    return (
                      <div key={key} className="rounded-lg border p-2 text-center bg-muted/20">
                        <p className="text-[10px] uppercase text-muted-foreground font-bold">{meta.label}</p>
                        <p className="text-lg font-bold">
                          {val != null ? `${val} / ${meta.max}` : "—"}
                        </p>
                      </div>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold flex items-center gap-2">
                <TrendingUp className="size-4 text-emerald-500" /> Métricas Financieras
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="rounded-xl bg-muted/50 p-4 border">
                  <p className="text-xs text-muted-foreground mb-1">EBITDA</p>
                  <p className="text-2xl font-bold">{formatEuro(fin?.ebitda ?? null)}</p>
                </div>
                <div className="rounded-xl bg-muted/50 p-4 border">
                  <p className="text-xs text-muted-foreground mb-1">Facturación</p>
                  <p className="text-2xl font-bold">{formatEuro(fin?.revenue ?? null)}</p>
                </div>
                <div className="rounded-xl bg-muted/50 p-4 border">
                  <p className="text-xs text-muted-foreground mb-1">Margen</p>
                  <p className="text-2xl font-bold">{fin?.ebitda_margin ? `${fin.ebitda_margin}%` : "—"}</p>
                </div>
              </div>

              <div className="rounded-lg border bg-muted/30 p-4 space-y-4">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">Actualizar Datos</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label className="text-xs">EBITDA (€)</Label>
                    <Input type="number" value={ebitda} onChange={(e) => setEbitda(e.target.value)} placeholder="2,500,000" />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Facturación (€)</Label>
                    <Input type="number" value={revenue} onChange={(e) => setRevenue(e.target.value)} placeholder="12,000,000" />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Margen EBITDA (%)</Label>
                    <Input type="number" value={margin} onChange={(e) => setMargin(e.target.value)} placeholder="20" />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs">Año Fiscal</Label>
                    <Input type="number" value={year} onChange={(e) => setYear(e.target.value)} placeholder="2025" />
                  </div>
                </div>
                <Button onClick={saveFinancial} disabled={savingFinance} className="w-full sm:w-auto">
                  {savingFinance && <Loader2 className="mr-2 size-4 animate-spin" />}
                  Actualizar Métricas
                </Button>
                {financeMsg && (
                  <p className={`text-xs ${financeIsError ? "text-destructive" : "text-emerald-600 dark:text-emerald-400"}`}>{financeMsg}</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <ShieldCheck className="size-4 text-muted-foreground" /> Registro Histórico (BORME)
          </CardTitle>
        </CardHeader>
        <CardContent>
          {(company.borme?.acts?.length ?? 0) === 0 ? (
            <p className="text-sm text-muted-foreground">Sin actos registrados.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {company.borme?.acts?.slice(0, 12).map((act, idx) => (
                <div key={idx} className="flex items-start gap-3 rounded-lg border p-3 bg-muted/10">
                  <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium">{act.type ?? "Acto"}</p>
                    <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                      {act.details}
                    </p>
                    <p className="mt-1 text-[10px] text-muted-foreground font-mono">
                      {act.date?.slice(0, 10)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
