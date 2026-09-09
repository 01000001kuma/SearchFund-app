import { useState } from "react"
import { Check, SlidersHorizontal, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import type { ScoreDistribution } from "@/lib/types"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export interface RangeOption {
  value: string
  label: string
  min?: number
  max?: number
}

export interface Filters {
  province: string
  scoreRange: string
  hasFinancial: string
  ebitdaRange: string
  revenueRange: string
}

interface FiltersBarProps {
  filters: Filters
  onChange: (filters: Filters) => void
  /** Banda rápida activa ("bajo"|"medio"|"alto") o null. */
  activeQuick?: string | null
  /** Empresas del ranking completo en cada banda. */
  counts?: ScoreDistribution | null
  /** Click en un chip (recibe el value o "all" si se deselecciona). */
  onQuickFilter?: (value: string) => void
}

/** Provincias de España (52) — deben coincidir con el texto de OpenMercantil. */
const PROVINCES = [
  "A Coruña", "Álava", "Albacete", "Alicante", "Almería", "Asturias", "Ávila",
  "Badajoz", "Barcelona", "Bizkaia", "Burgos", "Cáceres", "Cádiz", "Cantabria",
  "Castellón", "Ceuta", "Ciudad Real", "Córdoba", "Cuenca", "Girona", "Granada",
  "Guadalajara", "Gipuzkoa", "Huelva", "Huesca", "Illes Balears", "Jaén",
  "La Rioja", "Las Palmas", "León", "Lleida", "Lugo", "Madrid", "Málaga",
  "Melilla", "Murcia", "Navarra", "Ourense", "Palencia", "Pontevedra",
  "Salamanca", "Santa Cruz de Tenerife", "Segovia", "Sevilla", "Soria",
  "Tarragona", "Teruel", "Toledo", "Valencia", "Valladolid", "Zamora",
  "Zaragoza",
]

/** Rangos de score — valores compartidos por el select y los pre-filtros rápidos. */
export const SCORE_RANGES: RangeOption[] = [
  { value: "all", label: "Todos" },
  { value: "muy-alto", label: "Muy alto · 80–100", min: 80 },
  { value: "alto", label: "Alto · 60–100", min: 60 },
  { value: "medio", label: "Medio · 40–59", min: 40, max: 59 },
  { value: "bajo", label: "Bajo · 0–39", min: 0, max: 39 },
]

/** Pre-filtros rápidos (chips) junto al botón "Filtros", con color por banda. */
export const QUICK_SCORE_RANGES: (RangeOption & { tone: "red" | "orange" | "green" })[] = [
  { value: "bajo", label: "Bajo", tone: "red" },
  { value: "medio", label: "Medio", tone: "orange" },
  { value: "alto", label: "Alto", tone: "green" },
]

const TONE_CLASSES: Record<"red" | "orange" | "green", { idle: string; active: string }> = {
  red: {
    idle: "border-transparent bg-red-400 text-black hover:bg-red-300",
    active: "border-red-600 bg-red-500 text-black ring-1 ring-red-600",
  },
  orange: {
    idle: "border-transparent bg-orange-400 text-black hover:bg-orange-300",
    active: "border-orange-600 bg-orange-500 text-black ring-1 ring-orange-600",
  },
  green: {
    idle: "border-transparent bg-green-400 text-black hover:bg-green-300",
    active: "border-green-600 bg-green-500 text-black ring-1 ring-green-600",
  },
}

/** Rangos de EBITDA en €. "objetivo" = criterio de Cabiedes. */
export const EBITDA_RANGES: RangeOption[] = [
  { value: "all", label: "Todos" },
  { value: "1.5-3", label: "1,5–3M€ · objetivo", min: 1_500_000, max: 3_000_000 },
  { value: "0.5-1.5", label: "0,5–1,5M€", min: 500_000, max: 1_500_000 },
  { value: "3+", label: "≥ 3M€", min: 3_000_000 },
  { value: "lt0.5", label: "< 0,5M€", max: 500_000 },
]

/** Rangos de facturación anual en €. "objetivo" = criterio de Cabiedes. */
export const REVENUE_RANGES: RangeOption[] = [
  { value: "all", label: "Todos" },
  { value: "10-15", label: "10–15M€ · objetivo", min: 10_000_000, max: 15_000_000 },
  { value: "5-10", label: "5–10M€", min: 5_000_000, max: 10_000_000 },
  { value: "15+", label: "≥ 15M€", min: 15_000_000 },
  { value: "lt5", label: "< 5M€", max: 5_000_000 },
]

export const FINANCIAL_OPTIONS = [
  { value: "all", label: "Todos" },
  { value: "true", label: "Con datos financieros" },
  { value: "false", label: "Sin datos financieros" },
]

export const EMPTY_FILTERS: Filters = {
  province: "all",
  scoreRange: "all",
  hasFinancial: "all",
  ebitdaRange: "all",
  revenueRange: "all",
}

/** Devuelve {min,max} del rango seleccionado; {} si es "all" o desconocido. */
export function rangeBounds(
  ranges: RangeOption[],
  value: string,
): { min?: number; max?: number } {
  const found = ranges.find((r) => r.value === value)
  if (!found || found.value === "all") return {}
  const out: { min?: number; max?: number } = {}
  if (found.min !== undefined) out.min = found.min
  if (found.max !== undefined) out.max = found.max
  return out
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
}) {
  return (
    <div>
      <Label className="text-xs">{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="mt-1 h-8 text-xs">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

export function FiltersBar({
  filters,
  onChange,
  activeQuick = null,
  counts = null,
  onQuickFilter,
}: FiltersBarProps) {
  const [open, setOpen] = useState(false)
  const activeCount = Object.values(filters).filter((v) => v !== "all").length

  function update(key: keyof Filters, value: string) {
    onChange({ ...filters, [key]: value })
  }

  function clearAll() {
    onChange(EMPTY_FILTERS)
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setOpen(!open)}
          className="gap-1.5"
          aria-expanded={open}
        >
          <SlidersHorizontal className="size-3.5" />
          Filtros
          {activeCount > 0 && (
            <span className="ml-1 rounded-full bg-primary px-1.5 text-[10px] font-bold text-primary-foreground">
              {activeCount}
            </span>
          )}
        </Button>
        {QUICK_SCORE_RANGES.length > 0 && (
          <span className="ml-1 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Ranking de adquisición
          </span>
        )}
        {QUICK_SCORE_RANGES.map((r) => {
          const active = activeQuick === r.value
          const count = counts ? counts[r.value as keyof ScoreDistribution] : undefined
          const tone = TONE_CLASSES[r.tone]
          return (
            <Button
              key={r.value}
              variant="outline"
              size="sm"
              onClick={() => onQuickFilter?.(active ? "all" : r.value)}
              aria-pressed={active}
              className={`${active ? tone.active : tone.idle} font-medium`}
            >
              {active && <Check className="size-3.5" strokeWidth={3} />}
              {r.label}
              {count !== undefined && (
                <span className="ml-0.5 rounded-full bg-white px-1.5 text-[10px] font-bold text-black">
                  {count}
                </span>
              )}
            </Button>
          )
        })}
        {activeCount > 0 && (
          <Button variant="ghost" size="sm" onClick={clearAll} className="gap-1 text-xs">
            <X className="size-3" />
            Limpiar
          </Button>
        )}
      </div>

      {open && (
        <div className="grid grid-cols-1 gap-3 rounded-lg border bg-muted/30 p-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <FilterSelect
            label="Provincia"
            value={filters.province}
            onChange={(v) => update("province", v)}
            options={[
              { value: "all", label: "Todas" },
              ...PROVINCES.map((p) => ({ value: p, label: p })),
            ]}
          />
          <FilterSelect
            label="Score"
            value={filters.scoreRange}
            onChange={(v) => update("scoreRange", v)}
            options={SCORE_RANGES}
          />
          <FilterSelect
            label="EBITDA"
            value={filters.ebitdaRange}
            onChange={(v) => update("ebitdaRange", v)}
            options={EBITDA_RANGES}
          />
          <FilterSelect
            label="Facturación"
            value={filters.revenueRange}
            onChange={(v) => update("revenueRange", v)}
            options={REVENUE_RANGES}
          />
          <FilterSelect
            label="Datos financieros"
            value={filters.hasFinancial}
            onChange={(v) => update("hasFinancial", v)}
            options={FINANCIAL_OPTIONS}
          />
        </div>
      )}
    </div>
  )
}
