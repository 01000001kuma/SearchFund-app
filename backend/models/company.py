from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from .financial import FinancialData


class Administrator(BaseModel):
    """Administrador de la empresa"""
    name: str
    role: str
    since: Optional[str] = None
    until: Optional[str] = None


class BormeData(BaseModel):
    """Datos del BORME (Boletín Oficial del Registro Mercantil)"""
    acts_count: int = 0
    last_activity: Optional[str] = None
    acts: List[dict] = []
    source: str = "openmercantil"


class Company(BaseModel):
    """Modelo completo de empresa"""

    cif: str
    name: str
    slug: str

    legal_form: Optional[str] = None
    status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    cnae: Optional[str] = None
    founded_date: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    administrators: List[Administrator] = []
    borme: BormeData = BormeData()
    financial: FinancialData = FinancialData()

    score: Optional[float] = None
    score_breakdown: Optional[dict] = None

    last_updated: datetime = Field(default_factory=datetime.now)
    data_sources: List[str] = []

    tags: List[str] = []
    notes: Optional[str] = None
    agent_opinion: Optional[str] = None  # dictamen del Agente (LLM)

    def has_financial_data(self) -> bool:
        return self.financial.is_complete()

    def has_partial_financial_data(self) -> bool:
        return self.financial.has_partial_data()

    def get_age_years(self) -> Optional[int]:
        if not self.founded_date:
            return None
        try:
            founded = datetime.strptime(self.founded_date[:10], "%Y-%m-%d")
            age = (datetime.now() - founded).days / 365.25
            return int(age)
        except (ValueError, IndexError):
            return None

    def get_administrator_tenure(self) -> Optional[int]:
        if not self.administrators:
            return None
        admin = self.administrators[0]
        if not admin.since:
            return None
        try:
            since = datetime.strptime(admin.since[:10], "%Y-%m-%d")
            tenure = (datetime.now() - since).days / 365.25
            return int(tenure)
        except (ValueError, IndexError):
            return None

    def get_score_interpretation(self) -> str:
        if self.score is None:
            return "Sin evaluar"
        if self.score >= 80:
            return "MUY BUEN CANDIDATO"
        elif self.score >= 60:
            return "BUEN CANDIDATO"
        elif self.score >= 40:
            return "CANDIDATO MODERADO"
        elif self.score >= 20:
            return "CANDIDATO BAJO"
        else:
            return "NO RECOMENDADO"

    def to_export_dict(self) -> dict:
        return {
            "cif": self.cif,
            "name": self.name,
            "province": self.province,
            "city": self.city,
            "address": self.address,
            "postal_code": self.postal_code,
            "website": self.website,
            "phone": self.phone,
            "email": self.email,
            "legal_form": self.legal_form,
            "founded_date": self.founded_date,
            "age_years": self.get_age_years(),
            "administrators": [a.name for a in self.administrators],
            "administrator_tenure": self.get_administrator_tenure(),
            "ebitda": self.financial.ebitda,
            "ebitda_formatted": self.financial.format_ebitda(),
            "revenue": self.financial.revenue,
            "revenue_formatted": self.financial.format_revenue(),
            "employees": self.financial.employees,
            "financial_source": self.financial.source,
            "score": self.score,
            "score_interpretation": self.get_score_interpretation(),
            "borme_acts_count": self.borme.acts_count,
            "last_borme_activity": self.borme.last_activity,
            "data_sources": self.data_sources,
            "tags": self.tags,
            "notes": self.notes,
        }
