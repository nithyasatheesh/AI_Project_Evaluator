# Participant_M1_04 — Milestone 1

**Project:** Retail_Customer_Purchase  
**Submission:** `Submission-Milestone1/Participant_M1_04_retail_purchase_medium.ipynb`  
**Evaluated:** 2026-10-27T11:44:04+00:00  
**Score:** **85 / 100**

| Criterion | Marks | Feedback |
|---|---:|---|
| Data Understanding & Quality Checks | 18 / 20 | Good inspection of schemas, data types, missingness, and duplicates with a validated join. Could improve by explicitly reporting uniqueness of keys in each dataset, detailed join cardinality counts, and more thorough missingness patterns. |
| Exploratory Data Analysis (EDA) | 16 / 20 | Solid basic EDA with relevant plots and group summaries. Interpretation is minimal and could be enhanced by discussing outliers, distribution skewness, or notable patterns in customer/product groups. |
| Data Cleaning & Feature Engineering | 17 / 20 | Appropriate missing value treatment and encoding with leakage prevention. No explicit feature engineering beyond encoding is shown. Justification for imputation strategies is implicit but could be more explicit. No discussion on handling outliers or feature creation. |
| Linear Model Building | 19 / 20 | Well-structured baseline model with proper data splitting and preprocessing. Could improve by documenting assumptions about linearity or feature distributions explicitly. |
| Evaluation & Findings | 15 / 20 | Metrics are correctly reported on holdout data with caution against unsupported claims. Interpretation of results and business insights is limited and should be expanded. Limitations are acknowledged but not deeply discussed. |

## Strengths

- Clear and reproducible data loading, joining, and validation steps.
- Proper train/test split with preprocessing fit only on training data to prevent leakage.
- Baseline linear regression model built with standard metrics reported.
- Basic EDA with relevant plots and group summaries.
- Exclusion of identifiers from features to avoid leakage.

## Areas for improvement

- More detailed data quality checks including key uniqueness and join cardinality statistics.
- Deeper EDA interpretation including outlier analysis and pattern insights.
- Explicit justification for cleaning choices and more feature engineering.
- Expanded interpretation of evaluation metrics with business context.
- More thorough discussion of limitations and potential biases.

## Overall feedback

The submission meets the core requirements of Milestone 1 by loading and joining datasets with validation, performing basic EDA, cleaning data with justified preprocessing, building a reproducible linear regression baseline, and reporting standard evaluation metrics on holdout data. It demonstrates good practices such as leakage prevention and cautious interpretation. However, it lacks depth in data quality analysis, EDA interpretation, feature engineering, and evaluation discussion. Strengthening these areas would improve the rigor and business relevance of the analysis. Human review is recommended to verify dataset handling and metric correctness.

_AI-generated evaluation; subject to human review._
