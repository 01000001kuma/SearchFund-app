# PROGRESS.md — Registro de Progreso

## Estado Actual
**Fase**: Todas completadas hasta v1.1
**Proyecto completo**: 100%
**Última actualización**: 2026-09-08 (Finalización de mejoras visuales y funcionales)

## Resumen de Progreso
| Fase | Estado | Notas |
|---|---|---|
| 0. Preparación | ✅ Completada | Plan maestro definido |
| 1. Backend Core | ✅ Completada | API + models + storage + logging |
| 2. Storage | ✅ Completada | SQLite WAL + connection pool + asyncio.to_thread |
| 3. Frontend Base | ✅ Completada | React + Vite + shadcn/ui + strict TS |
| 4. Búsqueda UI | ✅ Completada | SearchBar + Results + Card + Filters + Skeletons |
| 5. Ficha Detalle | ✅ Completada | Reporte Ejecutivo + Fit Breakdown + Validation |
| 6. Listas + Exportar | ✅ Completada | Lists + PDF + Excel (headers correctos) |
| 7. LLM | ✅ Completada | Ollama lazy singleton + timeout guards + DI |
| 8. Electron | ✅ Completada | AppImage + backend lifecycle + CSP + IPC |
| 9. Pulido | ✅ Completada | 27 tests + docs + auditoría final |
| 10. Auditoría | ✅ Completada | 106 issues corregidos |

## Log de Cambios Recientes
### 2026-09-10 — Reportes Finance-Grade (v1.2 #1) ✅
- 📄 **PDF ejecutivo** (platypus): banda navy de cabecera (fecha + CONFIDENCIAL), medidor donut del score con color por banda, interpretación, desglose en mini-barras (Señales BORME / Solidez financiera), tabla de 6 criterios (puntos/máx), tabla de métricas financieras **con marcador "✓ objetivo"** frente al perfil de inversión (EBITDA 1,5–3M€, Facturación 10–15M€, margen >15%, empleados 20–200), corporativos/contacto, administradores, histórico BORME y pie con paginación y disclaimer.
- 📊 **Excel finance-grade**: título + fecha, cabecera navy con autofiltro y paneles congelados, filas alternas, **cifras numéricas** (EBITDA/Facturación € con formato) para análisis, columna Score y Clasificación coloreadas por banda, y **hoja "Leyenda"** con metodología y perfil objetivo.
- 🧪 Tests: 41/41 (+2: bandas de score y estructura finance-grade del Excel).
- Verificado end-to-end por API real: PDF 2 páginas 200 OK, Excel 2 hojas 200 OK.

### 2026-09-09 — Auditoría ronda 2 (post-refactor de frontend) ✅
- 🐛 **Bug corregido**: los filtros del panel (provincia, datos financieros, EBITDA, facturación) no aplicaban a la vista por defecto del ranking — solo a la búsqueda de texto. Ahora se aplican en cliente a cualquier lista visible, combinables con los chips de sector y banda.
- 🧹 **Código muerto eliminado** (oxlint): imports sin uso en SearchPage (Trophy, Input, QUICK_SCORE_RANGES), CompanyDetail (CalendarDays, Activity, Users, MapPin), CandidatesPage (TrendingUp) y un catch vacío en Dashboard. 25 → 16 avisos (los restantes son patrones benignos: fast-refresh de shadcn, setState en efectos de carga, AbortController en cleanup).
- ✅ Verificación completa: ruff limpio, 39/39 pytest, tsc 0 errores, build real ✓ 1957 módulos, 0 errores en oxlint.
- Lección aplicada: verificación de build con grep del mensaje de éxito (no solo tail ni tsc con caché).

### 2026-09-09 — Búsqueda diaria automática (v1.2 #6) ✅
- ⏰ **Timer systemd** `search-fund-daily.timer` (08:00 ± 5min, `Persistent=true` recupera ejecuciones perdidas si el equipo estaba apagado) + servicio oneshot `search-fund-daily.service`.
- 📜 `scripts/daily-search.sh`: llama a `POST /api/search/daily`, registra resultado en `data/daily-search.log` y si el backend no responde lo arranca y reintenta 3× (30s).
- 📊 Coste por ejecución: ~4 llamadas de cuota (1 por sector, gracias a la optimización anterior). Ejecución manual verificada: exit 0, deduplicación correcta (0 nuevas cuando ya está todo en caché), 65 empresas en BD sin duplicados.
- Verificado: ruff limpio, 38/38 pytest, tsc 0 errores, build OK, timer activo y habilitado.

