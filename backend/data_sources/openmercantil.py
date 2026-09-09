import httpx
import logging
import re
from typing import Optional, Dict, Any, List
from .base import DataSource

logger = logging.getLogger(__name__)

BASE_URL = "https://openmercantil.es/api/v1"
_CIF_PATTERN = re.compile(r"^[A-Z][0-9]{8}$")


class RateLimitError(Exception):
    """Error cuando OpenMercantil supera la cuota diaria (HTTP 429)"""
    def __init__(self, retry_at: str = None):
        self.retry_at = retry_at
        super().__init__("Límite diario de OpenMercantil alcanzado")


def company_to_internal_format(company) -> Dict:
    """Convertir un objeto Company cacheado al formato interno
    (basic_info / borme / financial) que espera el orchestrator."""
    return {
        "basic_info": {
            "cif": company.cif,
            "name": company.name,
            "slug": company.slug,
            "legal_form": company.legal_form,
            "status": company.status,
            "address": company.address,
            "city": company.city,
            "province": company.province,
            "cnae": company.cnae,
            "postal_code": company.postal_code,
            "founded_date": company.founded_date,
            "website": company.website,
            "phone": company.phone,
            "email": company.email,
            "administrators": [
                {"name": a.name, "role": a.role, "since": a.since, "until": a.until}
                for a in company.administrators
            ] if company.administrators else [],
        },
        "borme": {
            "acts_count": company.borme.acts_count if company.borme else 0,
            "last_activity": company.borme.last_activity if company.borme else None,
            "acts": company.borme.acts if company.borme else [],
        },
        "financial": company.financial,
    }


