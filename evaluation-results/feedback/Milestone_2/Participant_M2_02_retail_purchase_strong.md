# Participant_M2_02 — Milestone 2

**Project:** Retail_Customer_Purchase  
**Submission:** `Submission-Milestone2/Participant_M2_02_retail_purchase_strong.ipynb`  
**Evaluated:** 2026-10-27T11:44:27+00:00  
**Score:** **75 / 100**

| Criterion | Marks | Feedback |
|---|---:|---|
| ML Model Development | 25 / 25 | All required tree-based and boosting regression models were implemented appropriately with consistent preprocessing and reproducible settings. |
| Hyperparameter Tuning & Validation | 10 / 20 | Hyperparameter tuning was not performed using training-only cross-validation or validation splits. Parameters appear manually set without tuning process. Implementing proper tuning would improve model performance and robustness. |
| Model Comparison & Performance Evaluation | 20 / 20 | Model comparison metrics are correctly computed and presented on the same test set. Including interpretation and discussion of practical differences and error impact would strengthen this section. |
| Risk Factor / Feature Importance Analysis | 0 / 15 | Feature importance analysis is missing. Including valid feature importance measures and careful interpretation distinguishing association from causation is required. |
| Clustering & Customer Segmentation | 20 / 20 | Clustering and segmentation were well executed with appropriate aggregation, scaling, cluster quality evaluation, and cautious interpretation. |

## Strengths

- Implemented all required tree-based and boosting regression models with consistent preprocessing and reproducible train/test split.
- Performed customer-level aggregation and clustering with scaling and cluster quality evaluation.
- Compared models on the same holdout set with standard regression metrics.

## Areas for improvement

- Perform systematic hyperparameter tuning using cross-validation or validation splits to optimize model parameters.
- Include feature importance analysis using valid methods and interpret purchase drivers carefully.
- Provide discussion interpreting model comparison results and practical implications of errors.

## Overall feedback

The submission demonstrates solid implementation of multiple regression models with consistent preprocessing and reproducible evaluation on a holdout set. Customer segmentation is well done with appropriate aggregation, scaling, clustering, and cluster quality assessment. However, the submission lacks systematic hyperparameter tuning and any feature importance analysis, which are critical for model optimization and understanding purchase drivers. Additionally, the model comparison results are presented without interpretation or discussion of practical significance. Addressing these gaps would substantially improve the quality and completeness of the milestone deliverables.

_AI-generated evaluation; subject to human review._