### 2026-09-09 — Optimización de cuota (v1.2 #4) ✅
- 🔋 **Búsqueda con 1 llamada de API en vez de 21**: `openmercantil.search_companies` ahora construye las empresas directamente desde los ítems de `/search` (`_company_from_search_item`: nombre, CIF, slug, provincia, CNAE sección·código, acts_count, first/last_seen) **sin** pedir el detalle de cada slug. Verificado en vivo: `journalctl` muestra exactamente 1 llamada a openmercantil por búsqueda.
- El detalle (administradores, dirección, web, teléfono) se obtiene **bajo demanda** al abrir la ficha (`GET /api/company/{slug}` → 1 llamada) y ahí se re-scorea y persiste.
- Impacto: cuota 200/día ≈ 200 búsquedas (antes ≈ 9). Búsqueda diaria masiva posible.
- Trade-off documentado: en resultados de búsqueda el score es parcial (sin datos de administradores hasta abrir la ficha); se completa progresivamente.
- Tests +2 (38/38): builder desde ítem de búsqueda + casos inválidos.

### 2026-09-09 (tarde) — Auditoría de bugs y fallos
Hallazgos y correcciones:
- 🔴 **HIGH — Build Electron roto**: `package.json` incluía `electron/main.js`/`preload.js` pero los archivos reales son `main.cjs`/`preload.cjs`. La próxima build del AppImage habría salido sin proceso principal. Corregido. (Pendiente aparte: bundling del backend Python en el empaquetado — hoy requiere backend externo en :8000.)
- 🔴 **HIGH — LLM rápido inexistente**: `OLLAMA_FAST_MODEL=llama3.2:3b` ya no existe en Ollama → 404 en extracciones/scoring LLM. Fix: fallback en runtime (`LLMEngine.fast_complete` reintenta con el modelo principal si el rápido no existe) + default vacío en config (usa el modelo principal) + `.env.example` actualizado.
- 🔴 **HIGH — `candidate_search.search` ignoraba `max_analyze_per_sector`**: analizaba TODAS las empresas con LLM (minutos de espera). Fix: respeta el límite (default 8) y devuelve `analyzed`.
- 🟠 **MEDIUM — llamada desperdiciada por CIF**: `openmercantil.get_company` intentaba slug antes que CIF (1 llamada de cuota perdida por detalle). Fix: detecta CIF (`^[A-Z][0-9]{8}$`) y va directo a la búsqueda por CIF.
- 🟠 **MEDIUM — Score.tsx**: umbrales (70/50/30) desalineados de las bandas reales (80/60/40/20) y colores light-only → alineados + variantes dark.
- 🟠 **MEDIUM — CNAE en score**: keyword "SaaS" nunca matcheaba tras `.upper()`; los CNAE son códigos/letras de sección, no nombres. Fix: keywords normalizadas + matching por sección (C industria, H transporte, J IT, M servicios B2B) y enrich guarda `"{sección} · {código}"`. Re-score de 55 empresas reales en BD: distribución pasó de 9/32/24 a 21/23/21.
- 🐛 **BD: refresh escribió en clave inexistente** (`basic_info` en JSON de Company, ignorado por Pydantic) → cnae/provincia no persistían en refrescos manuales. Corregido apuntando a campos raíz del modelo; re-score aplicado.


