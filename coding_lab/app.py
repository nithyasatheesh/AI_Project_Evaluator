"""AI Coding Lab: Jupyter-style coding with instant, rubric-based AI evaluation per task.

Run locally:   streamlit run coding_lab/app.py
Deploy:        Streamlit Community Cloud, main file coding_lab/app.py, secrets as in secrets.toml.example
"""
import base64
import copy
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
from code_editor import code_editor

import auth
import evaluator
import kernel
import report
import storage
import tasks as T

HERE = Path(__file__).resolve().parent
st.set_page_config(page_title="AI Coding Lab", page_icon="💻", layout="wide")

st.markdown("""<style>
.cellhead{font-family:ui-monospace,Consolas,monospace;font-size:.8rem;color:#9AA4D0;margin:0 0 -6px 2px}
.outhead{font-family:ui-monospace,Consolas,monospace;font-size:.75rem;color:#9AA4D0;margin:4px 0 -8px 2px}
.taskbrief li{margin:2px 0}
.chk{font-size:.9rem;margin:2px 0}
.chk.ok{color:#3DDC97}.chk.no{color:#9AA4D0}
.errlabel{color:#FF6B81;font-size:.8rem;font-weight:600;margin:4px 0 -8px 2px}
div[data-testid="stMetricValue"]{font-variant-numeric:tabular-nums}
</style>""", unsafe_allow_html=True)


# --------------------------------------------------------------------------- config

def secret(key, default=None):
    try:
        return st.secrets[key]
    except Exception:
        return default


LAB = dict(secret("lab", {}) or {})
COHORT = LAB.get("cohort_name", "AI Coding Lab")
MODEL = LAB.get("model", "gpt-4.1-mini")
MAX_EVALS = int(LAB.get("max_evaluations_per_task", 1))
CELL_TIMEOUT = int(LAB.get("cell_timeout_seconds", 60))
USERS = {k: dict(v) for k, v in (secret("users", {}) or {}).items()}


@st.cache_resource
def get_store():
    return storage.make_store(dict(secret("storage", {}) or {}))


@st.cache_resource
def get_openai():
    key = secret("OPENAI_API_KEY")
    if not key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=key)


def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@st.cache_resource
def warm_kernel():
    """Start the shared Python process in the background so the first cell runs quickly."""
    import threading
    threading.Thread(target=kernel._ZYGOTE.ensure, daemon=True).start()
    return True


warm_kernel()


# --------------------------------------------------------------------------- records

def new_cell(kind="code", source=""):
    return {"id": uuid.uuid4().hex[:10], "type": kind, "source": source, "outputs": [], "exec_count": None}


def new_record(user):
    nb = {}
    for t in T.TASKS:
        nb[t["id"]] = [new_cell("code", s) for s in t["starter"]] + [new_cell("markdown", "")]
    return {"id": user["id"], "name": user["name"], "project": T.PROJECT_ID, "notebook": nb, "evaluations": {},
            "eval_attempts": {}, "facts": {}, "exec_counter": 0, "submitted_at": None, "overall_feedback": "",
            "admin_rev": 0, "created_at": now(), "updated_at": now()}


def storable(record):
    """Copy for storage: plots are not stored (they are re-created by running the cell), tables are trimmed."""
    rec = copy.deepcopy(record)
    for cells in rec["notebook"].values():
        for c in cells:
            outs = []
            for o in c.get("outputs", []):
                if o.get("type") == "image":
                    outs.append({"type": "image_saved"})
                elif o.get("type") == "table":
                    o["data"]["data"] = o["data"].get("data", [])[:20]
                    o["data"]["index"] = o["data"].get("index", [])[:20]
                    outs.append(o)
                else:
                    outs.append(o)
            c["outputs"] = outs
    return rec


def save(force=False):
    rec = st.session_state.record
    if not force and time.time() - st.session_state.get("last_save", 0) < 30:
        st.session_state.dirty = True
        return
    store = get_store()
    try:
        remote = store.load(rec["id"])
        if remote and remote.get("admin_rev", 0) > rec.get("admin_rev", 0):
            # The trainer changed evaluations (e.g. unlocked a task): their change wins.
            rec["evaluations"] = remote.get("evaluations", {})
            rec["eval_attempts"] = remote.get("eval_attempts", {})
            rec["submitted_at"] = remote.get("submitted_at")
            rec["overall_feedback"] = remote.get("overall_feedback", "")
            rec["admin_rev"] = remote["admin_rev"]
            st.toast("Your trainer updated your evaluations.")
        rec["updated_at"] = now()
        store.save(rec["id"], storable(rec), urgent=force)
        st.session_state.last_save = time.time()
        st.session_state.dirty = False
        st.session_state.save_error = ""
    except Exception as e:  # noqa: BLE001
        st.session_state.save_error = f"Could not save your work: {e}"