class OpenMercantilSource(DataSource):
    """Fuente de datos OpenMercantil (BORME) - Siempre gratis"""

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": "SearchFundTool/1.0",
                "Accept": "application/json",
            },
        )

    @property
    def name(self) -> str:
        return "openmercantil"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def provides_financial_data(self) -> bool:
        return False

    async def close(self):
        await self.client.aclose()

    async def get_company(self, identifier: str) -> Optional[Dict[str, Any]]:
        try:
            # Un CIF (letra+8) no es un slug: saltar la llamada por slug,
            # que gastaría cuota sin resultado.
            if _CIF_PATTERN.match(identifier):
                data = await self._search_by_cif(identifier)
            else:
                data = await self._get_by_slug(identifier)
                if not data:
                    data = await self._search_by_cif(identifier)
            if data:
                return self._format_response(data)
            return None
        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Error obteniendo empresa {identifier}: {e}")
            return None
        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Error obteniendo empresa {identifier}: {e}")
            return None

    async def _get_by_slug(self, slug: str) -> Optional[Dict]:
        try:
            url = f"{BASE_URL}/company/{slug}"
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                raise RateLimitError()
            return None
        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Error por slug {slug}: {e}")
            return None

    async def _search_by_cif(self, cif: str) -> Optional[Dict]:
        try:
            url = f"{BASE_URL}/search"
            params = {"q": cif}
            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                if items and len(items) > 0:
                    company_slug = items[0].get("slug")
                    if company_slug:
                        return await self._get_by_slug(company_slug)
            elif response.status_code == 429:
                raise RateLimitError()
            return None
        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Error buscando por CIF {cif}: {e}")
            return None

    async def search_companies(self, query: str, filters: Dict = None,
                               cached_lookup: Any = None) -> List[Dict]:
        try:
            url = f"{BASE_URL}/search"
            params = {"q": query, "limit": 20}
            if filters and "limit" in filters:
                params["limit"] = filters["limit"]

            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                # Los ítems de búsqueda traen provincia/CNAE/actividad que el
                # endpoint de detalle NO devuelve: se conservan para enriquecer.
                search_items: Dict[str, Dict] = {
                    it.get("slug"): it for it in items if it.get("slug")
                }

                # Optimización de cuota: la búsqueda devuelve todos los datos
                # que necesitamos para listar (nombre, CIF, provincia, CNAE,
                # actos). El detalle se pide bajo demanda al abrir la ficha.
                # Coste: 1 llamada por búsqueda en vez de 1 + N detalles.
                results_list = []
                for result in items:
                    slug = result.get("slug")
                    if not slug:
                        continue
                    if cached_lookup:
                        cached = await cached_lookup(slug)
                        if cached:
                            results_list.append(
                                self._enrich_with_search_item(
                                    company_to_internal_format(cached),
                                    search_items.get(slug),
                                )
                            )
                            continue
                    built = self._company_from_search_item(result)
                    if built:
                        results_list.append(built)

                return results_list
            elif response.status_code == 429:
                raise RateLimitError()
            else:
                logger.error(f"Error en búsqueda: {response.status_code}")
                return []
        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Error buscando empresas: {e}")
            return []

    def _company_from_search_item(self, item: Dict) -> Optional[Dict]:
        """Formato interno directo desde un ítem de /search (sin llamada de detalle)."""
        slug = item.get("slug")
        if not slug:
            return None
        name, cif = item.get("name", ""), item.get("cif", "")
        if not name and not cif:
            return None
        sec, code = item.get("cnae_section"), item.get("cnae_code")
        cnae = f"{sec} · {code}" if sec and code else (code or sec)
        return {
            "basic_info": {
                "cif": cif,
                "name": name,
                "slug": slug,
                "province": item.get("province") or None,
                "cnae": cnae,
                "administrators": [],
            },
            "borme": {
                "acts_count": item.get("acts_count", 0),
                "last_activity": item.get("last_seen"),
                "first_seen": item.get("first_seen"),
                "acts": [],
            },
            "financial": None,
        }

    def _enrich_with_search_item(
        self, formatted: Dict, item: Optional[Dict]
    ) -> Dict:
        """Añade provincia/CNAE/actividad del ítem de búsqueda al formato interno.
        El endpoint /company/{slug} no devuelve province; /search sí."""
        if not item:
            return formatted
        basic = formatted.setdefault("basic_info", {})
        if not basic.get("province") and item.get("province"):
            basic["province"] = item["province"]
        if not basic.get("cnae") and (item.get("cnae_code") or item.get("cnae_section")):
            sec, code = item.get("cnae_section"), item.get("cnae_code")
            if sec and code:
                basic["cnae"] = f"{sec} · {code}"
            else:
                basic["cnae"] = code or sec
        borme = formatted.setdefault("borme", {})
        if not borme.get("acts_count") and item.get("acts_count"):
            borme["acts_count"] = item["acts_count"]
        if not borme.get("last_activity") and item.get("last_seen"):
            borme["last_activity"] = item["last_seen"]
        return formatted

    def _format_response(self, raw_data: Dict) -> Optional[Dict]:
        if not raw_data:
            return None

        company = raw_data.get("company", raw_data)
        kpis = raw_data.get("kpis", {})
        acts_count = kpis.get("acts_count", 0)
        last_activity = kpis.get("last_seen")
        first_seen = kpis.get("first_seen")

        officers = raw_data.get("officers", {})
        current_officers = officers.get("current", [])
        administrators = [
            {
                "name": o.get("name", ""),
                "role": o.get("role", ""),
                "since": o.get("since", ""),
                "until": o.get("until"),
            }
            for o in current_officers
        ]

        events = raw_data.get("events", [])

        return {
            "basic_info": {
                "cif": company.get("cif", ""),
                "name": company.get("name", ""),
                "slug": company.get("slug", ""),
                "legal_form": company.get("company_type", ""),
                "status": company.get("status", ""),
                "address": company.get("address", ""),
                "city": company.get("city", ""),
                "province": company.get("province", ""),
                "cnae": company.get("cnae") or company.get("cnae_code"),
                "postal_code": company.get("postal_code", ""),
                "founded_date": company.get("date_creation"),
                "website": company.get("website"),
                "phone": company.get("phone") or company.get("telefono"),
                "email": company.get("email") or company.get("mail"),
                "workers": company.get("workers"),
                "administrators": administrators,
            },
            "borme": {
                "acts_count": acts_count,
                "last_activity": last_activity,
                "first_seen": first_seen,
                "acts": events[:10],
            },
            "financial": None,
        }



