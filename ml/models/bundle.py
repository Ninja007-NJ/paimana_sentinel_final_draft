from dataclasses import dataclass
from typing import Any


@dataclass
class ModelBundle:
    model_type: str
    model: Any
    calibrator: Any
    thresholds: dict
    features: list
    model_version: str
    dataset_version: str
    global_importance: list
    metadata: dict
