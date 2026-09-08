"""Tests de generación de PDF y Excel (engines.export)."""
from backend.engines.export import export_pdf, export_excel
from tests.conftest import make_company


def _pdf_header(buf: bytes) -> bool:
    """Un PDF válido empieza por %PDF."""
    return buf.startswith(b"%PDF")


def test_export_pdf_genera_pdf_valido():
    company = make_company(
        website="https://nanta.es",
        phone="+34 918075400",
        email="nanta@nutreco.com",
        ebitda=2_000_000,
        revenue=12_000_000,
    )
    pdf = export_pdf(company)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 500
    assert _pdf_header(pdf)


def test_export_pdf_sin_datos_extra_no_peta():
    # Empresa sin financiero, sin web, sin admin
    company = make_company(
        ebitda=None, revenue=None, website=None, phone=None, email=None,
    )
    pdf = export_pdf(company)
    assert _pdf_header(pdf)


def test_export_excel_genera_xlsx_validos():
    companies = [
        make_company(
            cif="B85767044", name="ALIMENTACION ANIMAL NANTA SL",
            ebitda=2_000_000, revenue=12_000_000,
        ),
        make_company(
            cif="A46103834", name="MERCADONA SA", slug="mercadona-sa",
            ebitda=None, revenue=None,
        ),
    ]
    xlsx = export_excel(companies)
    assert isinstance(xlsx, bytes)
    # El zip de un .xlsx arranca con PK
    assert xlsx.startswith(b"PK")
    assert len(xlsx) > 500


def test_export_excel_con_filas_esperadas():
    from openpyxl import load_workbook
    from io import BytesIO

    companies = [
        make_company(cif="B85767044", name="NANTA A", slug="nanta-a"),
        make_company(cif="A46103834", name="MERCADONA", slug="mercadona"),
    ]
    xlsx = export_excel(companies)
    wb = load_workbook(BytesIO(xlsx))
    ws = wb.active
    assert ws.title == "Candidatas"
    # 1 cabecera + 2 filas de datos
    assert ws.max_row == 3
    # La cabecera contiene los campos clave
    headers = [c.value for c in ws[1]]
    assert "CIF" in headers
    assert "Nombre" in headers
    assert "EBITDA" in headers
    assert "Score" in headers
