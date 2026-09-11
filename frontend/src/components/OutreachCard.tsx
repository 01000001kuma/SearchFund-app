import { useEffect, useRef, useState } from "react"
import { api } from "@/lib/api"
import type { Company, OutreachTouch } from "@/lib/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select"
import { Loader2, Handshake } from "lucide-react"

const CHANNELS = [
  { value: "telefono", label: "Teléfono", icon: "📞" },
  { value: "email", label: "Email", icon: "✉️" },
  { value: "linkedin", label: "LinkedIn", icon: "💼" },
  { value: "carta", label: "Carta", icon: "✉️" },
  { value: "visita", label: "Visita", icon: "🚗" },
  { value: "otro", label: "Otro", icon: "•" },
]

const STATUSES = [
  { value: "prospecto", label: "Prospecto" },
  { value: "contactado", label: "Contactado" },
  { value: "conversacion", label: "Conversación" },
  { value: "loi", label: "LOI firmada" },
  { value: "adquisicion", label: "Adquisición" },
  { value: "descartado", label: "Descartado" },
]

const CHANNEL_ICON: Record<string, string> = {
  telefono: "📞", email: "✉️", linkedin: "💼", carta: "✉️", visita: "🚶", otro: "·",
}

export function OutreachCard({ company }: { company: Company }) {
  const [status, setStatus] = useState(company.pipeline_status ?? "prospecto")
  const [touches, setTouches] = useState<OutreachTouch[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [channel, setChannel] = useState<string>("telefono")
  const [summary, setSummary] = useState("")
  const [nextAction, setNextAction] = useState("")
  const [nextDate, setNextDate] = useState("")
  const ctrlRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    ctrlRef.current = ctrl
    api.getTouches(company.cif, { signal: ctrl.signal })
      .then((res) => setTouches(res.touches))
      .catch(() => setTouches([]))
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [company.cif])

  async function saveTouch() {
    setSaving(true)
    setMessage(null)
    try {
      await api.addTouch(company.cif, {
        channel,
        summary: summary.trim() || undefined,
        next_action: nextAction || undefined,
        next_action_date: nextDate || undefined,
      })
      const res = await api.getTouches(company.cif)
      setTouches(res.touches)
      setSummary("")
      setNextAction("")
      setNextDate("")
      setMessage("Toque registrado")
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Error al guardar el toque")
    } finally {
      setSaving(false)
    }
  }

  async function changeStatus(value: string) {
    setStatus(value)
    try {
      await api.setPipelineStatus(company.cif, value)
    } catch {
      setMessage("Error al actualizar el estado")
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Handshake className="size-4" /> Outreach y pipeline
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label className="text-xs">Estado del pipeline</Label>
          <Select value={status} onValueChange={changeStatus}>
            <SelectTrigger className="mt-1 h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUSES.map((s) => (
                <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Historial de toques */}
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">
            {loading ? "Cargando toques…" : touches.length === 0 ? "Sin toques registrados." : `${touches.length} toque${touches.length === 1 ? "" : "s"}`}
          </p>
          {!loading && touches.map((t) => (
            <div key={t.id} className="rounded-lg border p-2.5 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-medium">{CHANNEL_ICON[t.channel] ?? "•"} {t.channel}</span>
                <span className="text-muted-foreground">{t.created_at?.slice(0, 10)}</span>
              </div>
              {t.summary && <p className="text-muted-foreground">{t.summary}</p>}
              {t.next_action && (
                <p className="text-primary">
                  ⏭ {t.next_action}
                  {t.next_action_date ? ` (${t.next_action_date})` : ""}
                </p>
              )}
            </div>
          ))}
        </div>

        {/* Registrar toque */}
        <div className="rounded-lg border bg-muted/30 p-3 space-y-3">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Registrar toque</p>
          <div>
            <Label className="text-xs">Canal</Label>
            <Select value={channel} onValueChange={setChannel}>
              <SelectTrigger className="mt-1 h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {CHANNELS.map((c) => (
                  <SelectItem key={c.value} value={c.value}>{c.icon} {c.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs">Resumen / notas</Label>
            <Textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Qué ha pasado, qué dijo, con quién hablé…"
              className="mt-1 min-h-[64px] text-xs"
            />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label className="text-xs">Siguiente acción</Label>
              <Input value={nextAction} onChange={(e) => setNextAction(e.target.value)} className="h-8 text-xs" placeholder="Ej: Volver a llamar" />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Fecha</Label>
              <Input type="date" value={nextDate} onChange={(e) => setNextDate(e.target.value)} className="h-8 text-xs" />
            </div>
          </div>
          <Button size="sm" onClick={saveTouch} disabled={saving}>
            {saving && <Loader2 className="mr-2 size-3.5 animate-spin" />}Guardar toque
          </Button>
          {message && <p className="text-xs text-destructive">{message}</p>}
        </div>
      </CardContent>
    </Card>
  )
}
