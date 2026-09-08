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

### 2026-09-08 (Mejoras Visuales y Funcionales v1.1)
- ✅ **Búsqueda Diaria**: Implementado endpoint `/api/search/daily` para descubrir automáticamente nuevos candidatos sin duplicar.
- ✅ **UI Ejecutiva**: Rediseño del Dashboard y la Ficha de Empresa para un look "Finance-Grade".
- ✅ **UX Fluida**: Implementación de `Skeletons` en la página de búsqueda y `Toaster` (sonner) para notificaciones.
- ✅ **Nativo OS**: Sincronización automática del tema (Dark/Light) según el sistema operativo del usuario.
- ✅ **Alineación de Score**: Reescritura total de `score.py` para implementar la detección de empresas familiares y validación de CNAE.

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
