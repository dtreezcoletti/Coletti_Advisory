"""
Coletti OS v2.0 — Document Generation Engine
Produces print-ready PDFs for litigation, forensic, and enterprise paperwork.
"""

import io
from datetime import date, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


FIRM = "Coletti & Co."
FOOTER_NOTE = "CONFIDENTIAL — ATTORNEY WORK PRODUCT — NOT FOR DISTRIBUTION"

# Colour palette
DARK = colors.HexColor("#0d1117")
BLUE = colors.HexColor("#1a73e8")
LIGHT_GREY = colors.HexColor("#f2f2f2")
MID_GREY = colors.HexColor("#cccccc")
RED = colors.HexColor("#c0392b")
BLACK = colors.black
WHITE = colors.white


# ── Style registry ────────────────────────────────────────────────────────────

def _styles():
    base = getSampleStyleSheet()
    custom = {
        "doc_title": ParagraphStyle(
            "doc_title", parent=base["Title"],
            fontSize=16, textColor=BLACK, spaceAfter=4, alignment=TA_CENTER,
        ),
        "doc_sub": ParagraphStyle(
            "doc_sub", parent=base["Normal"],
            fontSize=9, textColor=colors.grey, spaceAfter=12, alignment=TA_CENTER,
            fontName="Helvetica-Oblique",
        ),
        "section": ParagraphStyle(
            "section", parent=base["Normal"],
            fontSize=9, textColor=WHITE, fontName="Helvetica-Bold",
            spaceAfter=6, spaceBefore=10,
        ),
        "kv_label": ParagraphStyle(
            "kv_label", parent=base["Normal"],
            fontSize=9, textColor=colors.grey, fontName="Helvetica-Bold",
        ),
        "kv_value": ParagraphStyle(
            "kv_value", parent=base["Normal"],
            fontSize=9, textColor=BLACK, fontName="Helvetica",
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, textColor=BLACK, fontName="Helvetica",
            spaceAfter=4, leading=13,
        ),
        "motion_title": ParagraphStyle(
            "motion_title", parent=base["Normal"],
            fontSize=10, textColor=BLACK, fontName="Helvetica-Bold",
            spaceBefore=6, spaceAfter=2,
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"],
            fontSize=7, textColor=colors.grey, alignment=TA_CENTER,
        ),
        "small_label": ParagraphStyle(
            "small_label", parent=base["Normal"],
            fontSize=8, textColor=colors.grey, fontName="Helvetica",
        ),
    }
    return custom


# ── Header / footer callbacks ─────────────────────────────────────────────────

def _header_footer(canvas, doc, title: str, subtitle: str = ""):
    canvas.saveState()
    w, h = letter

    # Header bar
    canvas.setFillColor(DARK)
    canvas.rect(0, h - 50, w, 50, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(0.6 * inch, h - 22, FIRM.upper())
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(w - 0.6 * inch, h - 22, datetime.now().strftime("%Y-%m-%d %H:%M"))
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawCentredString(w / 2, h - 40, title)
    if subtitle:
        canvas.setFont("Helvetica-Oblique", 8)
        canvas.setFillColor(MID_GREY)
        canvas.drawCentredString(w / 2, h - 50, subtitle)

    # Footer
    canvas.setFillColor(colors.grey)
    canvas.setFont("Helvetica-Oblique", 7)
    canvas.drawCentredString(w / 2, 28, FOOTER_NOTE)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(w / 2, 18, f"Page {doc.page}")

    canvas.restoreState()


def _make_doc(buf, title: str, subtitle: str = "") -> SimpleDocTemplate:
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    doc._page_title = title
    doc._page_subtitle = subtitle
    doc.onPage = lambda c, d: _header_footer(c, d, title, subtitle)
    return doc


# ── Shared flowable helpers ───────────────────────────────────────────────────

def _section_header(label: str, styles: dict):
    tbl = Table([[Paragraph(f"  {label.upper()}", styles["section"])]], colWidths=["100%"])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _kv_table(rows: list, styles: dict):
    data = [[Paragraph(k, styles["kv_label"]), Paragraph(str(v), styles["kv_value"])] for k, v in rows]
    tbl = Table(data, colWidths=[1.6 * inch, 5.1 * inch])
    tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, LIGHT_GREY]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return tbl


