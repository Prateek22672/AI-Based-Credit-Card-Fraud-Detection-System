# Pre-processing in FraudLens: what it is, and why

Every number below comes from `reports/results/*.json` (experiments E2 and E3) and every test named exists in
`tests/`.

## 1. The short answer

**There is no pre-processing model.** Pre-processing is a fixed, rule-based pipeline: nothing in it is fitted on
the whole dataset, so nothing can carry information from the test period back into training. The only fitted
transformer is a `StandardScaler`, and it is fitted on training rows only, inside the pipeline of the models that need
scaling (Logistic Regression, MLP, CNN). The tree models (XGBoost, Random Forest, Isolation Forest) need no scaling.

The only learned components are the three detectors and the stacking layer, and those are the *model*, not
pre-processing.

## 2. The five steps

1. **Column selection and tokenisation.** 16 of 24 columns are loaded; card numbers become HMAC-SHA256 tokens
   used only to group a card's history.
2. **Chronological split, never shuffled.** Train 2019, validate Q1 2020, test Q2 2020, with a 7-day gap between
   blocks because real fraud labels take days to confirm.
3. **Causal feature engineering.** 41 features per transaction, each computed only from that card's earlier
   transactions: velocity (1 h / 24 h / 7 d), amount against the card's own average, time since the last
   transaction, distance from home, novelty flags.
4. **Class imbalance: class weighting** inside model training. No synthetic rows, no discarded rows.
5. **Scaling** only for the three models that need it, fitted on training data only.

## 3. Why not the alternatives

| Alternative | Why we did not use it |
|---|---|
| Learned transformer (autoencoder, PCA, learned imputer) fitted on all data | It sees the test period while "cleaning" training rows, so the evaluation is no longer on unseen data. Fitting it on training only is safe but adds a model whose benefit we cannot separate from the detector's. |
| Per-card statistics over the whole dataset | A 2019 transaction would be compared with an average that includes 2020. Our averages use earlier transactions only. |
| SMOTE before splitting | Synthetic rows are built from points that later land in the test set. Experiment E3 measures the damage (section 5). |
| Random undersampling | Experiment E2 shows it wrecks the probabilities (section 4). |
| Random (shuffled) split | Fraud patterns drift; a shuffled split lets the model train on the future. |

## 4. Why class weighting: experiment E2 (XGBoost, same chronological split)

| Strategy | PR-AUC | F1 @0.5 | F1 tuned | Brier | Mean predicted prob | Fit time |
|---|---|---|---|---|---|---|
| None | 0.9714 | 0.929 | 0.928 | 0.00069 | 0.0056 | 109 s |
| **Class weighting (ours)** | 0.9784 | 0.932 | 0.937 | 0.00066 | 0.0066 | 133 s |
| Undersampling 1:1 | 0.9598 | 0.539 | 0.907 | 0.00785 | 0.0198 | 9 s |
| SMOTE 1:1 | 0.9801 | 0.941 | 0.940 | 0.00055 | 0.0059 | 211 s |

The true fraud rate in the test period is 0.0060.

* **Undersampling is clearly worst**: mean predicted probability 0.0198 against a true 0.0060, Brier about 12x worse.
* **SMOTE is marginally ahead of class weighting on every column here** (0.9801 vs 0.9784 PR-AUC, 0.940 vs 0.937 F1).
  We do not claim class weighting wins on accuracy. We chose it because it trains on real transactions only (nothing
  synthetic to explain to an auditor), is 1.6x faster, and the difference is small enough that it does not change a
  decision.

## 5. Why order matters: experiment E3 (same XGBoost, four evaluation protocols)

| Protocol | ULB F1 | Sparkov F1 |
|---|---|---|
| A. SMOTE on the whole dataset, then random 80/20 split | **0.9998** | **0.9997** |
| B. Random split first, SMOTE on training data only | 0.835 | 0.938 |
| C. Chronological split, SMOTE on training data only, threshold tuned on validation | 0.806 | 0.933 |
| D. Chronological split, class weighting, threshold tuned on validation (**FraudLens**) | **0.803** | **0.929** |

Protocol A is not a better model: it is the same model measured badly. SMOTE built synthetic points from rows that
then appear in the test half, and the test half itself is half synthetic (`test_fraud_share` 0.50). On ULB the
honest number is 0.803, a gap of about 0.20 F1. On Sparkov the gap is smaller (0.9997 to 0.929) but the headline
is just as misleading.

Note what B to D shows: once the leak in A is removed, the remaining differences are small. The big effect is the
leak, not the choice between SMOTE and weighting.

## 6. How we prove the features are causal

Both tests are in `tests/test_features.py`:

* `test_features_do_not_see_future_transactions`: changes the last transaction of a card and asserts every earlier
  row's features are identical.
* `test_online_features_match_training_features`: replays 3,000 test transactions through the API's feature-store
  snapshot and asserts the features equal the offline training matrix to within 1e-5. So training and serving
  compute the same thing.

## 7. Answers to likely questions

**"What model do you use for pre-processing?"**
None. It is rule-based and causal. The only fitted transformer is a training-only `StandardScaler` for LR/MLP/CNN.

**"Why not SMOTE?"**
We tested it (E2). It is marginally ahead on PR-AUC (0.9801 vs 0.9784). We prefer class weighting because it uses
only real transactions and trains faster. The real danger is applying SMOTE before the split, which is what E3
quantifies.

**"Why not an autoencoder or PCA to denoise?"**
Fitted on all data it leaks the future; fitted on training only it is safe but adds a model we would have to defend
separately, and our features are already built from interpretable per-card behaviour. ULB's V1-V28 are PCA outputs
for exactly that reason, and they cannot be explained to an analyst.

**"Your F1 on ULB is only 0.80. Papers report 99%+."**
Those figures match Protocol A. Same model, same data: 0.9998 under A, 0.803 under D.

**"Is the feature store really leak-free?"**
Two tests, section 6. One proves a later transaction cannot change an earlier row; the other proves training and
live serving produce the same features.

## 8. Sources

* Santos et al. (2018), *Cross-Validation for Imbalanced Datasets: Avoiding Overoptimistic and Overfitting
  Approaches*: resampling must happen inside training folds only.
* Kaufman, Rosset, Perlich, Stitelman (2012), *Leakage in Data Mining: Formulation, Detection, and Avoidance*:
  the leakage taxonomy behind the causal feature store.
* Hayat and Magnier (2025), *Data Leakage and Deceptive Performance: A Critical Examination of Credit Card Fraud
  Detection Methodologies*: the published description of the effect E3 reproduces.
* Dal Pozzolo, Boracchi, Caelen, Alippi, Bontempi (2018), *Credit Card Fraud Detection: A Realistic Modeling and a
  Novel Learning Strategy*: chronological evaluation with a label-delay gap.
