"""Sandboxed, Jupyter-like Python kernels for the coding lab.

Design
------
* One "zygote" process is started with a CLEAN environment (no API keys, no tokens)
  and pre-imports pandas / numpy / matplotlib / seaborn / scikit-learn once.
* Each participant session gets its own kernel: a child forked from the zygote, so the
  heavy libraries are shared copy-on-write and a new kernel starts in milliseconds.
* Variables persist between cells (like Jupyter) until the kernel is restarted.
* Inside a kernel an audit hook (which cannot be removed) blocks: reading the app's
  files and secrets, /proc, network connections, starting processes, ctypes, and
  writing outside the temp folder. Long-running cells are stopped after a timeout.
* The app and kernels talk only in JSON (never pickle), so a kernel cannot run code
  inside the app process.

This is a practical sandbox for a training cohort, not a hardened multi-tenant one.
"""
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from multiprocessing.connection import Client, Listener
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
PRELOAD = [
    "numpy", "pandas", "matplotlib", "matplotlib.pyplot", "seaborn", "scipy.stats",
    "sklearn.linear_model", "sklearn.model_selection", "sklearn.metrics", "sklearn.preprocessing",
    "sklearn.impute", "sklearn.compose", "sklearn.pipeline",
]
MAX_TEXT = 20000
MAX_IMAGES = 8
MAX_TABLE_ROWS = 100
MAX_TABLE_COLS = 40


# ============================================================================
# Kernel side (runs inside the zygote and its forked children)
# ============================================================================

def _install_guard(app_dir, data_dir, tmp_dir):
    app_dir, data_dir, tmp_dir = str(app_dir), str(data_dir), str(tmp_dir)
    blocked_events = {
        "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.fork",
        "os.forkpty", "os.kill", "os.killpg", "pty.spawn", "socket.connect", "socket.bind",
        "socket.sendto", "socket.sendmsg", "ctypes.dlopen", "ctypes.dlsym", "ctypes.string_at",
        "ctypes.wstring_at", "ctypes.addressof", "ctypes.cdata", "ctypes.call_function",
        "ctypes.create_string_buffer", "os.chmod", "os.chown", "os.setuid",
        "urllib.Request", "webbrowser.open",
    }
    blocked_imports = {"ctypes", "_ctypes", "subprocess", "multiprocessing", "socket", "_socket",
                       "requests", "urllib3", "http.client", "ftplib", "smtplib", "telnetlib", "pty"}
    secret_words = ("secret", ".streamlit", ".ssh", ".git/", "shadow", ".env", "token")
    # CPU/memory info that numerical libraries read; every other /proc file (e.g. another
    # process's environment) stays blocked.
    proc_ok = ("/proc/cpuinfo", "/proc/meminfo", "/proc/stat", "/proc/loadavg", "/proc/self/stat",
               "/proc/self/status", "/proc/self/cgroup", "/proc/self/mountinfo", "/proc/self/maps")

    def allowed_path(p, writing):
        try:
            p = os.path.realpath(os.fsdecode(p))
        except Exception:
            return False
        low = p.lower()
        if writing:
            return p.startswith(tmp_dir) or p.startswith(tempfile.gettempdir()) or low.startswith("/dev/null")
        if any(w in low for w in secret_words):
            return False
        if low.startswith("/proc/"):
            own = f"/proc/{os.getpid()}/"
            if low.startswith(own):
                low = "/proc/self/" + low[len(own):]
            return low.startswith(proc_ok)
        if p.startswith(app_dir) and not p.startswith(data_dir):
            return False                       # app source and config are off-limits; the dataset is allowed
        return True

    def hook(event, args):
        if event in blocked_events:
            raise PermissionError(f"Not allowed in the lab: {event}")
        if event == "import" and args and args[0] in blocked_imports:
            raise PermissionError(f"Module '{args[0]}' is not available in the lab")
        if event == "open" and args:
            path, mode = args[0], args[1] if len(args) > 1 else "r"
            if isinstance(path, int) or path is None:
                return
            flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or \
                      bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND))
            if not allowed_path(path, writing):
                raise PermissionError(f"This file is not available in the lab: {os.fsdecode(path)}")
        if event in ("os.remove", "os.rename", "os.rmdir", "shutil.rmtree", "os.truncate"):
            p = args[0] if args else ""
            if not allowed_path(p, True):
                raise PermissionError("Not allowed in the lab")

    sys.addaudithook(hook)


def _jsonable_table(obj):
    import pandas as pd
    if isinstance(obj, pd.Series):
        obj = obj.to_frame()
    sub = obj.iloc[:MAX_TABLE_ROWS, :MAX_TABLE_COLS]
    data = json.loads(sub.to_json(orient="split", date_format="iso", default_handler=str))
    return {"type": "table", "data": data, "shape": [int(obj.shape[0]), int(obj.shape[1])]}


