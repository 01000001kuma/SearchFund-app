import { useEffect, useState, useRef, useCallback } from "react"
import { Download, Loader2, Plus, Trash2 } from "lucide-react"
import { api, getExportUrl } from "@/lib/api"
import type { CompanyList, ListResponse } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { CompanyCard } from "@/components/CompanyCard"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"

export function ListsPage() {
  const [lists, setLists] = useState<CompanyList[]>([])
  const [selected, setSelected] = useState<ListResponse | null>(null)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [newName, setNewName] = useState("")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const loadLists = useCallback(async (signal?: AbortSignal) => {
    try {
      const res = await api.getLists({ signal })
      setLists(res.lists)
      return res.lists
    } catch {
      if (signal?.aborted) return []
      setError("Error al cargar listas")
      return []
    }
  }, [])

  const loadList = useCallback(async (id: number, signal?: AbortSignal) => {
    try {
      const res = await api.getList(id, { signal })
      setSelected(res)
      setSelectedId(id)
    } catch {
      if (signal?.aborted) return
      setError("Error al cargar la lista")
    }
  }, [])

  useEffect(() => {
    const ctrl = new AbortController()
    loadLists(ctrl.signal)
      .then(async (allLists) => {
        if (allLists.length > 0) await loadList(allLists[0].id, ctrl.signal)
      })
      .finally(() => setLoading(false))
    return () => ctrl.abort()
  }, [loadLists, loadList])

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  async function createList() {
    const name = newName.trim()
    if (!name) return
    try {
      const list = await api.createList(name)
      setNewName("")
      setLists((prev) => [...prev, list])
      await loadList(list.id)
    } catch {
      setError("Error al crear la lista")
    }
  }

  async function removeCompany(cif: string) {
    if (!selectedId) return
    try {
      await api.removeFromList(selectedId, cif)
      await loadList(selectedId)
    } catch {
      setError("Error al quitar la empresa")
    }
  }

  async function handleExportExcel() {
    if (!selected) return
    try {
      const url = await getExportUrl(`/api/lists/${selected.list.id}/export/xlsx`)
      const res = await fetch(url)
      const blob = await res.blob()
      const a = document.createElement("a")
      a.href = URL.createObjectURL(blob)
      a.download = `lista_${selected.list.id}.xlsx`
      a.click()
      URL.revokeObjectURL(a.href)
    } catch {
      const url = await getExportUrl(`/api/lists/${selected.list.id}/export/xlsx`)
      window.open(url, "_blank")
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-muted-foreground">
        <Loader2 className="size-5 animate-spin" /> Cargando listas...
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="space-y-4">
        <header>
          <h1 className="text-2xl font-bold">Listas</h1>
          <p className="text-muted-foreground">
            Segmenta y prioriza candidatas.
          </p>
        </header>

        {error && (
          <div className="flex items-center justify-between rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-700">
            <span>{error}</span>
            <Button variant="ghost" size="sm" onClick={() => setError(null)}>
              Cerrar
            </Button>
          </div>
        )}

        <Card>
          <CardContent className="space-y-3 p-4">
            {lists.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No hay listas. Crea una para empezar.
              </p>
            )}
            {lists.map((l) => (
              <button
                key={l.id}
                onClick={() => loadList(l.id)}
                className={
                  selectedId === l.id
                    ? "w-full rounded-md border border-primary bg-primary/10 p-3 text-left"
                    : "w-full rounded-md border p-3 text-left hover:bg-accent"
                }
              >
                <p className="text-sm font-medium">{l.name}</p>
                {l.description && (
                  <p className="text-xs text-muted-foreground">
                    {l.description}
                  </p>
                )}
              </button>
            ))}
            <div className="flex gap-2 pt-2">
              <Input
                placeholder="Nueva lista"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createList()}
              />
              <Button
                variant="secondary"
                onClick={createList}
                disabled={!newName.trim()}
              >
                <Plus />
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="lg:col-span-2">
        <Card>
          <CardHeader>
            <CardTitle>
              {selected ? selected.list.name : "Selecciona una lista"}
            </CardTitle>
            {selected && (
              <Button variant="outline" size="sm" onClick={handleExportExcel}>
                <Download className="size-4" />
                Exportar Excel
              </Button>
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            {selected && selected.companies.length === 0 && (
              <p className="text-sm text-muted-foreground">
                Esta lista está vacía.
              </p>
            )}
            {selected?.companies.map((c) => (
              <div key={c.cif ?? c.slug} className="group relative">
                <CompanyCard company={c} />
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Quitar ${c.name} de la lista`}
                      className="absolute right-3 top-3 z-10 opacity-0 transition-opacity group-hover:opacity-100"
                    >
                      <Trash2 className="size-4 text-red-500" />
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>
                        ¿Quitar de la lista?
                      </AlertDialogTitle>
                      <AlertDialogDescription>
                        {c.name} se eliminará de "{selected.list.name}" pero
                        permanecerá en el cache.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancelar</AlertDialogCancel>
                      <AlertDialogAction onClick={() => removeCompany(c.cif)}>
                        Quitar
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
