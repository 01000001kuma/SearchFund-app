import { useState } from "react"
import { SlidersHorizontal, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export interface Filters {
  province: string
  minScore: string
  maxScore: string
  hasFinancial: string
}

interface FiltersBarProps {
  filters: Filters
  onChange: (filters: Filters) => void
  resultCount: number | null
}

const PROVINCES = [
  "Madrid",
  "Barcelona",
  "Valencia",
  "Sevilla",
  "Bizkaia",
  "Gipuzkoa",
  "A Coruña",
  "Pontevedra",
  "Zaragoza",
  "Málaga",
  "Alicante",
  "Castellón",
  "Murcia",
  "Valladolid",
  "Burgos",
  "León",
  "Salamanca",
  "Navarra",
  "Illes Balears",
  "Las Palmas",
  "Santa Cruz de Tenerife",
]

const SCORE_RANGES = [
  { label: "Todos", value: "" },
  { label: "≥ 80 (Muy alto)", value: "80" },
  { label: "≥ 60 (Alto)", value: "60" },
  { label: "≥ 40 (Medio)", value: "40" },
  { label: "< 40 (Bajo)", value: "max:39" },
]

const FINANCIAL_OPTIONS = [
  { label: "Todos", value: "" },
  { label: "Con datos financieros", value: "true" },
  { label: "Sin datos financieros", value: "false" },
]

const EMPTY_FILTERS: Filters = {
  province: "",
  minScore: "",
  maxScore: "",
  hasFinancial: "",
}

export function FiltersBar({ filters, onChange, resultCount }: FiltersBarProps) {
  const [open, setOpen] = useState(false)
  const activeCount = Object.values(filters).filter(Boolean).length

  function update(key: keyof Filters, value: string) {
    onChange({ ...filters, [key]: value })
  }

  function clearAll() {
    onChange(EMPTY_FILTERS)
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setOpen(!open)}
          className="gap-1.5"
        >
          <SlidersHorizontal className="size-3.5" />
          Filtros
          {activeCount > 0 && (
            <span className="ml-1 rounded-full bg-primary px-1.5 text-[10px] font-bold text-primary-foreground">
              {activeCount}
            </span>
          )}
        </Button>
        {activeCount > 0 && (
          <Button variant="ghost" size="sm" onClick={clearAll} className="gap-1 text-xs">
            <X className="size-3" />
            Limpiar
          </Button>
        )}
        {resultCount !== null && (
          <span className="text-xs text-muted-foreground">
            {resultCount} resultado{resultCount === 1 ? "" : "s"}
          </span>
        )}
      </div>

      {open && (
        <div className="grid grid-cols-1 gap-3 rounded-lg border bg-muted/30 p-4 sm:grid-cols-3">
          <div>
            <Label className="text-xs">Provincia</Label>
            <Select
              value={filters.province}
              onValueChange={(v) => update("province", v === "all" ? "" : v)}
            >
              <SelectTrigger className="mt-1 h-8 text-xs">
                <SelectValue placeholder="Todas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas</SelectItem>
                {PROVINCES.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs">Score mínimo</Label>
            <Select
              value={filters.minScore || filters.maxScore ? (filters.maxScore ? `max:${filters.maxScore}` : filters.minScore) : ""}
              onValueChange={(v) => {
                if (v === "all") {
                  update("minScore", "")
                  update("maxScore", "")
                } else if (v.startsWith("max:")) {
                  update("minScore", "")
                  update("maxScore", v.slice(4))
                } else {
                  update("minScore", v)
                  update("maxScore", "")
                }
              }}
            >
              <SelectTrigger className="mt-1 h-8 text-xs">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                {SCORE_RANGES.map((r) => (
                  <SelectItem key={r.value || "all"} value={r.value || "all"}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label className="text-xs">Datos financieros</Label>
            <Select
              value={filters.hasFinancial}
              onValueChange={(v) => update("hasFinancial", v === "all" ? "" : v)}
            >
              <SelectTrigger className="mt-1 h-8 text-xs">
                <SelectValue placeholder="Todos" />
              </SelectTrigger>
              <SelectContent>
                {FINANCIAL_OPTIONS.map((o) => (
                  <SelectItem key={o.value || "all"} value={o.value || "all"}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      )}
    </div>
  )
}
