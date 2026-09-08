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