def _render(obj, outputs):
    import pandas as pd
    if obj is None:
        return
    if isinstance(obj, (pd.DataFrame, pd.Series)):
        outputs.append(_jsonable_table(obj))
        return
    try:
        import matplotlib.figure
        if isinstance(obj, matplotlib.figure.Figure):
            return                                  # captured with the other figures
    except Exception:
        pass
    text = repr(obj)
    outputs.append({"type": "text", "text": text[:MAX_TEXT]})


def _capture_figures(outputs):
    import base64
    import io
    import matplotlib.pyplot as plt
    for n, num in enumerate(plt.get_fignums()):
        if n >= MAX_IMAGES:
            break
        buf = io.BytesIO()
        plt.figure(num).savefig(buf, format="png", dpi=90, bbox_inches="tight")
        outputs.append({"type": "image", "png": base64.b64encode(buf.getvalue()).decode()})
    plt.close("all")


def _run_cell(code, ns):
    import ast
    import contextlib
    import io
    import traceback
    outputs, out = [], io.StringIO()
    ns["display"] = lambda *objs: [_render(o, outputs) for o in objs]
    ok = True
    t0 = time.time()
    try:
        tree = ast.parse(code, "<cell>", "exec")
        last = None
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last = ast.Expression(tree.body.pop().value)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            exec(compile(tree, "<cell>", "exec"), ns)
            value = eval(compile(last, "<cell>", "eval"), ns) if last is not None else None
        text = out.getvalue()
        if text:
            outputs.insert(0, {"type": "text", "text": text[-MAX_TEXT:]})
        _render(value, outputs)
    except BaseException as exc:                 # noqa: BLE001 - show every error to the participant
        ok = False
        text = out.getvalue()
        if text:
            outputs.insert(0, {"type": "text", "text": text[-MAX_TEXT:]})
        tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tb = [line for line in tb if 'File "<cell>"' in line or not line.startswith("  File ")]
        outputs.append({"type": "error", "text": "".join(tb)[-MAX_TEXT:]})
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            outputs[-1]["text"] = "Execution stopped."
    try:
        _capture_figures(outputs)
    except Exception:
        pass
    return {"ok": ok, "outputs": outputs, "seconds": round(time.time() - t0, 2)}


def _inspect(ns):
    """Facts about the participant's variables, used for automated task checks."""
    import pandas as pd
    facts = {"dataframes": [], "fitted_models": [], "variables": sorted(k for k in ns if not k.startswith("_"))[:200]}
    for k, v in ns.items():
        if k.startswith("_"):
            continue
        if isinstance(v, pd.DataFrame):
            facts["dataframes"].append({"name": k, "rows": int(v.shape[0]), "cols": int(v.shape[1]),
                                        "missing": int(v.isna().sum().sum()),
                                        "duplicates": int(v.duplicated().sum()) if v.shape[0] < 200000 else -1,
                                        "has_target": "default_flag" in v.columns})
        if hasattr(v, "predict") and hasattr(v, "fit"):
            try:
                from sklearn.utils.validation import check_is_fitted
                check_is_fitted(v)
                names = type(v).__name__
                if hasattr(v, "steps"):
                    names += ":" + ",".join(type(s).__name__ for _, s in v.steps)
                facts["fitted_models"].append({"name": k, "type": names})
            except Exception:
                pass
    return facts


def _serve_child(conn, tmp_dir):
    os.chdir(DATA_DIR)
    import matplotlib.pyplot as plt
    plt.show = lambda *a, **k: None
    _install_guard(HERE, DATA_DIR, tmp_dir)
    ns = {"__name__": "__main__", "DATA_PATH": str(DATA_DIR / "loan_applications.csv")}
    conn.send_bytes(json.dumps({"pid": os.getpid()}).encode())
    while True:
        try:
            msg = json.loads(conn.recv_bytes().decode())
        except (EOFError, OSError):
            os._exit(0)
        op = msg.get("op")
        if op == "run":
            reply = _run_cell(msg.get("code", ""), ns)
        elif op == "inspect":
            try:
                reply = _inspect(ns)
            except Exception as e:  # noqa: BLE001
                reply = {"error": str(e)}
        else:
            reply = {"error": "unknown op"}
        conn.send_bytes(json.dumps(reply, default=str).encode())


def _warm_up():
    """Let libraries finish their one-time native set-up (e.g. scikit-learn's thread-pool
    scan, which uses ctypes) before kernels are forked and the sandbox switches on."""
    try:
        import numpy as np
        from sklearn.cluster import KMeans
        from sklearn.linear_model import LogisticRegression
        X = np.random.default_rng(0).random((60, 3))
        KMeans(2, n_init=1, random_state=0).fit(X)
        LogisticRegression().fit(X, (X[:, 0] > 0.5).astype(int))
        from sklearn.utils.parallel import _get_threadpool_controller  # noqa: F401
        _get_threadpool_controller()
    except Exception:
        pass