def get_kernel():
    k = st.session_state.get("kernel")
    if k is None:
        k = kernel.Kernel(timeout=CELL_TIMEOUT)
        st.session_state.kernel = k
    return k


def run_cell(cell):
    rec = st.session_state.record
    with st.spinner("Running…"):
        r = get_kernel().run(cell["source"])
    rec["exec_counter"] += 1
    cell["exec_count"] = rec["exec_counter"]
    cell["outputs"] = r["outputs"]
    if r.get("restarted"):
        st.session_state.kernel_restarted = True
    facts = get_kernel().inspect()
    if facts:
        rec["facts"] = facts
    save()
    return r


def run_all():
    rec = st.session_state.record
    get_kernel().restart()
    bar = st.progress(0.0, "Running all cells…")
    cells = [c for t in T.TASKS for c in rec["notebook"][t["id"]] if c["type"] == "code" and c["source"].strip()]
    for i, c in enumerate(cells, 1):
        r = run_cell(c)
        bar.progress(i / max(1, len(cells)), f"Running cell {i} of {len(cells)}")
        if not r["ok"]:
            bar.empty()
            st.warning(f"Stopped at an error in cell {i}. Fix it and run again.")
            return
    bar.empty()
    save(force=True)


# --------------------------------------------------------------------------- rendering helpers

def show_outputs(outputs):
    for o in outputs or []:
        t = o.get("type")
        if t == "text":
            st.code(o["text"], language=None)
        elif t == "error":
            st.markdown('<div class="errlabel">Error</div>', unsafe_allow_html=True)
            st.code(o["text"], language=None)
        elif t == "table":
            d = o["data"]
            try:
                df = pd.DataFrame(d.get("data", []), columns=d.get("columns"), index=d.get("index"))
            except Exception:
                df = pd.DataFrame(d.get("data", []))
            st.dataframe(df, width="stretch", height=min(38 + 35 * len(df), 360))
            r, c = o.get("shape", [len(df), len(df.columns)])
            if r > len(df) or c > len(df.columns):
                st.caption(f"Showing {len(df)} of {r} rows × {min(c, len(df.columns))} of {c} columns")
        elif t == "image":
            st.image(base64.b64decode(o["png"]))
        elif t == "image_saved":
            st.caption("📈 A plot was produced here. Run the cell again to display it.")


def band(pct):
    return "Distinction" if pct >= 80 else "Merit" if pct >= 65 else "Pass" if pct >= 50 else "Below 50%"


def task_status(rec, t):
    if t["id"] in rec["evaluations"]:
        e = rec["evaluations"][t["id"]]
        return f"✓ {e['marks']}/{t['marks']}"
    return "○"


# --------------------------------------------------------------------------- login

def login_page():
    left, mid, right = st.columns([1, 1.3, 1])
    with mid:
        st.markdown(f"### 💻 {COHORT}")
        st.markdown(f"**{T.LAB_TITLE}**  \n{T.MILESTONE}")
        with st.form("login"):
            lid = st.text_input("Login ID", placeholder="e.g. LD001")
            pw = st.text_input("Password", type="password")
            ok = st.form_submit_button("Log in", type="primary", width="stretch")
        if ok:
            if not USERS:
                st.error("No logins are set up yet. Ask your trainer.")
                return
            user, err = auth.login(USERS, lid, pw)
            if not user:
                st.error(err)
                return
            st.session_state.user = user
            if user["role"] == "participant":
                try:
                    rec = get_store().load(user["id"])
                except Exception as e:  # noqa: BLE001
                    st.error(f"Could not load your saved work: {e}")
                    return
                if not rec:
                    rec = new_record(user)
                rec["name"] = user["name"]
                st.session_state.record = rec
                st.session_state.seen = {}
                st.session_state.last_save = 0
                save(force=True)
            st.rerun()
        st.caption("Use the login ID and password your trainer gave you.")


