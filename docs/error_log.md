# ERRORS.md — Registro de Errores y Soluciones

## Errores Pendientes

### OpenMercantil: Cuota diaria superada (429)
- **Estado**: ⚠️ Límite alcanzado (200 peticiones/día en plan free)
- **Problema**: Cada búsqueda + cada obtención de empresa = 2 peticiones. Cuota se agota rápido.
- **Solución a corto**: esperar al día siguiente, o pagar plan Profesional (~15€/mes)
- **Solución implementada**: ✅ Caché por slug + fallback local con warning visible
  - `search_companies` reutiliza empresas guardadas sin gastar llamada de detalle
  - `get_company` devuelve desde caché sin llamar a la API
  - Fallback: si búsqueda devuelve 429, muestra coincidencias del caché local con warning
  - Frontend muestra banner amarillo cuando cuota agotada
- **Archivos**: openmercantil.py, orchestrator.py, main.py, database.py, SearchPage.tsx

### GitHub - Problema con cuenta
- **Estado**: Pendiente
- **Problema**: Usuario tiene problema temporal con su cuenta de GitHub
- **Impacto**: No se puede hacer push al repositorio
- **Solución**: Cuando se resuelva, ejecutar `gh auth login` y hacer push

### EmpresiF - Sin suscripción
- **Estado**: Pendiente
- **Problema**: EmpresiF requiere suscripción (~30-50€/mes) para datos financieros
- **Impacto**: Sin EBITDA real, score solo usa datos BORME (60%)
- **Solución**: Campo manual para EBITDA, o integrar cuando haya suscripción

---

## Errores Resueltos (Sesión Auditoría 2026-09-03)

### Excel export column mismatch (CRITICAL)
- **Problema**: `EXCEL_HEADERS` tenía 22 columnas pero `row` solo 21 valores. "EBITDA Score" no tenía dato, causando desalineación de columnas desde la posición 15.
- **Solución**: Eliminado header "EBITDA Score" (no hay datos para esa columna).
- **Archivo**: backend/engines/export.py

### global_exception_handler swallows HTTPException (CRITICAL)
- **Problema**: El handler capturaba TODAS las excepciones incluyendo `HTTPException` de FastAPI (404, 422), re-envolviéndolas como 500 genéricos.
- **Solución**: `if isinstance(exc, HTTPException): raise exc` antes de loggear.
- **Archivo**: backend/main.py

### clear_cache orphans list_items (HIGH)
- **Problema**: `clear_cache()` borraba `companies` y `list_items` pero no `lists`, dejando listas huérfanas.
- **Solución**: Ahora borra `list_items` → `lists` → `companies` en orden.
- **Archivo**: backend/storage/database.py

### remove_from_list missing CIF validation (HIGH)
- **Problema**: `DELETE /api/lists/{id}/items/{cif}` no validaba formato CIF (a diferencia de otros endpoints).
- **Solución**: Añadida validación `_CIF_RE.match(cif)` → 400 si inválido.
- **Archivo**: backend/main.py

### LLM singleton crash at import (HIGH)
- **Problema**: `llm_engine = LLMEngine()` se ejecutaba al importar el módulo. Si `LLM_PROVIDER=openai` sin `OPENAI_API_KEY`, el módulo entero fallaba al cargar.
- **Solución**: Lazy singleton con `get_llm_engine()` — solo instancia al primer uso.
- **Archivos**: backend/engines/llm.py, __init__.py, candidate_search.py, contact_enrichment.py, main.py

### FinancialMetrics dead code (MEDIUM)
- **Problema**: `FinancialMetrics` class (98 líneas) nunca se usaba — duplicaba lógica de `ScoreCalculator._calculate_financial_score()`.
- **Solución**: Clase eliminada del módulo financial.py.
- **Archivo**: backend/models/financial.py

### CompanyList unused on backend (MEDIUM)
- **Problema**: `CompanyList` model (21 líneas) existía pero nunca se usaba — lists se guardan como dicts raw.
- **Solución**: Clase eliminada de company.py, removida de exports.
- **Archivos**: backend/models/company.py, models/__init__.py

### AddToListDialog loading per-list (MEDIUM)
- **Problema**: Un solo `loading` boolean deshabilitaba TODOS los botones "Añadir" al hacer click en uno.
- **Solución**: `loadingId: number | null` — solo el botón clickeado muestra spinner.
- **Archivo**: frontend/src/components/AddToListDialog.tsx

