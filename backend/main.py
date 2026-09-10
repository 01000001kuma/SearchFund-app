from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timezone
import asyncio
import logging
import re
import uvicorn

from .data_sources.orchestrator import DataOrchestrator
from .engines.score import ScoreCalculator
from .engines.llm import get_llm_engine, LLMError
from .engines.candidate_search import CandidateSearch
from .engines.contact_enrichment import contact_enricher
from .engines.export import export_pdf, export_excel, _fmt_eur
from .storage.database import Database
from .models.financial import FinancialData
from .models.company import Company
from .config import settings
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

_CIF_RE = re.compile(r"^[A-Z0-9]{9}$")


def _sanitize_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await orchestrator.close()
    database.close()


app = FastAPI(
    title="Search Fund Tool API",
    description="API para buscar PYMES españolas candidatas a adquisición",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^app://|file://|null$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        raise exc
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )


orchestrator = DataOrchestrator()
score_calculator = ScoreCalculator()
database = Database()
candidate_search = CandidateSearch(database=database, orchestrator=orchestrator)


# ==================== MODELS ====================

class SearchRequest(BaseModel):
    query: Optional[str] = None
    province: Optional[str] = None
    min_score: Optional[float] = Field(None, ge=0, le=100)
    max_score: Optional[float] = Field(None, ge=0, le=100)
    has_financial_data: Optional[bool] = None
    ebitda_min: Optional[float] = Field(None, ge=0)
    ebitda_max: Optional[float] = Field(None, ge=0)
    revenue_min: Optional[float] = Field(None, ge=0)
    revenue_max: Optional[float] = Field(None, ge=0)
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)


def matches_financial_filters(company: Company, request: SearchRequest) -> bool:
    """True si la empresa pasa los filtros financieros (EBITDA/facturación en €).
    Si se pide un rango y el dato no está disponible, la empresa se excluye.
    """
    fin = company.financial
    if request.ebitda_min is not None and (fin.ebitda is None or fin.ebitda < request.ebitda_min):
        return False
    if request.ebitda_max is not None and (fin.ebitda is None or fin.ebitda > request.ebitda_max):
        return False
    if request.revenue_min is not None and (fin.revenue is None or fin.revenue < request.revenue_min):
        return False
    if request.revenue_max is not None and (fin.revenue is None or fin.revenue > request.revenue_max):
        return False
    return True


class ListCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class AddToListRequest(BaseModel):
    cif: str = Field(..., min_length=9, max_length=9)
    notes: Optional[str] = None


class FinancialUpdateRequest(BaseModel):
    revenue: Optional[float] = Field(None, ge=0)
    ebitda: Optional[float] = None
    ebitda_margin: Optional[float] = Field(None, ge=0, le=100)
    employees: Optional[int] = Field(None, ge=0)
    year: Optional[int] = Field(None, ge=1900, le=2100)


class CompanyNotesRequest(BaseModel):
    notes: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    context_cif: Optional[str] = None
    history: Optional[List[Dict]] = Field(default_factory=list)


class CandidateSearchRequest(BaseModel):
    sectors: Optional[List[str]] = None
    max_analyze: Optional[int] = Field(8, ge=1, le=50)


# ==================== ENDPOINTS ====================

@app.get("/")
async def root():
    return {
        "name": "Search Fund Tool API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/api/health")
async def health():
    sources = orchestrator.get_available_sources()
    stats = await database.get_stats()
    return {"status": "ok", "sources": sources, "stats": stats}


# ==================== EMPRESAS ====================

@app.get("/api/company/{identifier}")
async def get_company(identifier: str):
    cached = await database.get_company(identifier)
    if cached:
        return cached

    cached = await database.get_company_by_slug(identifier)
    if cached:
        return cached

    company = await orchestrator.get_company(identifier)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    existing = await database.get_company(company.cif)
    if existing and existing.financial.has_partial_data():
        company.financial = existing.financial

    score = score_calculator.calculate(company)
    company.score = score['total']
    company.score_breakdown = score

    await database.save_company(company)
    return company


@app.post("/api/company/{cif}/financial")
async def update_financial_data(cif: str, financial: FinancialUpdateRequest):
    if not _CIF_RE.match(cif):
        raise HTTPException(status_code=400, detail="CIF inválido (formato: letra + 8 dígitos)")

    company = await database.get_company(cif)
    if not company:
        company = await orchestrator.get_company(cif)
        if not company:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    company.financial = FinancialData(
        revenue=financial.revenue,
        ebitda=financial.ebitda,
        ebitda_margin=financial.ebitda_margin,
        employees=financial.employees,
        year=financial.year,
        source="manual",
        last_updated=datetime.now(timezone.utc),
    )

    score = score_calculator.calculate(company)
    company.score = score['total']
    company.score_breakdown = score

    await database.save_company(company)

    return {
        "status": "updated",
        "cif": cif,
        "financial": company.financial,
        "new_score": score,
    }