def _ledger_table(transactions, styles: dict):
    headers = ["Date", "Amount", "Description", "Category", "Dissipation"]
    col_w = [0.85 * inch, 0.85 * inch, 2.6 * inch, 1.2 * inch, 0.75 * inch]
    data = [[Paragraph(h, styles["kv_label"]) for h in headers]]
    for t in transactions:
        flag = "YES ⚠" if t.is_marital_dissipation else "—"
        data.append([
            Paragraph(t.effective_date, styles["body"]),
            Paragraph(f"${t.amount:,.2f}", styles["body"]),
            Paragraph(t.description[:60], styles["body"]),
            Paragraph(t.category, styles["body"]),
            Paragraph(flag, styles["body"]),
        ])
    tbl = Table(data, colWidths=col_w, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.25, MID_GREY),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
    ]
    for i, t in enumerate(transactions, 1):
        if t.is_marital_dissipation:
            style.append(("TEXTCOLOR", (4, i), (4, i), RED))
            style.append(("FONTNAME", (4, i), (4, i), "Helvetica-Bold"))
    tbl.setStyle(TableStyle(style))
    return tbl


# ── Document builders ─────────────────────────────────────────────────────────

def build_docket_summary(litigation) -> bytes:
    buf = io.BytesIO()
    doc = _make_doc(
        buf,
        title="LITIGATION DOCKET SUMMARY",
        subtitle=f"Case № {litigation.case_number}  ·  {litigation.jurisdiction}",
    )
    s = _styles()
    story = []

    story.append(_section_header("Case Information", s))
    story.append(Spacer(1, 4))
    story.append(_kv_table([
        ("Case Number:", litigation.case_number),
        ("Jurisdiction:", litigation.jurisdiction),
        ("Presiding Judge:", litigation.judge),
        ("Rule 36 Default:", f"{litigation.rule_36_days_default} Days"),
        ("Docket Leverage Score:", str(litigation.evaluate_docket_leverage())),
        ("Report Date:", date.today().isoformat()),
    ], s))
    story.append(Spacer(1, 10))

    story.append(_section_header("Filed Motions", s))
    story.append(Spacer(1, 4))
    for i, m in enumerate(litigation.motions, 1):
        story.append(Paragraph(f"{i}. {m.title}", s["motion_title"]))
        story.append(_kv_table([
            ("Filed:", m.date_filed),
            ("Hearing:", m.hearing_date or "TBD"),
            ("Status:", m.status),
            ("Strategic Objective:", m.strategic_objective),
        ], s))
        story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=6))
    story.append(Spacer(1, 6))

    story.append(_section_header("Active Subpoenas", s))
    story.append(Spacer(1, 4))
    for i, sub in enumerate(litigation.active_subpoenas, 1):
        story.append(Paragraph(f"{i}.  {sub}", s["body"]))
    story.append(Spacer(1, 10))

    story.append(_section_header("Leverage Analysis", s))
    story.append(Spacer(1, 4))
    score = litigation.evaluate_docket_leverage()
    if score >= 200:
        analysis = ("Docket position is DOMINANT. Rule 36 deemed admissions are established and "
                    "multiple evidentiary subpoenas are active. Opposing party has minimal procedural "
                    "recourse absent direct judicial intervention.")
    elif score >= 100:
        analysis = ("Docket position is STRONG. Rule 36 default threshold exceeded. Continue "
                    "pressing discovery and monitoring subpoena returns.")
    else:
        analysis = ("Docket position is BUILDING. Escalate filing cadence and expand subpoena "
                    "targets to increase procedural leverage.")
    story.append(Paragraph(analysis, s["body"]))

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, doc._page_title, doc._page_subtitle),
              onLaterPages=lambda c, d: _header_footer(c, d, doc._page_title, doc._page_subtitle))
    return buf.getvalue()


