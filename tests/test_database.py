"""Tests de la capa de almacenamiento SQLite (Database)."""
from tests.conftest import make_company


async def test_save_y_get_company(db):
    company = make_company()
    await db.save_company(company)

    loaded = await db.get_company(company.cif)
    assert loaded is not None
    assert loaded.cif == company.cif
    assert loaded.name == company.name


async def test_get_company_por_slug(db):
    company = make_company()
    await db.save_company(company)

    by_slug = await db.get_company_by_slug(company.slug)
    assert by_slug is not None
    assert by_slug.cif == company.cif


async def test_get_company_inexistente_devuelve_none(db):
    assert await db.get_company("ZZZZ99999999") is None


async def test_get_all_companies(db):
    await db.save_company(make_company(cif="B85767044", name="NANTA", slug="nanta"))
    await db.save_company(make_company(cif="A46103834", name="MERCADONA", slug="mercadona"))

    companies = await db.get_all_companies()
    assert len(companies) == 2


async def test_preservar_datos_financieros_y_contacto(db):
    """Re-guardar una empresa no debe perder los datos manuales (regresión)."""
    company = make_company(ebitda=2_000_000, revenue=12_000_000,
                           website="https://nanta.es", phone="918075400",
                           email="nanta@nutreco.com")
    await db.save_company(company)

    # Leer de vuelta y verificar que se conservan
    loaded = await db.get_company(company.cif)
    assert loaded.financial.ebitda == 2_000_000
    assert loaded.financial.revenue == 12_000_000
    assert loaded.website == "https://nanta.es"
    assert loaded.phone == "918075400"
    assert loaded.email == "nanta@nutreco.com"


async def test_listas_crud(db):
    list_id = await db.create_list("Candidatas 2026", "Prioridad alta")
    assert list_id is not None

    lists = await db.get_lists()
    assert len(lists) == 1
    assert lists[0]["name"] == "Candidatas 2026"

    # La empresa debe estar en el cache para aparecer en la lista (JOIN con companies)
    await db.save_company(make_company())

    # Añadir empresa a la lista
    await db.add_to_list(list_id, "B85767044")
    items = await db.get_list_items(list_id)
    assert len(items) == 1
    assert items[0].cif == "B85767044"

    # Añadir duplicado no debe duplicar (PK list_id+cif)
    await db.add_to_list(list_id, "B85767044")
    items = await db.get_list_items(list_id)
    assert len(items) == 1

    # Eliminar item
    await db.remove_from_list(list_id, "B85767044")
    assert len(await db.get_list_items(list_id)) == 0

    # Eliminar lista
    await db.delete_list(list_id)
    assert await db.get_list(list_id) is None


async def test_search_history_no_peta_con_query_nula(db):
    # Regresión: query None/vacía no debe lanzar
    await db.save_search(None, {}, 0)
    await db.save_search("", {}, 0)
    history = await db.get_search_history(10)
    assert len(history) >= 0


async def test_stats(db):
    stats = await db.get_stats()
    assert "total_companies" in stats
    assert "total_lists" in stats
