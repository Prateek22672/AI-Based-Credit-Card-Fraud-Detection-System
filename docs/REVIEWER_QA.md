# Reviewer Q&A: dataset, pre-processing, thresholds and metrics

Short, exact answers to the questions a reviewer is most likely to ask. Every number here is produced by
`python -m fraudlens.pipeline all` and stored in `reports/results/*.json`.

---

## 1. How many columns and categories are in the dataset, and how many do we process?

**"42" is not the number of columns.** The closest true number is **41 engineered features** (of which the model
uses 39). The raw Sparkov file has **24 columns**. Those are three different counts and it is worth keeping them apart:

| Count | Sparkov (primary dataset) | ULB (benchmark dataset) |
|---|---|---|
| Columns in the raw file | **24** | **31** |
| Columns we load | **16** (8 dropped) | **31** |
| Columns that are inputs | 15 + 1 label (`is_fraud`) | 30 + 1 label (`Class`) |
| **Merchant categories** | **14** (all used) | **0** — the data is anonymised |
| **Features built by us** | **41** (27 numeric + 14 category flags) | 31 (28 PCA + amount + 2 derived) |
| **Features the model uses** | **39** (`age` and `gender` excluded) | 31 |
| Transactions / frauds | 1,296,675 / 7,506 (0.58%) | 284,807 / 492 (0.17%) |
| Cards / merchants | 983 / 693 | not provided |
| Period | Jan 2019 – Jun 2020 | 2 days (Sept 2013) |

One sentence for the reviewer:

> "The file has 24 columns. We keep 16 of them, and from those we engineer 41 features — 27 numeric behavioural
> features plus 14 merchant-category flags — of which the deployed model uses 39."

### The 14 merchant categories (all 14 are used)

Fraud rate measured on the full Sparkov dataset. The model gets the category as 14 one-hot flags, and the
dashboard shows this table under **Results → Dataset**.

| Category | Fraud rate | Frauds | Transactions |
|---|---|---|---|
| Online shopping (`shopping_net`) | 1.76% | 1,713 | 97,543 |
| Online misc (`misc_net`) | 1.45% | 915 | 63,287 |
| Grocery in-store (`grocery_pos`) | 1.41% | 1,743 | 123,638 |
| Shopping in-store (`shopping_pos`) | 0.72% | 843 | 116,672 |
| Fuel & transport (`gas_transport`) | 0.47% | 618 | 131,659 |
| Misc in-store (`misc_pos`) | 0.31% | 250 | 79,655 |
| Online grocery (`grocery_net`) | 0.29% | 134 | 45,452 |
| Travel (`travel`) | 0.29% | 116 | 40,507 |
| Entertainment (`entertainment`) | 0.25% | 233 | 94,014 |
| Personal care (`personal_care`) | 0.24% | 220 | 90,758 |
| Kids & pets (`kids_pets`) | 0.21% | 239 | 113,035 |
| Food & dining (`food_dining`) | 0.17% | 151 | 91,461 |
| Home (`home`) | 0.16% | 198 | 123,115 |
| Health & fitness (`health_fitness`) | 0.15% | 133 | 85,879 |

Online categories carry ~10× the fraud rate of the safest in-store ones, which is why channel is a feature.

### What we take and what we leave

**Kept (16 columns)** — `trans_date_trans_time`, `cc_num`, `merchant`, `category`, `amt`, `gender`, `city`,
`state`, `lat`, `long`, `city_pop`, `dob`, `unix_time`, `merch_lat`, `merch_long`, `is_fraud`.

**Dropped at load (8 columns)** — and why:

| Dropped | Reason |
|---|---|
| `first`, `last`, `street`, `zip` | Personal data. A name or street address is not a fraud signal; keeping it only creates privacy risk. |
| `job` | High-cardinality personal attribute; its apparent predictive power is memorisation of individuals, not fraud behaviour. |
| `trans_num` | A unique id. A model can only memorise it, which is a classic leakage path. |
| `merch_zipcode` | Mostly empty, and merchant location is already captured by `merch_lat`/`merch_long`. |
| `Unnamed: 0` | The CSV row index. It correlates with time order and is pure leakage. |

**Built but deliberately excluded from the model (2 features):** `age` and `gender`. Including them would add
**+0.0057 PR-AUC** (0.9784 → 0.9841), and we give that up on purpose: a fraud decision should not depend on a
customer's gender or age. The cost is measured and reported rather than hidden (Project Report, E4).

`cc_num` is never a model input either — it is only the key used to group a card's history.

