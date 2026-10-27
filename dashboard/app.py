"""AI Evaluator — results dashboard.

Reads the scores the GitHub workflow commits to evaluation-results/results.json.
Nothing here calls the AI model; it only displays saved results.

Run locally (from the repo root):
    pip install -r dashboard/requirements.txt
    streamlit run dashboard/app.py

Deploy on Streamlit Community Cloud: point it at this repo, main file dashboard/app.py.
It reads the local results.json in the deployed checkout. To always show the latest
scores without redeploying, set these in the app's Secrets:
    RESULTS_URL  = "https://raw.githubusercontent.com/<owner>/<repo>/main/evaluation-results/results.json"
    GITHUB_TOKEN = "<fine-grained token with read access>"   # only needed for a private repo
"""
import json
import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

LOCAL_RESULTS = Path(__file__).resolve().parent.parent / "evaluation-results" / "results.json"

st.set_page_config(page_title="AI Evaluator Results", page_icon="📊", layout="wide")


def _secret(name):
    try:
        return st.secrets.get(name) or os.getenv(name)
    except Exception:
        return os.getenv(name)


@st.cache_data(ttl=60)
def load_results():
    url = _secret("RESULTS_URL")
    if url:
        headers = {}
        token = _secret("GITHUB_TOKEN")
        if token:
            headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.raw"}
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json(), url
    if LOCAL_RESULTS.exists():
        return json.loads(LOCAL_RESULTS.read_text(encoding="utf-8")), str(LOCAL_RESULTS)
    return {"submissions": {}}, None


def to_frame(ledger):
    rows = []
    for key, e in ledger.get("submissions", {}).items():
        r = e.get("result") or {}
        rows.append({
            "Participant": e.get("participant", Path(key).stem),
            "Milestone": (r.get("milestone_id") or "").replace("_", " "),
            "Project": r.get("project_id", ""),
            "Score": r.get("total_marks"),
            "Max": r.get("maximum_marks"),
            "Percent": round(100 * r["total_marks"] / r["maximum_marks"], 1) if r.get("maximum_marks") else None,
            "Status": e.get("status", ""),
            "Submitted by": e.get("submitted_by", ""),
            "Evaluated at": (e.get("evaluated_at") or "")[:16].replace("T", " "),
            "Submission": key,
        })
    return pd.DataFrame(rows)


ledger, source = load_results()
df = to_frame(ledger)

st.title("📊 AI Evaluator — Submission Scores")
st.caption(
    f"Each submission is evaluated once and its score is fixed. "
    f"Last updated: {ledger.get('updated_at', '—')}"
    + (f" · Source: `{source}`" if source else "")
)

if df.empty:
    st.info("No evaluations yet. Scores appear here once a participant uploads a submission and the GitHub workflow finishes.")
    st.stop()

if st.button("🔄 Refresh"):
    load_results.clear()
    st.rerun()

evaluated = df[df["Status"] == "evaluated"]
errors = df[df["Status"] == "error"]

with st.sidebar:
    st.header("Filters")
    milestones = sorted(evaluated["Milestone"].dropna().unique())
    projects = sorted(evaluated["Project"].dropna().unique())
    sel_ms = st.multiselect("Milestone", milestones, default=milestones)
    sel_pr = st.multiselect("Project", projects, default=projects)
    search = st.text_input("Search participant")

view = evaluated[evaluated["Milestone"].isin(sel_ms) & evaluated["Project"].isin(sel_pr)]
if search:
    view = view[view["Participant"].str.contains(search, case=False, na=False)]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Submissions evaluated", len(view))
c2.metric("Average score", f"{view['Percent'].mean():.1f}%" if len(view) else "—")
c3.metric("Highest", f"{view['Percent'].max():.0f}%" if len(view) else "—")
c4.metric("Needs attention", len(errors))

tab_board, tab_detail, tab_charts = st.tabs(["Leaderboard", "Participant feedback", "Charts"])

with tab_board:
    st.dataframe(
        view.sort_values(["Milestone", "Percent"], ascending=[True, False])[
            ["Participant", "Milestone", "Project", "Score", "Max", "Percent", "Submitted by", "Evaluated at"]],
        hide_index=True, width="stretch",
        column_config={"Percent": st.column_config.ProgressColumn("Percent", min_value=0, max_value=100, format="%.0f%%")},
    )
    st.download_button("Download CSV", view.to_csv(index=False).encode("utf-8"),
                       file_name="evaluation_scores.csv", mime="text/csv")
    if len(errors):
        st.warning("Some submissions could not be evaluated:")
        st.dataframe(errors[["Submission", "Submitted by"]], hide_index=True, width="stretch")

with tab_detail:
    options = view.sort_values(["Milestone", "Participant"])["Submission"].tolist()
    if not options:
        st.info("No submissions match the filters.")
    else:
        label = {s: f"{r.Participant} · {r.Milestone} · {r.Project}" for s, r in view.set_index("Submission").iterrows()}
        choice = st.selectbox("Submission", options, format_func=lambda s: label.get(s, s))
        entry = ledger["submissions"][choice]
        r = entry["result"]
        st.subheader(f"{entry['participant']} — {r['total_marks']} / {r['maximum_marks']}")
        st.caption(f"{r.get('project_id')} · {r.get('milestone_id', '').replace('_', ' ')} · `{choice}`")
        crit = pd.DataFrame([{"Criterion": c["name"], "Marks": c["marks_awarded"], "Max": c["max_marks"],
                              "Feedback": c.get("feedback", ""), "Evidence": c.get("evidence", "")}
                             for c in r.get("criteria", [])])
        st.dataframe(crit, hide_index=True, width="stretch",
                     column_config={"Feedback": st.column_config.TextColumn(width="large"),
                                    "Evidence": st.column_config.TextColumn(width="medium")})
        left, right = st.columns(2)
        with left:
            st.markdown("**Strengths**")
            for s in r.get("strengths") or []:
                st.markdown(f"- {s}")
        with right:
            st.markdown("**Areas for improvement**")
            for s in r.get("areas_for_improvement") or []:
                st.markdown(f"- {s}")
        st.markdown("**Overall feedback**")
        st.write(r.get("overall_feedback", ""))
        st.caption("AI-generated evaluation; subject to instructor review.")

with tab_charts:
    if len(view):
        st.markdown("**Average score by milestone and project (%)**")
        pivot = view.pivot_table(index="Milestone", columns="Project", values="Percent", aggfunc="mean").round(1)
        st.bar_chart(pivot)
        st.markdown("**Average marks per criterion**")
        crit_rows = []
        for key in view["Submission"]:
            res = ledger["submissions"][key]["result"]
            for c in res.get("criteria", []):
                crit_rows.append({"Milestone": res.get("milestone_id", "").replace("_", " "), "Criterion": c["name"],
                                  "Percent": 100 * c["marks_awarded"] / c["max_marks"] if c["max_marks"] else 0})
        cdf = pd.DataFrame(crit_rows)
        ms_pick = st.selectbox("Milestone", sorted(cdf["Milestone"].unique()))
        st.bar_chart(cdf[cdf["Milestone"] == ms_pick].groupby("Criterion")["Percent"].mean().round(1),
                     horizontal=True)
