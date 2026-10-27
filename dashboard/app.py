"""Project Evaluation — Streamlit results app (companion to evaluation-results/index.html).

Reads the same data.json the HTML dashboard uses. Nothing here calls the AI model.

Run locally from the evaluator repo root:
    pip install -r dashboard/requirements.txt
    streamlit run dashboard/app.py

On Streamlit Community Cloud (main file: dashboard/app.py), add to the app's Secrets:
    DATA_URL     = "https://raw.githubusercontent.com/<owner>/<submissions-repo>/main/evaluation-results/data.json"
    GITHUB_TOKEN = "<read-only token>"   # only if that repo is private
"""
import json
import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

LOCAL = Path(__file__).resolve().parent.parent / "evaluation-results" / "data.json"
BANDS = ["Distinction", "Merit", "Pass", "Below 50%"]

st.set_page_config(page_title="Project Evaluation", page_icon="📊", layout="wide")
st.markdown("""<style>
.kpi{background:#141B33;border:1px solid #2a3157;border-radius:12px;padding:14px 16px}
.kpi b{display:block;font-size:1.6rem;line-height:1.2} .kpi span{color:#9aa4d0;font-size:.8rem}
.crit{border:1px solid #2a3157;border-radius:10px;padding:10px 12px;margin-bottom:10px;background:#0E1222}
.crit .top{display:flex;justify-content:space-between;font-weight:600}
.crit .tr{background:#232a4d;border-radius:4px;height:8px;margin:6px 0;overflow:hidden}
.crit .tr i{display:block;height:100%;background:#6C8CFF}
.crit p{margin:0;color:#9aa4d0;font-size:.85rem}
</style>""", unsafe_allow_html=True)


def secret(name):
    try:
        return st.secrets.get(name) or os.getenv(name)
    except Exception:
        return os.getenv(name)


@st.cache_data(ttl=60)
def load():
    url = secret("DATA_URL")
    if url:
        headers = {}
        if secret("GITHUB_TOKEN"):
            headers = {"Authorization": f"Bearer {secret('GITHUB_TOKEN')}", "Accept": "application/vnd.github.raw"}
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json()
    if LOCAL.exists():
        return json.loads(LOCAL.read_text(encoding="utf-8"))
    return None