**ULB for contrast:** 31 columns = `Time`, `V1`–`V28`, `Amount`, `Class`. `V1`–`V28` are PCA components, so they
have no meaning and no categories exist. We drop `Time` and add `hour` and `log_amount`, giving 31 inputs. This is
exactly why Sparkov is our main dataset: you cannot build behavioural features or readable explanations from "V14".

---

## 2. What model do we use for pre-processing, and why is it the best way?

**Pre-processing uses no learned model** — and that is deliberate. Using a model (an autoencoder, PCA, a learned
imputer) in pre-processing on a time-ordered fraud problem is the easiest way to leak the future into the past.
Our pre-processing is five deterministic steps:

1. **Column selection + card tokenisation.** 16 columns kept; card numbers replaced by an HMAC-SHA256 token.
2. **Chronological ordering and splitting** — train 2019, validate Q1 2020, test Q2 2020, with a **7-day gap**
   between blocks because real fraud labels take days to confirm. Nothing is shuffled.
3. **Causal feature engineering** (`fraudlens/features.py`): 41 features, each computed from **only that card's
   earlier transactions** — velocity counts (1 h / 24 h / 7 d), amount vs the card's own average, time since the
   previous transaction, distance from home, novelty flags.
4. **Class-imbalance handling: class weighting**, applied inside training only.
5. **Scaling only where needed** — Logistic Regression, MLP and CNN get a `StandardScaler` fitted on training data
   inside their pipeline. Tree models need no scaling.

### Why class weighting rather than SMOTE (experiment E2, XGBoost on the same split)

| Strategy | PR-AUC | F1 @0.5 | F1 tuned | Brier | Mean predicted prob | Train time |
|---|---|---|---|---|---|---|
| No balancing | 0.9714 | 0.929 | 0.928 | 0.00069 | 0.0056 | 109 s |
| **Class weighting (ours)** | **0.9784** | 0.932 | 0.937 | 0.00066 | 0.0066 | 133 s |
| Random undersampling 1:1 | 0.9598 | 0.539 | 0.907 | **0.00785** | **0.0198** | 9 s |
| SMOTE 1:1 | 0.9801 | 0.941 | 0.940 | 0.00055 | 0.0059 | 211 s |

True fraud rate in the test period: **0.0060**.

Honest reading of this table:

* **Undersampling is clearly worst.** It throws away 99% of the genuine data and wrecks the probabilities: it
  predicts an average fraud probability of 0.0198 against a true rate of 0.0060 — more than 3× over-confident,
  with a Brier score 12× worse. Any risk score built on it would be meaningless.
* **SMOTE and class weighting are statistically indistinguishable** (0.9801 vs 0.9784, a gap of 0.0017 inside our
  ±0.005 confidence band). We chose class weighting because it (a) trains on **real transactions only** — SMOTE
  invents synthetic cardholder behaviour that never happened, which is hard to defend to an auditor, (b) keeps the
  natural class balance so the stacking layer's probabilities stay calibrated, and (c) is 1.6× faster to train.
* **The threshold matters more than the balancing trick.** Every strategy lands within ~0.01 F1 once the threshold
  is tuned; it is choosing the threshold on validation data that moves results, not the resampling.

The strongest defence is that this was **decided by experiment, not by assumption** — most reviewed papers simply
apply SMOTE because it is conventional.

---

## 3. The 0–100 risk score: on what basis are the bands set?

The model outputs a **calibrated probability** between 0 and 1. Two thresholds are learned **on validation data
only** and then applied unchanged to the test period:

| Threshold | Value | How it is chosen |
|---|---|---|
| **Alert** (Approve → Step-up) | **0.0142** | The point that **minimises total money lost** = missed-fraud value + $5 per alert raised. |
| **Block** (Step-up → Block) | **0.2065** | The **lowest** probability at which alerts are at least **90% precise** — we only auto-block when the model is demonstrably right 9 times out of 10. |

The 0–100 score is a straight-line (monotone) re-scaling of the probability through those two points:

```
probability 0      →   score 0
probability 0.0142 →   score 30      (band edge: Approve / Step-up)
probability 0.2065 →   score 60      (band edge: Step-up / Block)
probability 1.0    →   score 100
```

So **30 and 60 are not arbitrary**: they are exactly where the action changes. A score of 61 means "the model is at
least 90% precise at this level, block it"; a score of 29 means "cheaper to approve than to review". The mapping is
monotone, so no information is added or lost — it exists because `0.0142` is unreadable on an analyst's screen
while `31 / 100` is obvious.

**What the bands actually do on the unseen test quarter:**

