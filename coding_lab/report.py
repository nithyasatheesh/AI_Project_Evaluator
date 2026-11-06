"""Downloads: the participant's PDF result report and their notebook as .ipynb."""
import io
import json
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

rl_config.invariant = 1
INK, MUTED, ACCENT = colors.HexColor("#14182B"), colors.HexColor("#5D6584"), colors.HexColor("#2A5BD7")
TRACK, RULE, PANEL = colors.HexColor("#E8EBF4"), colors.HexColor("#DFE3EE"), colors.HexColor("#F5F6FA")
BANDS = [(80, "Distinction", "#0A8FA8"), (65, "Merit", "#2A5BD7"), (50, "Pass", "#B88700"), (0, "Below 50%", "#C0283F")]


def band(pct):
    for floor, name, colour in BANDS:
        if pct >= floor:
            return name, colour


def _fonts():
    for reg, bold in (("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),):
        if Path(reg).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont("LabBody", reg))
            pdfmetrics.registerFont(TTFont("LabBold", bold))
            return "LabBody", "LabBold"
    return "Helvetica", "Helvetica-Bold"


FONT, BOLD = _fonts()


def _st(name, size, font=None, color=INK, **kw):
    return ParagraphStyle(name, fontName=font or FONT, fontSize=size, leading=size * 1.35, textColor=color, **kw)


S = {"eyebrow": _st("e", 8, BOLD, MUTED), "title": _st("t", 18, BOLD), "meta": _st("m", 9, color=MUTED),
     "score": _st("s", 28, BOLD, ACCENT, alignment=TA_RIGHT), "right": _st("r", 9, color=MUTED, alignment=TA_RIGHT),
     "h2": _st("h", 11, BOLD, spaceBefore=6, spaceAfter=4), "crit": _st("c", 9.5, BOLD),
     "marks": _st("mk", 9.5, BOLD, alignment=TA_RIGHT), "body": _st("b", 9, color=MUTED), "text": _st("x", 9.5),
     "foot": _st("f", 7.5, color=MUTED)}


class Bar(Flowable):
    def __init__(self, frac, width, height=5):
        super().__init__()
        self.frac, self.width, self.height = max(0, min(1, frac)), width, height

    def wrap(self, *_):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(TRACK)
        c.roundRect(0, 0, self.width, self.height, 2.5, stroke=0, fill=1)
        if self.frac:
            c.setFillColor(ACCENT)
            c.roundRect(0, 0, max(5, self.width * self.frac), self.height, 2.5, stroke=0, fill=1)


def _p(text, style):
    return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), style)


def pdf_report(record, tasks, lab_title, milestone, cohort=""):
    res = record.get("evaluations", {})
    got = sum(res[t["id"]]["marks"] for t in tasks if t["id"] in res)
    total = sum(t["marks"] for t in tasks)
    pct = 100 * got / total if total else 0
    bname, bcol = band(pct)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=16 * mm, title=f"{record.get('name')} - {lab_title} result")
    W = doc.width
    submitted = record.get("submitted_at", "")
    when = submitted[:10] if submitted else datetime.now().strftime("%Y-%m-%d")
    head = Table([[
        [_p(f"{(cohort or 'AI Coding Lab').upper()} · CODING LAB RESULT", S["eyebrow"]), Spacer(0, 3),
         _p(record.get("name", ""), S["title"]), _p(f"Login ID: {record.get('id', '')}", S["meta"]),
         _p(f"{lab_title} · {milestone}", S["meta"]),
         _p(("Submitted " if submitted else "Report generated ") + when, S["meta"])],
        [Paragraph(f'{got}<font size="12" color="#5D6584"> / {total}</font>', S["score"]), Spacer(0, 4),
         Paragraph(f'<font color="{bcol}"><b>{bname}</b></font> · {pct:.0f}%', S["right"])]]],
        colWidths=[W * 0.68, W * 0.32])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0), ("LINEBELOW", (0, 0), (-1, 0), .8, RULE),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    story = [head, Spacer(0, 10), _p("Task-wise marks", S["h2"])]
    for t in tasks:
        r = res.get(t["id"])
        marks = f"{r['marks']} / {t['marks']}" if r else f"– / {t['marks']}"
        fb = r["feedback"] if r else "Not evaluated."
        extra = []
        if r and r.get("improvements"):
            extra = [_p("To improve: " + "; ".join(r["improvements"][:3]), S["body"])]
        block = Table([[_p(t["title"], S["crit"]), _p(marks, S["marks"])],
                       [Bar(r["marks"] / t["marks"] if r else 0, W - 42), ""],
                       [_p(fb, S["body"]), ""]] + ([[extra[0], ""]] if extra else []),
                      colWidths=[W - 84, 64], hAlign="LEFT")
        style = [("SPAN", (0, i), (1, i)) for i in range(1, 4 if extra else 3)]
        block.setStyle(TableStyle(style + [
            ("BACKGROUND", (0, 0), (-1, -1), PANEL), ("BOX", (0, 0), (-1, -1), .6, RULE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 3), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
        story += [KeepTogether(block), Spacer(0, 6)]
    if record.get("overall_feedback"):
        story += [_p("Overall feedback", S["h2"]), _p(record["overall_feedback"], S["text"])]
    story += [Spacer(0, 12), _p("AI-generated evaluation against the milestone rubric. Subject to trainer review.", S["foot"])]

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(d.leftMargin, 9 * mm, f"{lab_title} · {record.get('name', '')} · {record.get('id', '')}")
        canvas.drawRightString(d.leftMargin + d.width, 9 * mm, f"Page {d.page}")
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def to_ipynb(record, tasks, lab_title):
    cells = [{"cell_type": "markdown", "metadata": {},
              "source": [f"# {lab_title}\n", f"**{record.get('name', '')}** ({record.get('id', '')})"]}]
    for t in tasks:
        cells.append({"cell_type": "markdown", "metadata": {}, "source": [f"## {t['title']}"]})
        for c in record.get("notebook", {}).get(t["id"], []):
            if c["type"] == "markdown":
                cells.append({"cell_type": "markdown", "metadata": {}, "source": c["source"]})
            else:
                outs = []
                for o in c.get("outputs", []):
                    if o.get("type") in ("text", "error"):
                        outs.append({"output_type": "stream", "name": "stdout" if o["type"] == "text" else "stderr",
                                     "text": o.get("text", "")})
                cells.append({"cell_type": "code", "metadata": {}, "execution_count": c.get("exec_count"),
                              "source": c["source"], "outputs": outs})
    nb = {"cells": cells, "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
                                       "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    return json.dumps(nb, indent=1, ensure_ascii=False).encode("utf-8")
