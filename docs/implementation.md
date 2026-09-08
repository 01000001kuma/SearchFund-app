# Plan de Implementación — Multi-Source Data Architecture

## Resumen
Implementar arquitectura de datos multi fuente que permita:
- Hoy: Usar OpenMercantil (BORME) gratis
- Mañana: Integrar EmpreciF (pagado) automáticamente
- Futuro: Añadir más fuentes fácilmente

---

## Estructura de Archivos

```
search-fund-tool/
├── backend/
│   ├── __init__.py
│   ├── main.py                    # FastAPI server
│   ├── config.py                  # Configuración
│   ├── models/
│   │   ├── __init__.py
│   │   ├── company.py             # Modelo de empresa
│   │   ├── financial.py           # Modelo financiero (EBITDA)
│   │   └── borme.py              # Modelo BORME
│   ├── data_sources/
│   │   ├── __init__.py
│   │   ├── base.py               # Clase base abstracta
│   │   ├── orchestrator.py       # Coordinador de fuentes
│   │   ├── openmercantil.py      # Fuente BORME (ya creada)
│   │   ├── empresief.py          # Fuente EmpreciF (placeholder)
│   │   └── web_search.py         # Fallback web scraping
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── score.py              # Algoritmo de score (actualizar)
│   │   └── search.py             # Motor de búsqueda
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py           # SQLite connection
│   │   └── repositories.py       # CRUD operations
│   └── exports/
│       ├── __init__.py
│       ├── pdf.py                # Exportación PDF
│       └── excel.py              # Exportación Excel
├── frontend/                     # Fase 2
├── electron/                     # Fase 3
├── data/                         # Datos persistentes
├── config/                       # Configuración
├── tests/                        # Tests
├── README.md
├── LICENSE
├── .gitignore
├── requirements.txt
└── pyproject.toml
```

---

## Fase 1: Data Models

### 1.1 company.py
```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Administrator(BaseModel):
    name: str
    role: str
    since: Optional[str] = None
    until: Optional[str] = None

class BormeData(BaseModel):
    """Datos del BORME (siempre disponibles)"""
    acts_count: int = 0
    last_activity: Optional[str] = None
    acts: List[dict] = []

class FinancialData(BaseModel):
    """Datos financieros (disponibles según fuente)"""
    revenue: Optional[float] = None          # Facturación anual
    ebitda: Optional[float] = None           # EBITDA
    ebitda_margin: Optional[float] = None    # Margen EBITDA (%)
    net_profit: Optional[float] = None       # Beneficio neto
    employees: Optional[int] = None          # Número de empleados
    source: Optional[str] = None             # "empresief", "web", "manual"
    year: Optional[int] = None               # Año de los datos
    last_updated: Optional[datetime] = None

class Company(BaseModel):
    """Modelo completo de empresa"""
    # Identificación
    cif: str
    name: str
    slug: str
    
    # Datos legales (OpenMercantil)
    legal_form: Optional[str] = None
    status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    founded_date: Optional[str] = None
    
    # Administradores
    administrators: List[Administrator] = []
    
    # Datos BORME
    borme: BormeData = BormeData()
    
    # Datos financieros (multi-source)
    financial: FinancialData = FinancialData()
    
    # Score
    score: Optional[float] = None
    score_breakdown: Optional[dict] = None
    
    # Metadata
    last_updated: datetime = datetime.now()
    data_sources: List[str] = []  # ["openmercantil", "empresief"]
```

### 1.2 financial.py
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class FinancialMetrics(BaseModel):
    """Métricas financieras para scoring"""
    revenue: Optional[float] = None
    ebitda: Optional[float] = None
    ebitda_margin: Optional[float] = None
    revenue_growth: Optional[float] = None  # Crecimiento anual (%)
    profit_margin: Optional[float] = None
    
    def is_complete(self) -> bool:
        """Verificar si hay datos suficientes para scoring financiero"""
        return self.revenue is not None and self.ebitda is not None
    
    def get_score_range(self) -> str:
        """Determinar rango de scoring según datos disponibles"""
        if self.ebitda and self.revenue:
            if 1_500_000 <= self.ebitda <= 3_000_000:
                return "optimal"  # 1.5M - 3M EBITDA
            elif 500_000 <= self.ebitda < 1_500_000:
                return "acceptable"  # 500k - 1.5M
            elif self.ebitda > 3_000_000:
                return "large"  # > 3M (puede ser demasiado grande)
            else:
                return "small"  # < 500k
        return "unknown"
```

---

## Fase 2: Data Sources Layer

### 2.1 base.py (Abstract Base)
```python
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

