# Search Fund Tool

`,```text
Professional Desktop Application for SME Acquisition Targeting
```

Aplicación de escritorio diseñada para identificar y analizar PYMES españolas candidatas a adquisición para search funds. El sistema automatiza la detección de señales de venta mediante el análisis de BORME y datos financieros, aplicando un algoritmo de scoring profesional.

## 🚀 Características

- **Búsqueda Multi-Fuente**: Integración con OpenMercantil (BORME) con sistema de caché local y fallback robusto.
- **Sincronización Diaria**: Automatización de descubrimiento de nuevos candidatos basada en sectores configurables.
- **Professional Scoring**: Algoritmo alineado con criterios de inversión (Estructura familiar, CNAE, Edad, EBITDA).
- **Gestión Financiera**: Persistencia local de métricas clave (EBITDA, Facturación, Márgenes).
- **LLM Engine**: Chat conversacional y enriquecimiento de contactos mediante Ollama (local) o APIs externas.
- **Exportación Ejecutiva**: Generación de reportes en PDF y Excel listos para presentación a inversores.
- **UI Ejecutiva**: Interfaz moderna basada en `shadcn/ui` con soporte nativo de temas del OS.
- **Distribución Electron**: Empaquetado como AppImage portable para Linux, Windows y macOS.

## 🏗️ Arquitectura y Estructura

El proyecto sigue una separación clara entre la capa de datos, la lógica de negocio (engines) y la interfaz de usuario.

```text
search-fund-tool/
├── .github/                # Gobernanza y plantillas de Issues/PRs
├── backend/                # Python FastAPI Core
│   ├── data_sources/       # Abstracciones de fuentes (OpenMercantil, EmpresiF)
│   ├── engines/            # Lógica de Scoring, LLM y Exportación
│   ├── models/             # Esquemas de datos Pydantic
│   └── storage/            # Persistencia SQLite Async (WAL Mode)
├── frontend/               # React + TS + Vite + Electron
│   ├── src/                # Componentes, Páginas y Lógica de API
│   └── electron/           # Configuración del proceso principal y preload
├── docs/                   # Documentación de Ingeniería
│   ├── context.md          # Contexto y visión del proyecto
│   ├── implementation.md   # Plan de arquitectura y diseño
│   ├── progress.md         # Registro detallado de hitos
│   ├── roadmap.md          # Planificación de futuras versiones
│   └── error_log.md        # Registro de incidencias y soluciones
├── tests/                  # Suite de pruebas (pytest)
├── .gitignore              # Definición de archivos ignorados
├── CONTRIBUTING.md         # Guía de contribución profesional
└── LICENSE                 # Licencia MIT
```

## 🛠️ Requisitos

- **Python 3.11+**
- **Node.js 18+**
- **Ollama** (Opcional, para LLM local)

## 📦 Instalación y Ejecución

### Backend
```bash
cd search-fund-tool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Electron (Desktop)
```bash
cd frontend
npm run electron:dev
```

## 📊 Score de Venta (Algoritmo)

El score es una métrica ponderada que combina señales legales y financieras:
**Final Score = (BORME Signal * 0.6) + (Financial Signal * 0.4)**

| Rango | Interpretación | Acción Recomendada |
|-------|----------------|-------------------|
| 80-100 | MUY BUEN CANDIDATO | Contacto inmediato / Due Diligence |
| 60-79 | BUEN CANDIDATO | Investigación profunda |
| 40-59 | CANDIDATO MODERADO | Monitorizar señales |
| 20-39 | CANDIDATO BAJO | Archivar |
| 0-19 | NO RECOMENDADO | Descartar |

## ⚙️ Configuración

El proyecto utiliza variables de entorno para su configuración. Se recomienda crear un archivo `.env` basado en el ejemplo proporcionado.

| Variable | Descripción | Ejemplo |
|----------|-------------|----------|
| `LLM_PROVIDER` | Proveedor de LLM | `ollama` \| `openai` |
| `OLLAMA_MODEL` | Modelo de Chat | `llama3.1:8b` |
| `DB_PATH` | Ruta base de datos | `data/search_fund.db` |
| `SEARCH_SECTORS` | Sectores de interés | `transportes,industrial` |

## 🧪 Calidad y Pruebas

El proyecto mantiene un estándar de calidad riguroso:
- **Backend**: 27 tests unitarios y de integración vía `pytest`.
- **Frontend**: Tipado estricto con TypeScript y validación de builds con Vite.
- **Auditoría**: 100+ issues corregidos en la fase de pulido.

## 📄 Licencia

Distribuido bajo la Licencia MIT. Ver [LICENSE](./LICENSE) para más detalles.