def esc(s):
    return (str(s or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


D = load()
if not D or not D.get("participants"):
    st.title("📊 Project Evaluation")
    st.info("No scores yet. They appear here once a participant uploads to the submissions repo and the evaluator workflow finishes.")
    st.stop()

P = D["participants"]
MS = [str(m) for m in D.get("milestones", [1, 2, 3, 4])]

head_l, head_r = st.columns([4, 1])
head_l.title(f"📊 {D.get('cohort', 'Project Evaluation')}")
head_l.caption(f"As of {D.get('asOf', '')[:16].replace('T', ' ')} UTC · each submission is scored once · AI-generated, subject to instructor review")
if head_r.button("🔄 Refresh", width="stretch"):
    load.clear()
    st.rerun()

subs = [s for p in P for s in p["milestones"].values()]
avg = sum(s["pct"] for s in subs) / len(subs) if subs else None
kp = [(len(P), "Participants"), (len(subs), "Submissions scored"), (f"{avg:.0f}%" if avg is not None else "-", "Average score"),
      (sum(p["band"] == "Distinction" for p in P), "Distinction"), (sum(p["band"] == "Below 50%" for p in P), "Below 50%"),
      (len(D.get("errors", [])), "Could not evaluate")]
for col, (v, label) in zip(st.columns(6), kp):
    col.markdown(f'<div class="kpi"><b>{v}</b><span>{label}</span></div>', unsafe_allow_html=True)
st.write("")

with st.sidebar:
    st.header("Filters")
    projects = sorted({x for p in P for x in p["projects"]})
    sel_proj = st.multiselect("Project", projects, default=projects)
    sel_band = st.multiselect("Band", BANDS, default=BANDS)
    q = st.text_input("Search participant")

view = [p for p in P if (not p["projects"] or set(p["projects"]) & set(sel_proj)) and p["band"] in sel_band
        and q.lower() in (p["name"] + " " + p.get("submittedBy", "")).lower()]

tab_board, tab_fb, tab_charts = st.tabs(["Leaderboard", "Participant feedback", "Charts"])

with tab_board:
    rows = []
    for p in view:
        row = {"Participant": p["name"], "GitHub": p.get("submittedBy", ""), "Project": ", ".join(x.replace("_", " ") for x in p["projects"])}
        for m in MS:
            row[f"M{m}"] = p["milestones"][m]["pct"] if m in p["milestones"] else None
        row.update({"Average": p["avg"], "Band": p["band"]})
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        st.info("No participants match the filters.")
    else:
        df = df.sort_values("Average", ascending=False)
        cfg = {f"M{m}": st.column_config.ProgressColumn(f"M{m}", min_value=0, max_value=100, format="%.0f%%") for m in MS}
        cfg["Average"] = st.column_config.NumberColumn("Average", format="%.1f%%")
        st.dataframe(df, hide_index=True, width="stretch", column_config=cfg)
        st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "evaluation_scores.csv", "text/csv")
    if D.get("errors"):
        st.warning("Some submissions could not be evaluated:")
        st.dataframe(pd.DataFrame(D["errors"]), hide_index=True, width="stretch")

with tab_fb:
    if not view:
        st.info("No participants match the filters.")
    else:
        names = {p["id"]: p for p in sorted(view, key=lambda p: p["name"].lower())}
        pid = st.selectbox("Participant", list(names), format_func=lambda i: names[i]["name"])
        p = names[pid]
        have = [m for m in MS if m in p["milestones"]]
        m = st.radio("Milestone", have, index=len(have) - 1, horizontal=True, format_func=lambda x: f"Milestone {x}")
        s = p["milestones"][m]
        a, b = st.columns([3, 1])
        a.subheader(p["name"])
        a.caption(f"{s['project'].replace('_', ' ')} · `{s['file']}`")
        b.metric("Score", f"{s['total']} / {s['max']}", f"{s['pct']:.0f}%", delta_color="off")
        for name, got, mx, fb in s["criteria"]:
            w = 100 * got / mx if mx else 0
            st.markdown(f'<div class="crit"><div class="top"><span>{esc(name)}</span><span>{got} / {mx}</span></div>'
                        f'<div class="tr"><i style="width:{w:.0f}%"></i></div><p>{esc(fb)}</p></div>', unsafe_allow_html=True)
        l, r = st.columns(2)
        l.markdown("**Strengths**\n" + "\n".join(f"- {x}" for x in s["strengths"]))
        r.markdown("**Areas for improvement**\n" + "\n".join(f"- {x}" for x in s["improvements"]))
        st.markdown(f"**Overall:** {s['overall']}")

with tab_charts:
    if view:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Average score by milestone (%)**")
            ms_avg = {f"M{m}": [p["milestones"][m]["pct"] for p in view if m in p["milestones"]] for m in MS}
            st.bar_chart(pd.Series({k: sum(v) / len(v) for k, v in ms_avg.items() if v}, name="Average %"))
        with c2:
            st.markdown("**Participants per band**")
            st.bar_chart(pd.Series({b: sum(p["band"] == b for p in view) for b in BANDS}, name="Participants"))
        st.markdown("**Average by rubric criterion**")
        pick = st.selectbox("Milestone", [m for m in MS if any(m in p["milestones"] for p in view)],
                            format_func=lambda x: f"Milestone {x}")
        crit = {}
        for p in view:
            if pick in p["milestones"]:
                for name, got, mx, _ in p["milestones"][pick]["criteria"]:
                    crit.setdefault(name, []).append(100 * got / mx if mx else 0)
        st.bar_chart(pd.Series({k: sum(v) / len(v) for k, v in crit.items()}, name="Average %"), horizontal=True)
