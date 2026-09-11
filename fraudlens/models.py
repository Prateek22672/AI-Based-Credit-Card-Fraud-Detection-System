"""Model factory for every classifier and imbalance strategy compared."""
from __future__ import annotations

import lightgbm as lgb
import numpy as np
import xgboost as xgb
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.under_sampling import RandomUnderSampler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from . import config

MODEL_LABELS = {
    "rules": "Rule-based (legacy bank rules)",
    "lr": "Logistic Regression",
    "dt": "Decision Tree",
    "rf": "Random Forest",
    "xgb": "XGBoost",
    "lgbm": "LightGBM",
    "iforest": "Isolation Forest (unsupervised)",
    "mlp": "Deep MLP (PyTorch)",
    "cnn": "1D-CNN (PyTorch)",
    "hybrid": "FraudLens Hybrid (XGB + RF + IF)",
}
STRATEGIES = {
    "none": "No balancing",
    "weight": "Class weighting",
    "rus": "Random undersampling (1:1)",
    "smote": "SMOTE oversampling (1:1)",
}

XGB_PARAMS = dict(
    n_estimators=400, learning_rate=0.1, max_depth=6, subsample=0.8, colsample_bytree=0.8,
    min_child_weight=1.0, tree_method="hist", eval_metric="aucpr",
)
RF_PARAMS = dict(
    n_estimators=200, max_depth=16, min_samples_leaf=5, max_features="sqrt", max_samples=0.3,
)
LGBM_PARAMS = dict(
    n_estimators=400, learning_rate=0.1, num_leaves=63, subsample=0.8, subsample_freq=1,
    colsample_bytree=0.8, min_child_samples=20, verbose=-1,
    # With a ~177x positive-class weight LightGBM's leaf values blow up and validation
    # PR-AUC oscillates between 0.04 and 0.6; capping each leaf's step keeps training stable.
    max_delta_step=0.7,
)


def pos_weight(y: np.ndarray) -> float:
    pos = float(np.sum(y))
    return float((len(y) - pos) / max(pos, 1.0))


def make_classifier(name: str, weighted: bool, spw: float, seed: int = config.SEED):
    if name == "lr":
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=3000, C=1.0, class_weight="balanced" if weighted else None),
        )
    if name == "dt":
        return DecisionTreeClassifier(max_depth=12, min_samples_leaf=20, random_state=seed,
                                      class_weight="balanced" if weighted else None)
    if name == "rf":
        return RandomForestClassifier(**RF_PARAMS, random_state=seed, n_jobs=config.N_JOBS,
                                      class_weight="balanced_subsample" if weighted else None)
    if name == "xgb":
        return xgb.XGBClassifier(**XGB_PARAMS, scale_pos_weight=spw if weighted else 1.0,
                                 random_state=seed, n_jobs=config.N_JOBS)
    if name == "lgbm":
        return lgb.LGBMClassifier(**LGBM_PARAMS, scale_pos_weight=spw if weighted else 1.0,
                                  random_state=seed, n_jobs=config.N_JOBS)
    raise ValueError(name)


def make_model(name: str, strategy: str, y_train: np.ndarray, seed: int = config.SEED):
    """Classifier wrapped with an imbalance strategy.

    Resampling happens inside an imblearn pipeline, so it is only ever applied
    to the training data seen by ``fit`` and never leaks into validation or
    test data (Santos et al., 2018).
    """
    clf = make_classifier(name, weighted=(strategy == "weight"), spw=pos_weight(y_train), seed=seed)
    if strategy == "rus":
        return ImbPipeline([("sampler", RandomUnderSampler(sampling_strategy=1.0, random_state=seed)),
                            ("clf", clf)])
    if strategy == "smote":
        return ImbPipeline([("sampler", SMOTE(sampling_strategy=1.0, k_neighbors=5, random_state=seed)),
                            ("clf", clf)])
    return clf


def make_isolation_forest(seed: int = config.SEED) -> IsolationForest:
    return IsolationForest(n_estimators=300, max_samples=1024, random_state=seed, n_jobs=config.N_JOBS)