def logout():
    if st.session_state.get("record") is not None:
        save(force=True)
    k = st.session_state.get("kernel")
    if k:
        k.stop()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


# --------------------------------------------------------------------------- participant tabs

def tab_problem():
    st.markdown(f"## {T.LAB_TITLE}")
    st.caption(T.MILESTONE)
    st.markdown(T.PROBLEM_STATEMENT)
    st.markdown("### Data dictionary")
    st.dataframe(pd.DataFrame(T.DATA_DICTIONARY, columns=["Column", "Meaning"]), hide_index=True, width="stretch")
    st.markdown("### First rows")
    st.dataframe(load_data_preview(), width="stretch", hide_index=True)


@st.cache_data
def load_data_preview():
    return pd.read_csv(HERE / "data" / T.DATA_FILE, nrows=8)


def tab_rubric():
    st.markdown(f"## Rubric · {T.MILESTONE}")
    st.markdown("Each task is evaluated against one rubric criterion. **Total: 100 marks.**")
    st.dataframe(pd.DataFrame([{"Task": f"{i}. {t['title']}", "Rubric criterion": t["criterion"], "Marks": t["marks"],
                                "What is assessed": t["guidance"]} for i, t in enumerate(T.TASKS, 1)]),
                 hide_index=True, width="stretch", column_config={"What is assessed": st.column_config.TextColumn(width="large")})
    st.markdown("### What the evaluator looks for in each task")
    cols = st.columns(len(T.TASKS))
    for col, (i, t) in zip(cols, enumerate(T.TASKS, 1)):
        with col:
            st.markdown(f"**{i}. {t['title']}**")
            st.markdown("\n".join(f"- {label}" for label, _ in t["checks"]))
    st.markdown("### Score bands")
    st.markdown("**Distinction** 80+ · **Merit** 65–79 · **Pass** 50–64 · **Below 50%** under 50")


def code_cell(t, cell, idx, locked):
    seen = st.session_state.seen
    head = f"In [{cell['exec_count'] or ' '}]:"
    hc, bc = st.columns([6, 1])
    hc.markdown(f'<div class="cellhead">{head}' + ("" if locked else
                '&nbsp;&nbsp;·&nbsp;&nbsp;Run: button or Ctrl+Enter') + '</div>', unsafe_allow_html=True)
    if not locked and bc.button("🗑", key=f"del_{cell['id']}", help="Delete this cell"):
        st.session_state.record["notebook"][t["id"]].remove(cell)
        save()
        st.rerun()
    if locked:
        st.code(cell["source"] or "# (empty)", language="python")
        if st.button("▶ Run", key=f"runl_{cell['id']}", help="Run again to rebuild variables (code is locked)"):
            run_cell(cell)
            st.rerun()
    else:
        resp = code_editor(
            cell["source"], lang="python", theme="dark", height=[4, 28], key=f"ed_{cell['id']}",
            response_mode=["blur"], allow_reset=False,
            buttons=[{"name": "Run", "feather": "Play", "primary": True, "hasText": True, "showWithIcon": True,
                      "alwaysOn": True, "commands": ["submit"], "style": {"bottom": "0.44rem", "right": "0.4rem"}}],
            options={"wrap": True, "showLineNumbers": True}, props={"style": {"borderRadius": "8px"}})
        if resp and resp.get("id") and seen.get(cell["id"]) != resp["id"]:
            seen[cell["id"]] = resp["id"]
            changed = cell["source"] != resp.get("text", cell["source"])
            cell["source"] = resp.get("text", cell["source"])
            if resp.get("type") == "submit":
                run_cell(cell)
                st.rerun()                     # refresh the cell number and the checklist
            elif changed:
                save()
                st.rerun()
    if cell.get("outputs"):
        show_outputs(cell["outputs"])


def notes_cell(t, cell, locked):
    hc, bc = st.columns([6, 1])
    hc.markdown('<div class="cellhead">Notes</div>', unsafe_allow_html=True)
    if locked:
        st.markdown(cell["source"] or "_No notes._")
        return
    if bc.button("🗑", key=f"del_{cell['id']}", help="Delete this cell"):
        st.session_state.record["notebook"][t["id"]].remove(cell)
        save()
        st.rerun()

    def changed(c=cell):
        c["source"] = st.session_state[f"md_{c['id']}"]
        save()
    st.text_area("Notes", value=cell["source"], key=f"md_{cell['id']}", on_change=changed, height=120,
                 label_visibility="collapsed",
                 placeholder="Write your findings and reasoning here (Markdown supported). Explanations earn marks.")


