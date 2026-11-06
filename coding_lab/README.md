# AI Coding Lab

A browser-based coding platform: participants log in with their own ID, write Python in
Jupyter-style cells, and get each task scored **instantly** by AI against the milestone rubric.
First lab: **Loan Default Prediction · Milestone 1** (data understanding, EDA, cleaning, logistic
regression baseline, evaluation), on a realistic sample dataset of 5,042 loan applications.

**Participant tabs:** Problem statement · Instructions · Rubric · Notebook · Submission · Evaluation results
**Trainer view:** every participant's progress and task scores, their notebooks, a CSV export, PDF
reports and an "unlock task" action.

## How it works
1. The participant opens the app link and logs in with their **login ID and password**.
2. In **Notebook**, they work through 5 tasks (20 marks each), running cells with **Run** or **Ctrl + Enter**.
   A live checklist shows what the evaluator looks for.
3. When a task is done they click **Evaluate task**. In about 5–10 seconds the AI scores it against the rubric
   criterion and gives feedback. Each task can be evaluated **once** and is then locked.
4. After all 5 tasks they **submit**, get overall feedback, and download their notebook (.ipynb) and
   PDF result report.

## Safety
* Participants' code runs in a separate Python process that has **no access** to the OpenAI key, the
  GitHub token or the login data. It also cannot read the app's files, reach the internet, run system
  commands or write outside a temporary folder.
* A cell is stopped after 60 seconds.
* Passwords are stored only as salted hashes (PBKDF2) in Streamlit secrets.
* After 5 wrong passwords, a login ID is paused for 2 minutes.
* AI scores are validated (0 to the maximum marks) and labelled "subject to trainer review".

This is a practical sandbox for a trusted training cohort, not a hardened system for anonymous users.

## Set-up (about 30 minutes, once)
1. **Create logins** on your computer (Python 3.10+):
   ```
   python coding_lab/make_logins.py --names participants.csv --prefix LD --trainers "Nith"
   ```
   `participants.csv` needs a `name` column. Or use `--count 50` for numbered participants.
   This creates `coding_lab/logins/participant_logins.csv` (give each person **only their own row**) and
   `users_for_secrets.toml`. Never commit these files.
2. **Create a private GitHub repository for saved work**, e.g. `coding-lab-data`, with a README so it isn't empty.
   Create a fine-grained token: that repository only, **Contents: Read and write**.
3. **Deploy on Streamlit Community Cloud** (share.streamlit.io): New app → this repository →
   main file `coding_lab/app.py` → Advanced settings → Python 3.12.
4. In the app's **Settings → Secrets**, paste `coding_lab/secrets.toml.example`. Fill in the OpenAI key,
   the `[storage]` repository and token, then paste the contents of `users_for_secrets.toml` below it.
5. Log in with your trainer ID and open **⚙️ Setup check**. All lines should be ✅.

## Cost and capacity
* OpenAI (gpt-4.1-mini): about 5–6 AI calls per participant (one per task plus overall feedback), roughly
  **Rs 0.5–1 per participant**.
* Streamlit Community Cloud is free but has limited memory (about 1–3 GB). Each active participant uses
  roughly 30–60 MB, so it suits classes of up to about 25–40 people working at the same time. For a larger
  class, run the same app on a bigger server (any Python host or VM).
* GitHub saves are combined into one commit every ~90 seconds (~10 seconds after an evaluation), which
  stays within GitHub's rate limits for a full class.

## Changing the lab
Everything participants see is in `tasks.py`: problem statement, data dictionary, instructions, tasks,
starter code and checklist rules. For another project or milestone, copy it with new content and data.
Settings such as evaluations per task, cell time limit and model are under `[lab]` in secrets.
