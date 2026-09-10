from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ml.features.preprocessing import make_linear_preprocessor


def make_logistic(c=1.0, class_weight=None):
    return Pipeline([
        ("preprocess", make_linear_preprocessor(scale=True)),
        ("model", LogisticRegression(C=c, class_weight=class_weight, max_iter=3000, random_state=26103)),
    ])
