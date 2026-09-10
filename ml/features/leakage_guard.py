from __future__ import annotations

from fnmatch import fnmatch

from ml.features.feature_registry import ALLOWED_FEATURES, EXCLUDED_PATTERNS


def assert_leakage_safe(columns):
    columns = list(columns)
    forbidden = []
    for column in columns:
        if column not in ALLOWED_FEATURES:
            for pattern in EXCLUDED_PATTERNS:
                if fnmatch(column, pattern):
                    forbidden.append(column)
                    break
    if forbidden:
        raise ValueError(f"Leakage-prone features detected: {sorted(forbidden)}")
    unexpected = set(columns) - set(ALLOWED_FEATURES)
    if unexpected:
        raise ValueError(f"Unregistered predictive features: {sorted(unexpected)}")
    return True
