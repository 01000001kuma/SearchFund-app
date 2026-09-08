import { useState, useRef, useEffect, type FormEvent } from "react"
import { Send, Loader2, Bot, User, Building2, X } from "lucide-react"
import { api } from "@/lib/api"
import type { ChatMessage, LLMHealth } from "@/lib/types"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user"
  return (
    <div className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
          <Bot className="size-4" />
        </div>
      )}
      <div
        className={cn(
          "max-w-[75%] rounded-lg px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted",
        )}
      >
        {msg.content}
      </div>
      {isUser && (
        <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted">
          <User className="size-4" />
        </div>
      )}
    </div>
  )
}

let _msgId = 0

export function ChatPage() {
  const [messages, setMessages] = useState<(ChatMessage & { id: number })[]>([])
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [contextCif, setContextCif] = useState<string | null>(null)
  const [contextName, setContextName] = useState<string | null>(null)
  const [cifInput, setCifInput] = useState("")
  const [llmHealth, setLlmHealth] = useState<LLMHealth | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const messagesRef = useRef(messages)
  const abortRef = useRef<AbortController | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  messagesRef.current = messages

  useEffect(() => {
    const ctrl = new AbortController()
    api.llmHealth({ signal: ctrl.signal }).then((r) => setLlmHealth(r.llm)).catch(() => {})
    return () => ctrl.abort()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  useEffect(() => {
    return () => abortRef.current?.abort()
  }, [])

  async function handleSend(e: FormEvent) {
    e.preventDefault()
    const text = input.trim()
    if (!text || loading) return

    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl

    const userMsg = { role: "user" as const, content: text, id: ++_msgId }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setError(null)
    setLoading(true)

    try {
      const res = await api.chat({
        message: text,
        context_cif: contextCif,
        history: [...messagesRef.current, userMsg].slice(-8),
      }, { signal: ctrl.signal })
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.reply, id: ++_msgId },
      ])
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return
      setError(err instanceof Error ? err.message : "Error al contactar el LLM")
    } finally {
      setLoading(false)
    }
  }

  function handleSetContext() {
    const cif = cifInput.trim()
    if (!cif) return
    setContextCif(cif)
    setContextName(cif)
    setCifInput("")
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `Contexto cargado para la empresa ${cif}. Pregúntame lo que quieras sobre ella.`,
        id: ++_msgId,
      },
    ])
  }

  function handleClearContext() {
    setContextCif(null)
    setContextName(null)
  }

  return (
    <div className="flex h-[calc(100vh-3rem)] flex-col">
      <header className="flex items-center justify-between border-b pb-4">
        <div>
          <h1 className="text-2xl font-bold">Agente</h1>
          <p className="text-sm text-muted-foreground">
            Pideme lo que quieras.
          </p>
        </div>
        {llmHealth && (
          <Badge variant={llmHealth.configured ? "default" : "destructive"}>
            {llmHealth.configured
              ? `${llmHealth.provider} activo`
              : "Agente no disponible"}
          </Badge>
        )}
      </header>

      <div className="flex items-center gap-2 border-b py-2">
        <Building2 className="size-4 text-muted-foreground" />
        {contextCif ? (
          <div className="flex items-center gap-2">
            <Badge variant="secondary">
              Contexto: {contextName}
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleClearContext}
              className="h-6 px-2"
              aria-label="Limpiar contexto"
            >
              <X className="size-3" />
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Input
              placeholder="CIF de empresa (opcional)"
              value={cifInput}
              onChange={(e) => setCifInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSetContext()}
              className="h-7 w-48 text-xs"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={handleSetContext}
              disabled={!cifInput.trim()}
              className="h-7"
            >
              Cargar contexto
            </Button>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto py-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <Bot className="mb-4 size-12 opacity-30" />
            <p className="text-lg font-medium">Empieza a conversar</p>
            <p className="mt-1 mb-6 text-sm text-muted-foreground">
              Analiza empresas · Compara candidatas · Genera informes · Busca por sectores y provincias · Refina criterios de busqueda
            </p>
            <form onSubmit={handleSend} className="flex w-full max-w-lg gap-2" aria-label="Agente">
              <Input
                ref={inputRef}
                placeholder={
                  contextCif
                    ? `Pregunta sobre ${contextCif}...`
                    : "Preguntame..."
                }
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={loading}
                className="flex-1"
                aria-label="Mensaje para el Agente"
              />
              <Button type="submit" disabled={loading || !input.trim()} aria-label="Enviar mensaje" className="bg-emerald-600 hover:bg-emerald-700">
                {loading ? <Loader2 className="animate-spin" /> : <Send />}
              </Button>
            </form>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
                  <Bot className="size-4" />
                </div>
                <div className="flex items-center gap-2 rounded-lg bg-muted px-4 py-3">
                  <Loader2 className="size-4 animate-spin" />
                  <span className="text-sm text-muted-foreground">Pensando...</span>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {error && (
        <div className="mb-2 flex items-center justify-between text-sm text-red-600">
          <span>{error}</span>
          <Button variant="ghost" size="sm" onClick={() => setError(null)}>
            Cerrar
          </Button>
        </div>
      )}

      {messages.length > 0 && (
        <form onSubmit={handleSend} className="flex gap-2 border-t pt-3" aria-label="Agente">
          <Input
          placeholder={
            contextCif
              ? `Pregunta sobre ${contextCif}...`
              : "Preguntame..."
          }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            className="flex-1"
            aria-label="Mensaje para el Agente"
          />
          <Button type="submit" disabled={loading || !input.trim()} aria-label="Enviar mensaje" className="bg-emerald-600 hover:bg-emerald-700">
            {loading ? <Loader2 className="animate-spin" /> : <Send />}
          </Button>
        </form>
      )}
    </div>
  )
}