@app.post("/api/company/{cif}/contact")
async def update_company_contact(cif: str, data: CompanyNotesRequest):
    if not _CIF_RE.match(cif):
        raise HTTPException(status_code=400, detail="CIF inválido")

    company = await database.get_company(cif)
    if not company:
        company = await orchestrator.get_company(cif)
        if not company:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    if data.website is not None:
        company.website = data.website
    if data.phone is not None:
        company.phone = data.phone
    if data.email is not None:
        company.email = data.email
    if data.notes is not None:
        company.notes = data.notes

    await database.save_company(company)

    return {
        "status": "updated",
        "cif": cif,
        "contact": {
            "website": company.website,
            "phone": company.phone,
            "email": company.email,
        },
        "notes": company.notes,
    }


@app.get("/api/company/{cif}/score")
async def get_company_score(cif: str):
    company = await database.get_company(cif)
    if not company:
        company = await orchestrator.get_company(cif)
        if not company:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    score = score_calculator.calculate(company)
    indicators = score_calculator.get_score_indicators(company)

    return {"cif": cif, "score": score, "indicators": indicators}


@app.post("/api/company/{cif}/dictamen")
async def generate_dictamen(cif: str):
    """Dictamen narrativo del Agente (LLM) sobre la empresa, persistido en el caché."""
    if not _CIF_RE.match(cif):
        raise HTTPException(status_code=400, detail="CIF inválido")

    company = await database.get_company(cif)
    if not company:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Perfil de la empresa para el LLM
    admins = "; ".join(
        f"{a.name} ({a.role or 'administrador'}, desde {a.since or '?'})"
        for a in company.administrators[:6]
    ) or "no consta"
    acts = company.borme.acts[:8]
    acts_text = "; ".join(
        f"{(a.get('date') or '')[:10]}: {a.get('type') or a.get('title', '')}"
        for a in acts
    ) or "sin actos recientes"
    fin = company.financial
    fin_txt = (
        f"EBITDA {_fmt_eur(fin.ebitda)}, facturación {_fmt_eur(fin.revenue)}"
        if fin.ebitda is not None and fin.revenue is not None
        else "sin datos financieros (pendientes de fuentes)"
    )
    prompt = (
        "Eres un analista senior de un search fund español. Redacta un dictamen en 2 párrafos "
        "(máximo 120 palabras en total) sobre esta empresa para un inversor.\n"
        "Párrafo 1: síntesis de las señales del Registro Mercantil (antigüedad, administradores, actos).\n"
        "Párrafo 2: encaje con el perfil objetivo (facturación 10-15M€, EBITDA 1,5-3M€; si faltan datos, "
        "dilo) y recomendación de siguiente paso.\n\n"
        "Español sobrio y profesional. NO inventes datos que no se den.\n\n"
        f"EMPRESA\n"
        f"Nombre: {company.name}\n"
        f"CIF: {company.cif} | Forma: {company.legal_form or '?'} | Provincia: {company.province or '?'}\n"
        f"Antigüedad: {company.get_age_years() or '?'} años\n"
        f"Administradores: {admins}\n"
        f"Actos BORME: {company.borme.acts_count} (última actividad {company.borme.last_activity or '?'}). Últimos: {acts_text}\n"
        f"Financiero: {fin_txt}\n"
    )

    try:
        opinion = await asyncio.wait_for(
            get_llm_engine().fast_complete(prompt, temperature=0.4, max_tokens=320),
            timeout=180.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="El Agente tardó demasiado (180s); reintenta")
    except LLMError as e:
        raise HTTPException(status_code=503, detail=f"Agente no disponible: {e}")

    company.agent_opinion = opinion.strip()
    score = score_calculator.calculate(company)
    company.score = score["total"]
    company.score_breakdown = score
    await database.save_company(company)
    return {"status": "generated", "opinion": opinion}


@app.get("/api/company/{cif}/score")

@app.get("/api/company/{cif}/export/pdf")
async def export_company_pdf(cif: str):
    if not _CIF_RE.match(cif):
        raise HTTPException(status_code=400, detail="CIF inválido")

    company = await database.get_company(cif)
    if not company:
        company = await orchestrator.get_company(cif)
        if not company:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    pdf = await asyncio.to_thread(export_pdf, company)
    safe_cif = _sanitize_filename(company.cif)
    filename = f"informe_{safe_cif}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(pdf)),
        },
    )


