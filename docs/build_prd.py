# -*- coding: utf-8 -*-
"""
Render the ShebaLocal PRD to PDF.

    python docs/build_prd.py

Reads content from prd_content.py so prose and layout stay separate.
Requires: reportlab
"""

import os
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, ListFlowable, ListItem,
    NextPageTemplate, PageBreak, PageTemplate, Paragraph, Preformatted,
    Spacer, Table, TableStyle,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prd_content as C  # noqa: E402


# --------------------------------------------------------------------------
# Palette
# --------------------------------------------------------------------------
INK        = colors.HexColor("#14213D")   # headings, dark text
BODY       = colors.HexColor("#2B2B33")   # body copy
MUTED      = colors.HexColor("#6B7280")   # captions, footer
ACCENT     = colors.HexColor("#0F766E")   # teal: rules, h2 accents
ACCENT_LT  = colors.HexColor("#CCFBF1")   # callout background
BAND       = colors.HexColor("#F1F5F9")   # table header band
STRIPE     = colors.HexColor("#F8FAFC")   # table zebra stripe
LINE       = colors.HexColor("#D9DEE5")   # hairlines
CODE_BG    = colors.HexColor("#F6F8FA")
CODE_BRD   = colors.HexColor("#E2E8F0")

PAGE_W, PAGE_H = A4
LM = RM = 20 * mm
TM = 20 * mm
BM = 18 * mm
CONTENT_W = PAGE_W - LM - RM


# --------------------------------------------------------------------------
# Styles
# --------------------------------------------------------------------------
def build_styles():
    ss = getSampleStyleSheet()
    S = {}

    S["h1"] = ParagraphStyle(
        "h1", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=17,
        textColor=INK, leading=21, spaceBefore=2, spaceAfter=9,
    )
    S["h2"] = ParagraphStyle(
        "h2", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=12.5,
        textColor=ACCENT, leading=16, spaceBefore=14, spaceAfter=6,
    )
    S["h3"] = ParagraphStyle(
        "h3", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=10.5,
        textColor=INK, leading=14, spaceBefore=10, spaceAfter=4,
    )
    S["p"] = ParagraphStyle(
        "p", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5,
        textColor=BODY, leading=14.5, spaceAfter=7, alignment=TA_JUSTIFY,
    )
    S["li"] = ParagraphStyle(
        "li", parent=S["p"], spaceAfter=3.5, alignment=TA_LEFT, leading=13.8,
    )
    S["th"] = ParagraphStyle(
        "th", parent=ss["Normal"], fontName="Helvetica-Bold", fontSize=8.3,
        textColor=INK, leading=11.2,
    )
    S["td"] = ParagraphStyle(
        "td", parent=ss["Normal"], fontName="Helvetica", fontSize=8.3,
        textColor=BODY, leading=11.2,
    )
    S["code"] = ParagraphStyle(
        "code", parent=ss["Code"], fontName="Courier", fontSize=7.6,
        textColor=colors.HexColor("#1F2937"), leading=10.4,
        leftIndent=0, rightIndent=0, firstLineIndent=0,
        spaceBefore=0, spaceAfter=0,
    )
    S["callout_t"] = ParagraphStyle(
        "callout_t", parent=ss["Normal"], fontName="Helvetica-Bold",
        fontSize=9.5, textColor=colors.HexColor("#115E59"), leading=13,
        spaceAfter=3,
    )
    S["callout_b"] = ParagraphStyle(
        "callout_b", parent=ss["Normal"], fontName="Helvetica", fontSize=9,
        textColor=colors.HexColor("#134E4A"), leading=13.5,
        alignment=TA_JUSTIFY,
    )

    # cover
    S["cv_title"] = ParagraphStyle(
        "cv_title", parent=ss["Normal"], fontName="Helvetica-Bold",
        fontSize=46, textColor=INK, leading=50, alignment=TA_CENTER,
    )
    S["cv_sub"] = ParagraphStyle(
        "cv_sub", parent=ss["Normal"], fontName="Helvetica", fontSize=15,
        textColor=ACCENT, leading=20, alignment=TA_CENTER,
    )
    S["cv_type"] = ParagraphStyle(
        "cv_type", parent=ss["Normal"], fontName="Helvetica-Bold",
        fontSize=10.5, textColor=MUTED, leading=15, alignment=TA_CENTER,
    )
    S["cv_meta"] = ParagraphStyle(
        "cv_meta", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5,
        textColor=MUTED, leading=15, alignment=TA_CENTER,
    )
    S["cv_pitch"] = ParagraphStyle(
        "cv_pitch", parent=ss["Normal"], fontName="Helvetica-Oblique",
        fontSize=11, textColor=BODY, leading=17, alignment=TA_CENTER,
    )
    # TOC
    S["toc_h"] = ParagraphStyle(
        "toc_h", parent=ss["Normal"], fontName="Helvetica", fontSize=10,
        textColor=BODY, leading=17,
    )
    return S


