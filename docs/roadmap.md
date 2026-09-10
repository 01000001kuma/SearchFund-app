# Plan Maestro — Search Fund Tool v1.0

## Resumen
Aplicación de escritorio que busca PYMES españolas candidatas a adquisición para search funds. Detecta automáticamente empresas con probabilidad de venta (relevo generacional, tamaño adecuado, señales BORME).

## Objetivo
Encontrar candidatas para la reunión con José Cabiedes y vender la herramienta a empresas de search fund.

## Contacto Objetivo
- **Nombre**: José Alfonso Martín Gutiérrez de Cabiedes
- **Socio**: Luis Antonio
- **Empresa**: Inversiones Cabiedes SL (CIF B87078978)
- **Dirección**: Castellana 210, Madrid
- **Teléfono**: 913 433 242
- **Email**: juan@cabiedesandpartners.com
- **Web**: cabiedesandpartners.com
- **Ticket**: hasta 1 M€, EBITDA 1-3 M€

## Arquitectura Final
- **Backend**: Python FastAPI (24 endpoints REST)
- **Frontend**: React + Vite + TypeScript + shadcn/ui
- **Desktop**: Electron (cross-platform: Linux AppImage, Windows .exe, Mac .dmg)
- **LLM**: Ollama híbrido — `llama3.1:8b` (chat) + `llama3.2:3b` (extracciones), sin GPU (~7-8 tok/s)
- **Datos**: OpenMercantil API (BORME) + caché local + fallback offline
- **Persistencia**: SQLite (WAL mode, connection pool por thread, busy_timeout 5s)
- **Diseño**: shadcn/ui (20 componentes, ligero)
- **Entorno**: Omarchy (Arch-based, Python 3.14.7, pydantic 2.13.5)

## Fuentes de Datos
| Fuente | Qué da | Coste | Estado | EBITDA |
|---|---|---|---|---|
| OpenMercantil API | BORME: admin changes, company info, CNAE, succession signals | Gratis (200 req/día) | ✅ Disponible | ❌ NO |
| EmpresiF | Balances: facturación, EBITDA, evolución financiera | ~30-50€/mes | ⏸️ Placeholder | ✅ SÍ |
| Ollama | LLM local para análisis, reportes, búsqueda conversacional | Gratis | ✅ Operativo (8b+3b) | N/A |
| API LLM de pago | Búsquedas exhaustivas (opcional) | ~0.01€/búsqueda | ⚙️ Configurable | N/A |

### ⚠️ NOTA CRÍTICA: EBITDA
OpenMercantil NO da datos financieros. El score actual solo usa datos BORME.
**Solución**: Campo manual para EBITDA + filtros financieros con datos introducidos.

## Algoritmo de Score de Venta (Alineado v1.1)
```
CRITERIOS (ponderados):
├── BORME (60%):
│   ├── Edad administrador (Proxy Don/Doña) = +30 puntos
│   ├── Antigüedad sin cambios BORME (>5 años) = +15 puntos
│   ├── Empresa familiar (Mismo apellido admins) = +20 puntos
│   ├── Sin consejo externo (No roles "Consejo") = +10 puntos
│   ├── CNAE compatible (Industrial, Logística, B2B, etc.) = +10 puntos
│   └── Actividad BORME reciente (<1 año) = +25 puntos
└── Financial (40%):
    ├── EBITDA en rango (1.5-3M€ = +40, 0.5-1.5M = +25, >3M = +20)
    ├── Facturación en rango (10-15M€ = +30, 5-10M = +20)
    └── Margen EBITDA (>20% = +30, >15% = +20)

TOTAL: Score 0-100
  80-100: MUY BUEN CANDIDATO
  60-79:  BUEN CANDIDATO
  40-59:  CANDIDATO MODERADO
  20-39:  CANDIDATO BAJO
  0-19:   NO RECOMENDADO
```

## Funcionalidades MVP
1. ✅ Búsqueda por filtros (sector, provincia, edad admin, score min/max)
2. ✅ Score de venta (algoritmo BORME + Financial)
3. ✅ Tarjetas de resultado (CompanyCard con React.memo)
4. ✅ Ficha detallada de empresa (con abort cleanup)
5. ✅ Listas/rankings personales (CRUD completo)
6. ✅ Exportar PDF/Excel con leyenda de scores
7. ✅ Búsqueda programada diaria (architectural, no UI)
8. ✅ LLM: chat conversacional, búsqueda de candidatas, enriquecimiento de contactos
9. ✅ Persistencia completa en SQLite (WAL, connection pool)
10. ✅ Electron AppImage portable (113MB)

