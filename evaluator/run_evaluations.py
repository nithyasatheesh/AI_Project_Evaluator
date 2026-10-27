import argparse
import json
import os
import re
import shutil
from datetime import datetime, timezone
import sys
from pathlib import Path

from evaluator.core import SUPPORTED, collect_submission, evaluate, load_problem
from evaluator.ledger import (LEDGER_PATH, RESULTS_DIR, file_sha256, load_ledger, needs_evaluation,
                              now_iso, save_ledger, submitter_info)
from evaluator.report_generator import write_reports
from evaluator.html_report import person_id, person_name, write_dashboard

SUBMISSION_ROOTS = (
    "Submission-Milestone1",
    "Submission-Milestone2",
    "Submission-Milestone3",
    "Submission-Milestone4",
)

PROJECT_SIGNALS = {
    "Retail_Customer_Purchase": (
        "retail_purchase", "retail_customer_purchase", "customer purchase intelligence",
        "user_product_purchase_details", "customer_reviews"
    ),
    "Healthcare_Liver_Disease": (
        "healthcare", "liver_disease", "liver disease", "liver patient dataset",
        "healthcare_education_text"
    ),
    "Loan_Default": ("loan_default", "loan default", "default prediction", "credit risk")
}

def choose_project_milestone(path, config, root=Path(".")):
    path_text = path.as_posix().lower().replace("-", "_").replace(" ", "_")
    filename = path.stem.lower().replace("-", "_").replace(" ", "_")
    project_configs = config.get("projects", {})
    project = None

    # Prefer explicit project terms from filename/path.
    for project_name in project_configs:
        normalized = project_name.lower().replace("-", "_").replace(" ", "_")
        if normalized in path_text or normalized in filename:
            project = project_name
            break
    if project is None:
        for project_name, signals in PROJECT_SIGNALS.items():
            if project_name in project_configs and any(s.replace(" ", "_") in path_text or s.replace(" ", "_") in filename for s in signals):
                project = project_name
                break

    # Infer only from explicit project evidence inside text-based submissions.
    if project is None and path.suffix.lower() in {".ipynb", ".py", ".md", ".txt", ".json", ".html"}:
        try:
            sample = (root / path).read_text(encoding="utf-8", errors="replace")[:50000].lower().replace("-", "_")
            for project_name, signals in PROJECT_SIGNALS.items():
                if project_name in project_configs and any(s.lower().replace(" ", "_") in sample for s in signals):
                    project = project_name
                    break
        except OSError:
            pass

    # Legacy submissions in submission/Participant_xxx belong to the configured default.
    if project is None and path.parts and path.parts[0].lower() == "submission":
        default = config.get("default_project", "Loan_Default")
        if default in project_configs:
            project = default
    if project is None:
        raise ValueError(
            f"Cannot identify project for {path}. Put the project name or a recognized project-specific keyword in the filename or notebook."
        )

    milestone_match = re.search(r"milestone[_ -]?([1-4])", path.as_posix(), re.IGNORECASE)
    if not milestone_match:
        milestone_match = re.search(r"_m([1-4])_", path.stem, re.IGNORECASE)
    if not milestone_match:
        raise ValueError(f"Cannot identify milestone from path {path}.")
    milestone = f"Milestone_{milestone_match.group(1)}"

    if milestone not in project_configs.get(project, {}).get("rubrics", {}):
        raise ValueError(f"No rubric configured for {project}/{milestone}.")
    return project, milestone

def supported_submission(path):
    return (
        path.is_file()
        and (path.suffix.lower() in SUPPORTED or path.suffix.lower() == ".zip")
        and not path.name.startswith(".")
        and path.name.lower() not in {"readme.md", "readme.txt", ".gitkeep"}
    )