ST = build_styles()


# --------------------------------------------------------------------------
# Page furniture
# --------------------------------------------------------------------------
def cover_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(INK)
    canvas.rect(0, PAGE_H - 12 * mm, PAGE_W, 12 * mm, stroke=0, fill=1)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, PAGE_H - 14.5 * mm, PAGE_W, 2.5 * mm, stroke=0, fill=1)
    canvas.setFillColor(INK)
    canvas.rect(0, 0, PAGE_W, 8 * mm, stroke=0, fill=1)
    canvas.restoreState()


def body_page(canvas, doc):
    canvas.saveState()
    # header rule + running title
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(LM, PAGE_H - TM + 6 * mm, PAGE_W - RM, PAGE_H - TM + 6 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(LM, PAGE_H - TM + 8 * mm,
                      "%s  |  %s" % (C.TITLE, C.DOC_TYPE))
    canvas.drawRightString(PAGE_W - RM, PAGE_H - TM + 8 * mm,
                           "v%s" % C.VERSION)
    # footer
    canvas.line(LM, BM - 3 * mm, PAGE_W - RM, BM - 3 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(LM, BM - 7.5 * mm, C.DATE)
    canvas.drawRightString(PAGE_W - RM, BM - 7.5 * mm,
                           "Page %d" % (canvas.getPageNumber() - 2))
    canvas.restoreState()


def plain_page(canvas, doc):
    """TOC page: footer only, no page number."""
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(LM, BM - 3 * mm, PAGE_W - RM, BM - 3 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_W - RM, BM - 7.5 * mm, C.TITLE)
    canvas.restoreState()


# --------------------------------------------------------------------------
# Flowable builders
# --------------------------------------------------------------------------
def rule(width=CONTENT_W, color=ACCENT, thickness=1.6, space_after=8):
    t = Table([[""]], colWidths=[width], rowHeights=[thickness])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("LINEBELOW", (0, 0), (-1, -1), 0, color),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    return [t, Spacer(1, space_after)]


def make_table(spec):
    cols = spec["cols"]
    widths = [w * CONTENT_W for w in spec["widths"]]

    data = [[Paragraph(c, ST["th"]) for c in cols]]
    for row in spec["rows"]:
        data.append([Paragraph(str(c), ST["td"]) for c in row])

    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), BAND),
        ("LINEBELOW", (0, 0), (-1, 0), 0.9, ACCENT),
        ("LINEBELOW", (0, 1), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), STRIPE))
    t.setStyle(TableStyle(style))
    return [t, Spacer(1, 10)]


def make_code(lines):
    txt = "\n".join(lines)
    pre = Preformatted(txt, ST["code"])
    t = Table([[pre]], colWidths=[CONTENT_W], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CODE_BG),
        ("BOX", (0, 0), (-1, -1), 0.6, CODE_BRD),
        ("LINEBEFORE", (0, 0), (0, -1), 2.2, ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return [t, Spacer(1, 10)]


def make_callout(payload):
    inner = [Paragraph(payload["title"], ST["callout_t"]),
             Paragraph(payload["body"], ST["callout_b"])]
    t = Table([[inner]], colWidths=[CONTENT_W], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), ACCENT_LT),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
    ]))
    return [KeepTogether([t]), Spacer(1, 11)]


def make_list(items, ordered=False):
    lis = [ListItem(Paragraph(i, ST["li"]), leftIndent=14,
                    value=None) for i in items]
    lf = ListFlowable(
        lis,
        bulletType="1" if ordered else "bullet",
        start="1" if ordered else None,
        bulletFontName="Helvetica",
        bulletFontSize=8.5,
        bulletColor=ACCENT,
        leftIndent=16,
        bulletDedent=12,
        spaceAfter=8,
    )
    return [lf, Spacer(1, 3)]