### 2026-09-09 (Sección Filtrar Empresas — mejoras UX + filtros financieros)
- ✅ **Filtros financieros reales**: `POST/GET /api/search` acepta `ebitda_min/max` y `revenue_min/max` (€). Lógica extraída a `matches_financial_filters()` (pura y testeable).
- ✅ **FiltersBar v2**: Score por bandas reales del algoritmo (80-100/60-79/40-59/20-39/0-19, sin el hack `max:39`), EBITDA y Facturación con bandas "objetivo" (criterios Cabiedes), provincias 21→52, contador duplicado eliminado.
- ✅ **Estado en URL** (`?q=&provincia=&score=&ebitda=&rev=`): persistente al recargar y compartible; restaura la búsqueda al montar.
- ✅ **Dark mode**: banners de error/aviso con tokens semánticos (antes hardcodeados bg-red-50).
- ✅ **Tests**: +5 (32/32 pytest). tsc strict 0 errores, ruff limpio, vite build OK.
- ⚙️ **Infra**: servicio systemd `search-fund-api` reorientado de la copia obsoleta `~/Work/search-fund-proyecto` a `~/Projects/search-fund-proyecto` (copias separadas; Work quedó desfasada).
- ⚠️ **BD mixta**: 30 empresas = 10 dummy (seed_dummy.py, financieros manuales) + 20 reales OpenMercantil (sin EBITDA → score solo-BORME, cap ~55). **Decisión: se dejan tal cual**; al acabar el desarrollo se configurarán todas las APIs (EmpresiF, etc.) para búsquedas 100% reales.
- ⚠️ **Pendiente descubierto**: `OLLAMA_FAST_MODEL=llama3.2:3b` ya no existe en Ollama (actuales: llama3.1:8b, gemma3:4b, glm-5.3:cloud). Sin `backend/.env` — crear al configurar APIs.
- ✅ **Bug de provincia corregido** (openmercantil.py): el endpoint `/search` devuelve provincia/CNAE/acts_count, pero el código lo descartaba y consultaba el detalle por slug (que NO trae provincia y consume cuota). Ahora se fusiona el ítem de búsqueda con el detalle (cacheado y fresco) vía `_enrich_with_search_item()`. Orchestrator ahora mapea `cnae`. Las 20 empresas reales cacheadas refrescadas con provincia/CNAE (1 llamada de search, sin gastar detalle). Verificado: provincia+score filtran OK sobre datos reales; EBITDA/Facturación → 0 hasta EmpresiF/datos manuales.
- ✅ **Chips de ranking (v2)**: Bajo/Medio/Alto ahora son un navegador del ranking completo de la BD (independiente de la búsqueda de texto): siempre visibles con conteo en vivo desde `GET /api/stats` (`score_distribution` por SQL) y al pulsar muestran la lista de empresas de ese rango vía `GET /api/companies` (ahora soporta `max_score`+`has_financial_data` y `total` filtrado real; nuevo `database.count_companies()`). Vista `?rango=` persistente en URL; una búsqueda de texto la sustituye. Filtros EBITDA/facturación aplicados en cliente sobre la lista de ranking. Menú lateral: ítem renombrado a "Filtrar Empresas". `score.py` limpio de ruff (E701). Tests 36/36. UI chips: etiqueta "Ranking de adquisición" entre Filtros y los chips; colores por banda (Bajo rojo / Medio naranja / Alto verde) con fondo sólido y texto negro, badge de conteo con fondo blanco; estado activo con ✓ (evita confusión con el hover).


### 2026-09-08 (Mejoras Visuales y Funcionales v1.1)
- ✅ **Búsqueda Diaria**: Implementado endpoint `/api/search/daily` para descubrir automáticamente nuevos candidatos sin duplicar.
- ✅ **UI Ejecutiva**: Rediseño del Dashboard y la Ficha de Empresa para un look "Finance-Grade".
- ✅ **UX Fluida**: Implementación de `Skeletons` en la página de búsqueda y `Toaster` (sonner) para notificaciones.
- ✅ **Nativo OS**: Sincronización automática del tema (Dark/Light) según el sistema operativo del usuario.
- ✅ **Alineación de Score**: Reescritura total de `score.py` para implementar la detección de empresas familiares y validación de CNAE.
- ⚙️ **Pulido de Textos (En proceso)**: Optimización de títulos y descripciones en Dashboard para mayor profesionalidad.

### 2026-09-03 (Checkpoint v1.0 + auditoría exhaustiva)
- ✅ **Auditoría exhaustiva completada**: 106 issues identificados y corregidos.
- ✅ **Sincronización de Infra**: SQLite pool, Electron lifecycle, CSP, CORS, asyncio.to_thread.
- ✅ **AppImage regenerado**: 113MB con todos los cambios.

## Decisiones Tomadas
1. **Backend**: Python FastAPI.
2. **Frontend**: React + Vite + shadcn/ui.
3. **Desktop**: Electron (AppImage portable).
4. **LLM**: Ollama híbrido (local/nube).
5. **Datos**: OpenMercantil (BORME) + EmpresiF (futuro).
6. **Diseño**: UI Ejecutiva adaptable al OS.
7. **Persistencia**: SQLite WAL mode + connection pool por thread.

## Próximos Pasos (Post-MVP)
1. **GitHub**: Push una vez resuelto el problema de la cuenta.
2. **EmpresiF**: Integrar API de balances financieros (está el placeholder listo).
3. **Multi-OS**: Generar builds .exe y .app en entornos nativos.

## Estado de Tests
| Test Suite | Resultado | Notas |
|------------|-----------|-------|
| pytest (backend) | ✅ 27/27 | score, export, database, API |
| E2E endpoints | ✅ 10/10 | health, stats, sources, companies, search, lists, llm |
| ruff (lint) | ✅ All passed | backend/ + tests/ |
| TypeScript strict | ✅ 0 errores | tsc --noEmit |
| Vite build | ✅ OK | 21 chunks, code splitting |