def discover_submissions(root=Path("."), files_from=None):
    """Return submission paths RELATIVE to root (the submissions repo checkout)."""
    root = Path(root)
    found = set()
    for root_name in SUBMISSION_ROOTS:
        folder = root / root_name
        if folder.exists():
            found.update(p.relative_to(root) for p in folder.rglob("*") if supported_submission(p))
    if files_from and Path(files_from).exists():
        for line in Path(files_from).read_text(encoding="utf-8").splitlines():
            rel = Path(line.strip())
            if line.strip() and supported_submission(root / rel):
                found.add(rel)
    return sorted(found, key=lambda p: p.as_posix().lower())

def participant_name(path):
    p = Path(path)
    match = re.search(r"(Participant(?:[_ -]M[1-4])?[_ -]*\d+)", p.stem, re.IGNORECASE)
    if match:
        return re.sub(r"[ -]+", "_", match.group(1)).replace("__", "_")
    match = re.search(r"(Participant[_ -]*\d+)", p.as_posix(), re.IGNORECASE)
    return re.sub(r"[ -]+", "_", match.group(1)).replace("__", "_") if match else p.stem

def evaluate_one(path, config, root=Path(".")):
    project, milestone = choose_project_milestone(path, config, root)
    project_config = config["projects"][project]
    rubric_path = project_config.get("rubrics", {}).get(milestone)
    if not rubric_path or not Path(rubric_path).exists():
        raise FileNotFoundError(f"Configured rubric does not exist: {rubric_path}")
    rubric = json.loads(Path(rubric_path).read_text(encoding="utf-8"))
    if not rubric.get("criteria"):
        raise ValueError(f"Rubric has no criteria: {rubric_path}")
    problem_path = project_config.get("problem_statement")
    if not problem_path or not Path(problem_path).exists():
        raise FileNotFoundError(f"Configured problem statement does not exist: {problem_path}")
    problem = load_problem(problem_path)
    evidence, _ = collect_submission(
        [root / path],
        int(config.get("max_file_chars", 18000)),
        int(config.get("max_total_chars", 45000)),
    )
    if not evidence.strip():
        raise ValueError("No readable text extracted from submission.")
    result = evaluate(evidence, rubric, problem, config.get("model", "gpt-4.1-mini"))
    result["project_id"] = project
    result["milestone_id"] = milestone
    return result


def _md_cell(text):
    return str(text or "").replace("|", "\\|").replace("\n", " ").strip()


def _as_list(value):
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    return [str(value)] if value else []


def feedback_markdown(entry):
    r = entry["result"]
    lines = [
        f"# {entry['participant']} — {r.get('milestone_id', '').replace('_', ' ')}",
        "",
        f"**Project:** {r.get('project_id', '')}  ",
        f"**Submission:** `{entry['path']}`  ",
        f"**Evaluated:** {entry.get('evaluated_at', '')}  ",
        f"**Score:** **{r.get('total_marks', 0)} / {r.get('maximum_marks', 100)}**",
        "",
        "| Criterion | Marks | Feedback |",
        "|---|---:|---|",
    ]
    for c in r.get("criteria", []):
        lines.append(f"| {_md_cell(c['name'])} | {c['marks_awarded']} / {c['max_marks']} | {_md_cell(c.get('feedback'))} |")
    lines += ["", "## Strengths", ""] + [f"- {s}" for s in _as_list(r.get("strengths"))]
    lines += ["", "## Areas for improvement", ""] + [f"- {s}" for s in _as_list(r.get("areas_for_improvement"))]
    lines += ["", "## Overall feedback", "", str(r.get("overall_feedback", "")), "",
              "_AI-generated evaluation; subject to human review._", ""]
    return "\n".join(lines)


