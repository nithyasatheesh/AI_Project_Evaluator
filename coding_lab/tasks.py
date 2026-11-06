"""Lab content: Loan Default Prediction, Milestone 1 (Python + EDA + baseline model).

Everything a participant sees comes from this file, so a new project or milestone is a
copy of it with new text, tasks, starter code and checks.
Each task maps to one criterion of rubrics/Loan_Default/milestone_1_rubric.json.
"""
import re

LAB_TITLE = "Loan Default Prediction"
MILESTONE = "Milestone 1 · Data understanding, EDA and baseline model"
PROJECT_ID = "Loan_Default"
DATA_FILE = "loan_applications.csv"

PROBLEM_STATEMENT = """
### Business context
A retail lender wants to understand **which loan applications are likely to default** so that credit
officers can focus their reviews. You have been given a historical extract of **5,042 loan applications**
with each applicant's profile, the loan terms and whether the loan later **defaulted**.

### Your goal in this milestone
1. Understand the data and its quality problems.
2. Explore patterns that are associated with default.
3. Clean the data and engineer useful features, **without leaking information from the test set**.
4. Build a **logistic-regression baseline** that predicts `default_flag`.
5. Evaluate it with a confusion matrix, precision, recall, F1 and ROC-AUC, and explain what the results mean
   for the lender, including the limitations.

### The data
The file `loan_applications.csv` is already in your working folder:
```python
import pandas as pd
df = pd.read_csv("loan_applications.csv")
```
The extract comes straight from the source system, so **expect data-quality problems**. Finding and
handling them is part of the task.

### Responsible use
The model is a decision-**support** tool. Do not treat correlation as causation, do not invent column
meanings, and remember that a model must never be the only basis for a credit decision.
"""

DATA_DICTIONARY = [
    ("loan_id", "Unique application identifier. Not a feature: exclude it from models."),
    ("application_date", "Date the application was submitted (YYYY-MM-DD)."),
    ("applicant_age", "Age of the applicant in years."),
    ("gender", "Applicant gender as recorded."),
    ("employment_type", "Salaried, Self-Employed, Business Owner or Unemployed."),
    ("annual_income", "Declared annual income (INR)."),
    ("credit_score", "Bureau credit score (300–900)."),
    ("credit_history_years", "Length of credit history in years."),
    ("existing_loans", "Number of other active loans."),
    ("debt_to_income", "Existing monthly debt ÷ monthly income (0–1)."),
    ("loan_purpose", "Home, Personal, Education, Vehicle, Business or Medical."),
    ("loan_amount", "Loan amount requested (INR)."),
    ("loan_term_months", "Loan tenure in months."),
    ("interest_rate", "Annual interest rate offered (%)."),
    ("home_ownership", "Own, Rent or Mortgage."),
    ("region", "Branch region."),
    ("default_flag", "**Target.** 1 = the loan defaulted, 0 = repaid / performing."),
]

INSTRUCTIONS = """
### How this lab works
- Work through the **5 tasks** in the **Notebook** tab, in order. Each task is worth **20 marks** (100 in total).
- Each task has code cells (like Jupyter). Type your code and press **Run** (or **Ctrl + Enter**).
  Variables carry over between cells and tasks, just like a notebook.
- Add as many **code cells** or **notes cells** as you need. Use notes cells to explain your findings:
  **explanations earn marks**, not just code.
- The **checklist** at the top of each task updates as you work. It shows what the evaluator will look for.

### Evaluation
- When a task is finished, tick **"I've finished this task"** and click **Evaluate task**. Your score and
  feedback appear within seconds in the **Evaluation results** tab.
- **Each task can be evaluated only once**, and its cells are locked afterwards, so finish the task first.
- The AI evaluator scores each task against the **Rubric** using only the evidence in your cells: code,
  outputs and notes. Run your cells before evaluating so the outputs are there.
- When all 5 tasks are evaluated, go to **Submission** and submit your notebook. You can then download your
  notebook and your PDF result report.

### Good to know
- Your work is saved automatically when you run or evaluate a cell, and when you click **Save** in the sidebar.
  You can log out and continue later.
- A cell that runs longer than **60 seconds** is stopped and the kernel restarts. Use **Run all cells** in the
  sidebar to rebuild your variables.
- If your session restarts, your code is kept, but variables are cleared. Use **Run all cells**.
- The lab blocks internet access, system commands and files outside your working folder.
- Scores are AI-generated and subject to trainer review.
"""

