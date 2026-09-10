from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from ml.features.feature_registry import CATEGORICAL_FEATURES, NUMERICAL_FEATURES


def make_linear_preprocessor(scale=True):
    numeric_steps = [("impute", SimpleImputer(strategy="median"))]
    if scale:
        numeric_steps.append(("scale", StandardScaler()))
    numeric = Pipeline(numeric_steps)
    categorical = Pipeline([
        ("impute", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=3)),
    ])
    return ColumnTransformer([
        ("numeric", numeric, NUMERICAL_FEATURES),
        ("categorical", categorical, CATEGORICAL_FEATURES),
    ])


def prepare_catboost(frame):
    output = frame.copy()
    for column in CATEGORICAL_FEATURES:
        output[column] = output[column].fillna("__MISSING__").astype(str)
    return output
