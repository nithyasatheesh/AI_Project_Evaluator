# AI Project Evaluator

AI-powered, rubric-based evaluation of participant project submissions across four milestones, for three project domains:
- **Loan Default Prediction and Risk Intelligence** (`loan_default`)
- **Retail Customer Purchase Behaviour Prediction** (`retail_purchase`)
- **Liver Disease Prediction & AI-Powered Decision Support** (`healthcare`)

## Two repositories

| Repo | Who can see it | What lives there |
|---|---|---|
| **This evaluator repo** (private) | Instructors only | Rubrics, problem statements, evaluator code, OpenAI key, full results + Excel reports |
| **Shared submissions repo** | Participants (write access) | `Submission-Milestone1..4/` folders with notebooks, plus published `evaluation-results/` |

Participants never see the rubric files, the API key or this workflow.

## How it works

1. A participant uploads `Submission-MilestoneN/<Their_Name>_<project>.ipynb` to the **submissions repo**
   (e.g. `Submission-Milestone1/Priya_Venkatesh_loan_default.ipynb`).
2. Every 15 minutes (07:30–23:15 IST, Mon–Sat) this repo's workflow checks the submissions repo. If nothing changed, it stops in seconds.
3. Each **new** file is scored once against its milestone rubric. The result is saved in `evaluation-results/results.json`, so it is never sent to the AI again.
4. Results are published:
   - a **comment on the participant's upload commit** with their score and a link to their feedback,
   - `evaluation-results/SCORES.md`, `index.html` (HTML dashboard), `data.json` and `feedback/` in the **submissions repo**,
   - full results and Excel reports (one per milestone) in **this repo** and as a run artifact.

To evaluate immediately instead of waiting: **Actions → Evaluate Participant Submissions → Run workflow**.

## One-time setup

1. **Create the submissions repo** (e.g. `ai-project-submissions`) and add participants as collaborators with write access. Upload `submissions_repo_template/README.md` to it as its README.
2. In `evaluator/config.json` set:
   - `submissions_repo`: `"owner/repo-name"` of that repo
   - `cohort_name`: shown on the dashboards
3. **Create a token** for the submissions repo: GitHub → Settings → Developer settings → Fine-grained tokens → Generate.
   Repository access: *only* the submissions repo. Permissions: **Contents: Read and write**.
4. In **this** repo: Settings → Secrets and variables → Actions → add
   - `OPENAI_API_KEY`
   - `SUBMISSIONS_TOKEN` (the token from step 3)
5. In **this** repo: Settings → Actions → General → Workflow permissions → **Read and write permissions**.

## HTML dashboard

`evaluation-results/index.html` is regenerated on every run. It works three ways:
- open it from a downloaded copy (data is embedded),
- enable **GitHub Pages** on the submissions repo (Settings → Pages → Deploy from branch → `main` / root) and open `https://<owner>.github.io/<submissions-repo>/evaluation-results/` — it reads `data.json` live,
- view `SCORES.md` directly in GitHub.

## Streamlit app

```
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```
Reads the same `data.json`: leaderboard with milestone columns, participant feedback with criterion bars, charts.
To host on Streamlit Community Cloud, deploy `dashboard/app.py` and set the secret
`DATA_URL = "https://raw.githubusercontent.com/<owner>/<submissions-repo>/main/evaluation-results/data.json"`
(add `GITHUB_TOKEN` too if the submissions repo is private).

## Instructor controls (Run workflow)

- **force_path**: re-score one submission, e.g. `Submission-Milestone2/Priya_Venkatesh_loan_default.ipynb`.
- **rebuild_only**: regenerate dashboards and reports from saved results without calling the AI.
- `resubmission_policy` in `config.json`: `"lock"` (default; the first score is final) or `"reevaluate_on_change"`.
- `publish_results_to_submissions_repo`: set `false` to keep all scores private to this repo.

> **Privacy:** with publishing on, every participant can see everyone's scores and feedback in the submissions repo. Set `publish_results_to_submissions_repo` to `false` if that isn't wanted.

The evaluator reads submissions as evidence and never executes participant code. AI-generated scores require human review before being treated as final grades.
