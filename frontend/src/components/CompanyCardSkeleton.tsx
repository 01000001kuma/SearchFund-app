import { Card, CardContent } from "@/components/ui/card"

export function CompanyCardSkeleton() {
  return (
    <Card className="overflow-hidden">
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          <div className="size-12 rounded-full bg-muted animate-pulse" />
          <div className="min-w-0 flex-1 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <div className="h-5 w-1/3 rounded bg-muted animate-pulse" />
              <div className="h-5 w-16 rounded bg-muted animate-pulse" />
            </div>
            <div className="h-3 w-1/4 rounded bg-muted animate-pulse" />
            <div className="h-3 w-1/6 rounded bg-muted animate-pulse" />
            <div className="flex gap-4">
              <div className="h-3 w-20 rounded bg-muted animate-pulse" />
              <div className="h-3 w-20 rounded bg-muted animate-pulse" />
              <div className="h-3 w-24 rounded bg-muted animate-pulse" />
            </div>
            <div className="flex gap-2">
              <div className="h-5 w-16 rounded bg-muted animate-pulse" />
              <div className="h-3 w-24 rounded bg-muted animate-pulse" />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
