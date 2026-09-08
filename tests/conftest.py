import sys
from pathlib import Path

import pytest_asyncio

# Añadir la raíz del backend al path para imports como `from backend.engines...`
BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from backend.storage.database import Database  # noqa: E402
from backend.models.company import Company, Administrator, BormeData  # noqa: E402
from backend.models.financial import FinancialData  # noqa: E402


def make_company(
    cif="B85767044",
    name="ALIMENTACION ANIMAL NANTA SL",
    slug="alimentacion-animal-nanta-sl",
    founded_date="2008-01-15",
    website=None,
    phone=None,
    email=None,
    administrators=None,
    acts_count=12,
    last_activity=None,
    ebitda=None,
    revenue=None,
    ebitda_margin=None,
) -> Company:
    """Crear un modelo Company determinista para tests."""
    return Company(
        cif=cif,
        name=name,
        slug=slug,
        legal_form="SL",
        province="Madrid",
        city="Tres Cantos",
        address="C/ Ejemplo 1",
        founded_date=founded_date,
        website=website,
        phone=phone,
        email=email,
        administrators=administrators or [
            Administrator(name="DON MANUEL GARCIA", role="Administrador único", since="2008-03-01"),
        ],
        borme=BormeData(
            acts_count=acts_count,
            last_activity=last_activity,
            acts=[{"id": f"a{i}", "date": "2024-01-01", "title": f"Acta {i}"} for i in range(acts_count)],
        ),
        financial=FinancialData(
            ebitda=ebitda,
            revenue=revenue,
            ebitda_margin=ebitda_margin,
            employees=50,
            source="manual",
            year=2024,
        ),
    )


@pytest_asyncio.fixture
async def db(tmp_path):
    """Base de datos SQLite temporal por test."""
    yield Database(str(tmp_path / "test.db"))
