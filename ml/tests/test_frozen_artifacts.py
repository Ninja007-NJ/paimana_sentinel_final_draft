import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_frozen_dataset_and_primary_model_hashes_are_unchanged():
    manifest = json.loads((ROOT / "ml" / "artifacts" / "frozen_artifacts.json").read_text(encoding="utf-8"))
    paths = {
        "raw_snapshots_clean.csv": ROOT / "paimana_dataset_v3" / "raw_snapshots_clean.csv",
        "training_master.csv": ROOT / "paimana_dataset_v3" / "training_master.csv",
        "training_delay_3m.csv": ROOT / "paimana_dataset_v3" / "training_delay_3m.csv",
        "delay_3m_v1_1_bundle.joblib": ROOT / "ml" / "artifacts" / "models" / "delay_3m_v1_1_bundle.joblib",
        "delay_6m_model_bundle_v1.joblib": ROOT / "ml" / "artifacts" / "models" / "delay_6m_model_bundle_v1.joblib",
    }
    assert manifest["dataset_version"] == "paimana_dataset_v1.0"
    assert {name: sha256(path) for name, path in paths.items()} == {
        name: manifest[name] for name in paths
    }