@app.get("/api/lists/{list_id}/export/xlsx")
async def export_list_excel(list_id: int):
    list_info = await database.get_list(list_id)
    if not list_info:
        raise HTTPException(status_code=404, detail="Lista no encontrada")

    companies = await database.get_list_items(list_id)
    xlsx = await asyncio.to_thread(export_excel, companies)
    filename = f"lista_{list_id}.xlsx"
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(xlsx)),
        },
    )


@app.get("/api/export/companies.xlsx")
async def export_all_companies_excel():
    companies = await database.get_all_companies()
    xlsx = await asyncio.to_thread(export_excel, companies)
    return Response(
        content=xlsx,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="candidatas.xlsx"',
            "Content-Length": str(len(xlsx)),
        },
    )


# ==================== BÚSQUEDA ====================

@app.post("/api/search")
async def search_companies(request: SearchRequest):
    async def cached_lookup(slug: str):
        return await database.get_company_by_slug(slug)

    await orchestrator.reset_rate_limit()

    query = (request.query or "").strip()
    if not query:
        return {
            "total": 0,
            "offset": request.offset,
            "limit": request.limit,
            "results": [],
            "warning": None,
            "score_distribution": {"bajo": 0, "medio": 0, "alto": 0},
        }

    companies = await orchestrator.search(query, cached_lookup=cached_lookup)

    warning = None
    if orchestrator.rate_limit_hit and not companies:
        warning = "OpenMercantil alcanzó su cuota diaria. Mostrando resultados de tu caché local."
        companies = await database.search_local_companies(query, request.limit)

    results = []
    distribution = {"bajo": 0, "medio": 0, "alto": 0}
    for company in companies:
        score = score_calculator.calculate(company)
        company.score = score['total']
        company.score_breakdown = score

        # Filtros independientes del score primero (la distribución de bandas
        # debe contar todas las empresas encontradas, sin aplicar el filtro de score)
        if request.province and company.province != request.province:
            continue
        if request.has_financial_data is not None:
            if request.has_financial_data and not company.has_financial_data():
                continue
            if not request.has_financial_data and company.has_financial_data():
                continue

        if not matches_financial_filters(company, request):
            continue

        s = company.score or 0
        if s >= 60:
            distribution["alto"] += 1
        elif s >= 40:
            distribution["medio"] += 1
        else:
            distribution["bajo"] += 1

        if request.min_score is not None and company.score < request.min_score:
            continue
        if request.max_score is not None and company.score > request.max_score:
            continue

        results.append(company)

    results.sort(key=lambda x: x.score or 0, reverse=True)
    paginated = results[request.offset:request.offset + request.limit]

    for company in paginated:
        await database.save_company(company)

    await database.save_search(
        query=query,
        filters=request.model_dump(),
        results_count=len(results),
    )

    return {
        "total": len(results),
        "offset": request.offset,
        "limit": request.limit,
        "results": paginated,
        "warning": warning,
        "score_distribution": distribution,
    }


@app.get("/api/search")
async def search_get(
    q: str = Query(None, description="Texto de búsqueda"),
    province: str = Query(None, description="Filtrar por provincia"),
    min_score: float = Query(None, description="Score mínimo"),
    max_score: float = Query(None, description="Score máximo"),
    has_financial_data: bool = Query(None, description="Solo con datos financieros"),
    ebitda_min: float = Query(None, ge=0, description="EBITDA mínimo (€)"),
    ebitda_max: float = Query(None, ge=0, description="EBITDA máximo (€)"),
    revenue_min: float = Query(None, ge=0, description="Facturación mínima (€)"),
    revenue_max: float = Query(None, ge=0, description="Facturación máxima (€)"),
    limit: int = Query(100, description="Límite de resultados"),
    offset: int = Query(0, description="Offset para paginación"),
):
    request = SearchRequest(
        query=q,
        province=province,
        min_score=min_score,
        max_score=max_score,
        has_financial_data=has_financial_data,
        ebitda_min=ebitda_min,
        ebitda_max=ebitda_max,
        revenue_min=revenue_min,
        revenue_max=revenue_max,
        limit=limit,
        offset=offset,
    )
    return await search_companies(request)


# ==================== LISTAS ====================

@app.get("/api/lists")
async def get_lists():
    lists = await database.get_lists()
    return {"lists": lists}


