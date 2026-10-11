# Dataset columns: what the files contain, what we keep, what we drop

## Where the files are

Not committed to GitHub (`data/` is git-ignored, about 260 MB). Created by `python -m fraudlens.download`.

| File | Rows | Columns | What it is |
|---|---|---|---|
| `data/raw/sparkov_train.parquet` | 1,296,675 | 24 | Full Sparkov dataset as downloaded (Kaggle `kartik2112/fraud-detection`) |
| `data/raw/creditcard_ulb.csv` | 284,807 | 31 | ULB European dataset (Kaggle `mlg-ulb/creditcardfraud`) |
| `data/processed/sparkov_features.parquet` | 1,296,675 | 41 | Engineered feature matrix (the model input) |
| `data/processed/sparkov_meta.parquet` | 1,296,675 | 10 | Per-transaction timestamp, card token, amount, label and train/val/test split |

## The 24 raw Sparkov columns

| # | Column | Example | Distinct values | Status | Reason |
|---|---|---|---|---|---|
| 1 | `Unnamed: 0` | 0 | 1,296,675 | **Dropped** | CSV row index; tracks time order, pure leakage |
| 2 | `trans_date_trans_time` | 2019-01-01 00:00:18 | 1,274,791 | Kept | Timestamp: hour, weekday, ordering, velocity |
| 3 | `cc_num` | 2703186189652095 | 983 | Kept | Only as the key that groups a card's history (tokenised, never a feature) |
| 4 | `merchant` | fraud_Rippin, Kub and Mann | 693 | Kept | Merchant novelty per card |
| 5 | `category` | misc_net | 14 | Kept | 14 merchant categories, one-hot |
| 6 | `amt` | 4.97 | 52,928 | Kept | Amount and amount-vs-history features |
| 7 | `first` | Jennifer | 352 | **Dropped** | Personal name |
| 8 | `last` | Banks | 481 | **Dropped** | Personal name |
| 9 | `gender` | F | 2 | Kept | Loaded, but excluded from the model (fairness) |
| 10 | `street` | 561 Perry Cove | 983 | **Dropped** | Personal address; one per card, so it identifies the card |
| 11 | `city` | Moravian Falls | 894 | Kept | Cardholder home city (display and card profile) |
| 12 | `state` | NC | 51 | Kept | Cardholder home state |
| 13 | `zip` | 28654 | 970 | **Dropped** | Personal address detail; `lat`/`long` already give home location |
| 14 | `lat` | 36.0788 | 968 | Kept | Home latitude, for distance-from-home |
| 15 | `long` | -81.1781 | 969 | Kept | Home longitude |
| 16 | `city_pop` | 3495 | 879 | Kept | City population feature |
| 17 | `job` | Psychologist, counselling | 494 | **Dropped** | High-cardinality personal attribute; invites memorising individuals |
| 18 | `dob` | 1988-03-09 | 968 | Kept | Loaded for age, but `age` is excluded from the model (fairness) |
| 19 | `trans_num` | 0b242abb62... | 1,296,675 | **Dropped** | Unique id per row; can only be memorised |
| 20 | `unix_time` | 1325376018 | 1,274,823 | Kept | Numeric time for gaps and velocity windows |
| 21 | `merch_lat` | 36.011293 | 1,247,805 | Kept | Merchant latitude, for distance and impossible travel |
| 22 | `merch_long` | -82.048315 | 1,275,745 | Kept | Merchant longitude |
| 23 | `is_fraud` | 0 | 2 | Kept | Label (never a feature) |
| 24 | `merch_zipcode` | 28705.0 | 28,336 | **Dropped** | 15% missing; merchant location already exact in `merch_lat`/`merch_long` |

**Kept: 16. Dropped: 8.**
Dropped: `Unnamed: 0`, `first`, `last`, `street`, `zip`, `job`, `trans_num`, `merch_zipcode`.

Of the 16 kept, `cc_num` and `is_fraud` are never features, and `gender`/`dob` are used only to compute `age` and
`gender_m`, which the deployed model excludes. The model uses 39 engineered features.

## ULB (31 columns)

`Time`, `V1` to `V28` (anonymised PCA components), `Amount`, `Class` (label). No merchant categories, no card
identifier, no location, which is why it is a benchmark and not our primary dataset.
