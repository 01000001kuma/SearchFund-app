import logging
from typing import Optional, Dict, List
from .base import DataSource
from .openmercantil import OpenMercantilSource, RateLimitError
from .empresief import EmpresiFSource
from .web_search import WebSearchSource
from ..models.company import Company, Administrator, BormeData
from ..models.financial import FinancialData

logger = logging.getLogger(__name__)


class DataOrchestrator:
    """
    Coordinador de múltiples fuentes de datos
    """

    def __init__(self):
        self.sources: List[DataSource] = [
            OpenMercantilSource(),
            EmpresiFSource(),
            WebSearchSource(),
        ]
        self._rate_limit_hit: Optional[str] = None

    @property
    def rate_limit_hit(self) -> Optional[str]:
        return self._rate_limit_hit

    async def reset_rate_limit(self):
        self._rate_limit_hit = None

    async def close(self):
        for source in self.sources:
            try:
                await source.close()
            except Exception as e:
                logger.warning("Error closing source %s: %s", source.name, e)

    async def get_company(self, identifier: str) -> Optional[Company]:
        result = {
            'cif': identifier,
            'data_sources': [],
            'borme': None,
            'financial': None,
            'basic_info': None,
        }

        for source in self.sources:
            if not source.is_configured():
                continue
            try:
                data = await source.get_company(identifier)
                if data:
                    result['data_sources'].append(source.name)
                    if 'borme' in data and data['borme']:
                        result['borme'] = data['borme']
                    if 'financial' in data and data['financial']:
                        if result['financial'] is None or source.name == 'empresief':
                            result['financial'] = data['financial']
                    if 'basic_info' in data and data['basic_info']:
                        if result['basic_info'] is None:
                            result['basic_info'] = data['basic_info']
            except RateLimitError:
                self._rate_limit_hit = source.name
                continue
            except Exception as e:
                logger.warning("Error in source %s for %s: %s", source.name, identifier, e)
                continue

        return self._build_company_model(result)

    def _build_company_model(self, raw_data: Dict) -> Optional[Company]:
        basic = raw_data.get('basic_info') or {}

        has_any_data = bool(basic.get('name')) or len(raw_data.get('data_sources', [])) > 0
        if not has_any_data:
            return None

        if not basic or not basic.get('name'):
            cif = raw_data.get('cif', '')
            if not cif:
                return None
            basic = {
                'cif': cif,
                'name': basic.get('name') or f"Empresa {cif}",
                'slug': basic.get('slug') or cif.lower(),
                'administrators': basic.get('administrators', []),
            }

        admins = [
            Administrator(
                name=a.get('name', ''),
                role=a.get('role', ''),
                since=a.get('since'),
                until=a.get('until'),
            )
            for a in basic.get('administrators', [])
        ]

        borme_data = raw_data.get('borme') or {}
        borme = BormeData(
            acts_count=borme_data.get('acts_count', 0),
            last_activity=borme_data.get('last_activity'),
            acts=borme_data.get('acts', []),
        )

        financial_raw = raw_data.get('financial')
        if isinstance(financial_raw, FinancialData):
            financial = financial_raw
        elif financial_raw:
            financial = FinancialData(
                revenue=financial_raw.get('revenue'),
                ebitda=financial_raw.get('ebitda'),
                ebitda_margin=financial_raw.get('ebitda_margin'),
                employees=financial_raw.get('employees'),
                source=financial_raw.get('source'),
                year=financial_raw.get('year'),
            )
        else:
            financial = FinancialData()

        company = Company(
            cif=basic.get('cif') or raw_data.get('cif', ''),
            name=basic.get('name', ''),
            slug=basic.get('slug', ''),
            legal_form=basic.get('legal_form'),
            status=basic.get('status'),
            address=basic.get('address'),
            city=basic.get('city'),
            province=basic.get('province'),
            postal_code=basic.get('postal_code'),
            founded_date=basic.get('founded_date') or None,
            website=basic.get('website'),
            phone=basic.get('phone'),
            email=basic.get('email'),
            administrators=admins,
            borme=borme,
            financial=financial,
            data_sources=raw_data.get('data_sources', []),
        )

        return company

    async def search(self, query: str, filters: Dict = None,
                     cached_lookup=None) -> List[Company]:
        all_results = []

        for source in self.sources:
            if not source.is_configured():
                continue
            try:
                source_results = await source.search_companies(
                    query, filters, cached_lookup=cached_lookup,
                )
                all_results.extend(source_results)
            except RateLimitError:
                logger.warning("%s exceeded daily quota (429)", source.name)
                self._rate_limit_hit = source.name
                continue
            except Exception as e:
                logger.warning("Error searching in %s: %s", source.name, e)
                continue

        companies = []
        for result in all_results:
            company = self._build_company_model(result)
            if company:
                companies.append(company)

        return companies

    def get_available_sources(self) -> List[Dict]:
        return [source.get_status() for source in self.sources]

    def get_financial_sources(self) -> List[DataSource]:
        return [s for s in self.sources if s.provides_financial_data]
