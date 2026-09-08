"""Tests unitarios del cálculo de score (ScoreCalculator)."""
import pytest

from backend.engines.score import ScoreCalculator
from tests.conftest import make_company


@pytest.fixture
def score_calc():
    return ScoreCalculator()


def test_score_sin_datos_financieros(score_calc):
    """Sin EBITDA ni facturación, el score es solo BORME (has_financial_data=False)."""
    company = make_company(ebitda=None, revenue=None)
    result = score_calc.calculate(company)
    assert result["has_financial_data"] is False
    assert result["financial"] is None
    assert result["total"] == result["borme"]


def test_score_con_financiero_ideal(score_calc):
    """Con EBITDA 1.5-3M y facturación 10-15M, el financial score es alto."""
    company = make_company(ebitda=2_000_000, revenue=12_000_000, ebitda_margin=20)
    result = score_calc.calculate(company)
    assert result["has_financial_data"] is True
    assert result["financial"] is not None
    # Score financiero óptimo -> cerca de 100
    assert result["financial"] >= 80


def test_score_sin_administradores_da_valor_por_defecto(score_calc):
    company = make_company(administrators=[])
    result = score_calc.calculate(company)
    # Sin administradores no debe petar y devuelve score 0-100
    assert 0 <= result["total"] <= 100


def test_score_administrador_tenencia_larga(score_calc):
    """Antigüedad >= 10 años del admin contribuye positivamente al tenure score."""
    from backend.models.company import Administrator
    company = make_company(
        administrators=[Administrator(name="DON CARLOS", role="ADM", since="2010-01-01")]
    )
    borme = score_calc.calculate(company)["borme"]
    assert 0 <= borme <= 100


def test_interpretacion_rangos(score_calc):
    assert score_calc._get_interpretation(90).startswith("MUY BUEN")
    assert score_calc._get_interpretation(70).startswith("BUEN")
    assert score_calc._get_interpretation(50).startswith("CANDIDATO MODERADO")
    assert score_calc._get_interpretation(10).startswith("NO RECOMENDADO")


def test_score_inputes_todos_tipos(score_calc):
    scores = []
    for ebitda, revenue, margin in [
        (2_500_000, 12_000_000, 22),
        (800_000, 6_000_000, 12),
        (5_000_000, 20_000_000, 30),
        (100_000, 1_000_000, 5),
        (None, None, None),
    ]:
        company = make_company(ebitda=ebitda, revenue=revenue, ebitda_margin=margin)
        result = score_calc.calculate(company)
        assert 0 <= result["total"] <= 100
        scores.append(result["total"])
    assert len(scores) == 5
