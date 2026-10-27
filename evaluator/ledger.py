"""Evaluation ledger: guarantees each submission is evaluated only once.

The ledger lives in the repository at evaluation-results/results.json and is
committed back by the GitHub workflow after every run. A submission is keyed by
its file path. Once it has a successful result it is never sent to the model
again, so scores stay fixed and API cost is paid once per submission.

Resubmission policy (evaluator/config.json -> "resubmission_policy"):
  "lock"                  - (default) first successful score is final, even if the
                            participant later overwrites the same file.
  "reevaluate_on_change"  - re-score only when the file's content hash changes.
"""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path("evaluation-results")
LEDGER_PATH = RESULTS_DIR / "results.json"
MAX_ATTEMPTS = 3


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_ledger(path=LEDGER_PATH):
    p = Path(path)
    if not p.exists():
        return {"version": 1, "submissions": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("version", 1)
    data.setdefault("submissions", {})
    return data


def save_ledger(ledger, path=LEDGER_PATH):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    ledger["updated_at"] = now_iso()
    p.write_text(json.dumps(ledger, indent=2, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")


def needs_evaluation(entry, sha, policy="lock"):
    """Return (should_evaluate, reason)."""
    if not entry:
        return True, "new submission"
    status = entry.get("status")
    if status == "evaluated":
        if policy == "reevaluate_on_change" and entry.get("sha256") != sha:
            return True, "content changed"
        return False, "already evaluated"
    if status == "error":
        if entry.get("sha256") != sha:
            return True, "content changed after error"
        if int(entry.get("attempts", 0)) < MAX_ATTEMPTS:
            return True, f"retry {int(entry.get('attempts', 0)) + 1}/{MAX_ATTEMPTS}"
        return False, "max attempts reached"
    return True, "unknown status"


def submitter_info(path, root="."):
    """Commit author and time of the commit that first added the file (needs full git history of root)."""
    def git(*args):
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
        return r.stdout.strip()

    out = git("log", "--diff-filter=A", "--format=%an|%aI|%H", "--", str(path))
    line = out.splitlines()[-1] if out else git("log", "-1", "--format=%an|%aI|%H", "--", str(path))
    parts = (line.split("|") + ["", "", ""])[:3]
    return {"submitted_by": parts[0], "submitted_at": parts[1], "commit": parts[2]}
