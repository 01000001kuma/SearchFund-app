from .base import DataSource
from typing import Optional, Dict, Any, List
import httpx


class WebSearchSource(DataSource):
    """
    Fuente de datos fallback: búsqueda en web
    """

    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def provides_financial_data(self) -> bool:
        return False

    async def close(self):
        await self.client.aclose()

    async def get_company(self, identifier: str) -> Optional[Dict[str, Any]]:
        return None

    async def search_companies(self, query: str, filters: Dict = None,
                               cached_lookup: Any = None) -> List[Dict]:
        return []

    async def get_financials_from_web(self, company_name: str,
                                      website_url: str = None) -> Optional[Dict]:
        return None