def build_forensic_report(forensics) -> bytes:
    buf = io.BytesIO()
    doc = _make_doc(
        buf,
        title="FORENSIC ACCOUNTING REPORT",
        subtitle=f"{forensics.institution}  ·  Account {forensics.target_account}",
    )
    s = _styles()
    story = []

    story.append(_section_header("Account Summary", s))
    story.append(Spacer(1, 4))
    story.append(_kv_table([
        ("Institution:", forensics.institution),
        ("Target Account:", forensics.target_account),
        ("Known Balance:", f"${forensics.known_balance:,.2f}"),
        ("Report Date:", date.today().isoformat()),
    ], s))
    story.append(Spacer(1, 10))

    story.append(_section_header("Dissipation Analysis", s))
    story.append(Spacer(1, 4))
    story.append(_kv_table([
        ("Transactions Reviewed:", str(len(forensics.transactions))),
        ("Total Funds Reviewed:", f"${forensics.calculate_total():,.2f}"),
        ("Marital Dissipation Identified:", f"${forensics.calculate_dissipation():,.2f}"),
        ("Dissipation Rate:", f"{forensics.dissipation_rate():.1f}%"),
    ], s))
    story.append(Spacer(1, 10))

    if forensics.transactions:
        story.append(_section_header("Transaction Ledger", s))
        story.append(Spacer(1, 4))
        story.append(_ledger_table(forensics.transactions, s))
        story.append(Spacer(1, 10))

    story.append(_section_header("Evidentiary Notes", s))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "All transactions flagged as marital dissipation represent funds diverted from the marital "
        "estate without consent or legitimate marital purpose. This ledger is prepared for litigation "
        "support and may be submitted as an exhibit in conjunction with certified bank records obtained "
        "via subpoena.", s["body"]
    ))

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, doc._page_title, doc._page_subtitle),
              onLaterPages=lambda c, d: _header_footer(c, d, doc._page_title, doc._page_subtitle))
    return buf.getvalue()


def build_client_brief(enterprise) -> bytes:
    buf = io.BytesIO()
    doc = _make_doc(
        buf,
        title="CLIENT PORTFOLIO BRIEF",
        subtitle=f"{enterprise.firm_name}  ·  {enterprise.founder}",
    )
    s = _styles()
    story = []

    story.append(_section_header("Firm Overview", s))
    story.append(Spacer(1, 4))
    story.append(_kv_table([
        ("Firm Name:", enterprise.firm_name),
        ("Chief Executive:", enterprise.founder),
        ("Total Portfolios:", str(len(enterprise.active_portfolios))),
        ("Active Retainers:", str(enterprise.retainer_count())),
        ("Report Date:", date.today().isoformat()),
    ], s))
    story.append(Spacer(1, 10))

    story.append(_section_header("Client Engagements", s))
    story.append(Spacer(1, 4))

    if enterprise.active_portfolios:
        for i, c in enumerate(enterprise.active_portfolios, 1):
            story.append(Paragraph(f"{i}. {c.entity_name}", s["motion_title"]))
            story.append(_kv_table([
                ("Phase:", c.phase),
                ("Retainer:", "Active" if c.retainer_active else "None"),
                ("Objective:", c.primary_objective),
            ], s))
            story.append(HRFlowable(width="100%", thickness=0.5, color=MID_GREY, spaceAfter=6))
    else:
        story.append(Paragraph("No client engagements on record.", s["body"]))

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, doc._page_title, doc._page_subtitle),
              onLaterPages=lambda c, d: _header_footer(c, d, doc._page_title, doc._page_subtitle))
    return buf.getvalue()


