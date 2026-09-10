import joblib
import pandas as pd
from ml.config import MODEL_DIR
from ml.data.loader import load_delay_data
from ml.features.feature_registry import ALLOWED_FEATURES
from ml.predict_delay_3m import predict_delay_risk


def test_prediction_schema_probability_and_reload():
    row=load_delay_data(enrich=False).iloc[[0]][ALLOWED_FEATURES]
    result1=predict_delay_risk(row)
    result2=predict_delay_risk(row)
    assert 0<=result1["delay_probability_3m"]<=1
    assert result1["risk_level"] in {"LOW","MEDIUM","HIGH","CRITICAL"}
    assert result1["delay_probability_3m"]==result2["delay_probability_3m"]
    bundle=joblib.load(MODEL_DIR/"delay_3m_model_bundle_v1.joblib")
    assert bundle.model_version=="delay_3m_v1"