# --------------------------------------------------------------------------
# Document assembly
# --------------------------------------------------------------------------
def cover_flowables():
    f = [Spacer(1, 52 * mm)]
    f.append(Paragraph(C.TITLE, ST["cv_title"]))
    f.append(Spacer(1, 5))
    f.append(Paragraph(C.SUBTITLE, ST["cv_sub"]))
    f.append(Spacer(1, 11 * mm))

    t = Table([[""]], colWidths=[46 * mm], rowHeights=[2])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), ACCENT)]))
    t.hAlign = "CENTER"
    f.append(t)

    f.append(Spacer(1, 11 * mm))
    f.append(Paragraph(C.DOC_TYPE.upper(), ST["cv_type"]))
    f.append(Spacer(1, 16 * mm))
    f.append(Paragraph(
        "A marketplace connecting customers with verified local service "
        "providers &mdash; built around a transparent, multi-factor trust "
        "model rather than a single star rating.",
        ST["cv_pitch"]))
    f.append(Spacer(1, 26 * mm))

    meta = [
        ["Version", C.VERSION],
        ["Status", C.STATUS],
        ["Date", C.DATE],
        ["Author", C.AUTHOR],
        ["Stack", "Django &middot; DRF &middot; React (JS) &middot; PostgreSQL"],
    ]
    rows = [[Paragraph("<b>%s</b>" % k, ST["cv_meta"]),
             Paragraph(v, ST["cv_meta"])] for k, v in meta]
    mt = Table(rows, colWidths=[30 * mm, 60 * mm], hAlign="CENTER")
    mt.setStyle(TableStyle([
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (1, 0), (1, -1), "LEFT"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    f.append(mt)
    return f


def toc_flowables():
    f = [Paragraph("Contents", ST["h1"])]
    f += rule()
    f.append(Spacer(1, 4))

    entries = [t for k, t in C.DOC if k == "h1"]
    rows = []
    for e in entries:
        num, _, name = e.partition(". ")
        rows.append([
            Paragraph("<font color='#0F766E'><b>%s</b></font>" % num,
                      ST["toc_h"]),
            Paragraph(name, ST["toc_h"]),
        ])
    t = Table(rows, colWidths=[12 * mm, CONTENT_W - 12 * mm], hAlign="LEFT")
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#EDF0F4")),
    ]))
    f.append(t)
    return f


def body_flowables():
    out = []
    for kind, payload in C.DOC:
        if kind == "h1":
            out.append(Paragraph(payload, ST["h1"]))
            out += rule()
        elif kind == "h2":
            out.append(Paragraph(payload, ST["h2"]))
        elif kind == "h3":
            out.append(Paragraph(payload, ST["h3"]))
        elif kind == "p":
            out.append(Paragraph(payload, ST["p"]))
        elif kind == "bullets":
            out += make_list(payload, ordered=False)
        elif kind == "numbers":
            out += make_list(payload, ordered=True)
        elif kind == "table":
            out += make_table(payload)
        elif kind == "code":
            out += make_code(payload)
        elif kind == "callout":
            out += make_callout(payload)
        elif kind == "spacer":
            out.append(Spacer(1, payload))
        elif kind == "pagebreak":
            out.append(PageBreak())
        else:
            raise ValueError("unknown flowable kind: %r" % kind)
    return out


def build(out_path):
    doc = BaseDocTemplate(
        out_path, pagesize=A4,
        leftMargin=LM, rightMargin=RM, topMargin=TM, bottomMargin=BM,
        title="%s - %s" % (C.TITLE, C.DOC_TYPE),
        author=C.AUTHOR,
        subject="Product Requirements Document for %s" % C.SUBTITLE,
    )

    frame = Frame(LM, BM, CONTENT_W, PAGE_H - TM - BM, id="main",
                  leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0)

    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=cover_page),
        PageTemplate(id="toc", frames=[frame], onPage=plain_page),
        PageTemplate(id="body", frames=[frame], onPage=body_page),
    ])

    story = []
    story += cover_flowables()
    story.append(NextPageTemplate("toc"))
    story.append(PageBreak())
    story += toc_flowables()
    story.append(NextPageTemplate("body"))
    story.append(PageBreak())
    story += body_flowables()

    doc.build(story)
    return out_path


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    target = os.path.join(here, "ShebaLocal-PRD.pdf")
    build(target)
    size = os.path.getsize(target)
    print("Wrote %s (%.1f KB)" % (target, size / 1024.0))
