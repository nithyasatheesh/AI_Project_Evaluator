# Participant_M2_04 — Milestone 2

**Project:** Healthcare_Liver_Disease  
**Submission:** `Submission-Milestone2/Participant_M2_04_healthcare_medium.ipynb`  
**Evaluated:** 2026-10-27T11:44:38+00:00  
**Score:** **81 / 100**

| Criterion | Marks | Feedback |
|---|---:|---|
| ML Model Development | 23 / 25 | Models are appropriate and preprocessing is consistent with verified target. Could improve by showing more details on feature engineering or handling of outliers if any. |
| Hyperparameter Tuning & Validation | 15 / 20 | Validation strategy is appropriate and stratified. However, hyperparameter tuning is minimal or absent; using GridSearchCV or similar would improve robustness. |
| Model Comparison & Performance Evaluation | 17 / 20 | Good use of class-sensitive metrics and ROC-AUC. More detailed analysis of false negatives and explicit discussion of trade-offs would strengthen evaluation. |
| Risk Factor / Feature Importance Analysis | 8 / 15 | Feature importance analysis is missing or minimal. Including feature importance plots or explanations with caution about causality would improve this criterion. |
| Risk Scoring & Patient Grouping | 18 / 20 | Risk scoring is responsibly presented with appropriate disclaimers. Could improve by showing calibration plots or quantitative calibration assessment. |

## Strengths

- Appropriate choice of ML models with consistent preprocessing pipelines.
- Use of stratified validation to avoid data leakage.
- Clear disclaimers on risk scoring and non-clinical interpretation.

## Areas for improvement

- Include explicit hyperparameter tuning with grid search or randomized search.
- Provide detailed false negative analysis and confusion matrices.
- Add feature importance analysis with valid interpretation.
- Demonstrate calibration assessment quantitatively.

## Overall feedback

The submission demonstrates solid implementation of multiple ML classifiers with appropriate preprocessing and stratified validation. Model comparison uses relevant metrics but lacks deeper analysis of false negatives and trade-offs. Risk scoring is responsibly handled with disclaimers. However, hyperparameter tuning is minimal, feature importance analysis is missing, and calibration assessment is not shown. Addressing these gaps would strengthen the educational value and completeness of the milestone.

_AI-generated evaluation; subject to human review._