def scores_markdown(ledger):
    entries = [e for e in ledger["submissions"].values() if e.get("status") == "evaluated"]
    errors = [e for e in ledger["submissions"].values() if e.get("status") == "error"]
    lines = ["# Evaluation Scores", "",
             f"_Last updated: {ledger.get('updated_at', now_iso())} · {len(entries)} evaluated · {len(errors)} with errors_", "",
             "Each submission is evaluated once; scores below are final unless an instructor re-runs it.", ""]
    for n in range(1, 5):
        ms = f"Milestone_{n}"
        rows = sorted((e for e in entries if e["result"].get("milestone_id") == ms), key=lambda e: e["participant"].lower())
        if not rows:
            continue
        lines += [f"## Milestone {n}", "", "| Participant | Project | Score | Evaluated | Feedback |", "|---|---|---:|---|---|"]
        for e in rows:
            r = e["result"]
            fb = e.get("feedback_file", "")
            link = f"[view](feedback/{Path(fb).relative_to(RESULTS_DIR / 'feedback').as_posix()})" if fb else ""
            lines.append(f"| {_md_cell(e['participant'])} | {_md_cell(r.get('project_id'))} | "
                         f"**{r.get('total_marks', 0)}** / {r.get('maximum_marks', 100)} | {e.get('evaluated_at', '')[:10]} | {link} |")
        lines.append("")
    if errors:
        lines += ["## Needs attention", "", "| Submission | Attempts | Error |", "|---|---:|---|"]
        for e in sorted(errors, key=lambda e: e["path"]):
            lines.append(f"| `{e['path']}` | {e.get('attempts', 0)} | {_md_cell(e.get('error', ''))[:200]} |")
        lines.append("")
    return "\n".join(lines)


def rebuild_outputs(ledger, config=None):
    """Regenerate feedback pages, SCORES.md and Excel workbooks from the ledger (no model calls)."""
    fb_root = RESULTS_DIR / "feedback"
    if fb_root.exists():
        shutil.rmtree(fb_root)
    reports_dir = RESULTS_DIR / "reports"
    if reports_dir.exists():
        shutil.rmtree(reports_dir)
    for entry in ledger["submissions"].values():
        if entry.get("status") != "evaluated":
            continue
        ms = entry["result"].get("milestone_id", "Milestone_1")
        target = fb_root / ms / f"{Path(entry['path']).stem}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(feedback_markdown(entry), encoding="utf-8")
        entry["feedback_file"] = target.as_posix()
        write_reports(entry["result"], entry["path"], reports_dir)
    (RESULTS_DIR / "SCORES.md").write_text(scores_markdown(ledger), encoding="utf-8")
    write_dashboard(ledger, config or {}, RESULTS_DIR)
    # Keep a copy of the full dashboard next to the Excel reports so it can be downloaded the same way.
    if (RESULTS_DIR / "index.html").exists():
        reports_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(RESULTS_DIR / "index.html", reports_dir / "Cohort-Dashboard.html")


