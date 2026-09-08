import httpx
import logging
import asyncio
from typing import Optional, Dict, Any, List
from .base import DataSource

logger = logging.getLogger(__name__)

BASE_URL = "https://openmercantil.es/api/v1"


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
            data = await self._get_by_slug(identifier)
            if data:
                return self._format_response(data)
            data = await self._search_by_cif(identifier)
            if data:
                return self._format_response(data)
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

                slugs_to_fetch = []
                cached_results = []
                for result in items:
                    slug = result.get("slug")
                    if not slug:
                        continue
                    if cached_lookup:
                        cached = await cached_lookup(slug)
                        if cached:
                            cached_results.append(company_to_internal_format(cached))
                            continue
                    slugs_to_fetch.append(slug)

                # Fetch remaining slugs in parallel (max 5 concurrent)
                fetched = []
                if slugs_to_fetch:
                    sem = asyncio.Semaphore(5)

                    async def _fetch_one(s):
                        async with sem:
                            return await self._get_by_slug(s)

                    results = await asyncio.gather(
                        *[_fetch_one(s) for s in slugs_to_fetch],
                        return_exceptions=True,
                    )
                    for r in results:
                        if isinstance(r, RateLimitError):
                            raise r
                        if r and not isinstance(r, Exception):
                            formatted = self._format_response(r)
                            if formatted:
                                fetched.append(formatted)

                return cached_results + fetched
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



