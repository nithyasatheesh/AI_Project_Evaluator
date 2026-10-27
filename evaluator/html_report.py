"""Build the HTML results dashboard (index.html + data.json) from the evaluation ledger.

Same pattern as the rag_lab dashboard: the data is embedded in the page so it opens
straight from disk, and when served from GitHub Pages the page also reads data.json live.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE = Path(__file__).with_name("dashboard_template.html")

PROJECT_WORDS = (
    "loan_default", "loan", "default", "retail_customer_purchase", "retail_purchase", "retail", "purchase",
    "customer", "healthcare_liver_disease", "healthcare", "liver", "disease", "submission", "milestone",
    "final", "notebook", "project", "strong", "medium", "weak",
)


def person_name(path, submitted_by=""):
    """One identity per participant across milestones.

    Participant_M1_02_x -> Participant_02.  Priya_Venkatesh_loan_default_m1 -> Priya Venkatesh.
    Falls back to the GitHub user who uploaded the file.
    """
    stem = Path(path).stem
    m = re.search(r"participant[_ -]*(?:m[1-4][_ -]*)?(\d+)", stem, re.IGNORECASE)
    if m:
        return f"Participant_{int(m.group(1)):02d}"
    words = [w for w in re.split(r"[_\-\s.]+", stem) if w]
    keep = [w for w in words
            if w.lower() not in PROJECT_WORDS and not re.fullmatch(r"(m|ms|milestone)?[1-4]", w, re.IGNORECASE)]
    if keep:
        return " ".join(w if w.isupper() else w.capitalize() for w in keep)
    return submitted_by or stem


def band(avg):
    if avg is None:
        return None
    if avg >= 80:
        return "Distinction"
    if avg >= 65:
        return "Merit"
    if avg >= 50:
        return "Pass"
    return "Below 50%"


def _as_list(v):
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v if x]
    return [str(v)] if v else []


def build_data(ledger, config, results_dir=Path("evaluation-results")):
    people = {}
    errors = []
    for key, e in ledger.get("submissions", {}).items():
        if e.get("status") == "error":
            errors.append({"file": key, "error": e.get("error", ""), "attempts": e.get("attempts", 0)})
            continue
        if e.get("status") != "evaluated" or e.get("file_present") is False:
            continue
        r = e["result"]
        mnum = re.search(r"([1-4])$", str(r.get("milestone_id", "")))
        if not mnum:
            continue
        m = mnum.group(1)
        name = person_name(key, e.get("submitted_by", ""))
        pid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or key
        p = people.setdefault(pid, {"id": pid, "name": name, "submittedBy": e.get("submitted_by", ""),
                                    "milestones": {}, "projects": []})
        total, maximum = r.get("total_marks", 0), r.get("maximum_marks", 100) or 100
        fb = e.get("feedback_file", "")
        if fb:
            try:
                fb = Path(fb).relative_to(results_dir).as_posix()
            except ValueError:
                pass
        sub = {
            "total": total, "max": maximum, "pct": round(100 * total / maximum, 1),
            "project": r.get("project_id", ""), "file": key, "evaluatedAt": e.get("evaluated_at", ""),
            "submittedAt": e.get("submitted_at", ""), "feedbackFile": fb,
            "criteria": [[c["name"], c["marks_awarded"], c["max_marks"], c.get("feedback", "")] for c in r.get("criteria", [])],
            "strengths": _as_list(r.get("strengths")), "improvements": _as_list(r.get("areas_for_improvement")),
            "overall": str(r.get("overall_feedback", "")),
        }
        # If a participant has two files for one milestone, show the most recently evaluated one.
        old = p["milestones"].get(m)
        if not old or sub["evaluatedAt"] > old["evaluatedAt"]:
            p["milestones"][m] = sub
    for p in people.values():
        subs = list(p["milestones"].values())
        p["projects"] = sorted({s["project"] for s in subs if s["project"]})
        p["avg"] = round(sum(s["pct"] for s in subs) / len(subs), 1) if subs else None
        p["band"] = band(p["avg"])
        p["completed"] = len(subs)
        p["lastSubmitted"] = max((s["evaluatedAt"] for s in subs), default="")
    return {
        "cohort": config.get("cohort_name", "Project Evaluation"),
        "asOf": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "synthetic": False,
        "submissionsRepo": config.get("submissions_repo", ""),
        "milestones": [1, 2, 3, 4],
        "participants": sorted(people.values(), key=lambda p: p["name"].lower()),
        "errors": errors,
    }


def render_html(data):
    inner = TEMPLATE.read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    inner = inner.replace("__DATA__", blob, 1)
    # Template is body content (title/meta/style first); lift the head parts into <head>.
    head_end = inner.index("</style>") + len("</style>")
    head, body = inner[:head_end], inner[head_end:]
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + head + '\n</head>\n<body>' + body + "\n</body>\n</html>\n")


def write_dashboard(ledger, config, results_dir=Path("evaluation-results")):
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    data = build_data(ledger, config, results_dir)
    (results_dir / "data.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (results_dir / "index.html").write_text(render_html(data), encoding="utf-8")
    return data
