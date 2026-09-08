import { useState } from "react"
import { ListPlus, Loader2 } from "lucide-react"
import { api } from "@/lib/api"
import type { Company, CompanyList } from "@/lib/types"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function AddToListDialog({ company }: { company: Company }) {
  const [open, setOpen] = useState(false)
  const [lists, setLists] = useState<CompanyList[]>([])
  const [newName, setNewName] = useState("")
  const [loadingId, setLoadingId] = useState<number | null>(null)
  const [creating, setCreating] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [isError, setIsError] = useState(false)

  async function loadLists() {
    try {
      const res = await api.getLists()
      setLists(res.lists)
    } catch {
      setLists([])
    }
  }

  async function handleOpen(open: boolean) {
    setOpen(open)
    setMessage(null)
    setIsError(false)
    if (open) await loadLists()
  }

  async function addTo(listId: number) {
    setLoadingId(listId)
    setMessage(null)
    try {
      await api.addToList(listId, company.cif)
      setMessage("Añadida correctamente")
      setIsError(false)
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Error")
      setIsError(true)
    } finally {
      setLoadingId(null)
    }
  }

  async function createAndAdd() {
    const name = newName.trim()
    if (!name) return
    setCreating(true)
    setMessage(null)
    try {
      const list = await api.createList(name)
      await api.addToList(list.id, company.cif)
      setNewName("")
      setMessage(`Creada y añadida a "${name}"`)
      setIsError(false)
      await loadLists()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Error")
      setIsError(true)
    } finally {
      setCreating(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <ListPlus /> Añadir a lista
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Añadir a lista</DialogTitle>
          <DialogDescription>
            Guarda {company.name} en una lista de candidatas.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          {lists.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No hay listas todavía. Crea una abajo.
            </p>
          ) : (
            lists.map((l) => (
              <div
                key={l.id}
                className="flex items-center justify-between rounded-lg border p-3"
              >
                <div>
                  <p className="text-sm font-medium">{l.name}</p>
                  {l.description && (
                    <p className="text-xs text-muted-foreground">
                      {l.description}
                    </p>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={loadingId === l.id || creating}
                  onClick={() => addTo(l.id)}
                  aria-label={`Añadir a ${l.name}`}
                >
                  {loadingId === l.id ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    "Añadir"
                  )}
                </Button>
              </div>
            ))
          )}
        </div>

        <div className="space-y-2 pt-2">
          <Label className="text-sm">O crea una nueva lista</Label>
          <div className="flex gap-2">
            <Input
              placeholder="Nombre de la lista"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <Button
              variant="secondary"
              disabled={creating || !newName.trim()}
              onClick={createAndAdd}
            >
              {creating ? <Loader2 className="size-4 animate-spin" /> : "Crear y añadir"}
            </Button>
          </div>
        </div>

        {message && (
          <p className={`text-sm ${isError ? "text-red-600" : "text-emerald-600"}`}>
            {message}
          </p>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cerrar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