def zygote_main(address):
    for mod in PRELOAD:
        try:
            __import__(mod)
        except Exception:
            pass
    import matplotlib
    matplotlib.use("Agg")
    _warm_up()
    signal.signal(signal.SIGCHLD, signal.SIG_IGN)        # auto-reap finished kernels
    listener = Listener(address, family="AF_UNIX")
    print("ready", flush=True)
    devnull = os.open(os.devnull, os.O_RDWR)
    os.dup2(devnull, 1)                                  # nothing else goes to the app's pipe
    os.dup2(devnull, 2)
    while True:
        conn = listener.accept()
        pid = os.fork()
        if pid == 0:
            listener.close()
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
            tmp_dir = tempfile.mkdtemp(prefix="lab_")
            os.environ["MPLCONFIGDIR"] = tmp_dir
            _serve_child(conn, tmp_dir)
            os._exit(0)
        conn.close()


# ============================================================================
# App side
# ============================================================================

class _Zygote:
    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.address = None

    def ensure(self):
        with self.lock:
            if self.proc and self.proc.poll() is None:
                return self.address
            self.address = os.path.join(tempfile.gettempdir(), f"labzyg_{uuid.uuid4().hex[:10]}.sock")
            env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": tempfile.gettempdir(),
                "LANG": "C.UTF-8", "PYTHONPATH": str(HERE), "MPLBACKEND": "Agg",
                "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                "PYTHONDONTWRITEBYTECODE": "1", "MPLCONFIGDIR": tempfile.gettempdir(),
            }
            self.proc = subprocess.Popen(
                [sys.executable, "-I", "-c",
                 f"import sys; sys.path.insert(0, {str(HERE)!r}); import kernel; kernel.zygote_main({self.address!r})"],
                env=env, cwd=str(DATA_DIR), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                close_fds=True, start_new_session=True)
            line = self.proc.stdout.readline()
            if b"ready" not in line:
                raise RuntimeError("The Python kernel could not start.")
            return self.address


_ZYGOTE = _Zygote()
_REGISTRY = {}
_REG_LOCK = threading.Lock()
IDLE_SECONDS = 45 * 60
MAX_KERNELS = 120


class Kernel:
    """One participant's Python session."""

    def __init__(self, timeout=60):
        self.timeout = timeout
        self.conn = None
        self.pid = None
        self.last_used = time.time()
        self.lock = threading.Lock()
        self.key = uuid.uuid4().hex

    def _start(self):
        address = _ZYGOTE.ensure()
        self.conn = Client(address, family="AF_UNIX")
        if not self.conn.poll(20):
            raise RuntimeError("The Python kernel did not respond.")
        self.pid = json.loads(self.conn.recv_bytes().decode())["pid"]
        with _REG_LOCK:
            _REGISTRY[self.key] = self
        _reap()

    def alive(self):
        if not self.pid:
            return False
        try:
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False

    def stop(self):
        if self.pid:
            try:
                os.kill(self.pid, signal.SIGKILL)
            except OSError:
                pass
        try:
            if self.conn:
                self.conn.close()
        except OSError:
            pass
        self.conn, self.pid = None, None
        with _REG_LOCK:
            _REGISTRY.pop(self.key, None)

    def restart(self):
        self.stop()
        self._start()

    def _call(self, payload, timeout):
        with self.lock:
            if not self.alive() or self.conn is None:
                self._start()
            self.last_used = time.time()
            try:
                self.conn.send_bytes(json.dumps(payload).encode())
                if not self.conn.poll(timeout):
                    self.stop()
                    return None
                raw = self.conn.recv_bytes(maxlength=40_000_000)
                return json.loads(raw.decode())
            except (EOFError, OSError, ValueError):
                self.stop()
                return None

    def run(self, code):
        reply = self._call({"op": "run", "code": code}, self.timeout)
        if reply is None:
            return {"ok": False, "seconds": self.timeout, "restarted": True, "outputs": [{
                "type": "error",
                "text": f"The cell stopped: it ran longer than {self.timeout} seconds or used too much memory. "
                        "The kernel was restarted, so your variables were cleared. Use 'Run all cells' to rebuild them."}]}
        return reply

    def inspect(self):
        return self._call({"op": "inspect"}, 15) or {}


def _reap():
    now = time.time()
    with _REG_LOCK:
        kernels = sorted(_REGISTRY.values(), key=lambda k: k.last_used)
    for k in kernels:
        if now - k.last_used > IDLE_SECONDS:
            k.stop()
    with _REG_LOCK:
        extra = len(_REGISTRY) - MAX_KERNELS
        oldest = sorted(_REGISTRY.values(), key=lambda k: k.last_used)[:max(0, extra)]
    for k in oldest:
        k.stop()
