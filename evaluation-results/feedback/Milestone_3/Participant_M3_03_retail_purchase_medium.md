# Participant_M3_03 — Milestone 3

**Project:** Retail_Customer_Purchase  
**Submission:** `Submission-Milestone3/Participant_M3_03_retail_purchase_medium.ipynb`  
**Evaluated:** 2026-10-27T11:45:02+00:00  
**Score:** **70 / 100**

| Criterion | Marks | Feedback |
|---|---:|---|
| Neural Network Design & Implementation | 20 / 25 | The neural network architecture is clearly specified and reproducible settings are used. However, there is no detailed documentation of activation functions, optimizer settings, or rationale for architecture choice, which limits full assessment. |
| Data Preparation & Training | 18 / 20 | Data preparation is appropriate and correctly applied only on training data. Early stopping provides regularization. However, no explicit validation set split or cross-validation is shown, and no mention of hyperparameter tuning or other regularization techniques beyond early stopping. |
| Model Evaluation & Overfitting Analysis | 12 / 20 | Model evaluation on held-out data is done with appropriate metrics. However, the submission lacks analysis of training vs validation errors to assess overfitting or error patterns, and no plots or detailed discussion are provided. |
| ML vs DL Comparison | 15 / 15 | The comparison between ML and DL models is clear and uses identical held-out data and consistent metrics, fulfilling the criterion well. |
| NLP Implementation & Findings | 5 / 20 | The NLP task is limited to exploratory unsupervised text representation without a defined downstream task or evaluation. While this is cautious and avoids fabricating labels, it falls short of demonstrating a valid NLP task with findings. |

## Strengths

- Clear neural network architecture with reproducible settings.
- Proper data preprocessing applied only on training data.
- Consistent evaluation metrics used for ML and DL models on the same test set.
- Cautious and responsible approach to NLP without fabricating labels or metrics.

## Areas for improvement

- Provide more detailed documentation of neural network design choices and training parameters.
- Include validation set or cross-validation for better training and regularization assessment.
- Add training vs validation performance comparison and residual/error analysis to discuss overfitting.
- Extend NLP work to a defined task with evaluation if labels are available or justify unsupervised approach with insights.

## Overall feedback

The submission meets the core requirements of Milestone 3 by implementing a neural network regression model with appropriate preprocessing and comparing it fairly to a best ML model using consistent metrics on held-out data. The neural network design is documented but could be more detailed. Data preparation and training are sound, though validation and overfitting analysis are limited. The NLP component is cautious and avoids fabrication but lacks a defined task or findings. Overall, the work is solid but could be strengthened by deeper analysis and more comprehensive NLP implementation.

_AI-generated evaluation; subject to human review._
