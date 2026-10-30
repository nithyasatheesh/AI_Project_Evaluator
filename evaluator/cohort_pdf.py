"""Cohort dashboard as a PDF (instructor copy, kept in the evaluator repo).

Same content as the HTML cohort dashboard: summary, score bands, milestone progress,
project averages, participant x milestone table, rubric-criterion averages, needs attention.
"""
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from evaluator.pdf_report import ACCENT, BAND_COLORS, BOLD, FONT, INK, MUTED, PANEL, RULE, S, Bar, _p

LABEL = ParagraphStyle("label", fontName=BOLD, fontSize=8.5, leading=10.5, textColor=INK)

BANDS = ["Distinction", "Merit", "Pass", "Below 50%"]


def _avg(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _pct(v):
    return "-" if v is None else f"{v:.0f}%"


def _heat(v):
    """Cell background for a % score (pale -> accent)."""
    if v is None:
        return colors.HexColor("#EEF0F7")
    t = 0.15 + 0.6 * max(0, min(100, v)) / 100
    base = (0x2A / 255, 0x5B / 255, 0xD7 / 255)
    return colors.Color(1 - (1 - base[0]) * t, 1 - (1 - base[1]) * t, 1 - (1 - base[2]) * t)


class ColourBar(Bar):
    def __init__(self, frac, width, height=6, colour=ACCENT):
        super().__init__(frac, width, height)
        self.colour = colour

    def draw(self):
        c = self.canv
        c.setFillColor(colors.HexColor("#E8EBF4"))
        c.roundRect(0, 0, self.width, self.height, self.height / 2, stroke=0, fill=1)
        if self.frac > 0:
            c.setFillColor(self.colour)
            c.roundRect(0, 0, max(self.height, self.width * self.frac), self.height, self.height / 2, stroke=0, fill=1)


def _card(title, body, width):
    t = Table([[_p(title, S["h2"])], [body]], colWidths=[width], hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PANEL), ("BOX", (0, 0), (-1, -1), 0.6, RULE),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, -1), (-1, -1), 10)]))
    return t


def _bars(rows, width, label_w=46 * mm, value_w=26 * mm):
    data = []
    for label, frac, value, colour in rows:
        data.append([_p(label, LABEL), ColourBar(frac, width - label_w - value_w - 6, 6, colour or ACCENT),
                     _p(value, S["meta"])])
    if not data:
        return _p("No scores yet.", S["meta"])
    t = Table(data, colWidths=[label_w, width - label_w - value_w, value_w], hAlign="LEFT")
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                           ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return t