def evaluate_block(t, cells):
    rec = st.session_state.record
    client = get_openai()
    attempts = rec["eval_attempts"].get(t["id"], 0)
    st.markdown("#### Evaluate this task")
    unrun = [c for c in cells if c["type"] == "code" and c["source"].strip() and not c.get("exec_count")]
    if unrun:
        st.warning(f"{len(unrun)} code cell(s) in this task haven't been run. Run them first so the evaluator can see the outputs.")
    left = MAX_EVALS - attempts
    sure = st.checkbox("I've finished this task" + (" — evaluate it now (this can be done only once)" if MAX_EVALS == 1
                       else f" — evaluate it now ({left} evaluation{'s' if left != 1 else ''} left)"),
                       key=f"sure_{t['id']}")
    if st.button(f"Evaluate task · {t['marks']} marks", type="primary", disabled=not sure, key=f"eval_{t['id']}"):
        if client is None:
            st.error("Evaluation isn't set up yet (OpenAI key missing). Tell your trainer.")
            return
        checks = T.run_checks(t, cells, rec.get("facts", {}))
        with st.spinner("Evaluating against the rubric…"):
            try:
                result = evaluator.evaluate_task(client, MODEL, T.PROBLEM_STATEMENT, t, cells, checks)
            except Exception as e:  # noqa: BLE001
                st.error(f"The evaluation could not be completed, so nothing was used up. Try again in a minute. ({e})")
                return
        rec["evaluations"][t["id"]] = result
        rec["eval_attempts"][t["id"]] = attempts + 1
        save(force=True)
        st.session_state.flash = (t["id"], result)
        st.rerun()


def tab_notebook():
    rec = st.session_state.record
    labels = {t["id"]: f"{i}. {t['title']}  {task_status(rec, t)}" for i, t in enumerate(T.TASKS, 1)}
    if "task" not in st.session_state:
        st.session_state.task = next((t["id"] for t in T.TASKS if t["id"] not in rec["evaluations"]), T.TASKS[0]["id"])
    pick = st.segmented_control("Task", list(labels), format_func=labels.get, key="task_picker",
                                default=st.session_state.task, label_visibility="collapsed")
    if pick:
        st.session_state.task = pick
    t = T.TASK_BY_ID[st.session_state.task]
    cells = rec["notebook"][t["id"]]
    evaluated = t["id"] in rec["evaluations"]
    locked = (evaluated and rec["eval_attempts"].get(t["id"], 0) >= MAX_EVALS) or bool(rec.get("submitted_at"))

    flash = st.session_state.pop("flash", None)
    if flash and flash[0] == t["id"]:
        st.success(f"**Task evaluated: {flash[1]['marks']} / {t['marks']} marks.** {flash[1]['feedback']}")

    top_l, top_r = st.columns([3, 2])
    with top_l:
        st.markdown(f"### {t['title']} · {t['marks']} marks")
        st.markdown('<ul class="taskbrief">' + "".join(f"<li>{b}</li>" for b in
                    [x.replace("`", "") for x in t["brief"]]) + "</ul>", unsafe_allow_html=True)
    with top_r:
        st.markdown("**Checklist** (updates as you work)")
        for label, ok in T.run_checks(t, cells, rec.get("facts", {})):
            st.markdown(f'<div class="chk {"ok" if ok else "no"}">{"✓" if ok else "○"} {label}</div>', unsafe_allow_html=True)
    if evaluated:
        e = rec["evaluations"][t["id"]]
        st.info(f"**Evaluated: {e['marks']} / {t['marks']}.** " + ("This task is locked. " if locked else "")
                + "Full feedback is in the Evaluation results tab.")
    st.divider()

    for i, c in enumerate(list(cells), 1):
        with st.container(border=True):
            if c["type"] == "code":
                code_cell(t, c, i, locked)
            else:
                notes_cell(t, c, locked)

    if not locked:
        a, b, c3, _ = st.columns([1, 1, 1.4, 3])
        if a.button("＋ Code cell", key=f"addc_{t['id']}"):
            cells.append(new_cell("code"))
            save()
            st.rerun()
        if b.button("＋ Notes cell", key=f"addm_{t['id']}"):
            cells.append(new_cell("markdown"))
            save()
            st.rerun()
        if c3.button("▶ Run this task's cells", key=f"runt_{t['id']}"):
            for cell in cells:
                if cell["type"] == "code" and cell["source"].strip():
                    if not run_cell(cell)["ok"]:
                        break
            st.rerun()
        st.divider()
        evaluate_block(t, cells)