class DataSource(ABC):
    """Clase base abstracta para todas las fuentes de datos"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre de la fuente"""
        pass
    
    @property
    @abstractmethod
    def is_free(self) -> bool:
        """Si es gratuita"""
        pass
    
    @abstractmethod
    async def get_company(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Obtener datos de empresa"""
        pass
    
    @abstractmethod
    async def search_companies(self, query: str) -> list:
        """Buscar empresas"""
        pass
    
    def is_configured(self) -> bool:
        """Verificar si la fuente está configurada"""
        return True
```

### 2.2 orchestrator.py (Multi-Source Coordinator)
```python
from typing import Optional, Dict, Any, List
from .base import DataSource
from .openmercantil import OpenMercantilSource
from .empresief import EmpresiFSource
from .web_search import WebSearchSource

class DataOrchestrator:
    """Coordina múltiples fuentes de datos"""
    
    def __init__(self):
        self.sources: List[DataSource] = [
            OpenMercantilSource(),    # Siempre activo (gratis)
            EmpresiFSource(),         # Activo cuando haya suscripción
            WebSearchSource()         # Fallback
        ]
    
    async def get_company(self, cif: str) -> Dict[str, Any]:
        """Obtener datos completos de empresa desde múltiples fuentes"""
        result = {
            'cif': cif,
            'data_sources': [],
            'borme': None,
            'financial': None
        }
        
        for source in self.sources:
            if not source.is_configured():
                continue
            
            try:
                data = await source.get_company(cif)
                if data:
                    result['data_sources'].append(source.name)
                    
                    # Merge BORME data
                    if 'borme' in data:
                        result['borme'] = data['borme']
                    
                    # Merge financial data (EmpresiF tiene prioridad)
                    if 'financial' in data:
                        if result['financial'] is None:
                            result['financial'] = data['financial']
                        elif source.name == 'empresief':
                            # EmpresiF sobrescribe si está disponible
                            result['financial'] = data['financial']
            
            except Exception as e:
                print(f"Error en fuente {source.name}: {e}")
                continue
        
        return result
    
    async def search(self, query: str, filters: Dict = None) -> List[Dict]:
        """Buscar empresas en todas las fuentes configuradas"""
        results = []
        
        for source in self.sources:
            if not source.is_configured():
                continue
            
            try:
                source_results = await source.search_companies(query)
                results.extend(source_results)
            except Exception as e:
                print(f"Error buscando en {source.name}: {e}")
                continue
        
        return results
```

### 2.3 empresief.py (Placeholder)
```python
from .base import DataSource
from typing import Optional, Dict, Any

class EmpresiFSource(DataSource):
    """Fuente de datos financieros (placeholder para futura integración)"""
    
    def __init__(self):
        self.api_key = None  # Se configurará cuando haya suscripción
        self.base_url = "https://api.empresief.com/v1"  # URL ficticia
    
    @property
    def name(self) -> str:
        return "empresief"
    
    @property
    def is_free(self) -> bool:
        return False  # Requiere suscripción
    
    def is_configured(self) -> bool:
        """Solo activo cuando haya API key configurada"""
        return self.api_key is not None
    
    async def get_company(self, cif: str) -> Optional[Dict[str, Any]]:
        """Obtener datos financieros de EmpresiF"""
        if not self.is_configured():
            return None
        
        # TODO: Implementar cuando tengamos API key
        # Por ahora retorna None
        return None
    
    async def search_companies(self, query: str) -> list:
        """Buscar empresas (no disponible en EmpresiF)"""
        return []
    
    def configure(self, api_key: str):
        """Configurar API key de EmpresiF"""
        self.api_key = api_key
```

### 2.4 web_search.py (Fallback)
```python
from .base import DataSource
from typing import Optional, Dict, Any
import httpx
import re

class WebSearchSource(DataSource):
    """Fallback: buscar datos financieros en web"""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def is_free(self) -> bool:
        return True
    
    async def get_company(self, cif: str) -> Optional[Dict[str, Any]]:
        """Buscar datos financieros básicos en web"""
        # TODO: Implementar scraping básico
        # Por ahora retorna None
        return None
    
    async def search_companies(self, query: str) -> list:
        """Buscar empresas en web"""
        return []
    
    async def get_financials_from_web(self, company_name: str) -> Optional[Dict]:
        """Buscar EBITDA/facturación en web de la empresa"""
        # Implementación futura: scraping de página web de la empresa
        return None
```

---

## Fase 3: Score Algorithm (Actualizado)

### 3.1 score.py (Multi-Source)
```python
from typing import Dict, Any, Optional
from ..models.company import Company

class ScoreCalculator:
    """Calcula score de candidatura usando datos multi-source"""
    
    # Pesos del score
    WEIGHTS = {
        'borme': 0.6,      # 60% datos BORME
        'financial': 0.4   # 40% datos financieros
    }
    
    def calculate(self, company: Company) -> Dict[str, Any]:
        """Calcular score completo con desglose"""
        
        # Score BORME (siempre disponible)
        borme_score = self._calculate_borme_score(company)
        
        # Score financiero (solo si hay datos)
        financial_score = None
        if company.financial and company.financial.is_complete():
            financial_score = self._calculate_financial_score(company)
        
        # Score final
        if financial_score is not None:
            final_score = (
                borme_score * self.WEIGHTS['borme'] +
                financial_score * self.WEIGHTS['financial']
            )
        else:
            # Sin datos financieros, score solo BORME
            final_score = borme_score
        
        return {
            'total': round(final_score, 1),
            'borme': round(borme_score, 1),
            'financial': round(financial_score, 1) if financial_score else None,
            'has_financial_data': financial_score is not None,
            'interpretation': self._get_interpretation(final_score)
        }
    
    def _calculate_borme_score(self, company: Company) -> float:
        """Score basado solo en datos BORME"""
        # Implementación existente...
        pass
    
    def _calculate_financial_score(self, company: Company) -> float:
        """Score basado en datos financieros"""
        financial = company.financial
        score = 0
        
        # Rango de EBITDA óptimo (1.5M - 3M)
        if financial.ebitda:
            if 1_500_000 <= financial.ebitda <= 3_000_000:
                score += 40  # Puntuación máxima
            elif 500_000 <= financial.ebitda < 1_500_000:
                score += 25
            elif financial.ebitda > 3_000_000:
                score += 20  # Puede ser demasiado grande
            else:
                score += 10
        
        # Margen EBITDA
        if financial.ebitda_margin:
            if financial.ebitda_margin >= 15:
                score += 30
            elif financial.ebitda_margin >= 10:
                score += 20
            else:
                score += 10
        
        # Crecimiento (si está disponible)
        if financial.revenue_growth:
            if financial.revenue_growth >= 10:
                score += 30
            elif financial.revenue_growth >= 5:
                score += 20
            else:
                score += 10
        
        return min(score, 100)
    
    def _get_interpretation(self, score: float) -> str:
        """Interpretación del score"""
        if score >= 80:
            return "MUY BUEN CANDIDATO - Alta probabilidad de transición"
        elif score >= 60:
            return "BUEN CANDIDATO - Posible candidato a investigar"
        elif score >= 40:
            return "CANDIDATO MODERADO - Requiere más información"
        elif score >= 20:
            return "CANDIDATO BAJO - Poca probabilidad de venta"
        else:
            return "NO RECOMENDADO - No parece candidato"
```

---

## Fase 4: FastAPI Endpoints

### 4.1 main.py
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .data_sources.orchestrator import DataOrchestrator
from .engines.score import ScoreCalculator
from .storage.database import Database

app = FastAPI(title="Search Fund Tool API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instances
orchestrator = DataOrchestrator()
score_calculator = ScoreCalculator()
database = Database()

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/company/{cif}")
async def get_company(cif: str):
    """Obtener empresa completa (multi-source)"""
    data = await orchestrator.get_company(cif)
    if not data:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    # Calcular score
    company = Company(**data)
    score = score_calculator.calculate(company)
    company.score = score['total']
    company.score_breakdown = score
    
    # Guardar en cache
    await database.save_company(company)
    
    return company

@app.get("/api/search")
async def search_companies(
    q: str = None,
    province: str = None,
    min_score: float = 0,
    has_financial_data: bool = None
):
    """Buscar empresas con filtros"""
    results = await orchestrator.search(q)
    
    # Aplicar filtros
    filtered = []
    for result in results:
        company = Company(**result)
        score = score_calculator.calculate(company)
        company.score = score['total']
        
        if company.score >= min_score:
            if province and company.province != province:
                continue
            if has_financial_data is not None:
                if has_financial_data and not company.financial.is_complete():
                    continue
            filtered.append(company)
    
    # Ordenar por score
    filtered.sort(key=lambda x: x.score, reverse=True)
    
    return filtered

@app.post("/api/company/{cif}/financial")
async def update_financial_data(cif: str, financial: FinancialData):
    """Actualizar datos financieros manualmente"""
    company = await database.get_company(cif)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    company.financial = financial
    company.financial.source = "manual"
    await database.save_company(company)
    
    return {"status": "updated"}
```

---

## Fase 5: SQLite Storage

### 5.1 database.py
```python
import sqlite3
import json
from typing import Optional, List
from ..models.company import Company

class Database:
    def __init__(self, db_path: str = "data/search_fund.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Inicializar tablas"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS companies (
                    cif TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    score REAL,
                    last_updated TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS list_items (
                    list_id INTEGER,
                    cif TEXT,
                    added_at TIMESTAMP,
                    FOREIGN KEY (list_id) REFERENCES lists(id),
                    PRIMARY KEY (list_id, cif)
                )
            """)
    
    async def save_company(self, company: Company):
        """Guardar empresa en cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO companies (cif, data, score, last_updated) VALUES (?, ?, ?, ?)",
                (company.cif, company.json(), company.score, company.last_updated)
            )
    
    async def get_company(self, cif: str) -> Optional[Company]:
        """Obtener empresa del cache"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT data FROM companies WHERE cif = ?", (cif,)
            ).fetchone()
            if row:
                return Company.parse_raw(row[0])
        return None
    
    async def search_companies(self, filters: dict) -> List[Company]:
        """Buscar empresas con filtros"""
        # Implementación de búsqueda con filtros
        pass
