import numpy as np
from ml.evaluation.metrics import classification_metrics
from ml.evaluation.thresholding import risk_level


def test_metrics_and_probability_bounds():
    probability=np.array([.1,.2,.8,.9]); metrics=classification_metrics([0,0,1,1],probability,.5)
    assert metrics["pr_auc"]==1.0
    assert np.all((probability>=0)&(probability<=1))


def test_risk_mapping():
    thresholds={"BALANCED":.3,"CONSERVATIVE":.5,"CRITICAL":.8}
    assert [risk_level(x,thresholds) for x in [.1,.4,.6,.9]]==["LOW","MEDIUM","HIGH","CRITICAL"]
