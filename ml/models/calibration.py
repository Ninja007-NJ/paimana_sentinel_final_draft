from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression


class ProbabilityCalibrator:
    def __init__(self, method="sigmoid"):
        self.method = method
        self.estimator = None

    def fit(self, probabilities, y):
        p = np.asarray(probabilities).reshape(-1)
        if self.method == "sigmoid":
            self.estimator = LogisticRegression(random_state=26103).fit(p.reshape(-1, 1), y)
        elif self.method == "isotonic":
            self.estimator = IsotonicRegression(out_of_bounds="clip").fit(p, y)
        elif self.method != "none":
            raise ValueError(self.method)
        return self

    def transform(self, probabilities):
        p = np.asarray(probabilities).reshape(-1)
        if self.method == "none" or self.estimator is None:
            return np.clip(p, 0, 1)
        if self.method == "sigmoid":
            return self.estimator.predict_proba(p.reshape(-1, 1))[:, 1]
        return np.clip(self.estimator.predict(p), 0, 1)