def tab_submission():
    rec = st.session_state.record
    done = [t for t in T.TASKS if t["id"] in rec["evaluations"]]
    got = sum(rec["evaluations"][t["id"]]["marks"] for t in done)
    st.markdown("## Submission")
    st.dataframe(pd.DataFrame([{"Task": f"{i}. {t['title']}",
                                "Status": "Evaluated" if t["id"] in rec["evaluations"] else "Not evaluated yet",
                                "Marks": (f"{rec['evaluations'][t['id']]['marks']} / {t['marks']}"
                                          if t["id"] in rec["evaluations"] else f"– / {t['marks']}")}
                               for i, t in enumerate(T.TASKS, 1)]), hide_index=True, width="stretch")
    if rec.get("submitted_at"):
        st.success(f"✅ Submitted on {rec['submitted_at'][:16].replace('T', ' ')} UTC. Final score: **{got} / 100**.")
    else:
        missing = len(T.TASKS) - len(done)
        if missing:
            st.warning(f"{missing} task(s) are not evaluated yet. If you submit now, they score 0.")
        sure = st.checkbox("I'm ready to submit. My notebook will be locked.", key="sure_submit")
        if st.button("Submit notebook", type="primary", disabled=not sure):
            client = get_openai()
            if client and done:
                with st.spinner("Preparing your overall feedback…"):
                    try:
                        rec["overall_feedback"] = evaluator.overall_summary(client, MODEL, rec["evaluations"], T.TASKS)
                    except Exception:  # noqa: BLE001
                        rec["overall_feedback"] = ""
            rec["submitted_at"] = now()
            save(force=True)
            st.balloons()
            st.rerun()
    st.markdown("#### Downloads")
    d1, d2 = st.columns(2)
    d1.download_button("⬇ My notebook (.ipynb)", report.to_ipynb(rec, T.TASKS, T.LAB_TITLE),
                       file_name=f"{rec['id']}_{T.PROJECT_ID}_milestone1.ipynb", mime="application/x-ipynb+json")
    if done:
        d2.download_button("⬇ My result report (PDF)", report.pdf_report(rec, T.TASKS, T.LAB_TITLE, T.MILESTONE, COHORT),
                           file_name=f"{rec['id']}_{T.PROJECT_ID}_milestone1_result.pdf", mime="application/pdf")


def tab_results():
    rec = st.session_state.record
    done = [t for t in T.TASKS if t["id"] in rec["evaluations"]]
    if not done:
        st.info("No tasks evaluated yet. Finish a task in the Notebook tab and click **Evaluate task**.")
        return
    got = sum(rec["evaluations"][t["id"]]["marks"] for t in done)
    m1, m2, m3 = st.columns(3)
    m1.metric("Score so far", f"{got} / 100")
    m2.metric("Tasks evaluated", f"{len(done)} / {len(T.TASKS)}")
    max_done = sum(t["marks"] for t in done)
    m3.metric("Band (on evaluated tasks)", band(100 * got / max_done))
    if rec.get("overall_feedback"):
        st.markdown("#### Overall feedback")
        st.markdown(rec["overall_feedback"])
    st.markdown("#### Task results")
    for i, t in enumerate(T.TASKS, 1):
        e = rec["evaluations"].get(t["id"])
        if not e:
            st.markdown(f"**{i}. {t['title']}** · not evaluated yet")
            continue
        with st.expander(f"{i}. {t['title']} · **{e['marks']} / {t['marks']}**", expanded=len(done) <= 2):
            st.progress(e["marks"] / t["marks"])
            st.markdown(e["feedback"])
            a, b = st.columns(2)
            a.markdown("**Strengths**\n" + "\n".join(f"- {x}" for x in e.get("strengths", [])))
            b.markdown("**To improve**\n" + "\n".join(f"- {x}" for x in e.get("improvements", [])))
            st.caption("Checks at evaluation: " + " · ".join(f"{'✓' if ok else '○'} {l}" for l, ok in e.get("checks", [])))
            st.caption(f"Evaluated {e['evaluated_at'][:16].replace('T', ' ')} UTC · AI-generated, subject to trainer review")
    st.download_button("⬇ Download my result report (PDF)", report.pdf_report(rec, T.TASKS, T.LAB_TITLE, T.MILESTONE, COHORT),
                       file_name=f"{rec['id']}_{T.PROJECT_ID}_milestone1_result.pdf", mime="application/pdf", key="pdf2")