@app.post("/api/lists")
async def create_list(request: ListCreateRequest):
    name = request.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="El nombre de la lista no puede estar vacío")
    if len(name) > 200:
        raise HTTPException(status_code=422, detail="El nombre de la lista es demasiado largo (máx. 200)")
    list_id = await database.create_list(name, request.description)
    return {"id": list_id, "name": name}


@app.get("/api/lists/{list_id}")
async def get_list(list_id: int):
    list_info = await database.get_list(list_id)
    if not list_info:
        raise HTTPException(status_code=404, detail="Lista no encontrada")

    companies = await database.get_list_items(list_id)
    return {"list": list_info, "companies": companies, "total": len(companies)}


@app.post("/api/lists/{list_id}/items")
async def add_to_list(list_id: int, request: AddToListRequest):
    if not await database.get_list(list_id):
        raise HTTPException(status_code=404, detail="Lista no encontrada")
    if not await database.get_company(request.cif):
        raise HTTPException(status_code=404, detail="La empresa no está en el caché; búscala primero")
    added = await database.add_to_list(list_id, request.cif, request.notes)
    if not added:
        raise HTTPException(status_code=409, detail="La empresa ya está en la lista")
    return {"status": "added"}


@app.delete("/api/lists/{list_id}/items/{cif}")
async def remove_from_list(list_id: int, cif: str):
    if not _CIF_RE.match(cif):
        raise HTTPException(status_code=400, detail="CIF inválido (formato: 9 caracteres alfanuméricos)")
    await database.remove_from_list(list_id, cif)
    return {"status": "removed"}


@app.delete("/api/lists/{list_id}")
async def delete_list(list_id: int):
    await database.delete_list(list_id)
    return {"status": "deleted"}


# ==================== ESTADÍSTICAS ====================

@app.get("/api/stats")
async def get_stats():
    stats = await database.get_stats()
    return stats


@app.get("/api/stats/daily")
async def get_daily_stats(days: int = Query(14, ge=1, le=90)):
    daily = await database.get_daily_stats(days)
    return {"daily": daily}


@app.get("/api/search-history")
async def get_search_history(limit: int = Query(50, ge=1, le=200)):
    history = await database.get_search_history(limit)
    return {"history": history}


# ==================== EMPRESAS (LISTADO) ====================

@app.get("/api/companies")
async def list_companies(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    province: Optional[str] = None,
    has_financial_data: Optional[bool] = None,
):
    """Listar empresas en caché con paginación y filtros (para el ranking)."""
    companies = await database.search_companies(
        min_score=min_score, max_score=max_score, province=province,
        has_financial_data=has_financial_data,
        limit=limit, offset=offset,
    )
    filtered_count = await database.count_companies(
        min_score=min_score, max_score=max_score, province=province,
        has_financial_data=has_financial_data,
    )
    return {
        "companies": companies,
        "total": filtered_count,
        "offset": offset,
        "limit": limit,
    }


# ==================== FUENTES ====================

@app.get("/api/sources")
async def get_sources():
    sources = orchestrator.get_available_sources()
    return {"sources": sources}


# ==================== UTILIDADES ====================

@app.post("/api/search/daily")
async def search_daily():
    """
    Busca automáticamente nuevas candidatas basadas en sectores configurados,
    filtrando las que ya existen en la base de datos local.
    """
    from .config import settings
    sectors = settings.search_sectors
    
    all_new_companies = []
    seen_cifs = set()
    
    # Obtener todos los CIFs ya conocidos para filtrar
    existing_companies = await database.get_all_companies()
    known_cifs = {c.cif for c in existing_companies}
    
    async def cached_lookup(slug: str):
        return await database.get_company_by_slug(slug)

    for sector in sectors:
        sector_term = sector.strip()
        if not sector_term:
            continue
        
        await orchestrator.reset_rate_limit()
        found = await orchestrator.search(sector_term, cached_lookup=cached_lookup)
        
        for c in found:
            if c.cif not in known_cifs and c.cif not in seen_cifs:
                seen_cifs.add(c.cif)
                all_new_companies.append(c)
    
    # Guardar los nuevos hallazgos en la base de datos
    for company in all_new_companies:
        score = score_calculator.calculate(company)
        company.score = score['total']
        company.score_breakdown = score
        await database.save_company(company)
        
    return {
        "new_count": len(all_new_companies),
        "companies": all_new_companies
    }

@app.post("/api/cache/clear")

async def clear_cache():
    await database.clear_cache()
    return {"status": "cleared"}


