"""
streamlit_app/app.py
Robust Streamlit frontend to run the full YouTube Reasoning pipeline:
  1) transcript collection
  2) prompt generation
  3) golden answer generation
  4) evaluation
  5) dataset packaging
and to view previously built datasets.
"""

import sys
import os
from pathlib import Path
import json
import traceback

import streamlit as st
import pandas as pd

# ---------------------------------------------------------
# Ensure project root and src are importable (fixes ModuleNotFoundError on Streamlit)
# ---------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]  # repo root
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ---------------------------------------------------------
# Pipeline imports (wrapped to surface friendly errors in the UI)
# ---------------------------------------------------------
IMPORT_ERRORS = []
try:
    from src.collectors.yt_dlp_collector import YTDLPTranscriptCollector
except Exception as e:
    YTDLPTranscriptCollector = None
    IMPORT_ERRORS.append(("YTDLPTranscriptCollector", e, traceback.format_exc()))

try:
    from src.generation.prompt_generator import generate_prompts_for_video
except Exception as e:
    generate_prompts_for_video = None
    IMPORT_ERRORS.append(("generate_prompts_for_video", e, traceback.format_exc()))

try:
    from src.generation.golden_answer_generator import generate_golden_answers
except Exception as e:
    generate_golden_answers = None
    IMPORT_ERRORS.append(("generate_golden_answers", e, traceback.format_exc()))

try:
    from src.evaluation.evaluator import evaluate_video
except Exception as e:
    evaluate_video = None
    IMPORT_ERRORS.append(("evaluate_video", e, traceback.format_exc()))

try:
    from src.dataset.build_dataset import build_dataset
except Exception as e:
    build_dataset = None
    IMPORT_ERRORS.append(("build_dataset", e, traceback.format_exc()))

# ---------------------------------------------------------
# Paths
# ---------------------------------------------------------
DATA_DIR = ROOT / "data" / "raw"
DATASET_DIR = ROOT / "dataset"
PROMPTS_DIR = ROOT / "prompts"
MODELS_OUTPUT_DIR = ROOT / "models_outputs"

# ensure dataset dir exists
DATASET_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------
st.set_page_config(page_title="YouTube Reasoning Dataset", layout="wide")
st.title("🎬 YouTube Reasoning Dataset Builder & Viewer")

# show import problems if any
if IMPORT_ERRORS:
    with st.expander("⚠️ Import errors (click to inspect)"):
        for name, exc, tb in IMPORT_ERRORS:
            st.error(f"Module import failed: {name}")
            st.text(str(exc))
            st.code(tb)

st.sidebar.header("🛠 Build Dataset")
yt_url = st.sidebar.text_input("Enter YouTube URL or ID", value="")
selected_model = st.sidebar.selectbox("Generation model (Gemini)", ["gemini-2.5-flash"], index=0)
max_attempts = st.sidebar.number_input("Max attempts (per prompt)", value=3, min_value=1, max_value=10)

# helper: extract id
def extract_video_id(url: str) -> str:
    if not url:
        return ""
    u = url.strip()
    if "v=" in u:
        return u.split("v=")[1].split("&")[0]
    if "youtu.be/" in u:
        return u.split("youtu.be/")[1].split("?")[0]
    return u  # assume it's an id already

# helper: read json if exists
def load_json_safe(p: Path):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