def participant_view():
    rec = st.session_state.record
    with st.sidebar:
        st.markdown(f"### {rec['name']}")
        st.caption(f"Login ID: {rec['id']}")
        done = [t for t in T.TASKS if t["id"] in rec["evaluations"]]
        st.progress(len(done) / len(T.TASKS), f"{len(done)} of {len(T.TASKS)} tasks evaluated")
        st.metric("Score so far", f"{sum(rec['evaluations'][t['id']]['marks'] for t in done)} / 100")
        if st.button("💾 Save", width="stretch"):
            save(force=True)
            st.toast("Saved")
        if st.button("▶▶ Run all cells", width="stretch", help="Restart Python and run every code cell in order"):
            run_all()
            st.rerun()
        if st.button("↺ Restart kernel", width="stretch", help="Clear all variables"):
            get_kernel().restart()
            st.toast("Kernel restarted. Variables cleared.")
        if st.session_state.get("save_error"):
            st.error(st.session_state.save_error)
        elif st.session_state.get("dirty"):
            st.caption("Unsaved changes (auto-saves shortly)")
        else:
            st.caption("All changes saved")
        st.divider()
        if st.button("Log out", width="stretch"):
            logout()
    if st.session_state.pop("kernel_restarted", False):
        st.warning("A cell ran too long and the kernel was restarted. Use **Run all cells** in the sidebar to rebuild your variables.")
    tabs = st.tabs(["📄 Problem statement", "📋 Instructions", "📐 Rubric", "💻 Notebook", "📤 Submission", "📊 Evaluation results"])
    with tabs[0]:
        tab_problem()
    with tabs[1]:
        st.markdown("## Instructions")
        st.markdown(T.INSTRUCTIONS)
    with tabs[2]:
        tab_rubric()
    with tabs[3]:
        tab_notebook()
    with tabs[4]:
        tab_submission()
    with tabs[5]:
        tab_results()


# --------------------------------------------------------------------------- trainer view

@st.cache_data(ttl=60, show_spinner="Loading participants…")
def load_all(_nonce):
    return get_store().load_all()


