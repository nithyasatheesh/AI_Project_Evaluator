"""Where each participant's notebook and scores are kept.

* GitHub (recommended for Streamlit Cloud, whose disk is wiped on restart): one JSON file
  per participant in a PRIVATE repository, e.g. lab-data/LD001.json. Configure in secrets:

    [storage]
    github_repo  = "your-account/coding-lab-data"
    github_token = "github_pat_..."     # fine-grained, Contents: Read and write, that repo only
    branch = "main"
    folder = "lab-data"

* Local folder (for trying the app on your own computer): coding_lab/.lab_data/
"""
import base64
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

LOCAL_DIR = Path(__file__).resolve().parent / ".lab_data"


class LocalStore:
    kind = "local"

    def __init__(self):
        LOCAL_DIR.mkdir(exist_ok=True)
        self.lock = threading.Lock()

    def load(self, uid):
        p = LOCAL_DIR / f"{uid}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def save(self, uid, record, urgent=False):
        with self.lock:
            tmp = LOCAL_DIR / f"{uid}.json.tmp"
            tmp.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
            tmp.replace(LOCAL_DIR / f"{uid}.json")
        return True

    def load_all(self):
        return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in LOCAL_DIR.glob("*.json")}


class GitHubStore:
    """Saves are queued and written to GitHub as ONE commit for all pending participants:
    within ~10 s for important saves (evaluation, submission, log-out) and every ~90 s otherwise.
    That keeps a full class well inside GitHub's limit of ~500 writes per hour."""
    kind = "github"
    URGENT_WINDOW, ROUTINE_WINDOW = 10, 90

    def __init__(self, repo, token, branch="main", folder="lab-data"):
        self.repo, self.branch, self.folder = repo, branch, folder.strip("/")
        self.api = f"https://api.github.com/repos/{repo}"
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28"})
        self.pending, self.lock = {}, threading.Lock()
        self.urgent_since, self.oldest = None, None
        self.last_error = ""
        threading.Thread(target=self._loop, daemon=True).start()

    def _path(self, uid):
        return f"{self.folder}/{uid}.json"

    def load(self, uid):
        with self.lock:
            if uid in self.pending:
                return json.loads(self.pending[uid])
        r = self.s.get(f"{self.api}/contents/{self._path(uid)}", params={"ref": self.branch}, timeout=20)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        meta = r.json()
        if meta.get("content"):
            return json.loads(base64.b64decode(meta["content"]).decode("utf-8"))
        raw = self.s.get(meta["download_url"], timeout=20)                    # files over 1 MB
        raw.raise_for_status()
        return raw.json()

    def save(self, uid, record, urgent=False):
        with self.lock:
            self.pending[uid] = json.dumps(record, ensure_ascii=False)
            t = time.time()
            self.oldest = self.oldest or t
            if urgent:
                self.urgent_since = self.urgent_since or t
        return True

    def _loop(self):
        while True:
            time.sleep(2)
            with self.lock:
                now = time.time()
                due = self.pending and ((self.urgent_since and now - self.urgent_since >= self.URGENT_WINDOW)
                                        or (self.oldest and now - self.oldest >= self.ROUTINE_WINDOW))
                if not due:
                    continue
                batch = dict(self.pending)
                self.pending.clear()
                self.urgent_since = self.oldest = None
            try:
                self._commit(batch)
                self.last_error = ""
            except Exception as e:  # noqa: BLE001 - keep the work and retry on the next round
                self.last_error = str(e)
                with self.lock:
                    for uid, body in batch.items():
                        self.pending.setdefault(uid, body)
                    self.oldest = self.oldest or time.time()
                    self.urgent_since = self.urgent_since or time.time()
                time.sleep(20)

    def _commit(self, batch):
        ref = self.s.get(f"{self.api}/git/ref/heads/{self.branch}", timeout=20)
        if ref.status_code in (404, 409):                                    # empty repo: create the branch
            uid, body = next(iter(batch.items()))
            self.s.put(f"{self.api}/contents/{self._path(uid)}", timeout=30, json={
                "message": "Coding lab: first save", "branch": self.branch,
                "content": base64.b64encode(body.encode()).decode()}).raise_for_status()
            batch = {k: v for k, v in batch.items() if k != uid}
            if not batch:
                return
            ref = self.s.get(f"{self.api}/git/ref/heads/{self.branch}", timeout=20)
        ref.raise_for_status()
        head = ref.json()["object"]["sha"]
        base_tree = self.s.get(f"{self.api}/git/commits/{head}", timeout=20).json()["tree"]["sha"]
        tree = self.s.post(f"{self.api}/git/trees", timeout=60, json={"base_tree": base_tree, "tree": [
            {"path": self._path(uid), "mode": "100644", "type": "blob", "content": body} for uid, body in batch.items()]})
        tree.raise_for_status()
        commit = self.s.post(f"{self.api}/git/commits", timeout=30, json={
            "message": f"Coding lab: save {len(batch)} participant(s)", "tree": tree.json()["sha"], "parents": [head]})
        commit.raise_for_status()
        upd = self.s.patch(f"{self.api}/git/refs/heads/{self.branch}", timeout=30, json={"sha": commit.json()["sha"]})
        upd.raise_for_status()

    def flush_now(self):
        with self.lock:
            batch = dict(self.pending)
            self.pending.clear()
            self.urgent_since = self.oldest = None
        if batch:
            self._commit(batch)

    def load_all(self):
        r = self.s.get(f"{self.api}/contents/{self.folder}", params={"ref": self.branch}, timeout=20)
        ids = [f["name"][:-5] for f in r.json() if f["name"].endswith(".json")] if r.status_code == 200 else []
        if r.status_code not in (200, 404):
            r.raise_for_status()
        with self.lock:
            ids = sorted(set(ids) | set(self.pending))
        with ThreadPoolExecutor(8) as pool:
            return {uid: rec for uid, rec in zip(ids, pool.map(self.load, ids)) if rec}


def make_store(cfg):
    if cfg and cfg.get("github_repo") and cfg.get("github_token"):
        return GitHubStore(cfg["github_repo"], cfg["github_token"], cfg.get("branch", "main"), cfg.get("folder", "lab-data"))
    return LocalStore()
