# src/dataset/build_dataset.py

import json
import shutil
from pathlib import Path
from datetime import datetime
from src.config import DATA_DIR, PROMPTS_DIR, MODELS_OUTPUT_DIR

DATASET_ROOT = Path("dataset")


def _safe_copy(src: Path, dest: Path):
    if src.exists():
        shutil.copy(src, dest)
    else:
        print(f"[WARN] Missing file: {src}")


def build_dataset(video_id: str):
    DATASET_ROOT.mkdir(exist_ok=True)
    out_dir = DATASET_ROOT / video_id
    out_dir.mkdir(exist_ok=True)

    # ---- TRANSCRIPT ----
    _safe_copy(
        DATA_DIR / "raw" / f"{video_id}.json",
        out_dir / "transcript.json"
    )

    # ---- PROMPTS ----
    _safe_copy(
        PROMPTS_DIR / f"{video_id}.json",
        out_dir / "prompts.json"
    )

    # ---- GOLDEN ANSWERS ----
    _safe_copy(
        PROMPTS_DIR / f"{video_id}_gold.jsonl",
        out_dir / "golden_answers.jsonl"
    )

    # ---- MODEL RESPONSES ----
    _safe_copy(
        MODELS_OUTPUT_DIR / f"{video_id}_gemini.jsonl",
        out_dir / "responses.jsonl"
    )

    # ---- SCORES CSV ----
    _safe_copy(
        MODELS_OUTPUT_DIR / f"{video_id}_results.csv",
        out_dir / "scores.csv"
    )

    # ---- Update manifest ----
    manifest_path = DATASET_ROOT / "manifest.json"

    # Load manifest if exists, otherwise create empty one
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {"updated_at": None, "videos": []}

    # Ensure the "videos" key exists
    if "videos" not in manifest:
        manifest["videos"] = []

    # Append video ID if new
    if video_id not in manifest["videos"]:
        manifest["videos"].append(video_id)

    # Update timestamp
    manifest["updated_at"] = datetime.utcnow().isoformat()

    # Save back
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"[OK] Dataset packaged at: {out_dir}")
    print(f"[OK] Manifest updated at: {manifest_path}")

    return out_dir
