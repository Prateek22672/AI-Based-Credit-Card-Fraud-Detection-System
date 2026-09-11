# FraudLens results

Generated from `reports/results/*.json` by `python -m reporting.build`.

## E1 Model benchmark (Sparkov, unseen test period Apr-Jun 2020)

| Model | PR-AUC [95% CI] | ROC-AUC | Precision | Recall | F1 | MCC | Latency p50 ms |
|---|---|---|---|---|---|---|---|
| **FraudLens Hybrid (XGB + RF + IF)** | 0.979 [0.973, 0.984] | 0.999 | 0.946 | 0.925 | 0.935 | 0.935 | 209.39 |
| XGBoost | 0.978 [0.973, 0.984] | 0.999 | 0.937 | 0.937 | 0.937 | 0.936 | 1.67 |
| LightGBM | 0.980 [0.975, 0.985] | 1.000 | 0.948 | 0.942 | 0.945 | 0.945 | 2.03 |
| Random Forest | 0.943 [0.933, 0.952] | 0.998 | 0.896 | 0.851 | 0.873 | 0.872 | 38.76 |
| Deep MLP (PyTorch) | 0.960 [0.952, 0.968] | 0.999 | 0.914 | 0.890 | 0.902 | 0.902 | - |
| 1D-CNN (PyTorch) | 0.933 [0.922, 0.944] | 0.998 | 0.892 | 0.827 | 0.858 | 0.858 | - |
| Decision Tree | 0.787 [0.760, 0.809] | 0.943 | 0.895 | 0.743 | 0.812 | 0.814 | 0.43 |
| Logistic Regression | 0.441 [0.415, 0.473] | 0.990 | 0.481 | 0.735 | 0.581 | 0.592 | 1.29 |
| Isolation Forest (unsupervised) | 0.421 | 0.965 | 0.478 | 0.514 | 0.495 | 0.492 | 65.36 |
| Rule-based (legacy bank rules) | 0.248 | 0.795 | 0.648 | 0.268 | 0.380 | 0.415 | - |

## E2 Imbalance handling

| Model | Strategy | PR-AUC | F1 @0.5 | F1 tuned | Brier |
|---|---|---|---|---|---|
| Logistic Regression | No balancing | 0.652 | 0.591 | 0.675 | 0.00309 |
| Logistic Regression | Class weighting | 0.441 | 0.316 | 0.581 | 0.02464 |
| Logistic Regression | Random undersampling (1:1) | 0.433 | 0.300 | 0.580 | 0.02604 |
| Logistic Regression | SMOTE oversampling (1:1) | 0.451 | 0.319 | 0.591 | 0.02271 |
| Random Forest | No balancing | 0.951 | 0.852 | 0.894 | 0.00124 |
| Random Forest | Class weighting | 0.943 | 0.875 | 0.873 | 0.00147 |
| Random Forest | Random undersampling (1:1) | 0.880 | 0.345 | 0.810 | 0.02003 |
| Random Forest | SMOTE oversampling (1:1) | 0.941 | 0.863 | 0.875 | 0.00167 |
| XGBoost | No balancing | 0.971 | 0.929 | 0.928 | 0.00069 |
| XGBoost | Class weighting | 0.978 | 0.932 | 0.937 | 0.00066 |
| XGBoost | Random undersampling (1:1) | 0.960 | 0.539 | 0.907 | 0.00785 |
| XGBoost | SMOTE oversampling (1:1) | 0.980 | 0.941 | 0.940 | 0.00055 |

## E3 Evaluation protocol (ULB)

| Protocol | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| Predict 'genuine' for everything (no model) | 0.9987 | 0.000 | 0.000 | 0.000 |
| SMOTE on the whole dataset, then random 80/20 split, threshold 0.5 | 0.9998 | 1.000 | 1.000 | 1.000 |
| Random split first, SMOTE on training data only, threshold 0.5 | 0.9994 | 0.796 | 0.878 | 0.835 |
| Chronological split, SMOTE on training data only, threshold tuned on validation | 0.9995 | 0.915 | 0.720 | 0.806 |
| Chronological split, class weighting (no synthetic data), threshold tuned on validation (FraudLens) | 0.9995 | 0.887 | 0.733 | 0.803 |

## E3 Evaluation protocol (SPARKOV)

