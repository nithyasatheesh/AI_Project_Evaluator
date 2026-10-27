# Participant_M2_01 — Milestone 2

**Project:** Healthcare_Liver_Disease  
**Submission:** `Submission-Milestone2/Participant_M2_01_healthcare_strong.ipynb`  
**Evaluated:** 2026-10-27T11:44:21+00:00  
**Score:** **78 / 100**

| Criterion | Marks | Feedback |
|---|---:|---|
| ML Model Development | 23 / 25 | Strong implementation of multiple classifiers with appropriate preprocessing and target verification. Minor deduction as no explicit mention of leakage checks or feature engineering beyond basic preprocessing. |
| Hyperparameter Tuning & Validation | 15 / 20 | Validation strategy is appropriate and stratified, but hyperparameter tuning is not demonstrated with GridSearchCV or similar. Including tuning would improve robustness. |
| Model Comparison & Performance Evaluation | 18 / 20 | Good use of class-sensitive metrics and comparison. Could improve by including confusion matrices and more detailed discussion of trade-offs, especially false negatives. |
| Risk Factor / Feature Importance Analysis | 5 / 15 | Feature importance analysis is missing. Including SHAP values, permutation importance, or model feature importance with cautious interpretation would meet this criterion. |
| Risk Scoring & Patient Grouping | 17 / 20 | Good responsible labeling of risk bands and disclaimers. Would benefit from explicit calibration assessment (e.g., calibration curve or Brier score) to strengthen this section. |

## Strengths

- Implemented multiple ML classifiers with consistent preprocessing and verified target mapping.
- Used stratified cross-validation and train/test split appropriately.
- Compared models with ROC-AUC, recall, and F1-score, highlighting false negatives importance.
- Created illustrative risk scores with clear disclaimers about clinical validity.

## Areas for improvement

- Demonstrate explicit hyperparameter tuning using GridSearchCV or similar methods.
- Include feature importance analysis with valid interpretation methods.
- Provide confusion matrices and precision metrics for more comprehensive model evaluation.
- Assess and present calibration metrics or plots for risk scoring.

## Overall feedback

The submission shows a solid implementation of multiple machine learning models with appropriate preprocessing and validation strategy. Model comparison uses relevant metrics with attention to false negatives. The illustrative risk scoring is responsibly presented with disclaimers. However, the lack of explicit hyperparameter tuning, feature importance analysis, and calibration assessment limits the completeness of the milestone requirements. Including these elements would strengthen the educational value and rigor of the work.

_AI-generated evaluation; subject to human review._
