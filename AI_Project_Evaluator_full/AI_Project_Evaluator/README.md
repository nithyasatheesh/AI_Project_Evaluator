# AI_Evaluator

AI-powered rubric-based evaluation of project submissions across four milestones.

## Supported project domains
- **Loan Default Prediction and Risk Intelligence**
- **Retail Customer Purchase Behaviour Prediction**
- **Liver Disease Prediction & AI-Powered Decision Support**

Retail Sales Forecasting has been removed from this repository's supported projects.

## How automatic evaluation works
1. A participant uploads a notebook into `Submission-MilestoneN/` (filename must contain `loan_default`, `retail_purchase` or `healthcare`).
2. The **Evaluate Participant Submissions** workflow starts automatically on that push.
3. It evaluates **only submissions that have not been scored before**. Every result is saved in `evaluation-results/results.json` and committed back to the repo, so each submission is sent to the AI model exactly once and its score never changes on later runs.
4. The score is shown in GitHub in three places:
   - a **comment on the participant's commit** with the score and a link to their feedback,
   - the workflow run's **summary page** (Actions tab),
   - `evaluation-results/SCORES.md` — a leaderboard per milestone, with one feedback page per submission in `evaluation-results/feedback/`.
5. Consolidated Excel reports (one per milestone) are kept up to date in `evaluation-results/reports/` and also uploaded as a run artifact.

### Resubmissions
Set `"resubmission_policy"` in `evaluator/config.json`:
- `"lock"` (default) — the first score is final, even if the participant overwrites the same file.
- `"reevaluate_on_change"` — re-score only when the file content changes (the earlier score is kept in `previous_scores`).

Failed evaluations (e.g. API error) are retried automatically on the next run, up to 3 times.

### Instructor controls (Actions → Evaluate Participant Submissions → Run workflow)
- **force_path** — re-evaluate one specific submission.
- **rebuild_only** — regenerate SCORES.md, feedback pages and Excel files from saved results without calling the AI.

## Results dashboard (Streamlit)
```
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
```
Shows a leaderboard with filters, per-participant criterion breakdown and feedback, and charts. To host it, deploy `dashboard/app.py` on Streamlit Community Cloud and (optionally) set the secret `RESULTS_URL` to the raw URL of `evaluation-results/results.json` so it always shows the latest scores; add `GITHUB_TOKEN` too if the repo is private.

## Setup
1. Store `OPENAI_API_KEY` as a GitHub Actions repository secret.
2. Settings → Actions → General → Workflow permissions: choose **Read and write permissions** (needed to commit results and post comments). If `main` is a protected branch, allow GitHub Actions to push to it.
3. Participants need write access to upload into the submission folders.

> **Privacy:** anyone who can read this repository can see `evaluation-results/` (all participants' scores and feedback). Keep the repository private, or remove the commit/SCORES steps if participants should only see their own results.

The evaluator reads submissions as evidence; it does not execute participant notebooks or source code. AI-generated scores require human review before being treated as final grades.