## Estructura del Proyecto
```
search-fund-tool/
├── backend/
│   ├── main.py              ← 24 endpoints, CORS ampliado, global exception handler, CIF validation
│   ├── config.py            ← Settings/LLMSettings híbridos, CORS_ORIGINS env var
│   ├── __init__.py          ← logging.basicConfig
│   ├── engines/
│   │   ├── score.py         ← algoritmo scoring (single computation, cached parts)
│   │   ├── llm.py           ← motor LLM híbrido (lazy singleton, fast_provider=3b)
│   │   ├── contact_enrichment.py ← DuckDuckGo + LLM (DI pattern)
│   │   ├── candidate_search.py   ← búsqueda por subagentes (DI pattern)
│   │   └── export.py        ← PDF (reportlab) + Excel (openpyxl, headers match data)
│   ├── models/
│   │   ├── company.py       ← Company, BormeData, Administrator (dead code removed)
│   │   ├── financial.py     ← FinancialData (FinancialMetrics removed)
│   │   └── search.py        ← SearchRequest (con min/max_score)
│   ├── storage/
│   │   └── database.py      ← SQLite: WAL, busy_timeout, asyncio.to_thread, LIKE escape, province index
│   └── data_sources/
│       ├── base.py           ← DataSource ABC + close() base method
│       ├── openmercantil.py  ← BORME + cache, asyncio.gather, orphan singleton removed
│       ├── orchestrator.py   ← coordinador multi-source, logging (not print)
│       ├── web_search.py     ← DuckDuckGo
│       └── empresief.py      ← placeholder (close() inherited from base)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/           ← shadcn/ui (20 componentes, "use client" removed)
│   │   │   ├── Layout.tsx
│   │   │   ├── Score.tsx
│   │   │   ├── CompanyCard.tsx  ← React.memo, formatDate, formatEuro, accessibility
│   │   │   ├── FiltersBar.tsx   ← provincia, score min/max, financial
│   │   │   ├── AddToListDialog.tsx ← loading per-list, isError state
│   │   │   └── ErrorBoundary.tsx  ← React error boundary
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx     ← AbortController + cleanup
│   │   │   ├── SearchPage.tsx    ← AbortController, debounce 400ms, aria attributes
│   │   │   ├── CompanyDetail.tsx ← AbortController, blob download PDF, financeIsError
│   │   │   ├── ListsPage.tsx     ← AbortController, useCallback, blob download Excel
│   │   │   ├── ChatPage.tsx      ← AbortController, messagesRef stale closure fix, unique IDs
│   │   │   └── CandidatesPage.tsx ← AbortController
│   │   ├── lib/
│   │   │   ├── api.ts           ← AbortSignal everywhere, Electron IPC, getExportUrl helper
│   │   │   ├── types.ts
│   │   │   └── utils.ts         ← formatEuro exportado
│   │   └── main.tsx
│   ├── electron/
│   │   ├── main.js          ← Backend lifecycle (spawn uvicorn, waitForBackend, stopBackend), CSP, IPC
│   │   └── preload.js       ← contextBridge: isElectron, platform, getApiBase
│   ├── package.json         ← electron-builder config, author, homepage, engines
│   └── tsconfig.app.json    ← strict: true
├── tests/
│   ├── conftest.py
│   ├── test_score.py        ← 7 tests
│   ├── test_export.py       ← 3 tests
│   ├── test_database.py     ← 10 tests
│   └── test_api.py          ← 7 tests
├── data/                    ← SQLite database
├── release/
│   └── Search Fund Tool-1.0.0.AppImage (113MB)
├── PLAN.md
├── PROGRESS.md
├── ERRORS.md
└── README.md
```

## Endpoints (24 totales)

### Core
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/health` | Estado de fuentes y Ollama |
| GET | `/api/stats` | Estadísticas de la base |
| GET | `/api/sources` | Fuentes de datos disponibles |
| GET | `/api/search-history` | Historial de búsquedas (últimas 500) |

### Companies
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/companies` | Listado paginado con filtros |
| GET | `/api/company/{id}` | Detalle de empresa (slug o CIF) |
| GET | `/api/company/{id}/score` | Score desglosado |
| GET | `/api/company/{id}/export/pdf` | Export PDF (async, abortable) |
| POST | `/api/company/{id}/financial` | Guardar datos financieros (CIF validated) |
| POST | `/api/company/{id}/contact` | Editar contacto (CIF validated) |
| POST | `/api/company/{id}/enrich` | Enriquecer contactos (DuckDuckGo + LLM) |

