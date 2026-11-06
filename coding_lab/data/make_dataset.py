"""Generate the synthetic Loan Default dataset used by the coding lab.

Realistic structure with deliberate data-quality issues for participants to find:
missing values, exact duplicate rows, inconsistent category labels, impossible values
and outliers. Default risk depends on credit score, debt-to-income, interest rate,
employment and loan-to-income, so a logistic-regression baseline reaches ROC-AUC ~0.75.

Run:  python coding_lab/data/make_dataset.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2026
N = 5000
OUT = Path(__file__).with_name("loan_applications.csv")


def main():
    rng = np.random.default_rng(SEED)
    age = rng.integers(21, 66, N)
    gender = rng.choice(["Male", "Female"], N, p=[0.62, 0.38])
    employment = rng.choice(["Salaried", "Self-Employed", "Business Owner", "Unemployed"], N, p=[0.58, 0.22, 0.15, 0.05])
    base_income = {"Salaried": 780000, "Self-Employed": 650000, "Business Owner": 1100000, "Unemployed": 180000}
    income = np.array([rng.lognormal(np.log(base_income[e]), 0.45) for e in employment]).round(-3)
    credit_hist = np.clip((age - 21) * rng.uniform(0.3, 0.9, N) + rng.normal(0, 1.5, N), 0, None).round(1)
    credit_score = np.clip(rng.normal(690, 70, N) + credit_hist * 2.2, 300, 900).round()
    existing_loans = rng.poisson(1.1, N)
    purpose = rng.choice(["Home", "Personal", "Education", "Vehicle", "Business", "Medical"], N,
                         p=[0.24, 0.30, 0.10, 0.18, 0.12, 0.06])
    loan_amount = (income * rng.uniform(0.2, 1.6, N) * np.where(purpose == "Home", 2.5, 1.0)).round(-3)
    term = rng.choice([12, 24, 36, 48, 60, 120, 180, 240], N, p=[.08, .14, .22, .14, .2, .08, .08, .06])
    interest = np.clip(18.5 - (credit_score - 600) * 0.025 + rng.normal(0, 1.4, N), 7.5, 24).round(2)
    dti = np.clip(existing_loans * 0.07 + (loan_amount / np.maximum(income, 1)) * 0.12 + rng.normal(0.18, 0.08, N), 0.02, 0.95).round(3)
    home = rng.choice(["Own", "Rent", "Mortgage"], N, p=[0.3, 0.45, 0.25])
    region = rng.choice(["North", "South", "East", "West", "Central"], N, p=[.22, .26, .17, .23, .12])
    dates = pd.Timestamp("2022-01-01") + pd.to_timedelta(rng.integers(0, 3 * 365, N), unit="D")

    z = (-2.05 - 0.012 * (credit_score - 690) + 3.1 * (dti - 0.35) + 0.09 * (interest - 13)
         + np.select([employment == "Unemployed", employment == "Self-Employed"], [1.2, 0.35], 0)
         + 0.25 * np.log1p(loan_amount / np.maximum(income, 1)) - 0.02 * credit_hist
         + 0.15 * existing_loans + rng.normal(0, 0.35, N))
    default = (rng.random(N) < 1 / (1 + np.exp(-z))).astype(int)

    df = pd.DataFrame({
        "loan_id": [f"LN{100000 + i}" for i in range(N)],
        "application_date": dates.strftime("%Y-%m-%d"),
        "applicant_age": age,
        "gender": gender,
        "employment_type": employment,
        "annual_income": income,
        "credit_score": credit_score,
        "credit_history_years": credit_hist,
        "existing_loans": existing_loans,
        "debt_to_income": dti,
        "loan_purpose": purpose,
        "loan_amount": loan_amount,
        "loan_term_months": term,
        "interest_rate": interest,
        "home_ownership": home,
        "region": region,
        "default_flag": default,
    })

    # ---- deliberate data-quality issues ----
    def pick(frac):
        return rng.choice(N, int(N * frac), replace=False)
    df.loc[pick(0.041), "annual_income"] = np.nan
    df.loc[pick(0.033), "credit_score"] = np.nan
    df.loc[pick(0.018), "employment_type"] = np.nan
    df.loc[pick(0.012), "debt_to_income"] = np.nan
    idx = pick(0.03)                                                   # inconsistent labels
    df.loc[idx, "employment_type"] = df.loc[idx, "employment_type"].map(
        {"Salaried": "salaried", "Self-Employed": "Self Employed", "Business Owner": "business owner", "Unemployed": "UNEMPLOYED"})
    df.loc[pick(0.01), "gender"] = "F"
    df.loc[pick(0.004), "applicant_age"] = rng.choice([0, 150, 999], int(N * 0.004))   # impossible ages
    df.loc[pick(0.003), "annual_income"] = rng.choice([1.2e8, 9.9e7], int(N * 0.003))  # extreme outliers
    df.loc[pick(0.002), "loan_amount"] = -df["loan_amount"].abs().median()            # negative amounts
    dups = df.sample(42, random_state=SEED)
    df = pd.concat([df, dups]).sample(frac=1, random_state=SEED).reset_index(drop=True)

    df.to_csv(OUT, index=False)
    print(f"{OUT.name}: {len(df)} rows, default rate {df.default_flag.mean():.1%}")


if __name__ == "__main__":
    main()
