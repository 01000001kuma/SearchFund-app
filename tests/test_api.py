"""Tests de humo sobre la API HTTP (endpoints rápidos, sin LLM/externos)."""
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert "status" in resp.json()


def test_sources():
    resp = client.get("/api/sources")
    assert resp.status_code == 200
    assert "sources" in resp.json()


def test_stats():
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_companies" in body


def test_llm_health():
    resp = client.get("/api/llm/health")
    assert resp.status_code == 200
    assert "llm" in resp.json()


def test_company_inexistente_devuelve_404():
    resp = client.get("/api/company/ZZZZ999999999")
    assert resp.status_code == 404


def test_search_query_vacia_no_es_error():
    resp = client.post("/api/search", json={"query": "", "limit": 5})
    assert resp.status_code == 200
    assert "results" in resp.json()


def test_export_excel_todas_responde_xlsx():
    resp = client.get("/api/export/companies.xlsx")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats"
    )
    assert resp.content.startswith(b"PK")


def test_export_lista_inexistente_404():
    resp = client.get("/api/lists/99999/export/xlsx")
    assert resp.status_code == 404

# ==================== FILTROS FINANCIEROS ====================

from backend.main import SearchRequest, matches_financial_filters  # noqa: E402
from backend.models.company import Company  # noqa: E402
from backend.models.financial import FinancialData  # noqa: E402


def _company(ebitda=None, revenue=None):
    return Company(
        name="Test SL",
        cif="B12345678",
        slug="test-sl-b12345678",
        financial=FinancialData(ebitda=ebitda, revenue=revenue),
    )


def test_filtro_ebitda_min_excluye_sin_dato():
    req = SearchRequest(ebitda_min=500_000)
    assert matches_financial_filters(_company(ebitda=1_500_000), req) is True
    assert matches_financial_filters(_company(ebitda=100_000), req) is False
    # Sin dato EBITDA → excluida cuando se pide rango
    assert matches_financial_filters(_company(), req) is False


def test_filtro_ebitda_rango_objetivo():
    req = SearchRequest(ebitda_min=1_500_000, ebitda_max=3_000_000)
    assert matches_financial_filters(_company(ebitda=2_000_000), req) is True
    assert matches_financial_filters(_company(ebitda=3_500_000), req) is False


def test_filtro_revenue_min():
    req = SearchRequest(revenue_min=10_000_000)
    assert matches_financial_filters(_company(revenue=12_000_000), req) is True
    assert matches_financial_filters(_company(revenue=5_000_000), req) is False


def test_sin_filtros_financieros_pasa_todo():
    req = SearchRequest()
    assert matches_financial_filters(_company(), req) is True
    assert matches_financial_filters(_company(ebitda=9_999_999), req) is True


def test_search_valida_parametros_financieros():
    # ebitda_min negativo → 422
    resp = client.post("/api/search", json={"query": "", "ebitda_min": -1})
    assert resp.status_code == 422
    # Aceptado con rango válido (query vacía → early return, sin red)
    resp = client.post(
        "/api/search",
        json={"query": "", "ebitda_min": 1_500_000, "ebitda_max": 3_000_000},
    )
    assert resp.status_code == 200


# ==================== VALIDACIÓN DE LISTAS ====================


def test_crear_lista_con_nombre_en_blanco_rechazada():
    resp = client.post("/api/lists", json={"name": "   "})
    assert resp.status_code == 422


def test_anadir_a_lista_inexistente_devuelve_404():
    # Antes devolvía 409 "ya está en la lista" (bug de FK → IntegrityError)
    resp = client.post("/api/lists/99999/items", json={"cif": "B66778899"})
    assert resp.status_code == 404


def test_anadir_empresa_no_cacheada_devuelve_404():
    lists = client.get("/api/lists").json()["lists"]
    resp = client.post(
        f"/api/lists/{lists[0]['id']}/items", json={"cif": "Z99999999"}
    )
    assert resp.status_code == 404


def test_search_devuelve_distribucion_de_scores():
    resp = client.post("/api/search", json={"query": "", "limit": 5})
    body = resp.json()
    assert set(body["score_distribution"].keys()) == {"bajo", "medio", "alto"}


# ==================== OPTIMIZACIÓN DE CUOTA ====================


def test_company_from_search_item_sin_llamada_de_detalle():
    from backend.data_sources.openmercantil import OpenMercantilSource

    src = OpenMercantilSource()
    item = {
        "slug": "transportes-urbanos-de-zaragoza-sa",
        "name": "TRANSPORTES URBANOS DE ZARAGOZA SA",
        "cif": "A50002930",
        "province": "Zaragoza",
        "cnae_code": "49",
        "cnae_section": "H",
        "acts_count": 60,
        "first_seen": "2009-01-16",
        "last_seen": "2026-05-07",
    }
    fmt = src._company_from_search_item(item)
    assert fmt is not None
    assert fmt["basic_info"]["name"] == "TRANSPORTES URBANOS DE ZARAGOZA SA"
    assert fmt["basic_info"]["province"] == "Zaragoza"
    assert fmt["basic_info"]["cnae"] == "H · 49"
    assert fmt["borme"]["acts_count"] == 60
    assert fmt["financial"] is None


def test_company_from_search_item_item_invalido():
    from backend.data_sources.openmercantil import OpenMercantilSource

    src = OpenMercantilSource()
    assert src._company_from_search_item({"slug": ""}) is None
    assert src._company_from_search_item({"slug": "x", "name": "", "cif": ""}) is None
