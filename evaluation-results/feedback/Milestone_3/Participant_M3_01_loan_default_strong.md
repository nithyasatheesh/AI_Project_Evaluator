# Participant_M3_01 — Milestone 3

**Project:** Loan_Default  
**Submission:** `Submission-Milestone3/Participant_M3_01_loan_default_strong.ipynb`  
**Evaluated:** 2026-10-27T11:44:49+00:00  
**Score:** **18 / 100**

| Criterion | Marks | Feedback |
|---|---:|---|
| Neural Network Design & Implementation | 10 / 25 | The architecture is appropriate for tabular data but lacks explicit discussion of activation functions, loss, or optimizer choices. More detailed justification and exploration of architecture variants would improve this section. |
| Data Preparation & Training | 8 / 20 | Data preparation is well structured but incomplete due to missing TARGET assignment and no actual training or reproducibility details (e.g., seed for neural network beyond random_state). Explicit handling of class imbalance for the neural network is missing. |
| Model Evaluation & Overfitting Analysis | 0 / 20 | No evidence of model evaluation or overfitting analysis is present. Actual metrics, learning curves, or validation analysis must be included to award marks. |
| ML vs DL Comparison | 0 / 15 | No executed comparison or conclusions are provided. A fair comparison with consistent splits and metrics is required. |
| NLP Implementation & Findings | 0 / 20 | No NLP implementation or findings are provided. This section is missing entirely. |

## Strengths

- Clear and leakage-aware data preprocessing pipeline with stratified train/test split.
- Appropriate baseline neural network architecture proposed with early stopping and random state for reproducibility.
- Consideration of responsible AI practices by not claiming metrics without execution.

## Areas for improvement

- Set and verify the TARGET variable to enable actual training and evaluation.
- Execute model training and report detailed evaluation metrics including overfitting analysis.
- Provide a fair and executed comparison between ML and DL models on the same data splits.
- Implement and report on the NLP task if relevant text data is available.
- Include more detailed justification of neural network design choices and training configuration.

## Overall feedback

The submission provides a well-structured plan and partial implementation for Milestone 3, including data preparation and neural network design. However, it lacks execution of training, evaluation, and comparison steps, as well as any NLP implementation. To meet the milestone requirements, the participant must run the code with the verified dataset, produce and report metrics, analyze overfitting, and implement the NLP component if applicable. The submission demonstrates understanding but is incomplete in evidence.

_AI-generated evaluation; subject to human review._
