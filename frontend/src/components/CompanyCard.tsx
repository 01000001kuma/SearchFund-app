import React from "react"
import { useNavigate } from "react-router-dom"
import { Building2, Activity, CalendarDays, FileText } from "lucide-react"
import type { Company } from "@/lib/types"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ScoreBadge, ScoreCircle } from "@/components/Score"
import { formatEuro } from "@/lib/utils"

function formatDate(iso: string | null): string {
  if (!iso) return "No disponible"
  const parts = iso.split("-")
  if (parts.length !== 3) return iso
  const [y, m, d] = parts
  return `${d}/${m}/${y}`
}

export const CompanyCard = React.memo(function CompanyCard({
  company,
}: {
  company: Company
}) {
  const navigate = useNavigate()
  const ebitda = company.financial?.ebitda
  const revenue = company.financial?.revenue
  const hasFinancial = ebitda != null && revenue != null

  return (
    <Card
      className="cursor-pointer transition-shadow hover:shadow-md"
      role="button"
      tabIndex={0}
      onClick={() => navigate(`/empresa/${company.slug}`)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault()
          navigate(`/empresa/${company.slug}`)
        }
      }}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          <ScoreCircle score={company.score} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <h3 className="truncate font-semibold">{company.name}</h3>
              <div className="flex shrink-0 items-center gap-1.5">
                {hasFinancial ? (
                  <Badge className="bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-400">
                    <FileText className="size-3" />
                    Con datos financieros
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-muted-foreground">
                    Sin datos financieros
                  </Badge>
                )}
                <Badge variant="outline" className="shrink-0">
                  {company.legal_form ?? "—"}
                </Badge>
              </div>
            </div>
            <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
              <Building2 className="size-3" />
              <span>{company.cif}</span>
            </div>
            {company.province && (
              <p className="mt-0.5 text-xs text-muted-foreground">
                {company.province}
              </p>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
              <span className="flex items-center gap-1 text-muted-foreground">
                <Activity className="size-3 text-muted-foreground" />
                EBITDA: {formatEuro(ebitda)}
              </span>
              <span className="flex items-center gap-1 text-muted-foreground">
                <Activity className="size-3 text-muted-foreground" />
                Fact.: {formatEuro(revenue)}
              </span>
              <span className="flex items-center gap-1 text-muted-foreground">
                <CalendarDays className="size-3 text-muted-foreground" />
                Últ. acto: {formatDate(company.borme?.last_activity)}
              </span>
            </div>
            <div className="mt-2 flex items-center gap-2">
              <ScoreBadge score={company.score} />
              {company.borme?.acts_count != null && (
                <span className="text-xs text-muted-foreground">
                  {company.borme.acts_count} actos BORME
                </span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
})
