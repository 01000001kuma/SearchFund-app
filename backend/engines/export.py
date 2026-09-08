"""
Exportación de datos a PDF y Excel.

- PDF: informe legible de una empresa (reportlab).
- Excel: hoja de cálculo con varias empresas (openpyxl).

Se usa Company.to_export_dict() como fuente de datos canónica.
"""
import io
import logging
from typing import List

from ..models.company import Company

logger = logging.getLogger(__name__)

PDF_COLUMNS = [
    ("CIF", "cif"),
    ("Nombre", "name"),
    ("Provincia", "province"),
    ("Ciudad", "city"),
    ("Dirección", "address"),
    ("Web", "website"),
    ("Teléfono", "phone"),
    ("Email", "email"),
    ("Forma legal", "legal_form"),
    ("Antigüedad", "age_years"),
    ("EBITDA", "ebitda_formatted"),
    ("Facturación", "revenue_formatted"),
    ("Empleados", "employees"),
    ("Score", "score"),
    ("Interpretación", "score_interpretation"),
    ("Actos BORME", "borme_acts_count"),
    ("Último acto BORME", "last_borme_activity"),
    ("Notas", "notes"),
]

EXCEL_HEADERS = [
    "CIF", "Nombre", "Provincia", "Ciudad", "Dirección", "CP",
    "Web", "Teléfono", "Email", "Forma legal", "Antigüedad (años)",
    "EBITDA", "Facturación", "Empleados", "Score",
    "Interpretación", "Actos BORME", "Admin. principales",
    "Antigüedad admin. (años)", "Tags", "Notas",
]


def _value(d: dict, key: str):
    v = d.get(key)
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return v


def export_pdf(company: Company) -> bytes:
    """Generar informe PDF de una empresa. Devuelve los bytes del PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    d = company.to_export_dict()
    buf = io.BytesIO()

    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 20 * mm

    y = height - margin
    c.setTitle(f"Informe - {d.get('name', '')}")

    # Cabecera
    c.setFont("Helvetica-Bold", 20)
    c.drawString(margin, y, d.get("name", "") or "Sin nombre")
    y -= 8 * mm
    c.setFont("Helvetica", 11)
    c.setStrokeColorRGB(0.2, 0.4, 0.8)
    c.setFillColorRGB(0.2, 0.4, 0.8)
    c.drawString(margin, y, "Search Fund Tool - Informe de candidata")
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(0, 0, 0)
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.35, 0.35, 0.35)
    c.drawString(margin, y,
                 f"Generado: {company.last_updated.strftime('%d/%m/%Y %H:%M') if company.last_updated else 'n/d'}")
    c.setFillColorRGB(0, 0, 0)
    y -= 12 * mm

    # Score destacado
    score = d.get("score")
    if score is not None:
        c.setFont("Helvetica-Bold", 14)
        interp = d.get("score_interpretation", "")
        c.drawString(margin, y, f"Score: {int(score)}/100 — {interp}")
        y -= 12 * mm

    # Bloques de datos
    def block(title, pairs):
        nonlocal y
        if y < 30 * mm:
            c.showPage()
            y = height - margin
        c.setFont("Helvetica-Bold", 12)
        c.setFillColorRGB(0.15, 0.15, 0.4)
        c.drawString(margin, y, title)
        c.setFillColorRGB(0, 0, 0)
        y -= 7 * mm
        c.setFont("Helvetica", 10)
        for label, value in pairs:
            if value is None or value == "":
                continue
            if y < 25 * mm:
                c.showPage()
                y = height - margin
                c.setFont("Helvetica", 10)
            c.drawString(margin + 4 * mm, y, f"{label}:")
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin + 45 * mm, y, str(value)[:60])
            c.setFont("Helvetica", 10)
            y -= 5.5 * mm
        y -= 5 * mm

    block("Datos básicos", [
        ("CIF", d.get("cif")),
        ("Provincia", d.get("province")),
        ("Ciudad", d.get("city")),
        ("Dirección", d.get("address")),
        ("Forma legal", d.get("legal_form")),
        ("Antigüedad", f"{d.get('age_years')} años" if d.get("age_years") else None),
    ])

    block("Contacto", [
        ("Web", d.get("website")),
        ("Teléfono", d.get("phone")),
        ("Email", d.get("email")),
    ])

    block("Financiero", [
        ("EBITDA", d.get("ebitda_formatted")),
        ("Facturación", d.get("revenue_formatted")),
        ("Empleados", d.get("employees")),
    ])

    block("Registro (BORME)", [
        ("Actos", d.get("borme_acts_count")),
        ("Último acto", d.get("last_borme_activity")),
    ])

    admins = d.get("administrators")
    if admins:
        block("Administradores", [(f"A-{i+1}", n) for i, n in enumerate(admins[:8])])

    if d.get("notes"):
        block("Notas", [("Notas", d.get("notes"))])

    c.showPage()
    c.save()
    return buf.getvalue()


def export_excel(companies: List[Company]) -> bytes:
    """Generar hoja Excel con las empresas. Devuelve los bytes del .xlsx."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Candidatas"

    # Cabecera
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    for col, header in enumerate(EXCEL_HEADERS, start=1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font

    # Datos
    for r, company in enumerate(companies, start=2):
        d = company.to_export_dict()
        row = [
            _value(d, "cif"),
            _value(d, "name"),
            _value(d, "province"),
            _value(d, "city"),
            _value(d, "address"),
            _value(d, "postal_code"),
            _value(d, "website"),
            _value(d, "phone"),
            _value(d, "email"),
            _value(d, "legal_form"),
            _value(d, "age_years"),
            _value(d, "ebitda_formatted"),
            _value(d, "revenue_formatted"),
            _value(d, "employees"),
            _value(d, "score"),
            _value(d, "score_interpretation"),
            _value(d, "borme_acts_count"),
            _value(d, "administrators"),
            _value(d, "administrator_tenure"),
            ", ".join(_value(d, "tags")) if isinstance(_value(d, "tags"), list) else _value(d, "tags"),
            _value(d, "notes"),
        ]
        for col, value in enumerate(row, start=1):
            ws.cell(row=r, column=col, value=value)

    # Ajustar ancho de columnas
    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value is not None:
                max_len = max(max_len, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = min(max_len + 2, 40)

    ws.freeze_panes = "A2"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