| Tier | Action | Transactions | Frauds | Fraud rate in tier |
|---|---|---|---|---|
| LOW (0–30) | Approve | 181,024 (99.0%) | 18 | 0.01% |
| MEDIUM (31–60) | Step-up (OTP) | 599 (0.33%) | 36 | 6.0% |
| HIGH (61–100) | Block + case | 1,151 (0.63%) | 1,038 | **90.2%** |

Nine out of ten blocked transactions are genuinely fraud, and only 18 frauds out of 1,092 slip into the approve tier.

A safety layer of documented rules sits after this and can only **raise** a decision to at least Step-up, never
approve one.

---

## 4. How is PR-AUC calculated, and what do the headline numbers mean?

### PR-AUC (the primary metric)

**Definition.** PR-AUC = average precision = the area under the precision–recall curve, computed as

$$\text{AP} = \sum_n (R_n - R_{n-1})\, P_n$$

where $P_n, R_n$ are the precision and recall at the $n$-th threshold. Implementation:
`sklearn.metrics.average_precision_score(y_true, y_score)`.

**How we computed it.** We sort all **182,774 unseen test transactions** (Apr–Jun 2020, containing **1,092 frauds**)
by the hybrid's calibrated probability, sweep every possible threshold, and integrate precision over recall.
**No threshold is involved** — PR-AUC measures how well the model *ranks* fraud above genuine, so it cannot be
flattered by a lucky cut-off.

**Why it is the primary metric, not accuracy or ROC-AUC:**

* A model that approves everything scores **99.4% accuracy** on this data. Accuracy is useless here.
* ROC-AUC is **0.9994** — it looks near-perfect for almost any model, because with 0.6% positives the false-positive
  rate stays tiny whatever you do.
* PR-AUC punishes false alarms directly. A random model scores the positive rate: **0.006**. We score **0.979**.

**Confidence.** 95% CI **[0.973, 0.984]** from 500 bootstrap resamples of the test set.

### Where each headline number comes from

The tiles are measured at the **F1-tuned threshold (0.4607)**, chosen on the validation period and applied unchanged
to the test period. The confusion matrix at that threshold is:

| | Predicted fraud | Predicted genuine |
|---|---|---|
| **Actually fraud** | TP = 1,010 | FN = 82 |
| **Actually genuine** | FP = 58 | TN = 181,624 |

| Tile | Value | Exactly how it is computed |
|---|---|---|
| PR-AUC | **0.979** | Area under the precision–recall curve, all thresholds, 182,774 transactions |
| Recall | **92.5%** | TP / (TP + FN) = 1,010 / 1,092 |
| Precision | **94.6%** | TP / (TP + FP) = 1,010 / 1,068 |
| F1 | **0.935** | Harmonic mean of precision and recall |
| MCC | **0.935** | Matthews correlation — uses all four cells, so it cannot be inflated by the huge TN count |
| Fraud $ caught | **95.2%** | $555,881 of **$584,135** — the summed amount of all fraudulent test transactions |
| Latency p50 | **209.4 ms** | Median time to score one transaction through all three models + meta-learner, single thread (p95 424.8 ms). Full API path including SHAP and the audit write: 256.6 ms median. In batches: **1.37 ms** per transaction. |

### The one thing to say before a reviewer asks

There are **two operating points**, and both are honest:

| | Threshold | Recall | Precision | Fraud value stopped |
|---|---|---|---|---|
| **F1-tuned** (used to compare models) | 0.4607 | 92.5% | 94.6% | 95.2% |
| **Deployed** (used by the live system) | 0.0142 | **98.4%** | 61.4% | **99.6%** |

The deployed engine deliberately accepts lower precision to catch almost every fraud, because a missed fraud costs
the transaction amount while an alert costs about $5. At that setting it raises ~23 alerts a day and avoids
**98.1%** of fraud losses net of alert costs. The Live Monitor shows this operating point, which is why its
precision reads ~61% and not 94.6%.

### Why these numbers are trustworthy

* **Trained on the past, tested on the future** — train 2019, test Apr–Jun 2020, with 7-day label-delay gaps.
* **Thresholds never touched the test set** — all chosen on the validation quarter.
* **Features are causal** — a unit test proves that changing a later transaction cannot change an earlier row's
  features, and a second test replays 3,000 live transactions through the API's feature store and checks they
  match the training matrix to within floating-point tolerance (no training/serving skew).
* **The shortcut is demonstrated, not used** — applying SMOTE before a random split (common in published papers)
  reports a perfect F1 of 1.000 on ULB; the same model evaluated honestly gives 0.803.
