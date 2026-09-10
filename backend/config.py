import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)
load_dotenv(ROOT / "backend" / ".env", override=False)
def env_path(name: str, default: Path) -> Path:
    return Path(os.getenv(name, str(default))).expanduser().resolve()


MODEL_BUNDLE = env_path("PAIMANA_MODEL_BUNDLE", ROOT / "ml" / "artifacts" / "models" / "delay_3m_v1_1_bundle.joblib")
DELAY_6M_MODEL_BUNDLE = env_path("PAIMANA_DELAY_6M_MODEL_BUNDLE", ROOT / "ml" / "artifacts" / "models" / "delay_6m_model_bundle_v1.joblib")
TRAINING_DATA = env_path("PAIMANA_TRAINING_DATA", ROOT / "paimana_dataset_v3" / "training_delay_3m.csv")
TRAINING_MASTER = env_path("PAIMANA_TRAINING_MASTER", ROOT / "paimana_dataset_v3" / "training_master.csv")
RAW_SNAPSHOTS = env_path("PAIMANA_RAW_SNAPSHOTS", ROOT / "paimana_dataset_v3" / "raw_snapshots_clean.csv")
IDENTITY_AUDIT = env_path("PAIMANA_IDENTITY_AUDIT", ROOT / "paimana_dataset_v3" / "identity_audit.csv")
ALLOWED_ORIGINS = [
    item.strip()
    for item in os.getenv(
        "PAIMANA_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if item.strip()
]

MODEL_STATUS = "YELLOW"
DEFAULT_THRESHOLD_PROFILE = "BALANCED"
API_VERSION = "product_v1"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-4-26b-a4b-it:free").strip()
OPENROUTER_FALLBACK_MODELS = [
    item.strip()
    for item in os.getenv("OPENROUTER_FALLBACK_MODELS", "openrouter/free").split(",")
    if item.strip()
]
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "").strip()
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "PAIMANA Sentinel").strip()
OPENROUTER_TIMEOUT_SECONDS = max(3.0, min(float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "8")), 60.0))
