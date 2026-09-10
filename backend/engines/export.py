"""
Exportación finance-grade a PDF y Excel.

- PDF: informe ejecutivo de una empresa (platypus/reportlab): banda de
  cabecera, medidor donut del score, desglose de criterios, métricas
  financieras frente al perfil objetivo, corporativos, administradores
  y últimos actos BORME.
- Excel: hoja "Candidatas" estilizada (cabecera navy, color por banda de
  score, cifras numéricas, autofiltro) + hoja "Leyenda" con la
  metodología de scoring.
"""
import io
import logging
from datetime import datetime
from typing import List, Optional

from ..models.company import Company

logger = logging.getLogger(__name__)

# ---- Identidad visual (finance-grade) ----
NAVY = "#1F4E79"
TEXT_DARK = "#1A1A1A"
TEXT_GRAY = "#5A5A5A"
ROW_ALT = "#F5F8FB"
BORDER_GRAY = "#C9D3E0"
TRACK_GRAY = "#E5E9EF"

# Bandas de score (alineadas con engines.score)
BANDS = [
    (80, "MUY BUENO", "#047857"),
    (60, "BUENO", "#15803D"),
    (40, "MODERADO", "#B45309"),
    (20, "BAJO", "#C2410C"),
    (0, "NO RECOMENDADO", "#B91C1C"),
]

BORME_CRITERIA_MAX = {
    "admin_age": ("Edad del administrador", 40),
    "stability": ("Estabilidad BORME", 15),
    "family": ("Empresa familiar", 20),
    "no_council": ("Sin consejo externo", 10),
    "cnae": ("Sector compatible", 10),
    "recent_activity": ("Actividad reciente", 25),
}

# Perfil objetivo de inversión (criterios Cabiedes)
TARGET = {
    "revenue_min": 10_000_000, "revenue_max": 15_000_000,
    "ebitda_min": 1_500_000, "ebitda_max": 3_000_000,
}


def score_band(score: Optional[float]):
    """(color_hex, etiqueta) de la banda del score; (None, 'Sin evaluar') si no hay."""
    if score is None:
        return None, "Sin evaluar"
    for threshold, label, color in BANDS:
        if score >= threshold:
            return color, label
    return BANDS[-1][2], BANDS[-1][1]


def _fmt_eur(v) -> str:
    if v is None:
        return "—"
    if v >= 1_000_000:
        return f"{v / 1_000_000:,.2f} M€".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{v:,.0f} €".replace(",", ".")


def _fmt_date(iso) -> str:
    if not iso:
        return "—"
    parts = str(iso)[:10].split("-")
    return f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else str(iso)


def _fit_mark(value, lo, hi) -> str:
    if value is None:
        return "—"
    if lo <= value <= hi:
        return "✓ objetivo"
    return "—"


# ============================ PDF ============================