def build_cohort_pdf(data, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    P = data["participants"]
    MS = [str(m) for m in data.get("milestones", [1, 2, 3, 4])]
    subs = [s for p in P for s in p["milestones"].values()]
    n = len(P)
    cohort = data.get("cohort", "Project Evaluation")
    try:
        asof = datetime.fromisoformat(data["asOf"].replace("Z", "+00:00")).strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        asof = data.get("asOf", "")

    doc = SimpleDocTemplate(str(target), pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=14 * mm, title=f"{cohort} - cohort evaluation report",
                            author=cohort)
    W = doc.width
    half = (W - 8) / 2
    story = [_p(f"{cohort.upper()} · COHORT EVALUATION REPORT", S["eyebrow"]), Spacer(0, 2),
             _p(f"{cohort}: project evaluation results", S["title"]),
             _p(f"{n} participants · {len(subs)} scored submissions · as of {asof}", S["meta"]), Spacer(0, 8)]

    # KPI strip
    kp = [(n, "Participants"), (len(subs), "Submissions scored"), (_pct(_avg([s["pct"] for s in subs])), "Average score"),
          (sum(p["band"] == "Distinction" for p in P), "Distinction"), (sum(p["band"] == "Below 50%" for p in P), "Below 50%"),
          (len(data.get("errors", [])), "Could not evaluate")]
    kpi = Table([[[_p(str(v), S["title"]), _p(l, S["meta"])] for v, l in kp]], colWidths=[W / 6] * 6)
    kpi.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, RULE), ("INNERGRID", (0, 0), (-1, -1), 0.6, RULE),
                             ("BACKGROUND", (0, 0), (-1, -1), PANEL), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                             ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story += [kpi, Spacer(0, 8)]

    inner = half - 20
    bands = _bars([(b, (sum(p["band"] == b for p in P) / n) if n else 0,
                    f"{sum(p['band'] == b for p in P)} · {round(100 * sum(p['band'] == b for p in P) / n) if n else 0}%",
                    colors.HexColor(BAND_COLORS[b])) for b in BANDS], inner)
    prog = []
    for m in MS:
        s = [p["milestones"][m] for p in P if m in p["milestones"]]
        prog.append((f"Milestone {m}", len(s) / n if n else 0, f"{len(s)}/{n} · {_pct(_avg([x['pct'] for x in s]))}", None))
    row = Table([[_card("Score bands (average across milestones)", bands, half),
                  _card("Milestone progress (submitted · average)", _bars(prog, inner), half)]],
                colWidths=[half + 4, half + 4], hAlign="LEFT")
    row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    story += [row, Spacer(0, 8)]

    proj = {}
    for s in subs:
        proj.setdefault(s["project"], []).append(s["pct"])
    proj_rows = [(k.replace("_", " "), _avg(v) / 100, f"{_pct(_avg(v))} · {len(v)}", None) for k, v in sorted(proj.items())]
    attention = [(e["file"], "could not evaluate") for e in data.get("errors", [])] + \
                [(p["name"], f"average {_pct(p['avg'])}") for p in P if p["band"] == "Below 50%"]
    att = Table([[_p(a, S["text"]), _p(b, S["meta"])] for a, b in attention] or [[_p("Nothing needs attention.", S["meta"]), ""]],
                colWidths=[inner * 0.65, inner * 0.35], hAlign="LEFT")
    att.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -2), 0.5, RULE), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    row2 = Table([[_card("Average by project (score · submissions)", _bars(proj_rows, inner), half),
                   _card("Needs attention", att, half)]], colWidths=[half + 4, half + 4], hAlign="LEFT")
    row2.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 4)]))
    story += [row2, Spacer(0, 10)]

    # Participant x milestone table
    head = ["#", "Participant", "Project"] + [f"M{m}" for m in MS] + ["Average", "Band"]
    rows = [[_p(h, S["eyebrow"]) for h in head]]
    ordered = sorted(P, key=lambda p: (-(p["avg"] or -1), p["name"].lower()))
    for i, p in enumerate(ordered, 1):
        rows.append([_p(str(i), S["meta"]), _p(p["name"], S["crit"]),
                     _p(", ".join(x.replace("_", " ") for x in p["projects"]), S["meta"])]
                    + [_p(_pct(p["milestones"][m]["pct"]) if m in p["milestones"] else "·", S["marks"]) for m in MS]
                    + [_p(_pct(p["avg"]), S["marks"]),
                       Paragraph(f'<font color="{BAND_COLORS.get(p["band"], "#5D6584")}"><b>{p["band"] or "-"}</b></font>', S["text"])])
    mw = 18 * mm
    tbl = Table(rows, colWidths=[10 * mm, 48 * mm, W - 10 * mm - 48 * mm - mw * len(MS) - 22 * mm - 26 * mm]
                + [mw] * len(MS) + [22 * mm, 26 * mm], repeatRows=1, hAlign="LEFT")
    st = [("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    for r, p in enumerate(ordered, 1):
        for j, m in enumerate(MS):
            st.append(("BACKGROUND", (3 + j, r), (3 + j, r), _heat(p["milestones"][m]["pct"] if m in p["milestones"] else None)))
    tbl.setStyle(TableStyle(st))
    story += [_p("Participants · % score per milestone", S["h2"]), tbl, Spacer(0, 10)]

    # Criterion averages per milestone (2 x 2 grid)
    cards = []
    for m in MS:
        agg = {}
        for p in P:
            s = p["milestones"].get(m)
            if s:
                for name, got, mx, _ in s["criteria"]:
                    agg.setdefault(name, []).append(100 * got / mx if mx else 0)
        rows_m = [(k, _avg(v) / 100, _pct(_avg(v)), None) for k, v in agg.items()]
        cards.append(_card(f"Milestone {m} · average by rubric criterion", _bars(rows_m, inner, 74 * mm, 14 * mm), half))
    grid = Table([cards[i:i + 2] + [""] * (2 - len(cards[i:i + 2])) for i in range(0, len(cards), 2)],
                 colWidths=[half + 4, half + 4], hAlign="LEFT")
    grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    story += [KeepTogether([_p("Where the cohort is strong or struggling", S["h2"]), grid]),
              _p("AI-generated scores against the milestone rubrics. Subject to trainer review.", S["foot"])]

    def footer(canvas, d):
        canvas.saveState()
        canvas.setFont(FONT, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(d.leftMargin, 8 * mm, f"{cohort} · Cohort evaluation report · {asof}")
        canvas.drawRightString(d.leftMargin + d.width, 8 * mm, f"Page {d.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return target
