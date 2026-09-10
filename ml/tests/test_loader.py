from ml.data.loader import load_delay_data
from ml.data.validation import validate_training_data


def test_loader_and_frozen_row_count():
    data=load_delay_data(); validate_training_data(data)
    assert len(data)==10368
    assert data.canonical_project_id.nunique()==2154