### "use client" en shadcn components (LOW)
- **Problema**: 5 componentes shadcn tenían `"use client"` (Next.js) que no aplica a Vite.
- **Solución**: Directiva eliminada de alert-dialog, select, avatar, tabs, separator.
- **Archivos**: frontend/src/components/ui/*.tsx

---

## Errores Resueltos (Sesión Original 2026-09-03)

### Lint score.py - 7 bare except + imports
- **Solución**: Bare excepts → `(ValueError, IndexError)`, imports limpiados
- **Archivo**: backend/engines/score.py

### LLM endpoints sin timeout guard
- **Solución**: `asyncio.wait_for(30s)` health, `asyncio.wait_for(120s)` chat
- **Archivo**: backend/main.py

### Errores 500 sin formato consistente
- **Solución**: Global exception handler → `{"detail": "Error interno: ..."}`
- **Archivo**: backend/main.py

### CORS incompleto
- **Solución**: Añadido `localhost:5174`, `null`, `file://`, `allow_origin_regex`
- **Archivo**: backend/main.py

### N+1 HTTP calls en búsquedas
- **Solución**: `asyncio.gather` con semáforo de 5 conexiones paralelas
- **Archivo**: backend/data_sources/openmercantil.py

### RateLimitError silenciado
- **Solución**: Re-lanza `RateLimitError` en lugar de devolver `None`
- **Archivo**: backend/data_sources/openmercantil.py

### Búsqueda con min_score=0.0 no se aplicaba
- **Solución**: Cambiado a `if min_score is not None:`
- **Archivo**: backend/main.py

### DELETE list sin transacción
- **Solución**: Envuelto en `BEGIN TRANSACTION` / `COMMIT`
- **Archivo**: backend/storage/database.py

### clear_cache no cascadeaba
- **Solución**: Ahora borra `list_items` antes de `companies`
- **Archivo**: backend/storage/database.py

### INSERT OR REPLACE sobrescribía created_at
- **Solución**: SELECT previo + `COALESCE` para preservar `created_at`
- **Archivo**: backend/storage/database.py

### Database() múltiples en candidate_search
- **Solución**: Reutilizar una sola instancia de `Database()`
- **Archivo**: backend/engines/candidate_search.py

### Búsqueda con query null → 500
- **Solución**: Normaliza query (`or ""`), devuelve 0 resultados si vacía
- **Archivo**: backend/main.py, backend/storage/database.py

### Pérdida de datos financieros al reabrir empresa
- **Solución**: Preserva datos financieros existentes al re-obtener de fuentes
- **Archivo**: backend/main.py

### pydantic-core incompatible con Python 3.14
- **Solución**: Actualizar a pydantic 2.13.5
- **Archivo**: requirements.txt

### Rate limit 429 silencioso → warning visible
- **Solución**: `RateLimitError` + banner amarillo en frontend
- **Archivos**: openmercantil.py, orchestrator.py, main.py, SearchPage.tsx

---

## Limitaciones Conocidas

### Sin datos financieros reales (EBITDA)
- **Estado**: RESUELTO con campo manual + arquitectura multi-source
- **Score**: Si no hay EBITDA → solo BORME (100%). Si hay → combinado (60% BORME + 40% Financial)

### GitHub no conecta
- **Estado**: Pendiente resolución de cuenta

### Rendimiento LLM en CPU
- **Estado**: Conocido — sin GPU, ~7-8 tok/s
- **Mitigación**: Timeout guards (30s health, 120s chat)
- **Solución a largo**: API de pago (env var `LLM_PROVIDER=openai|anthropic`)

### EmpresiF sin integrar
- **Estado**: Placeholder — requiere suscripción
- **Workaround**: Campo manual para EBITDA/facturación

---

## Debug
Si hay errores al ejecutar la app:
1. Logs backend: `journalctl --user -u search-fund-api.service --no-pager -n 20`
2. Logs frontend: `journalctl --user -u search-fund-frontend.service --no-pager -n 20`
3. Verificar OpenMercantil API: `curl http://localhost:8000/api/health`
4. Verificar SQLite: `ls -la data/search_fund.db`
5. Verificar Ollama: `curl http://localhost:11434/api/tags`
6. Verificar logs Python: stdout del uvicorn (logging.basicConfig configurado)