TASKS = [
    {
        "id": "t1",
        "title": "Data understanding & quality checks",
        "criterion": "Data Understanding & Quality Checks",
        "marks": 20,
        "guidance": "Assess dataset structure, target variable, data types, missing values, duplicates, "
                    "inconsistent values, and data-quality risks.",
        "brief": [
            "Load `loan_applications.csv` into a DataFrame called `df`.",
            "Inspect the structure: shape, column types and summary statistics.",
            "Examine the target `default_flag`: values and class balance.",
            "Check missing values, duplicate rows, inconsistent category labels and impossible values.",
            "In a notes cell, list the data-quality problems you found and why they matter.",
        ],
        "starter": [
            "import pandas as pd\nimport numpy as np\n\ndf = pd.read_csv(\"loan_applications.csv\")\ndf.head()",
            "# Structure and data types\n",
            "# Target variable and class balance\n",
            "# Missing values, duplicates, inconsistent labels, impossible values\n",
        ],
        "checks": [
            ("Dataset loaded into a DataFrame", {"ns": "dataframe_with_target"}),
            ("Structure inspected (shape / info / dtypes / describe)", {"code": [r"\.(info|dtypes|shape|describe)\b"]}),
            ("Target variable examined", {"code_all": [r"default_flag", r"value_counts|\.mean\(\)|normalize"]}),
            ("Missing values checked", {"code": [r"\.isna\(|\.isnull\(|\.notna\("]}),
            ("Duplicate rows checked", {"code": [r"duplicated\("]}),
            ("Category labels inspected", {"code": [r"\.unique\(|\.value_counts\(|nunique"]}),
            ("Findings explained in notes", {"notes": 80}),
        ],
    },
    {
        "id": "t2",
        "title": "Exploratory data analysis (EDA)",
        "criterion": "Exploratory Data Analysis (EDA)",
        "marks": 20,
        "guidance": "Assess univariate/bivariate analysis, plots, class balance, and explanations of patterns "
                    "relevant to loan default.",
        "brief": [
            "Plot the class balance of `default_flag`.",
            "Explore key numeric variables (e.g. credit score, debt-to-income, interest rate) with plots.",
            "Compare the default rate across categories (e.g. employment type, loan purpose).",
            "Look at relationships between variables (e.g. a correlation matrix).",
            "In a notes cell, explain the 3–5 most important patterns for default, without claiming causation.",
        ],
        "starter": [
            "import matplotlib.pyplot as plt\nimport seaborn as sns\n\n# Class balance\n",
            "# Distributions of key numeric variables vs default\n",
            "# Default rate by category\n",
        ],
        "checks": [
            ("At least 2 plots", {"plots": 2}),
            ("Class balance shown", {"code_all": [r"default_flag", r"countplot|value_counts|\.plot|hist|bar"]}),
            ("Numeric variables explored", {"code": [r"hist|box|kde|violin|scatter|displot"]}),
            ("Default rate compared across a category", {"code": [r"groupby\(.*\)\s*\[?.*default_flag|crosstab|pivot_table|barplot|hue=.?default_flag"]}),
            ("Relationships explored (e.g. correlation)", {"code": [r"\.corr\(|heatmap|pairplot|scatter"]}),
            ("Patterns explained in notes", {"notes": 120}),
        ],
    },
    {
        "id": "t3",
        "title": "Data cleaning & feature engineering",
        "criterion": "Data Cleaning & Feature Engineering",
        "marks": 20,
        "guidance": "Assess missing-value handling, duplicates, encoding, scaling where appropriate, leakage "
                    "prevention, and feature engineering rationale.",
        "brief": [
            "Remove duplicate rows.",
            "Standardise inconsistent category labels (e.g. `salaried` vs `Salaried`, `F` vs `Female`).",
            "Handle impossible values and extreme outliers (ages, negative amounts, extreme incomes).",
            "Decide how to handle missing values. Imputation that learns from data belongs in the model "
            "pipeline (Task 4) to avoid leakage.",
            "Engineer at least one useful feature (e.g. loan-to-income ratio) and exclude `loan_id`.",
            "In a notes cell, justify each decision.",
        ],
        "starter": [
            "# Work on a copy so the raw data stays available\nclean = df.copy()\n",
            "# Fix category labels and invalid values\n",
            "# Feature engineering\n",
        ],
        "checks": [
            ("Duplicates removed", {"code": [r"drop_duplicates"]}),
            ("Category labels standardised", {"code": [r"str\.(lower|title|strip|upper|capitalize)|\.replace\(|\.map\("]}),
            ("Invalid values / outliers handled", {"code": [r"applicant_age|loan_amount\s*[<>]|clip\(|between\(|quantile|annual_income\s*[<>]"]}),
            ("Missing values handled", {"code": [r"fillna|SimpleImputer|dropna|interpolate"]}),
            ("New feature engineered", {"code": [r"\[\s*['\"]\w+['\"]\s*\]\s*=\s*[^=\n]*[/*\-+]|assign\("]}),
            ("Identifier excluded", {"code": [r"loan_id"]}),
            ("Decisions justified in notes", {"notes": 100}),
        ],
    },
    {
        "id": "t4",
        "title": "Baseline logistic regression",
        "criterion": "Linear Model Building",
        "marks": 20,
        "guidance": "Assess baseline classifier, train/test split, preprocessing, target mapping, and assumptions.",
        "brief": [
            "Choose your features and the target `default_flag`.",
            "Split into train and test sets, stratified on the target.",
            "Build a preprocessing + `LogisticRegression` pipeline (impute, scale numeric, one-hot encode "
            "categorical), fitted on the training data only.",
            "Fit the model and show its coefficients or most influential features.",
            "In a notes cell, state your modelling assumptions and how you prevented leakage.",
        ],
        "starter": [
            "from sklearn.model_selection import train_test_split\n"
            "from sklearn.compose import ColumnTransformer\n"
            "from sklearn.pipeline import Pipeline\n"
            "from sklearn.impute import SimpleImputer\n"
            "from sklearn.preprocessing import StandardScaler, OneHotEncoder\n"
            "from sklearn.linear_model import LogisticRegression\n",
            "# Train/test split\n",
            "# Pipeline and fit\n",
        ],
        "checks": [
            ("Train/test split", {"code": [r"train_test_split"]}),
            ("Split stratified on the target", {"code": [r"stratify"]}),
            ("Preprocessing (scaling / encoding)", {"code": [r"StandardScaler|OneHotEncoder|get_dummies|MinMaxScaler"]}),
            ("Pipeline used (leakage-safe)", {"code": [r"Pipeline|ColumnTransformer|make_pipeline"]}),
            ("Logistic regression fitted", {"ns": "fitted_logistic"}),
            ("Assumptions explained in notes", {"notes": 80}),
        ],
    },
    {
        "id": "t5",
        "title": "Evaluation & findings",
        "criterion": "Evaluation & Findings",
        "marks": 20,
        "guidance": "Assess confusion matrix, precision, recall, F1, ROC-AUC where appropriate, interpretation, "
                    "limitations, and actionable findings.",
        "brief": [
            "Predict on the **test set** only.",
            "Show the confusion matrix, precision, recall and F1 (e.g. `classification_report`).",
            "Calculate ROC-AUC and plot the ROC curve.",
            "Explain what the numbers mean for the lender: which error is more costly, a missed defaulter or a rejected good borrower?",
            "In a notes cell, give 3 actionable findings and the main limitations of this baseline.",
        ],
        "starter": [
            "from sklearn.metrics import (confusion_matrix, ConfusionMatrixDisplay, classification_report,\n"
            "                             roc_auc_score, RocCurveDisplay)\n",
            "# Confusion matrix and classification report\n",
            "# ROC-AUC and ROC curve\n",
        ],
        "checks": [
            ("Confusion matrix", {"code": [r"confusion_matrix|ConfusionMatrixDisplay"]}),
            ("Precision, recall and F1", {"code": [r"classification_report|precision_score|recall_score|f1_score"]}),
            ("ROC-AUC", {"code": [r"roc_auc_score|RocCurveDisplay|roc_curve"]}),
            ("Evaluated on the test set", {"code": [r"X_test|Xte|x_test|X_val|test"]}),
            ("Findings & limitations in notes", {"notes": 150}),
        ],
    },
]

