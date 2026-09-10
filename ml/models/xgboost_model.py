from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from ml.features.preprocessing import make_linear_preprocessor


def make_xgboost(**overrides):
    params = dict(
        n_estimators=600, max_depth=4, learning_rate=0.04, min_child_weight=4,
        subsample=0.85, colsample_bytree=0.85, objective="binary:logistic",
        eval_metric="logloss", random_state=26103, n_jobs=-1,
    )
    params.update(overrides)
    return Pipeline([
        ("preprocess", make_linear_preprocessor(scale=False)),
        ("model", XGBClassifier(**params)),
    ])
