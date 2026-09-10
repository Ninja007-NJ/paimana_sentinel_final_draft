from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ML_ROOT = ROOT / "ml"
DATASET = ROOT / "paimana_dataset_v3" / "training_delay_3m.csv"
RAW_DATASET = ROOT / "paimana_dataset_v3" / "raw_snapshots_clean.csv"
IDENTITY_AUDIT = ROOT / "paimana_dataset_v3" / "identity_audit.csv"
ARTIFACTS = ML_ROOT / "artifacts"
MODEL_DIR = ARTIFACTS / "models"
REPORT_DIR = ARTIFACTS / "reports"
PLOT_DIR = ARTIFACTS / "plots"
PREDICTION_DIR = ARTIFACTS / "predictions"

TARGET = "delay_event_next_3m"
DATASET_VERSION = "paimana_dataset_v1.0"
MODEL_VERSION = "delay_3m_v1"
RANDOM_SEED = 26103
QUALITY_THRESHOLD = 80

TRAIN_START, TRAIN_END = "2025-01", "2025-08"
VALID_START, VALID_END = "2025-09", "2025-11"
TEST_START, TEST_END = "2025-12", "2026-01"

for directory in (MODEL_DIR, REPORT_DIR, PLOT_DIR, PREDICTION_DIR):
    directory.mkdir(parents=True, exist_ok=True)
