import pandas as pd

from ml.features.temporal_v1_1 import V1_1_FEATURES, build_temporal_features


def test_v1_1_features_at_t_ignore_future_changes(tmp_path):
    rows=[]
    for month,progress,expense,target in [
        ("2025-01",10,10,"2025-12-01"),("2025-02",12,15,"2025-12-01"),
        ("2025-03",15,22,"2026-01-01"),("2025-04",19,30,"2026-01-01"),
    ]:
        rows.append({"canonical_project_id":"P-1","snapshot_month":month,"sector":"Roads","current_target_doc":target,"current_forecast_cost_cr":100,"cumulative_expenditure_cr":expense,"physical_progress_pct":progress})
    first=tmp_path/"first.csv"; second=tmp_path/"second.csv"
    pd.DataFrame(rows).to_csv(first,index=False)
    changed=[dict(row) for row in rows]; changed[-1].update({"physical_progress_pct":99,"cumulative_expenditure_cr":99,"current_target_doc":"2030-01-01"})
    pd.DataFrame(changed).to_csv(second,index=False)
    a=build_temporal_features(first).query("snapshot_month == '2025-03'")[V1_1_FEATURES[:-2]].reset_index(drop=True)
    b=build_temporal_features(second).query("snapshot_month == '2025-03'")[V1_1_FEATURES[:-2]].reset_index(drop=True)
    pd.testing.assert_frame_equal(a,b)
