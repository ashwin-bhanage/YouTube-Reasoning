# src/dataset/build_dataset.py
"""
Dataset Packager (Phase 5)
--------------------------

This script merges all artifacts for a single video ID into a final
dataset folder:

dataset/
  <video_id>/
    transcript.json
    prompts.json
    golden.jsonl
    responses.jsonl
    scores.csv
  manifest.json

Run:
    python -m src.dataset.build_dataset --video-id dQw4w9WgXcQ
"""

import json
import shutil
from pathlib import Path
import argparse

from src.config import DATA_DIR, PROMPTS_DIR, MODELS_OUTPUT_DIR


def load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_dataset(video_id: str):
    out_dir = Path("dataset") / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- FILE PATHS ----
    raw_path         = DATA_DIR / "raw" / f"{video_id}.json"
    prompts_path     = PROMPTS_DIR / f"{video_id}.json"
    gold_path        = PROMPTS_DIR / f"{video_id}_gold.jsonl"
    responses_path   = MODELS_OUTPUT_DIR / f"{video_id}_gemini.jsonl"
    scores_path      = MODELS_OUTPUT_DIR / f"{video_id}_results.csv"

    # ---- COPY RAW TRANSCRIPT ----
    if raw_path.exists():
        shutil.copy(raw_path, out_dir / "transcript.json")
    else:
        print(f"[WARN] Missing transcript: {raw_path}")

    # ---- COPY PROMPTS ----
    if prompts_path.exists():
        shutil.copy(prompts_path, out_dir / "prompts.json")
    else:
        print(f"[WARN] Missing prompts: {prompts_path}")

    # ---- COPY GOLDEN ANSWERS ----
    if gold_path.exists():
        shutil.copy(gold_path, out_dir / "gold.jsonl")
    else:
        print(f"[WARN] Missing golden answers: {gold_path}")

    # ---- COPY MODEL RESPONSES ----
    if responses_path.exists():
        shutil.copy(responses_path, out_dir / "responses.jsonl")
    else:
        print(f"[WARN] Missing responses: {responses_path}")

    # ---- COPY SCORES ----
    if scores_path.exists():
        shutil.copy(scores_path, out_dir / "scores.csv")
    else:
        print(f"[WARN] Missing scores: {scores_path}")

    # ---- UPDATE MANIFEST ----
    manifest_path = Path("dataset/manifest.json")
    manifest = {}

    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    manifest[video_id] = {
        "transcript": (out_dir / "transcript.json").exists(),
        "prompts":    (out_dir / "prompts.json").exists(),
        "gold":       (out_dir / "gold.jsonl").exists(),
        "responses":  (out_dir / "responses.jsonl").exists(),
        "scores":     (out_dir / "scores.csv").exists(),
    }

    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[OK] Dataset packaged at: {out_dir.resolve()}")
    print(f"[OK] Manifest updated at: {manifest_path.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True, help="Video ID to package")
    args = parser.parse_args()

    build_dataset(args.video_id)