```

---

## Fase 6: Tests

### 6.1 test_data_orchestrator.py
```python
import pytest
from backend.data_sources.orchestrator import DataOrchestrator

@pytest.mark.asyncio
async def test_get_company_mercadona():
    """Test obtener empresa conocida"""
    orchestrator = DataOrchestrator()
    data = await orchestrator.get_company("B87078978")
    
    assert data is not None
    assert 'borme' in data
    assert data['cif'] == "B87078978"

@pytest.mark.asyncio
async def test_score_with_financial_data():
    """Test score con datos financieros"""
    from backend.models.company import Company, FinancialData
    
    company = Company(
        cif="B12345678",
        name="Test Company",
        slug="test-company",
        financial=FinancialData(
            revenue=12_000_000,
            ebitda=2_000_000,
            ebitda_margin=16.7
        )
    )
    
    calculator = ScoreCalculator()
    score = calculator.calculate(company)
    
    assert score['has_financial_data'] == True
    assert score['financial'] is not None
```

---

## Checklist de Implementación

### Fase 1: Data Models ✅
- [x] company.py
- [x] financial.py
- [x] borme.py (incluido en company.py)

### Fase 2: Data Sources ✅
- [x] base.py (abstract)
- [x] orchestrator.py
- [x] openmercantil.py (actualizar)
- [x] empresief.py (placeholder)
- [x] web_search.py (placeholder)

### Fase 3: Engines ⏳ (parcial)
- [x] score.py (actualizar con financial)
- [ ] search.py (usado vía main.py endpoint, sin módulo dedicado aún)

### Fase 4: Storage ✅
- [x] database.py
- [x] repositories.py (folders)

### Fase 5: API ✅
- [x] main.py
- [x] Endpoints de búsqueda
- [x] Endpoints de empresa

### Fase 6: Tests ⏳ (pendiente de formalizar)
- [ ] test_data_orchestrator.py
- [ ] test_score.py
- [ ] test_api.py

---

## Orden de Implementación

1. **Primero**: Data Models (company.py, financial.py)
2. **Segundo**: Data Sources (orchestrator.py, actualizar openmercantil.py)
3. **Tercero**: Score Algorithm (actualizar con financial)
4. **Cuarto**: Storage (database.py)
5. **Quinto**: API (main.py)
6. **Sexto**: Tests

---

**Última actualización**: 2026-09-02 (checkpoint)
**Estado**: Implementado y probado (ver PLAN.md para el checklist de fases 1-9 completo)

> Nota: este documento detalla la arquitectura backend (fases 0-1). El estado real por fases
> (frontend, caché, contacto, exportar, LLM, Electron) está en **PLAN.md** y **PROGRESS.md**.

### Mejoras no planificadas ya integradas (aumentan el % de avance)
- ✅ **Caché por slug con índice** en SQLite (`get_company_by_slug`, columna `slug` indexada, migración automática). Reutiliza empresas ya vistas sin gastar calls de OpenMercantil.
- ✅ **Fallback a caché local en búsquedas**: si OpenMercantil devuelve 429 (cuota diaria), `database.search_local_companies` devuelve coincidencias de la base local con warning "Mostrando resultados de tu caché local".
- ✅ **Preservación de datos financieros manuales** al volver a abrir una ficha (no se pierden el EBITDA/facturación introducidos).
- ✅ **Datos de contacto por candidato**: campos `website`, `phone`, `email` en `Company` + endpoint `POST /api/company/{cif}/contact` + sección en la ficha (dirección, web clicable, teléfono, email, notas). Teléfono/email reales los rellenará el LLM (F7) buscando en internet.
- ✅ **Límites de firma**: todas las fuentes aceptan `cached_lookup`; `search` robusto a query vacío/null.
- ✅ **Checkpoint de bugs 2026-09-02**: 27/27 pruebas de endpoints pasan.
