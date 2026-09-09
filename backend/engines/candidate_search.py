"""
Búsqueda automática de PYMES candidatas a adquisición para search funds.

Recorre sectores/actividades configurados (backend.config), obtiene empresas
de OpenMercantil (vía DataOrchestrator) y, con el LLM, razona sobre las
señales de venta (relevo generacional, tamaño, sector) para asignar:
- fit_score: 0-100 de adecuación al perfil del search fund (Cabiedes).
- rationale: breve justificación.
- suggested_contact: síntesis de por qué contactarla.

El resultado se integra con el resto del sistema (Company + score BORME)
y permite rankear candidatas antes de enriquecer sus contactos.
"""
import logging
from typing import Dict, List, Optional

from ..models.company import Company
from ..data_sources.orchestrator import DataOrchestrator
from ..engines.score import ScoreCalculator
from .llm import get_llm_engine, LLMError

logger = logging.getLogger(__name__)

CRITERIA_SYSTEM = """
Eres un analista senior de un search fund español. Evalúas PYMES españolas
como posibles candidatas a adquisición (relevo generacional, venta).

El perfil objetivo del fondo:
- Facturación aproximada 10-15 M€ al año.
- EBITDA aproximado 1,5-3 M€ (ticket de compra hasta ~1 M€).
- Señales de relevo generacional: administradores fundadores de edad avanzada,
  cambios recientes de administración, falta de una segunda generación clara.
- Sector industrial, logística, servicios B2B, agroalimentario.

Te doy datos parciales de una empresa (BORME: administradores, últimos actos,
provincia, antigüedad). Devuelve SOLO JSON:
{
  "fit_score": número 0-100 (adecuación al perfil del fondo),
  "fit_label": "ALTO" | "MEDIO" | "BAJO",
  "rationale": "explicación breve en español (máx 2 frases)",
  "succession_signal": true/false (si hay indicios de relevo generacional)
}

No inventes datos financieros que no se den. Basa el fit en las señales y
en la coherencia sectorial.
"""


class CandidateSearch:
    """Pipeline: sector -> empresas -> scoring BORME -> ranking LLM por fit."""

    def __init__(self, database=None, orchestrator=None):
        if database is None:
            from ..storage.database import Database
            database = Database()
        if orchestrator is None:
            orchestrator = DataOrchestrator()
        self.orchestrator = orchestrator
        self.score_calculator = ScoreCalculator()
        self._database = database

    def _company_profile(self, company: Company) -> str:
        """Resumir la empresa para el LLM en texto plano."""
        admins = "; ".join(
            f"{a.name} ({a.role or 'admin'}, desde {a.since or '?'})"
            for a in company.administrators[:6]
        ) or "no consta"
        acts = company.borme.acts[:6]
        acts_text = "; ".join(
            f"{a.get('date', '')[:10]}: {a.get('title', '')}"
            for a in acts
        ) or "sin actos recientes"
        return (
            f"Nombre: {company.name} ({company.city or company.province or '?'})\n"
            f"CIF: {company.cif or '?'} | Forma: {company.legal_form or '?'} | "
            f"Antigüedad: {company.get_age_years() or '?'} años\n"
            f"Administradores: {admins}\n"
            f"Últimos actos BORME: {acts_text}"
        )

    async def score_candidates(self, companies: List[Company],
                               max_analyze: int = 10) -> List[Dict]:
        """
        Aplicar el LLM a cada empresa y devolver lista enriquecida con fit.
        Ordena por fit_score descendente.
        """
        results: List[Dict] = []
        analyzed = companies[:max_analyze]

        for company in analyzed:
            s = self.score_calculator.calculate(company)
            borme_score = s["total"]

            profile = self._company_profile(company)
            entry = {
                "company": company,
                "borme_score": borme_score,
                "fit_score": borme_score,
                "fit_label": "MEDIO",
                "rationale": "",
                "succession_signal": None,
            }
            try:
                data = await get_llm_engine().extract_json(
                    CRITERIA_SYSTEM, profile
                )
                fit = data.get("fit_score")
                if isinstance(fit, (int, float)):
                    entry["fit_score"] = max(0, min(100, float(fit)))
                entry["fit_label"] = data.get("fit_label", "MEDIO")
                entry["rationale"] = data.get("rationale", "")
                entry["succession_signal"] = bool(data.get("succession_signal", False))
            except LLMError as e:
                logger.warning("LLM falló al puntuar %r: %s", company.name, e)

            results.append(entry)

        results.sort(key=lambda x: (x["fit_score"], x["borme_score"]), reverse=True)
        return results

    async def search(self, sectors: Optional[List[str]] = None,
                     max_analyze_per_sector: int = 8) -> List[Dict]:
        """
        Recorrer sectores configurados y devolver candidatas rankeadas.
        Respeta la cuota de OpenMercantil reutilizando la caché local.
        """
        from ..config import settings
        sectors = sectors or settings.search_sectors

        all_companies: List[Company] = []
        seen_cifs = set()
        warnings: List[str] = []

        for sector in sectors:
            sector_term = sector.strip()
            if not sector_term:
                continue

            async def cached_lookup(slug: str):
                return await self._database.get_company_by_slug(slug)

            await self.orchestrator.reset_rate_limit()
            companies = await self.orchestrator.search(sector_term, cached_lookup=cached_lookup)

            if self.orchestrator.rate_limit_hit:
                warnings.append(
                    f"Cuota OpenMercantil agotada al buscar '{sector_term}'. "
                    "Se usó caché local."
                )

            for c in companies:
                if c.cif not in seen_cifs:
                    seen_cifs.add(c.cif)
                    all_companies.append(c)

        # Respetar el límite pedido (por defecto 8); el análisis LLM es lento en CPU
        ranked = await self.score_candidates(all_companies, max_analyze=max_analyze_per_sector)
        return {
            "results": ranked,
            "warnings": warnings,
            "total_companies": len(all_companies),
            "analyzed": min(max_analyze_per_sector, len(all_companies)),
        }