# ==================== LLM ====================

@app.get("/api/llm/health")
async def llm_health():
    try:
        health = await asyncio.wait_for(get_llm_engine().health(), timeout=30.0)
    except asyncio.TimeoutError:
        health = {"configured": False, "provider": get_llm_engine().provider_name, "error": "Timeout tras 30s"}
    return {"llm": health, "config": settings.llm.describe()}


@app.get("/api/llm/models")
async def llm_models():
    """Listar modelos LLM disponibles"""
    return {
        "provider": settings.llm.provider,
        "active_model": settings.llm.ollama_model if settings.llm.provider == "ollama" else settings.llm.openai_model,
        "fast_model": settings.llm.ollama_fast_model if settings.llm.provider == "ollama" else None,
        "use_cloud": settings.llm.use_cloud,
    }


@app.post("/api/llm/search-candidates")
async def llm_search_candidates(request: CandidateSearchRequest):
    result = await candidate_search.search(
        sectors=request.sectors,
        max_analyze_per_sector=request.max_analyze,
    )

    items = []
    for entry in result["results"]:
        company = entry["company"]
        items.append({
            "company": {
                "cif": company.cif,
                "name": company.name,
                "slug": getattr(company, "slug", None),
                "province": getattr(company, "province", None),
                "city": getattr(company, "city", None),
                "borme_acts_count": company.borme.acts_count,
                "administrators": [a.model_dump() for a in company.administrators],
            },
            "borme_score": entry["borme_score"],
            "fit_score": entry["fit_score"],
            "fit_label": entry["fit_label"],
            "rationale": entry["rationale"],
            "succession_signal": entry["succession_signal"],
        })

    return {
        "total_companies": result["total_companies"],
        "count": len(items),
        "results": items,
        "warnings": result["warnings"],
    }


@app.post("/api/company/{cif}/enrich")
async def enrich_company_contact(cif: str):
    company = await database.get_company(cif)
    if not company:
        company = await orchestrator.get_company(cif)
        if not company:
            raise HTTPException(status_code=404, detail="Empresa no encontrada")

    data = await contact_enricher.enrich(
        company_name=company.name,
        cif=company.cif,
        website_hint=company.website,
    )

    changed = False
    if data.get("website") and data["website"] != company.website:
        company.website = data["website"]
        changed = True
    if data.get("phone") and data["phone"] != company.phone:
        company.phone = data["phone"]
        changed = True
    if data.get("email") and data["email"] != company.email:
        company.email = data["email"]
        changed = True

    if changed:
        await database.save_company(company)

    return {
        "status": "enriched",
        "cif": cif,
        "contact": {"website": company.website, "phone": company.phone, "email": company.email},
        "found": data,
    }


@app.post("/api/llm/chat")
async def llm_chat(request: ChatRequest):
    message = (request.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Mensaje vacío")

    system = (
        "Eres el asistente de un tool de search fund español que busca PYMES "
        "candidatas a adquisición (perfil: EBITDA 1,5-3M€, facturación 10-15M€, "
        "relevo generacional/sucesión, sectores industrial/logística/agroalimentario). "
        "Ayudas a analizar y priorizar candidatas. Sé conciso y en español."
    )

    messages = [{"role": "system", "content": system}]

    if request.context_cif:
        company = await database.get_company(request.context_cif) \
            or await database.get_company_by_slug(request.context_cif)
        if company:
            ctx = (
                f"Empresa en consulta: {company.name} (CIF {company.cif}).\n"
                f"Provincia: {company.province or company.city or '?'}\n"
                f"Antigüedad: {company.get_age_years() or '?'} años\n"
                f"Administradores: {', '.join(a.name for a in company.administrators[:5])}\n"
                f"Actos BORME: {company.borme.acts_count}\n"
                f"Website: {company.website or 'no consta'}\n"
                f"Teléfono: {company.phone or 'no consta'}\n"
                f"Email: {company.email or 'no consta'}"
            )
            messages.append({"role": "system", "content": ctx})

    for h in (request.history or [])[-8:]:
        role = h.get("role")
        content = h.get("content")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": str(content)})

    messages.append({"role": "user", "content": message})

    try:
        reply = await asyncio.wait_for(get_llm_engine().chat(messages), timeout=120.0)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="LLM timeout: la respuesta tardó demasiado (>120s)")
    except LLMError as e:
        raise HTTPException(status_code=503, detail=f"LLM no disponible: {e}")

    return {"reply": reply, "provider": get_llm_engine().provider_name}


# ==================== MAIN ====================

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
