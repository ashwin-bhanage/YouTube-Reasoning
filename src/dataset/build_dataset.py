# src/dataset/build_dataset.py

import json
import shutil
from pathlib import Path
from datetime import datetime

from src.config import DATA_DIR, PROMPTS_DIR, MODELS_OUTPUT_DIR

# Always use absolute project-level dataset directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "dataset"


def _assert_exists(path: Path, label: str):
    if not path.exists():
        raise FileNotFoundError(f"[ERROR] Missing {label}: {path}")
    print(f"[OK] Found {label}: {path}")


def build_dataset(video_id: str) -> Path:
    print(f"\n[BUILD DATASET] Packaging dataset for video: {video_id}")

    DATASET_ROOT.mkdir(exist_ok=True)
    out_dir = DATASET_ROOT / video_id
    out_dir.mkdir(exist_ok=True)

    # ------------------------------------------------------
    # Validate all required source files first
    # ------------------------------------------------------

    transcript_src = DATA_DIR / "raw" / f"{video_id}.json"
    prompts_src = PROMPTS_DIR / f"{video_id}.json"
    gold_src = PROMPTS_DIR / f"{video_id}_gold.jsonl"
    outputs_src = MODELS_OUTPUT_DIR / f"{video_id}_gemini.jsonl"
    scores_src = MODELS_OUTPUT_DIR / f"{video_id}_results.csv"

    _assert_exists(transcript_src, "transcript")
    _assert_exists(prompts_src, "prompts file")
    _assert_exists(gold_src, "golden answers file")
    _assert_exists(outputs_src, "model outputs")
    _assert_exists(scores_src, "results/scores")

    # ------------------------------------------------------
    # Copy files into dataset folder
    # ------------------------------------------------------

    shutil.copy(transcript_src, out_dir / "transcript.json")
    print("[COPIED] transcript.json")

    shutil.copy(prompts_src, out_dir / "prompts.json")
    print("[COPIED] prompts.json")

    shutil.copy(gold_src, out_dir / "golden_answers.jsonl")
    print("[COPIED] golden_answers.jsonl")

    shutil.copy(outputs_src, out_dir / "model_outputs.jsonl")
    print("[COPIED] model_outputs.jsonl")

    shutil.copy(scores_src, out_dir / "results.csv")
    print("[COPIED] results.csv")

    # ------------------------------------------------------
    # Update manifest.json safely
    # ------------------------------------------------------
    manifest_path = DATASET_ROOT / "manifest.json"

    # If file exists, load it
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
    else:
        manifest = {}

    # Ensure required fields exist
    if "videos" not in manifest or not isinstance(manifest["videos"], list):
        manifest["videos"] = []

    manifest["updated_at"] = datetime.utcnow().isoformat()

    # Add video if missing
    if video_id not in manifest["videos"]:
        manifest["videos"].append(video_id)

    # Save back
    manifest_path.write_text(json.dumps(manifest, indent=2))

    return out_dir


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True, help="Video ID to package dataset for")
    args = parser.parse_args()

    print(f"[RUN] Building dataset for: {args.video_id}")
    out = build_dataset(args.video_id)
    print(f"[DONE] Dataset created at: {out}")