| Protocol | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| Predict 'genuine' for everything (no model) | 0.9940 | 0.000 | 0.000 | 0.000 |
| SMOTE on the whole dataset, then random 80/20 split, threshold 0.5 | 0.9997 | 1.000 | 1.000 | 1.000 |
| Random split first, SMOTE on training data only, threshold 0.5 | 0.9993 | 0.958 | 0.918 | 0.938 |
| Chronological split, SMOTE on training data only, threshold tuned on validation | 0.9992 | 0.954 | 0.912 | 0.933 |
| Chronological split, class weighting (no synthetic data), threshold tuned on validation (FraudLens) | 0.9992 | 0.952 | 0.907 | 0.929 |

## E4 Ablation

| Feature set | PR-AUC | Recall | Precision |
|---|---|---|---|
| Raw transaction fields only (typical project) | 0.825 | 0.759 | 0.768 |
| + behavioural features (FraudLens, protected attributes excluded) | 0.978 | 0.937 | 0.937 |
| + age and gender (protected attributes) | 0.984 | 0.943 | 0.962 |

| Stacked combination | PR-AUC | Recall | Precision |
|---|---|---|---|
| xgb | 0.9784 | 0.936 | 0.938 |
| rf | 0.9431 | 0.852 | 0.895 |
| iforest | 0.4210 | 0.513 | 0.479 |
| xgb+rf | 0.9786 | 0.937 | 0.936 |
| xgb+iforest | 0.9783 | 0.928 | 0.947 |
| rf+iforest | 0.9429 | 0.822 | 0.928 |
| xgb+rf+iforest | 0.9785 | 0.925 | 0.946 |
| avg(xgb,rf) | 0.9731 | 0.924 | 0.943 |
| xgb_with_if_feature | 0.9801 | 0.936 | 0.949 |

## E5 Unseen fraud type (recall on the held-out type)

| Held-out type | Frauds | XGBoost | RF | Isolation Forest | Hybrid | Hybrid (saw it) |
|---|---|---|---|---|---|---|
| online | 391 | 0.537 | 0.000 | 0.987 | 0.432 | 0.997 |
| in_person | 701 | 0.227 | 0.000 | 0.437 | 0.106 | 0.976 |

## E6 ULB European dataset

| Model | PR-AUC | Precision | Recall | F1 |
|---|---|---|---|---|
| FraudLens Hybrid (XGB + RF + IF) | 0.795 | 0.905 | 0.760 | 0.826 |
| XGBoost | 0.793 | 0.905 | 0.760 | 0.826 |
| LightGBM | 0.792 | 0.851 | 0.760 | 0.803 |
| Random Forest | 0.808 | 0.853 | 0.773 | 0.811 |
| Deep MLP (PyTorch) | 0.809 | 0.931 | 0.720 | 0.812 |
| Logistic Regression | 0.778 | 0.911 | 0.680 | 0.779 |
| Isolation Forest (unsupervised) | 0.051 | 0.084 | 0.560 | 0.146 |

## E7 Business impact (hybrid, cost-optimal thresholds)

| Alert cost | Recall | Precision | Alerts/day | Loss avoided |
|---|---|---|---|---|
| $1 | 0.987 | 0.454 | 31.8 | 99.4% |
| $2 | 0.987 | 0.454 | 31.8 | 99.0% |
| $5 | 0.984 | 0.614 | 23.5 | 98.1% |
| $10 | 0.973 | 0.830 | 17.2 | 96.9% |
| $25 | 0.973 | 0.836 | 17.1 | 93.7% |

## Safety layer (test period)

| Rule | Fires | On genuine | Fraud rate | Extra alerts beyond ML | Extra frauds | Extra / day |
|---|---|---|---|---|---|---|
| P1 | 52 | 9 | 83% | 8 | 0 | 0.11 |
| P2 | 0 | 0 | - | 0 | 0 | 0.00 |
| P3 | 15 | 15 | 0% | 15 | 0 | 0.20 |
| N1 | 155 | 45 | 71% | 39 | 0 | 0.52 |

ML only: recall 0.984, precision 0.614; ML + safety layer: recall 0.984, precision 0.593; 0.81 extra step-ups per day.

## Latency (idle machine, one thread, one transaction per call)

| Model | p50 ms | p95 ms |
|---|---|---|
| lr | 1.29 | 1.69 |
| dt | 0.43 | 0.54 |
| rf | 38.76 | 55.47 |
| xgb | 1.67 | 2.26 |
| lgbm | 2.03 | 2.55 |
| iforest | 65.36 | 185.61 |
| hybrid | 209.39 | 424.85 |

Full API path (features + models + safety layer + SHAP + DB write): p50 256.6 ms, p95 526.7 ms; stream throughput 730 txn/s.
