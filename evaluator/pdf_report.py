"""One PDF result report per evaluated submission.

Output mirrors the submission path, so a grad finds their report next to where they uploaded:
    Submission-Milestone1/Priya_Venkatesh_loan_default.ipynb
 -> Results/Submission-Milestone1/Priya_Venkatesh_loan_default.pdf

PDFs are built only from saved results (no AI calls) and are byte-for-byte stable,
so re-running the workflow does not create new commits for unchanged reports.
"""
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

rl_config.invariant = 1  # no timestamps/random IDs inside the PDF -> identical bytes on rebuild

INK = colors.HexColor("#14182B")
MUTED = colors.HexColor("#5D6584")
ACCENT = colors.HexColor("#2A5BD7")
TRACK = colors.HexColor("#E8EBF4")
RULE = colors.HexColor("#DFE3EE")
PANEL = colors.HexColor("#F5F6FA")
BAND_COLORS = {"Distinction": "#0A8FA8", "Merit": "#2A5BD7", "Pass": "#B88700", "Below 50%": "#C0283F"}


def _fonts():
    for regular, bold in (
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ):
        if Path(regular).exists() and Path(bold).exists():
            try:
                pdfmetrics.registerFont(TTFont("Body", regular))
                pdfmetrics.registerFont(TTFont("Body-Bold", bold))
                return "Body", "Body-Bold"
            except Exception:
                pass
    return "Helvetica", "Helvetica-Bold"


FONT, BOLD = _fonts()


def _style(name, size, font=None, color=INK, leading=None, **kw):
    return ParagraphStyle(name, fontName=font or FONT, fontSize=size, textColor=color,
                          leading=leading or size * 1.35, **kw)


S = {
    "eyebrow": _style("eyebrow", 8, BOLD, MUTED),
    "title": _style("title", 18, BOLD, leading=22),
    "meta": _style("meta", 9, color=MUTED),
    "score": _style("score", 30, BOLD, ACCENT, leading=32, alignment=TA_RIGHT),
    "scoremeta": _style("scoremeta", 9, color=MUTED, alignment=TA_RIGHT),
    "h2": _style("h2", 11, BOLD, spaceBefore=6, spaceAfter=4),
    "crit": _style("crit", 9.5, BOLD),
    "marks": _style("marks", 9.5, BOLD, alignment=TA_RIGHT),
    "body": _style("body", 9, color=MUTED),
    "text": _style("text", 9.5),
    "foot": _style("foot", 7.5, color=MUTED),
}


def band(pct):
    return "Distinction" if pct >= 80 else "Merit" if pct >= 65 else "Pass" if pct >= 50 else "Below 50%"


class Bar(Flowable):
    def __init__(self, frac, width, height=5):
        super().__init__()
        self.frac, self.width, self.height = max(0.0, min(1.0, frac)), width, height

    def wrap(self, *_):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(TRACK)
        c.roundRect(0, 0, self.width, self.height, self.height / 2, stroke=0, fill=1)
        if self.frac > 0:
            c.setFillColor(ACCENT)
            c.roundRect(0, 0, max(self.height, self.width * self.frac), self.height, self.height / 2, stroke=0, fill=1)


def _p(text, style):
    return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), style)


def _date(iso):
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).strftime("%d %b %Y")
    except ValueError:
        return str(iso)[:10]


def _as_list(v):
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if x]
    return [str(v)] if v else []


def build_pdf(entry, target, cohort_name="Project Evaluation", participant=""):
    r = entry["result"]
    total, maximum = r.get("total_marks", 0), r.get("maximum_marks", 100) or 100
    pct = 100 * total / maximum
    milestone = str(r.get("milestone_id", "")).replace("_", " ")
    project = str(r.get("project_id", "")).replace("_", " ")
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(str(target), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"{participant} - {milestone} result", author=cohort_name)
    W = doc.width
    story = []

    head = Table([[
        [_p(f"{cohort_name.upper()} · PROJECT EVALUATION", S["eyebrow"]), Spacer(0, 3),
         _p(participant or Path(entry["path"]).stem, S["title"]), Spacer(0, 2),
         _p(f"{milestone} · {project}", S["meta"]),
         _p(f"Submission: {entry['path']}", S["meta"]),
         _p(f"Evaluated: {_date(entry.get('evaluated_at', ''))}", S["meta"])],
        [Paragraph(f'{total}<font size="12" color="#5D6584"> / {maximum}</font>', S["score"]),
         Spacer(0, 4),
         Paragraph(f'<font color="{BAND_COLORS[band(pct)]}"><b>{band(pct)}</b></font> · {pct:.0f}%', S["scoremeta"])],
    ]], colWidths=[W * 0.68, W * 0.32])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                              ("LINEBELOW", (0, 0), (-1, 0), 0.8, RULE), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    story += [head, Spacer(0, 10), _p("Criterion-wise marks", S["h2"])]

    for c in r.get("criteria", []):
        got, mx = c.get("marks_awarded", 0), c.get("max_marks", 0)
        block = Table([
            [_p(c.get("name", ""), S["crit"]), _p(f"{got} / {mx}", S["marks"])],
            [Bar(got / mx if mx else 0, W - 20), ""],
            [_p(c.get("feedback", ""), S["body"]), ""],
        ], colWidths=[W - 64, 64], hAlign="LEFT")
        block.setStyle(TableStyle([
            ("SPAN", (0, 1), (1, 1)), ("SPAN", (0, 2), (1, 2)),
            ("BACKGROUND", (0, 0), (-1, -1), PANEL), ("BOX", (0, 0), (-1, -1), 0.6, RULE),
            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, 0), 8), ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
            ("TOPPADDING", (0, 1), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, 1), 3),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story += [KeepTogether(block), Spacer(0, 6)]

    def bullets(items):
        return [_p(f"•  {x}", S["text"]) for x in items] or [_p("-", S["text"])]

    cols = Table([[[_p("Strengths", S["h2"])] + bullets(_as_list(r.get("strengths"))),
                   [_p("To improve next time", S["h2"])] + bullets(_as_list(r.get("areas_for_improvement")))]],
                 colWidths=[W / 2, W / 2], hAlign="LEFT")
    cols.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (0, 0), 12)]))
    story += [Spacer(0, 4), cols, Spacer(0, 6), _p("Overall feedback", S["h2"]),
              _p(r.get("overall_feedback", ""), S["text"]), Spacer(0, 14),
              _p("AI-generated evaluation against the milestone rubric. Subject to trainer review. "
                 "Each submission is evaluated once; this score is recorded.", S["foot"])]

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(d.leftMargin, 9 * mm, f"{cohort_name} · {participant} · {milestone}")
        canvas.drawRightString(d.leftMargin + d.width, 9 * mm, f"Page {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return target


def write_pdf_reports(ledger, config, out_dir, name_for):
    """Write a PDF for every evaluated submission. Returns the list of written paths."""
    out_dir = Path(out_dir)
    written = []
    for key, e in ledger.get("submissions", {}).items():
        if e.get("status") != "evaluated" or e.get("file_present") is False:
            continue
        target = out_dir / Path(key).with_suffix(".pdf")
        build_pdf(e, target, config.get("cohort_name", "Project Evaluation"), name_for(key, e))
        e["pdf_file"] = Path(key).with_suffix(".pdf").as_posix()
        written.append(target)
    return written