def trainer_view():
    user = st.session_state.user
    with st.sidebar:
        st.markdown(f"### {user['name']}")
        st.caption("Trainer")
        if st.button("🔄 Refresh data", width="stretch"):
            st.session_state.nonce = time.time()
        if st.button("Log out", width="stretch"):
            logout()
    records = load_all(st.session_state.get("nonce", 0))
    participants = {uid: u for uid, u in USERS.items() if u.get("role", "participant") == "participant"}
    rows = []
    for uid, u in sorted(participants.items()):
        rec = records.get(uid.upper()) or records.get(uid)
        row = {"Login ID": uid, "Name": u.get("name", uid)}
        total = 0
        for i, t in enumerate(T.TASKS, 1):
            e = (rec or {}).get("evaluations", {}).get(t["id"])
            row[f"T{i}"] = e["marks"] if e else None
            total += e["marks"] if e else 0
        n = len((rec or {}).get("evaluations", {}))
        row.update({"Total": total if rec else None, "Tasks evaluated": n,
                    "Status": "Submitted" if rec and rec.get("submitted_at") else ("In progress" if rec else "Not started"),
                    "Last saved": (rec or {}).get("updated_at", "")[:16].replace("T", " ")})
        rows.append(row)
    df = pd.DataFrame(rows)
    tabs = st.tabs(["👥 Participants", "🔎 Participant detail", "📈 Cohort", "⚙️ Setup check"])
    with tabs[0]:
        st.markdown(f"## {COHORT} · {T.LAB_TITLE}")
        if df.empty:
            st.info("No participant logins are set up yet.")
        else:
            c = st.columns(4)
            c[0].metric("Participants", len(df))
            c[1].metric("Started", int((df["Status"] != "Not started").sum()))
            c[2].metric("Submitted", int((df["Status"] == "Submitted").sum()))
            scored = df[df["Tasks evaluated"] > 0]
            c[3].metric("Average total (started)", f"{scored['Total'].mean():.0f}" if len(scored) else "–")
            st.dataframe(df, hide_index=True, width="stretch")
            st.download_button("⬇ Download CSV", df.to_csv(index=False).encode(), "coding_lab_scores.csv", "text/csv")
    with tabs[1]:
        if df.empty:
            st.info("No participants yet.")
        else:
            uid = st.selectbox("Participant", df["Login ID"], format_func=lambda x: f"{x} · {participants[x].get('name', x)}")
            rec = records.get(uid)
            if not rec:
                st.info("This participant hasn't logged in yet.")
            else:
                for i, t in enumerate(T.TASKS, 1):
                    e = rec.get("evaluations", {}).get(t["id"])
                    with st.expander(f"{i}. {t['title']} · " + (f"{e['marks']} / {t['marks']}" if e else "not evaluated")):
                        if e:
                            st.markdown(f"**Feedback:** {e['feedback']}")
                        for c in rec["notebook"].get(t["id"], []):
                            if c["type"] == "code":
                                st.code(c["source"] or "# (empty)", language="python")
                                show_outputs(c.get("outputs"))
                            elif c["source"].strip():
                                st.markdown(c["source"])
                        if e and st.button(f"Unlock task {i} (removes its score so it can be evaluated again)",
                                           key=f"unlock_{uid}_{t['id']}"):
                            rec["evaluations"].pop(t["id"], None)
                            rec.get("eval_attempts", {}).pop(t["id"], None)
                            rec["submitted_at"] = None
                            rec["admin_rev"] = rec.get("admin_rev", 0) + 1
                            get_store().save(uid, rec, urgent=True)
                            st.session_state.nonce = time.time()
                            st.success("Unlocked. The participant sees it the next time their work saves.")
                if rec.get("submitted_at"):
                    st.success(f"Submitted {rec['submitted_at'][:16].replace('T', ' ')} UTC")
                    if rec.get("overall_feedback"):
                        st.markdown(f"**Overall feedback:** {rec['overall_feedback']}")
                if rec.get("evaluations"):
                    st.download_button("⬇ PDF result report", report.pdf_report(rec, T.TASKS, T.LAB_TITLE, T.MILESTONE, COHORT),
                                       file_name=f"{uid}_result.pdf", mime="application/pdf")
                st.download_button("⬇ Notebook (.ipynb)", report.to_ipynb(rec, T.TASKS, T.LAB_TITLE),
                                   file_name=f"{uid}_notebook.ipynb", key="nbdl")
    with tabs[2]:
        if df.empty or df["Tasks evaluated"].sum() == 0:
            st.info("Charts appear once tasks are evaluated.")
        else:
            st.markdown("**Average marks per task (evaluated tasks only, out of 20)**")
            avg = {f"{i}. {t['title']}": df[f"T{i}"].dropna().mean() for i, t in enumerate(T.TASKS, 1)}
            st.bar_chart(pd.Series(avg).dropna(), horizontal=True)
            st.markdown("**Tasks evaluated per participant**")
            st.bar_chart(df["Tasks evaluated"].value_counts().sort_index())
    with tabs[3]:
        st.markdown("### Setup check")
        st.write("✅ OpenAI key set" if secret("OPENAI_API_KEY") else "❌ OPENAI_API_KEY missing: evaluation won't work")
        kind = get_store().kind
        if getattr(get_store(), "last_error", ""):
            st.error(f"Last save to GitHub failed (will retry): {get_store().last_error}")
        st.write("✅ Saving to GitHub (permanent)" if kind == "github"
                 else "⚠️ Saving to the app's local disk. On Streamlit Cloud this is wiped on restart: set up [storage].")
        st.write(f"👥 {len(participants)} participant logins, {len(USERS) - len(participants)} trainer logins")
        st.write(f"🤖 Model: {MODEL} · Evaluations per task: {MAX_EVALS} · Cell time limit: {CELL_TIMEOUT}s")


# --------------------------------------------------------------------------- main

if "user" not in st.session_state:
    login_page()
elif st.session_state.user["role"] == "trainer":
    trainer_view()
else:
    participant_view()