def build_master_report(sys_instance) -> bytes:
    buf = io.BytesIO()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    doc = _make_doc(
        buf,
        title="COLETTI OS — MASTER OPERATIONAL REPORT",
        subtitle=f"Generated {timestamp}",
    )
    s = _styles()
    story = []

    # ── Litigation ────────────────────────────────────────────────────────────
    lit = sys_instance.litigation
    story.append(_section_header(f"LITIGATION OPS — CASE {lit.case_number}", s))
    story.append(Spacer(1, 4))
    story.append(_kv_table([
        ("Jurisdiction:", lit.jurisdiction),
        ("Judge:", lit.judge),
        ("Rule 36 Default:", f"{lit.rule_36_days_default} Days"),
        ("Docket Leverage:", str(lit.evaluate_docket_leverage())),
    ], s))
    story.append(Spacer(1, 8))
    for i, m in enumerate(lit.motions, 1):
        story.append(Paragraph(f"{i}. {m.title}", s["motion_title"]))
        story.append(_kv_table([
            ("Status:", m.status),
            ("Hearing:", m.hearing_date or "TBD"),
            ("Objective:", m.strategic_objective),
        ], s))
        story.append(Spacer(1, 4))
    story.append(Paragraph("Active Subpoenas:", s["kv_label"]))
    for sub in lit.active_subpoenas:
        story.append(Paragraph(f"• {sub}", s["body"]))

    story.append(PageBreak())

    # ── Income Disparity ──────────────────────────────────────────────────────
    idp = sys_instance.income_disparity
    story.append(_section_header("INCOME DISPARITY ANALYSIS", s))
    story.append(Spacer(1, 4))
    story.append(_kv_table([
        ("Sworn Monthly Net:", f"${idp.sworn_monthly_net:,.2f}"),
        ("Verified Monthly Net:", f"${idp.verified_monthly_net:,.2f}"),
        ("Monthly Understatement:", f"${idp.monthly_understatement():,.2f}  ({idp.understatement_pct():.1f}% above sworn)"),
        ("Tracking Period:", f"{idp.tracking_months} Months"),
        ("Cumulative Understatement:", f"${idp.cumulative_understatement():,.2f}"),
        ("Sequestered Hard Assets:", f"${idp.sequestered_hard_assets:,.2f}"),
        ("Total Concealed Value:", f"${idp.total_concealed_value():,.2f}"),
    ], s))
    story.append(Spacer(1, 10))

    # ── Forensics ─────────────────────────────────────────────────────────────
    foren = sys_instance.forensics
    story.append(_section_header(f"FORENSIC OPS — {foren.institution}", s))
    story.append(Spacer(1, 4))
    story.append(_kv_table([
        ("Account:", foren.target_account),
        ("Known Balance:", f"${foren.known_balance:,.2f}"),
        ("Transactions Reviewed:", str(len(foren.transactions))),
        ("Total Reviewed:", f"${foren.calculate_total():,.2f}"),
        ("Dissipation Identified:", f"${foren.calculate_dissipation():,.2f}"),
        ("Dissipation Rate:", f"{foren.dissipation_rate():.1f}%"),
    ], s))
    if foren.transactions:
        story.append(Spacer(1, 6))
        story.append(_ledger_table(foren.transactions, s))

    story.append(PageBreak())

    # ── Enterprise ────────────────────────────────────────────────────────────
    ent = sys_instance.enterprise
    story.append(_section_header("ENTERPRISE OPS — COLETTI & CO.", s))
    story.append(Spacer(1, 4))
    story.append(_kv_table([
        ("Firm:", ent.firm_name),
        ("Chief Executive:", ent.founder),
        ("Total Clients:", str(len(ent.active_portfolios))),
        ("Retainers Active:", str(ent.retainer_count())),
    ], s))
    story.append(Spacer(1, 8))
    for i, c in enumerate(ent.active_portfolios, 1):
        story.append(Paragraph(f"{i}. {c.entity_name}", s["motion_title"]))
        story.append(_kv_table([
            ("Phase:", c.phase),
            ("Retainer:", "Active" if c.retainer_active else "None"),
            ("Objective:", c.primary_objective),
        ], s))
        story.append(Spacer(1, 4))

    doc.build(story, onFirstPage=lambda c, d: _header_footer(c, d, doc._page_title, doc._page_subtitle),
              onLaterPages=lambda c, d: _header_footer(c, d, doc._page_title, doc._page_subtitle))
    return buf.getvalue()