def write_run_summary(new_entries, skipped, errors):
    """Markdown for the GitHub Actions job summary plus JSON consumed by the comment step."""
    lines = ["## AI Evaluator run", "",
             f"Newly evaluated: **{len(new_entries)}** · Skipped (already evaluated): **{skipped}** · Errors: **{len(errors)}**", ""]
    if new_entries:
        lines += ["| Participant | Milestone | Project | Score |", "|---|---|---|---:|"]
        for e in new_entries:
            r = e["result"]
            lines.append(f"| {e['participant']} | {r.get('milestone_id')} | {r.get('project_id')} | **{r.get('total_marks')}/{r.get('maximum_marks')}** |")
        lines.append("")
    for e in errors:
        lines.append(f"- ⚠️ `{e['path']}`: {e.get('error', '')}")
    summary = "\n".join(lines) + "\n"
    target = os.getenv("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as fh:
            fh.write(summary)
    print(summary)
    Path(os.getenv("RUNNER_TEMP", ".")).joinpath("new_results.json").write_text(
        json.dumps([{"path": e["path"], "participant": e["participant"], "commit": e.get("commit", ""),
                     "milestone": e["result"].get("milestone_id"), "project": e["result"].get("project_id"),
                     "total": e["result"].get("total_marks"), "maximum": e["result"].get("maximum_marks"),
                     "feedback_file": e.get("feedback_file", ""),
                     "pid": person_id(person_name(e["path"], e.get("submitted_by", "")))} for e in new_entries], indent=2),
        encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files-from", required=False, default=None)
    parser.add_argument("--force", action="append", default=[],
                        help="Re-evaluate this submission path even if already scored (instructor override). Repeatable.")
    parser.add_argument("--submissions-root", default=None,
                        help="Folder containing the Submission-Milestone1..4 folders (e.g. a checkout of the shared submissions repo). "
                             "Defaults to config 'submissions_root' or the current folder.")
    parser.add_argument("--rebuild-only", action="store_true", help="Regenerate reports from saved results without evaluating.")
    args = parser.parse_args()

    config = json.loads(Path("evaluator/config.json").read_text(encoding="utf-8"))
    policy = config.get("resubmission_policy", "lock")
    ledger = load_ledger()

    if args.rebuild_only:
        rebuild_outputs(ledger, config)
        save_ledger(ledger)
        print("Rebuilt reports from saved results.")
        return 0

    root = Path(args.submissions_root or config.get("submissions_root") or ".")
    candidates = discover_submissions(root, args.files_from)
    forced = {f.strip().replace("\\", "/") for f in args.force if f.strip()}
    todo, skipped = [], 0
    for path in candidates:
        key = path.as_posix()
        sha = file_sha256(root / path)
        should, reason = needs_evaluation(ledger["submissions"].get(key), sha, policy)
        if key in forced:
            should, reason = True, "forced by instructor"
        if should:
            todo.append((path, sha, reason))
        else:
            skipped += 1
    print(f"{len(candidates)} submissions found; {len(todo)} to evaluate; {skipped} already evaluated.")

    if todo and not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY secret is missing.", file=sys.stderr)
        return 2

    new_entries, errors = [], []
    for path, sha, reason in todo:
        key = path.as_posix()
        previous = ledger["submissions"].get(key) or {}
        entry = {"path": key, "participant": participant_name(path), "sha256": sha, **submitter_info(path, root)}
        try:
            print(f"Evaluating {key} ({reason}) ...")
            result = evaluate_one(path, config, root)
            entry.update(status="evaluated", evaluated_at=now_iso(), attempts=int(previous.get("attempts", 0)) + 1,
                         model=config.get("model", "gpt-4.1-mini"), result=result)
            if previous.get("status") == "evaluated":
                entry["previous_scores"] = previous.get("previous_scores", []) + [
                    {"total": previous["result"].get("total_marks"), "evaluated_at": previous.get("evaluated_at")}]
            new_entries.append(entry)
            print(f"  -> {result.get('total_marks', 0)}/{result.get('maximum_marks', 100)}")
        except Exception as exc:
            attempts = int(previous.get("attempts", 0)) + 1 if previous.get("status") == "error" and previous.get("sha256") == sha else 1
            if previous.get("status") == "evaluated":
                # Keep the earlier valid score if a forced/changed re-run fails.
                entry = previous
                entry["last_error"] = f"{type(exc).__name__}: {exc}"
            else:
                entry.update(status="error", attempts=attempts, error=f"{type(exc).__name__}: {exc}", last_attempt_at=now_iso())
            errors.append({"path": key, "error": f"{type(exc).__name__}: {exc}"})
            print(f"ERROR evaluating {key}: {type(exc).__name__}: {exc}", file=sys.stderr)
        ledger["submissions"][key] = entry
        save_ledger(ledger)  # save after each one so a crash never loses finished work

    # Keep history for deleted files, but flag them so dashboards can show it.
    present = {p.as_posix() for p in candidates}
    for key, entry in ledger["submissions"].items():
        entry["file_present"] = key in present

    rebuild_outputs(ledger, config)
    save_ledger(ledger)
    write_run_summary(new_entries, skipped, errors)
    return 1 if errors and not new_entries else 0


if __name__ == "__main__":
    raise SystemExit(main())