### Search
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/search` | Búsqueda simple |
| POST | `/api/search` | Búsqueda avanzada con filtros (min/max_score) |

### Lists
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/lists` | Todas las listas |
| POST | `/api/lists` | Crear lista |
| GET | `/api/lists/{id}` | Detalle de lista con empresas |
| POST | `/api/lists/{id}/items` | Añadir empresa a lista (409 si duplicado) |
| DELETE | `/api/lists/{id}/items/{cif}` | Quitar empresa de lista (CIF validated) |
| DELETE | `/api/lists/{id}` | Eliminar lista |
| GET | `/api/lists/{id}/export/xlsx` | Export Excel de lista (async, abortable) |
| GET | `/api/export/companies.xlsx` | Export todas las empresas |

### LLM
| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/llm/health` | Estado de Ollama (timeout 30s) |
| GET | `/api/llm/models` | Info del modelo activo |
| POST | `/api/llm/chat` | Chat conversacional (timeout 120s) |
| POST | `/api/llm/search-candidates` | Búsqueda + scoring por LLM |

### Cache
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/cache/clear` | Limpiar toda la caché (companies + lists + list_items) |

## Fases de Desarrollo

### Fase 1: Backend Core ✅
- [x] Crear estructura del proyecto
- [x] FastAPI server con 24 endpoints
- [x] OpenMercantil client con cache por slug
- [x] Score algorithm (BORME + Financial, single computation)
- [x] Global exception handler (re-raises HTTPException, no swallows)
- [x] CORS ampliado (null, file://, allow_origin_regex, PATCH)

### Fase 2: Storage ✅
- [x] SQLite WAL mode + busy_timeout 5s
- [x] Connection pool por thread (threading.local as instance attr)
- [x] Company cache (slug indexed, INSERT OR REPLACE preserva created_at)
- [x] Lists CRUD (transacciones, cascade delete)
- [x] Search history (retención 500 registros)
- [x] LIKE escape para % y _
- [x] Province column + index for SQL filtering
- [x] asyncio.to_thread en todas las operaciones

### Fase 3: Frontend Base ✅
- [x] React + Vite setup
- [x] shadcn/ui installation (20 componentes)
- [x] Routing + Layout
- [x] Tipos TypeScript (strict: true)

### Fase 4: Búsqueda UI ✅
- [x] SearchBar component
- [x] FiltersBar (21 provincias, score min/max, financial)
- [x] Results grid
- [x] CompanyCard (React.memo, formatDate, formatEuro, accessibility)
- [x] Debounce 400ms en filtros

### Fase 5: Ficha Detalle ✅
- [x] CompanyDetail page (AbortController, blob download PDF)
- [x] BORME timeline
- [x] Financial data display + inline edit
- [x] Contact info (website, phone, email)
- [x] Export PDF button
- [x] Number input constraints (min, max, step)

### Fase 6: Listas + Exportar ✅
- [x] Lists CRUD (AbortController, useCallback)
- [x] PDF generation (reportlab, sanitized filenames)
- [x] Excel generation (openpyxl, headers match data)
- [x] Score legend in exports
- [x] 409 on duplicate list item
- [x] Blob download for exports

### Fase 7: LLM ✅
- [x] Ollama local (8b chat + 3b extracciones)
- [x] Híbrido: Ollama + preparado para API de pago
- [x] Lazy singleton (no crash at import if API key missing)
- [x] Conversational search (chat endpoint)
- [x] Search candidates with fit_score + rationale
- [x] Contact enrichment (DuckDuckGo + LLM)
- [x] LLM timeout guards (health 30s, chat 120s)
- [x] GET /api/llm/models (info de modelos)

### Fase 8: Electron ✅
- [x] Electron setup (main.js + preload.js) en `frontend/electron/`
- [x] Backend lifecycle (spawn uvicorn, waitForBackend, stopBackend)
- [x] CSP headers via onHeadersReceived
- [x] IPC handlers (get-api-base, get-platform)
- [x] Cross-platform packaging config (electron-builder)
- [x] Scripts: electron:dev, electron:build, electron:build:linux
- [x] AppImage Linux: `release/Search Fund Tool-1.0.0.AppImage` (113MB)

### Fase 9: Pulido ✅
- [x] Tests formales (27/27 pytest)
- [x] E2E tests (21/21)
- [x] Architecture review exhaustiva (106 issues identificados)
- [x] Todos los issues corregidos (12 Critical, 23 High, 35 Medium, 26 Low)
- [x] Documentation (PLAN.md, PROGRESS.md, ERRORS.md, README.md)

### Fase 10: Auditoría Arquitectónica ✅
- [x] **CRITICAL**: SQLite connection pool por thread + WAL mode + busy_timeout
- [x] **CRITICAL**: Electron backend lifecycle (spawn, waitForBackend, stopBackend)
- [x] **CRITICAL**: CSP headers en Electron
- [x] **CRITICAL**: CORS para Electron (null, file://, allow_origin_regex)
- [x] **CRITICAL**: asyncio.to_thread en exports + DB
- [x] **CRITICAL**: global_exception_handler re-raises HTTPException
- [x] **CRITICAL**: Excel export headers mismatch (22→21)
- [x] **HIGH**: Dependency injection (CandidateSearch, ContactEnricher)
- [x] **HIGH**: AbortControllers en todos los pages
- [x] **HIGH**: strict: true + Error Boundary + React.lazy
- [x] **HIGH**: Electron asar reduction + IPC exports
- [x] **HIGH**: Python logging module
- [x] **HIGH**: LLM lazy singleton (no crash at import)
- [x] **HIGH**: clear_cache() borra list_items + lists + companies
- [x] **HIGH**: remove_from_list CIF validation
- [x] **MEDIUM**: LIKE escape, Pydantic v2, input validation
- [x] **MEDIUM**: Province SQL filter, debounce 400ms
- [x] **MEDIUM**: FinancialMetrics + CompanyList dead code removed
- [x] **MEDIUM**: AddToListDialog per-list loading
- [x] **LOW**: "use client" removed, React.memo, orphan singleton

## Decisiones Pendientes
- [ ] **CRÍTICO: Rediseño de Reportes Ejecutivos**: Crear plantillas profesionales (Finance-Grade) para exportaciones de PDF y Excel. Revisar backend (`export.py`) y frontend para que las tablas de análisis y EBITDA sean herramientas de decisión profesional para Cabiedes.
- [ ] Autenticar `gh` para push a GitHub (problema de cuenta)
- [ ] Decidir fecha de reunión con Cabiedes (para deadline del MVP)
- [ ] Distribución multiplataforma (builds .exe/.app en otra máquina)
- [ ] Integrar EmpresiF (pendiente suscripción ~30-50€/mes)

## Estado Global (checkpoint 2026-09-03 — v1.0 completo + auditoría exhaustiva)
- **Proyecto completo (todas las fases): 100%**
- **Tests**: 27/27 pytest, 10/10 E2E endpoints, ruff limpio, TS strict 0 errores
- **AppImage**: `release/Search Fund Tool-1.0.0.AppImage` (113MB, regenerado)
- **Issues de auditoría**: 106 identificados → 0 pendientes (12C + 23A + 35M + 26B + 10 test gaps)
- **Pendiente solo**: GitHub push (problema de cuenta), builds .exe/.app (en otra máquina)
- **No urgentes**: Import CSV, filter config vía LLM, búsqueda programada, EmpresiF
## Fase v1.2 — Mejoras y Optimizaciones (propuesta 2026-09-09)

### Prioridad alta (negocio)
1. ~~**Reportes PDF/Excel Finance-Grade**~~ ✅ HECHOS (2026-09-10): PDF ejecutivo con medidor, criterios, métricas vs objetivo y BORME; Excel estilizado con números reales + hoja Leyenda.
2. **EmpresiF real** — completar `empresief.py` (placeholder listo) para EBITDA/facturación reales → filtros financieros y scores 100% operativos.
3. **Empaquetado completo del AppImage** — bundling del backend Python (`extraResources` + arranque sin venv externo) y regenerar release v1.1 con los fixes.

### Prioridad media (rendimiento/cuota)
4. **Ahorro de cuota OpenMercantil**: construir empresas desde los ítems de `/search` (traen provincia/CNAE/acts) y pedir detalle solo bajo demanda → ~1 llamada por búsqueda en vez de 21.
5. **Modelo LLM**: instalar/encadenar un modelo pequeño local (gemma3:4b ya descargado) o API de pago para extracciones.
6. ~~**Búsqueda diaria automática**~~ ✅ HECHA (2026-09-09): timer systemd + scripts/daily-search.sh.
7. **Re-score en cascada**: al guardar datos financieros de una empresa, recalcular y persistir su score (ya lo hace) + opción de recalcular todo el caché.
8. **Import CSV** de empresas/contactos.

### Prioridad baja (pulido)
9. Paginación "cargar más" en la vista de ranking.
10. Contador de miembros por lista en el sidebar; marcar en el diálogo las listas que ya contienen la empresa.
11. Historial de búsquedas accesible desde la UI (`/api/search-history` ya existe).
12. Filtro por sector/CNAE en el panel de filtros (backend + UI).
## Fase v1.3 — CRM de outreach y adquisición (propuesta tras research 2026-09-10)

Comparativa del producto contra cómo trabajan los searchers reales
(docs/research/sourcing-espana.md). Hoy cubrimos: buy box (filtros),
universo (caché), priorización por riesgo de sucesión (score) y dictamen.
Lo que falta para acompañar el flujo completo de un searcher:

1. **CRM de outreach** 🌟 — la pieza más grande que falta. Por empresa:
   registrar toques multicanal (email/teléfono/LinkedIn/carta/visita),
   estado del pipeline (prospecto → contactado → conversación → LOI →
   adquisición/descarte), notas de cada toque y próximas acciones con
   recordatorio. Base técnica: tabla `outreach_touches` + vista
   "pipeline" en el Panel de Control.
2. **Presets de buy box** — guardar el conjunto de filtros con nombre
   (ej. "Industria Euskadi 1-3M") y recargarlos en un clic.
3. **Directorio de search funds España** — los ~50 fondos del research
   como referencia estática (mapeo competitivo + potenciales coinversores).
4. **Enriquecimiento de contactos**: hoy DDG+LLM (básico); añadir
   LinkedIn como fuente (Sales Navigator manual o API) y captura de
   "team pages" de webs corporativas.
5. **Fuentes financieras**: EmpresiF (ya con placeholder) — alternativa
   o complemento: SABI/Informa/Axesor (suscripción). El informe PDF ya
   está preparado para crecer con los datos.
6. **Export de outreach**: Excel con el pipeline de toques por empresa.
### v1.3.1 — Transcripción local de llamadas/reuniones (aprobada, por implementar)

**Coste: 0€/mes.** Whisper local (open-source, MIT) integrado en la app —
sin nube, sin suscripciones. Plaud Note solo es opción para la calle.

Flujo (desde la ficha de empresa):
1. Botón "Nueva llamada" → grabar con el micro del PC (MediaRecorder)
   o "Subir audio" (móvil, Plaud, grabadora de calle)
2. Protocolo de apertura dictado antes de la llamada: nombre de empresa,
   contacto y teléfono — el Agente lo parsea y precarga el toque
3. Transcripción local con `faster-whisper` (modelo `base`/`small`,
   español, ~1GB RAM; en la i7 de 2011 una llamada de 15 min se
   transcribe en ~5-10 min en segundo plano)
4. El Agente (gemma3:4b local) destila del transcript: contacto
   confirmado, resumen, señales, siguiente paso + fecha
5. Se registra como "toque" en el pipeline (tabla `outreach_touches`)

Tareas técnicas: `pip install faster-whisper` en el venv · endpoint
`POST /api/company/{cif}/transcribe` (multipart audio) · UI: grabadora
con MediaRecorder + botón de subida · temporal: guardar audios en
`data/audio/` y limpiar tras transcribir · modelo descargable bajo
demanda (base ≈500MB, small ≈1GB).

Legalidad: grabar conversaciones en las que se participa es legal en
España; el procesamiento es local (nada sale de la máquina).

### v1.3.2 — Localización en Google Maps (aprobada, por implementar)

- En la ficha de empresa y en las tarjetas: botón "Cómo llegar" que
  abre Google Maps con la dirección registrada:
  `https://www.google.com/maps/dir/?api=1&destination=<dirección codificada>`
- Si no hay dirección, construir con ciudad + provincia; si tampoco,
  ocultar el botón
- (Futuro opcional): mini-mapa embebido en la ficha (iframe de Google
  Maps embed, sin API key usando el enlace directo)
