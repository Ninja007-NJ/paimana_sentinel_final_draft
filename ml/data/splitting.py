from __future__ import annotations

import pandas as pd

from ml.config import TRAIN_END, TRAIN_START, VALID_END, VALID_START, TEST_END, TEST_START, TARGET


def temporal_split(data: pd.DataFrame):
    train = data[data.snapshot_month.between(TRAIN_START, TRAIN_END)].copy()
    valid = data[data.snapshot_month.between(VALID_START, VALID_END)].copy()
    test = data[data.snapshot_month.between(TEST_START, TEST_END)].copy()
    if not (train.snapshot_month.max() < valid.snapshot_month.min() <= valid.snapshot_month.max() < test.snapshot_month.min()):
        raise ValueError("Temporal split is not chronological")
    return train, valid, test


def split_summary(frame: pd.DataFrame) -> dict:
    positives = int(frame[TARGET].sum())
    return {
        "start": frame.snapshot_month.min(), "end": frame.snapshot_month.max(),
        "rows": len(frame), "unique_projects": frame.canonical_project_id.nunique(),
        "positives": positives, "negatives": int(len(frame) - positives),
        "positive_rate_pct": round(100 * positives / len(frame), 4),
    }


def project_overlap(left: pd.DataFrame, right: pd.DataFrame) -> dict:
    a, b = set(left.canonical_project_id), set(right.canonical_project_id)
    return {"overlap_projects": len(a & b), "left_projects": len(a), "right_projects": len(b)}


def unseen_project_test(train: pd.DataFrame, valid: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    seen = set(train.canonical_project_id) | set(valid.canonical_project_id)
    return test[~test.canonical_project_id.isin(seen)].copy()