def export_pdf(company: Company) -> bytes:
    """Informe ejecutivo PDF finance-grade de una empresa."""
    from reportlab.lib import colors
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable,
    )

    class ScoreGauge(Flowable):
        """Medidor donut (arco lleno + número central)."""

        def __init__(self, size, score):
            super().__init__()
            self.size, self.score = size, score

        def wrap(self, availWidth, availHeight):
            return (self.size, self.size)

        def draw(self):
            band_color, _ = score_band(self.score)
            pct = max(0.0, min(100.0, self.score or 0))
            sw = max(5, self.size / 14)
            r = (self.size - sw - 4) / 2
            cx = cy = self.size / 2
            self.canv.setStrokeColor(HexColor("#D8DEE6"))
            self.canv.setFillColor(HexColor("#FFFFFF"))
            self.canv.setLineWidth(sw)
            self.canv.circle(cx, cy, r, stroke=1, fill=1)
            if pct > 0:
                self.canv.setStrokeColor(HexColor(band_color))
                self.canv.setLineWidth(sw)
                self.canv.setLineCap(1)
                self.canv.arc(cx - r, cy - r, cx + r, cy + r, startAng=90, extent=-3.6 * pct)
            self.canv.setFillColor(HexColor(band_color if self.score is not None else "#9AA3AE"))
            fs = self.size * 0.3
            self.canv.setFont("Helvetica-Bold", fs)
            self.canv.drawCentredString(cx, cy - fs * 0.18, "—" if self.score is None else str(int(round(self.score))))
            self.canv.setFont("Helvetica", max(7, self.size * 0.075))
            self.canv.setFillColor(HexColor("#6B7280"))
            self.canv.drawCentredString(cx, cy - fs * 0.55, "de 100")

    class MiniBar(Flowable):
        """Barra de progreso fina."""

        def __init__(self, pct, color):
            super().__init__()
            self.pct, self.color = pct, color
            self.height = 5
            self.width = 1

        def wrap(self, availWidth, availHeight):
            self.width = availWidth
            return (availWidth, self.height)

        def draw(self):
            self.canv.setFillColor(HexColor(TRACK_GRAY))
            self.canv.rect(0, 0, self.width, self.height, stroke=0, fill=1)
            if self.pct:
                self.canv.setFillColor(HexColor(self.color))
                self.canv.rect(0, 0, self.width * min(100, self.pct) / 100, self.height, stroke=0, fill=1)

    # Desglose calculado al vuelo si la empresa no lo trae persistido
    if company.score_breakdown:
        sb = company.score_breakdown
    else:
        from .score import ScoreCalculator
        sb = ScoreCalculator().calculate(company)

    score = company.score
    band_color, band_label = score_band(score)
    fin = company.financial
    br = (sb.get("breakdown") or {}).get("borme") or {}

    txt = ParagraphStyle("cell", fontName="Helvetica", fontSize=9, leading=11.5)
    sub_style = ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5, leading=12, textColor=HexColor(TEXT_GRAY))
    small = ParagraphStyle("section", fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=HexColor(NAVY), spaceBefore=8, spaceAfter=3)
    muted = ParagraphStyle("muted", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=HexColor("#6B7280"))
    head_small = ParagraphStyle("hs", fontName="Helvetica", fontSize=7.5, leading=10, textColor=HexColor("#D6E2F0"))
    company_style = ParagraphStyle("company", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=HexColor(TEXT_DARK))

    def head_white(txt, size=13):
        return Paragraph(f"<b>{txt}</b>", ParagraphStyle("hw", fontName="Helvetica-Bold", fontSize=size, leading=size + 3, textColor=colors.white))

    def right(txt, size=8):
        return Paragraph(f'<font color="{TEXT_GRAY}"><b>{txt}</b></font>', ParagraphStyle("r", parent=txt, alignment=2, fontSize=8))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm, topMargin=10 * mm, bottomMargin=14 * mm,
        title=f"Informe Ejecutivo — {company.name}",
    )
    width, _ = A4
    inner = width - 32 * mm
    story = []

    # ---- Banda de cabecera ----
    header_tbl = Table(
        [[Paragraph("<b>Informe Ejecutivo de Candidata</b>", ParagraphStyle("hw2", fontName="Helvetica-Bold", fontSize=14, leading=17, textColor=colors.white)),
          Paragraph(f"<b>Search Fund Tool</b><br/>Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} · CONFIDENCIAL",
                    ParagraphStyle("hr", parent=head_small, alignment=2))]],
        colWidths=[inner * 0.6, inner * 0.4],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor(NAVY)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]),
    )
    story.append(header_tbl)
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(company.name or "Sin nombre", company_style))
    meta = [x for x in [company.cif, company.legal_form, company.province] if x]
    story.append(Paragraph(" · ".join(meta) or "—", sub_style))
    story.append(Spacer(1, 5 * mm))

    # ---- Medidor + interpretación ----
    interp = Paragraph(
        f'<font color="{band_color}"><b>{band_label}</b></font><br/>'
        f'<font size="9" color="{TEXT_GRAY}">Probabilidad de adquisición según las señales '
        f"del Registro Mercantil y los datos financieros.</font>",
        ParagraphStyle("interp", parent=txt, fontSize=10.5, leading=14),
    )
    story.append(Table(
        [[ScoreGauge(size=3.4 * 28.35, score=score), interp]],
        colWidths=[inner * 0.28, inner * 0.72],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]),
    ))
    story.append(Spacer(1, 3 * mm))

    # ---- Desglose del medidor + criterios ----
    borme_pct = sb.get("borme")
    fin_pct = sb.get("financial")

    def bar_cell(label, pct, color):
        label_cell = Paragraph(f'<font size="8" color="{TEXT_GRAY}">{label}</font>', txt)
        val_cell = Paragraph(f'<font size="8" color="{TEXT_GRAY}"><b>{"sin datos" if pct is None else f"{pct:.0f}%"}</b></font>',
                             ParagraphStyle("rv", parent=txt, fontSize=8, alignment=2))
        t = Table([[label_cell, val_cell], [MiniBar(pct, color), ""]],
                  colWidths=[inner * 0.25 - 10, 44],
                  style=TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (0, 0), 0)]))
        return t

    summary_tbl = Table(
        [[bar_cell("Señales BORME", borme_pct, NAVY), bar_cell("Solidez financiera", fin_pct, "#047857")]],
        colWidths=[inner * 0.5, inner * 0.5],
        style=TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 8)]),
    )
    story.append(summary_tbl)
    story.append(Spacer(1, 2 * mm))

    criteria_rows = [["Criterio", "Puntos", "Máximo"]]
    for key, (label, mx) in BORME_CRITERIA_MAX.items():
        val = br.get(key)
        criteria_rows.append([label, "—" if val is None else str(int(val)), str(mx)])
    story.append(Paragraph("Desglose del score", small))
    story.append(Table(
        criteria_rows,
        colWidths=[inner * 0.5, inner * 0.25, inner * 0.25],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#EAF0F7")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, HexColor(BORDER_GRAY)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#F7F9FC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]),
    ))
    story.append(Spacer(1, 5 * mm))

    # ---- Métricas financieras vs perfil objetivo ----
    def fit(v, lo, hi):
        return "✓ objetivo" if (v is not None and lo <= v <= hi) else "—"

    fin_rows = [
        ["Métrica", "Valor", "Perfil objetivo", "Encaje"],
        ["EBITDA", _fmt_eur(fin.ebitda), "1,5–3,0 M€", fit(fin.ebitda, TARGET["ebitda_min"], TARGET["ebitda_max"])],
        ["Facturación", _fmt_eur(fin.revenue), "10–15 M€", fit(fin.revenue, TARGET["revenue_min"], TARGET["revenue_max"])],
        ["Margen EBITDA", f"{fin.ebitda_margin:.0f}%" if fin.ebitda_margin else "—", "> 15%", "✓" if (fin.ebitda_margin or 0) > 15 else "—"],
        ["Empleados", str(fin.employees) if fin.employees else "—", "20–200", "✓" if (fin.employees or 0) and 20 <= fin.employees <= 200 else "—"],
        ["Fuente", fin.source or "—", "", ""],
        ["Año fiscal", str(fin.year) if fin.year else "—", "", ""],
    ]
    story.append(Paragraph("Métricas financieras", small))
    story.append(Table(
        fin_rows,
        colWidths=[inner * 0.22, inner * 0.26, inner * 0.27, inner * 0.21],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor(NAVY)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.4, HexColor(BORDER_GRAY)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#F7F9FC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]),
    ))
    story.append(Spacer(1, 5 * mm))

    # ---- Corporativos y contacto ----
    corp_rows = [
        ["Provincia", company.province or "—", "Web", company.website or "—"],
        ["Ciudad", company.city or "—", "Teléfono", company.phone or "—"],
        ["Dirección", company.address or "—", "Email", company.email or "—"],
        ["Fundación", _fmt_date(company.founded_date), "Forma legal", company.legal_form or "—"],
    ]
    story.append(Paragraph("Datos corporativos y contacto", small))
    story.append(Table(
        corp_rows,
        colWidths=[inner * 0.16, inner * 0.34, inner * 0.16, inner * 0.34],
        style=TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("GRID", (0, 0), (-1, -1), 0.4, HexColor(BORDER_GRAY)),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, HexColor("#F7F9FC")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]),
    ))
    story.append(Spacer(1, 5 * mm))

    # ---- Administradores ----
    if company.administrators:
        adm_rows = [["Administrador", "Cargo", "Desde"]]
        for a in company.administrators[:8]:
            adm_rows.append([a.name, a.role or "—", _fmt_date(a.since)])
        story.append(Paragraph("Administradores", small))
        story.append(Table(
            adm_rows,
            colWidths=[inner * 0.5, inner * 0.28, inner * 0.22],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor(NAVY)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.4, HexColor(BORDER_GRAY)),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#F5F8FB")]),
            ]),
        ))
        story.append(Spacer(1, 5 * mm))

    # ---- Dictamen del Agente (si está generado) ----
    if company.agent_opinion:
        story.append(Paragraph("Dictamen y análisis del Agente", small))
        story.append(Table(
            [[Paragraph(company.agent_opinion.replace("\n", "<br/>"),
                        ParagraphStyle("op", parent=txt, fontSize=9, leading=13, textColor=colors.HexColor(TEXT_DARK)))]],
            colWidths=[inner],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), HexColor("#EAF0F7")),
                ("BOX", (0, 0), (-1, -1), 0.6, HexColor(NAVY)),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]),
        ))
        story.append(Spacer(1, 5 * mm))

    # ---- Histórico BORME ----
    acts = company.borme.acts or []
    story.append(Paragraph("Registro histórico (BORME)", small))
    if acts:
        act_rows = [["Fecha", "Acto", "Detalle"]]
        for act in acts[:12]:
            act_rows.append([
                _fmt_date(act.get("date")),
                act.get("type") or "—",
                (act.get("details") or act.get("title") or "—")[:120],
            ])
        story.append(Table(
            act_rows,
            colWidths=[inner * 0.14, inner * 0.22, inner * 0.64],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), HexColor(NAVY)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, HexColor(BORDER_GRAY)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, HexColor("#F5F8FB")]),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]),
        ))
    else:
        story.append(Paragraph("Sin actos registrados en el caché.", sub_style))

    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph(
        f"Fuente de datos: {', '.join(company.data_sources) or '—'} · "
        "Informe generado automáticamente por Search Fund Tool. Uso interno; no constituye asesoramiento de inversión.",
        muted,
    ))

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setStrokeColor(HexColor(BORDER_GRAY))
        canvas.setLineWidth(0.5)
        canvas.line(16 * mm, 12 * mm, width - 16 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(HexColor(TEXT_GRAY))
        canvas.drawString(16 * mm, 8 * mm, "Search Fund Tool — Informe ejecutivo de candidata · CONFIDENCIAL")
        canvas.drawRightString(width - 16 * mm, 8 * mm, f"Página {doc_.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


# ============================ EXCEL ============================

EXCEL_HEADERS = [
    "CIF", "Nombre", "Forma legal", "Provincia", "Ciudad", "Dirección",
    "Web", "Teléfono", "Email", "Antigüedad (años)",
    "EBITDA (€)", "Facturación (€)", "Margen (%)", "Empleados", "Fuente fin.",
    "Score", "Clasificación", "Actos BORME", "Últ. actividad",
    "Administradores", "Tags", "Notas",
]


def _argb(hex6: str) -> str:
    """openpyxl exige aRGB de 8 dígitos en Font.color."""
    return "FF" + hex6.lstrip("#")


def export_excel(companies: List[Company]) -> bytes:
    """Excel finance-grade: hoja 'Candidatas' estilizada + hoja 'Leyenda'."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Candidatas"

    head_fill = PatternFill("solid", start_color=NAVY.lstrip("#"), end_color=NAVY.lstrip("#"))
    head_font = Font(color=_argb("FFFFFF"), bold=True, size=10)
    title_font = Font(color=_argb(NAVY), bold=True, size=14)
    sub_font = Font(color=_argb("6B7280"), size=9)
    thin = Side(style="thin", color="C9D3E0")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    alt_fill = PatternFill("solid", start_color="F5F8FB", end_color="F5F8FB")

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=12)
    ws.cell(row=1, column=1, value="Search Fund Tool — Ranking de candidatas").font = title_font
    ws.cell(row=2, column=1, value=f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} · {len(companies)} empresas · CONFIDENCIAL").font = sub_font

    HEADER_ROW = 4
    for col, header in enumerate(EXCEL_HEADERS, start=1):
        cell = ws.cell(row=HEADER_ROW, column=col, value=header)
        cell.fill = head_fill
        cell.font = head_font
        cell.border = border
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    label_bg = {"MUY BUENO": "D1FAE5", "BUENO": "DCFCE7", "MODERADO": "FEF3C7",
                "BAJO": "FFEDD5", "NO RECOMENDADO": "FEE2E2", "Sin evaluar": "F3F4F6"}
    label_fg = {"MUY BUENO": "065F46", "BUENO": "166534", "MODERADO": "92400E",
                "BAJO": "9A3412", "NO RECOMENDADO": "991B1B", "Sin evaluar": "6B7280"}

    DATA_START = HEADER_ROW + 1
    for r, company in enumerate(companies, start=DATA_START):
        d = company.to_export_dict()
        fin = company.financial
        color, label = score_band(company.score)
        row = [
            d.get("cif") or "",
            d.get("name") or "",
            d.get("legal_form") or "",
            d.get("province") or "",
            d.get("city") or "",
            d.get("address") or "",
            d.get("website") or "",
            d.get("phone") or "",
            d.get("email") or "",
            d.get("age_years"),
            fin.ebitda,
            fin.revenue,
            fin.ebitda_margin,
            fin.employees,
            fin.source or "",
            round(d["score"], 1) if d.get("score") is not None else None,
            label,
            d.get("borme_acts_count"),
            _fmt_date(d.get("last_borme_activity")) if d.get("last_borme_activity") else "",
            ", ".join(a.name for a in company.administrators[:5]) or "",
            ", ".join(d.get("tags") or []) if d.get("tags") else "",
            d.get("notes") or "",
        ]
        for col, value in enumerate(row, start=1):
            cell = ws.cell(row=r, column=col, value=value)
            cell.border = border
            if (r - DATA_START) % 2 == 1:
                cell.fill = alt_fill
            header = EXCEL_HEADERS[col - 1]
            if header in ("EBITDA (€)", "Facturación (€)"):
                cell.number_format = "#,##0 €"
            elif header == "Margen (%)":
                cell.number_format = '0"%"'
            elif header in ("Score", "Clasificación") and company.score is not None:
                cell.fill = PatternFill("solid", start_color=label_bg.get(label, "F3F4F6"), end_color=label_bg.get(label, "F3F4F6"))
                cell.font = Font(bold=True, color=_argb(label_fg.get(label, "1A1A1A")))
                if header == "Score":
                    cell.number_format = "0"

    widths = [12, 34, 9, 11, 12, 26, 22, 13, 22, 9, 12, 13, 9, 10, 10, 8, 16, 10, 12, 30, 14, 28]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = f"C{DATA_START}"
    ws.auto_filter.ref = f"A{HEADER_ROW}:{get_column_letter(len(EXCEL_HEADERS))}{DATA_START + len(companies) - 1}"

    # ---- Hoja Leyenda ----
    lg = wb.create_sheet("Leyenda")
    lg.merge_cells("A1:C1")
    lg.cell(row=1, column=1, value="Metodología del Score").font = Font(color=_argb(NAVY), bold=True, size=13)
    lg.cell(row=3, column=1, value="Banda").fill = head_fill
    lg.cell(row=3, column=1).font = head_font
    lg.cell(row=3, column=2, value="Rango").fill = head_fill
    lg.cell(row=3, column=2).font = head_font
    lg.cell(row=3, column=3, value="Significado").fill = head_fill
    lg.cell(row=3, column=3).font = head_font
    bands = [
        ("MUY BUENO", "80–100", "Alta probabilidad de transición"),
        ("BUENO", "60–79", "Posible candidato a investigar"),
        ("MODERADO", "40–59", "Requiere más información"),
        ("BAJO", "20–39", "Poca probabilidad de venta"),
        ("NO RECOMENDADO", "0–19", "No parece candidato"),
    ]
    for i, (band, rng, meaning) in enumerate(bands, start=4):
        lg.cell(row=i, column=1, value=band).font = Font(bold=True, color=_argb(BANDS[i - 4][2]))
        lg.cell(row=i, column=2, value=rng)
        lg.cell(row=i, column=3, value=meaning)
    extra = [
        (10, "Perfil objetivo de inversión"),
        (11, "Facturación 10–15 M€ · EBITDA 1,5–3 M€ · Empleados 20–200"),
        (13, "Score = 60% señales BORME + 40% solidez financiera"),
        (14, "Señales BORME: edad del administrador, estabilidad, empresa familiar, consejo externo, sector CNAE, actividad reciente."),
    ]
    for r_i, val in extra:
        lg.cell(row=r_i, column=1, value=val)
    lg.cell(row=10, column=1).font = Font(bold=True, color=_argb(NAVY))
    lg.column_dimensions["A"].width = 38
    lg.column_dimensions["B"].width = 12
    lg.column_dimensions["C"].width = 40

    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
