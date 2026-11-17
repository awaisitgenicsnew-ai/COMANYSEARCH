"""
report.py - Turn scraped company data into a formatted Word (.docx) report.
"""

import re
from datetime import datetime

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

MAX_PARAGRAPHS_PER_PAGE = 25


def _safe(text: str) -> str:
    # strip characters Word XML can't store
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text or "")


def _kv_table(doc, rows):
    table = doc.add_table(rows=0, cols=2)
    table.style = "Light Grid Accent 1"
    for key, value in rows:
        cells = table.add_row().cells
        cells[0].text = key
        cells[1].text = _safe(value) or "—"
        cells[0].paragraphs[0].runs[0].bold = True
    return table


def build_report(company_name: str, data: dict, out_path: str) -> str:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    # ---- Title
    title = doc.add_heading(_safe(company_name), level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = sub.add_run(f"Company Website Report  •  {data['home_url']}\n"
                      f"Generated {datetime.now():%d %B %Y, %H:%M}")
    run.font.size = Pt(10)
    run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    # ---- Overview
    doc.add_heading("1. Overview", level=1)
    _kv_table(doc, [
        ("Company name", company_name),
        ("Website", data["home_url"]),
        ("Site title", data["title"]),
        ("Description", data["description"]),
        ("Keywords", data["keywords"]),
        ("Pages scanned", str(len(data["pages"]))),
    ])

    # ---- Contact
    doc.add_heading("2. Contact Information", level=1)
    _kv_table(doc, [
        ("Emails", "\n".join(data["emails"])),
        ("Phone numbers", "\n".join(data["phones"])),
        ("Addresses", "\n".join(data["addresses"])),
    ])

    # ---- Social
    doc.add_heading("3. Social Media", level=1)
    if data["socials"]:
        _kv_table(doc, sorted(data["socials"].items()))
    else:
        doc.add_paragraph("No social media links found.")

    # ---- Pages
    doc.add_heading("4. Website Content", level=1)
    for i, page in enumerate(data["pages"], 1):
        doc.add_heading(f"4.{i}  {_safe(page['title']) or page['url']}", level=2)
        p = doc.add_paragraph()
        r = p.add_run(page["url"])
        r.italic = True
        r.font.color.rgb = RGBColor(0x1F, 0x4E, 0x99)

        if page["description"]:
            doc.add_paragraph(_safe(page["description"]), style="Intense Quote")

        if page["headings"]:
            doc.add_heading("Key headings", level=3)
            for h in page["headings"][:20]:
                doc.add_paragraph(_safe(h), style="List Bullet")

        if page["paragraphs"]:
            doc.add_heading("Text content", level=3)
            for para in page["paragraphs"][:MAX_PARAGRAPHS_PER_PAGE]:
                doc.add_paragraph(_safe(para))

    # ---- Pages list
    doc.add_heading("5. Pages Visited", level=1)
    for page in data["pages"]:
        doc.add_paragraph(page["url"], style="List Number")

    doc.save(out_path)
    return out_path