# pipeline runner (ordered and defensive)
def run_pipeline(video_url_or_id: str, model_name: str = "gemini-2.5-flash", max_attempts_local: int = 3):
    vid = extract_video_id(video_url_or_id)
    if not vid:
        st.error("Could not extract a video id. Paste a valid YouTube URL or video id.")
        return None

    # Phase 1: transcript
    st.info("1/5 — Collecting transcript (yt-dlp)...")
    if YTDLPTranscriptCollector is None:
        st.error("Transcript collector not available (import error). See Import Errors.")
        return None

    try:
        collector = YTDLPTranscriptCollector(DATA_DIR)
        transcript_json_path = collector.collect(video_url_or_id)
        st.success(f"Transcript saved: {transcript_json_path}")
    except Exception as e:
        st.error(f"Transcript collection failed: {e}")
        st.exception(e)
        return None

    # Phase 2: prompts
    st.info("2/5 — Generating prompts...")
    if generate_prompts_for_video is None:
        st.error("Prompt generator not available (import error).")
        return None
    try:
        generate_prompts_for_video(vid, n_prompts_hint=4, model=model_name)
        st.success("Prompts generated.")
    except Exception as e:
        st.error(f"Prompt generation failed: {e}")
        st.exception(e)
        return None

    # Phase 3: golden answers
    st.info("3/5 — Generating golden answers...")
    if generate_golden_answers is None:
        st.error("Golden answer generator not available (import error).")
        return None
    try:
        generate_golden_answers(vid, model=model_name)
        st.success("Golden answers generated.")
    except Exception as e:
        st.error(f"Golden answer generation failed: {e}")
        st.exception(e)
        return None

    # Phase 4: evaluation
    st.info("4/5 — Evaluating prompts (model responses)...")
    if evaluate_video is None:
        st.error("Evaluator not available (import error).")
        return None
    try:
        # evaluator signature may accept (video_id, model, max_attempts) or (video_id,)
        # call defensively
        try:
            evaluate_video(vid, model=model_name, max_attempts=max_attempts_local)
        except TypeError:
            # older signature fallback
            evaluate_video(vid)
        st.success("Evaluation complete.")
    except Exception as e:
        st.error(f"Evaluation failed: {e}")
        st.exception(e)
        return None

    # Phase 5: build dataset
    st.info("5/5 — Packaging dataset...")
    if build_dataset is None:
        st.error("Dataset builder not available (import error).")
        return None
    try:
        out_dir = build_dataset(vid)
        st.success(f"Dataset packaged at: {out_dir}")
        return vid
    except Exception as e:
        st.error(f"Dataset build failed: {e}")
        st.exception(e)
        return None


# Run button
if st.sidebar.button("Generate Dataset"):
    if not yt_url:
        st.sidebar.error("Paste a YouTube link or ID first.")
    else:
        with st.spinner("Running full pipeline — this may take a while..."):
            vid_result = run_pipeline(yt_url, model_name=selected_model, max_attempts_local=int(max_attempts))
            if vid_result:
                st.balloons()

# ---------------------------------------------------------
# Dataset viewer
# ---------------------------------------------------------
st.header("📂 Browse Existing Datasets")
datasets = sorted([p.name for p in DATASET_DIR.iterdir() if p.is_dir()])

if not datasets:
    st.info("No datasets found. Use the sidebar to generate one.")
else:
    sel = st.selectbox("Select dataset", datasets)
    vpath = DATASET_DIR / sel

    st.subheader("Summary")
    meta = load_json_safe(vpath / "manifest.json") or {}
    st.write(f"Dataset: **{sel}**")
    if meta:
        st.json(meta)

    # Transcript
    st.subheader("Transcript")
    t = load_json_safe(vpath / "transcript.json")
    if t:
        st.json(t)
    else:
        st.warning("Transcript not found in dataset folder.")

    # Prompts
    st.subheader("Prompts")
    p = load_json_safe(vpath / "prompts.json")
    if p:
        st.json(p)
    else:
        st.warning("Prompts not found.")

    # Golden answers
    st.subheader("Golden Answers")
    ga_path = vpath / "golden_answers.jsonl"
    if ga_path.exists():
        ga = [json.loads(line) for line in ga_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        st.json(ga)
    else:
        st.warning("golden_answers.jsonl not found.")

    # Model outputs
    st.subheader("Model Outputs")
    mo_path = vpath / "model_outputs.jsonl"
    if mo_path.exists():
        mo = [json.loads(line) for line in mo_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        st.json(mo)
    else:
        st.warning("model_outputs.jsonl not found.")

    # Results CSV
    st.subheader("Scores / Results")
    scores_path = vpath / "results.csv"
    if scores_path.exists():
        df = pd.read_csv(scores_path)
        st.dataframe(df)
    else:
        st.warning("results.csv not found.")

# Footer
st.markdown("---")
st.markdown("Tip: on Streamlit Cloud add `GOOGLE_API_KEY` to App Secrets (Settings → Secrets) so Gemini calls work.")
