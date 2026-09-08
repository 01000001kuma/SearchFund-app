# CONTEXTO.md — Información Completa del Proyecto

## Resumen Ejecutivo
Proyecto para crear una herramienta de escritorio que busque PYMES españolas candidatas a adquisición por search funds. Incluye dossier profesional para contactar a José Cabiedes (Inversiones Cabiedes SL).

---

## 1. Perfil del Usuario
*Emprendedor serial con experiencia en startups, logística y SEO. Objetivo: Adquirir una empresa con EBITDA 1-3M€.*

---

## 2. Datos de Cabiedes
*Socio director José Alfonso Martín Gutiérrez de Cabiedes. Enfoque en disciplina, transición generacional y coinversión.*

---

## 3. Criterios de Búsqueda (Empresa Objetivo)
- **Financieros**: Facturación 10-15M€, EBITDA 1.5-3M€.
- **Estructurales**: Relevo generacional (Fundador >55 años), Empresa Familiar, Sin consejo externo.
- **Sectores**: Industrial, Logística, Servicios B2B, SaaS nicho.

---

## 4. Herramienta: Search Fund Tool

### Arquitectura Actual (v1.1)
- **Backend**: Python FastAPI (Endpoints REST, Scoring avanzado).
- **Frontend**: React + Vite + TypeScript + shadcn/ui (UI Ejecutiva).
- **Desktop**: Electron (AppImage portable).
- **LLM**: Ollama (local) con modelos híbridos (8b chat / 3b extracción).
- **Datos**: OpenMercantil (BORME) + Caché SQLite local.

### Algoritmo de Score (Alineado v1.1)
Combine datos BORME (60%) y Financieros (40%):
- **BORME**: Edad admin, estabilidad, empresa familiar, consejo externo, CNAE, actividad reciente.
- **Financial**: EBITDA, Facturación, Margen.

### Funcionalidades Implementadas
- [x] Búsqueda avanzada y filtrado.
- [x] Scoring profesional alineado al dossier.
- [x] Ficha de empresa con análisis de Fit.
- [x] Gestión de listas y rankings.
- [x] Exportación de reportes ejecutivos (PDF/Excel).
- [x] Chat con LLM y enriquecimiento de contactos.
- [x] Búsqueda Diaria automatizada (Sincronización de nuevos candidatos).
- [x] Interfaz Adaptativa (Modo Oscuro/Claro según OS).

---

## 5. Estado Global del Proyecto (Check-point Final)
- **Desarrollo**: 100% completado (MVP+).
- **Calidad**: Auditoría arquitectónica finalizada (106 issues resueltos).
- **Distribución**: AppImage lista para distribución portable.

**Última actualización**: 2026-09-08