TASK_BY_ID = {t["id"]: t for t in TASKS}


def run_checks(task, cells, facts):
    """Return [(label, passed)] for a task, from its cells and the kernel's variable facts."""
    code = "\n".join(c["source"] for c in cells if c["type"] == "code")
    notes = "\n".join(c["source"] for c in cells if c["type"] == "markdown").strip()
    plots = sum(1 for c in cells if c["type"] == "code" for o in c.get("outputs", [])
                if o.get("type") in ("image", "image_saved"))
    results = []
    for label, rule in task["checks"]:
        ok = False
        if "code" in rule:
            ok = any(re.search(p, code, re.I | re.S) for p in rule["code"])
        elif "code_all" in rule:
            ok = all(re.search(p, code, re.I | re.S) for p in rule["code_all"])
        elif "notes" in rule:
            ok = len(re.sub(r"\s+", " ", notes)) >= rule["notes"]
        elif "plots" in rule:
            ok = plots >= rule["plots"]
        elif rule.get("ns") == "dataframe_with_target":
            ok = any(d.get("has_target") and d.get("rows", 0) >= 1000 for d in facts.get("dataframes", []))
        elif rule.get("ns") == "fitted_logistic":
            ok = any("LogisticRegression" in m.get("type", "") for m in facts.get("fitted_models", []))
        results.append((label, ok))
    return results
