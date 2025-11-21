import sys
from pathlib import Path

# Add project root to PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import streamlit as st
from pathlib import Path
import pandas as pd

from src.collectors.yt_dlp_collector import YTDLPTranscriptCollector
from src.generation.golden_answer_generator import generate_golden_answers
from src.evaluation.evaluator import evaluate_video
from src.dataset.build_dataset import build_dataset

DATASET_ROOT = Path("dataset")
DATASET_ROOT.mkdir(exist_ok=True)

st.set_page_config(page_title="YouTube Reasoning Dataset", layout="wide")
st.title("📊 YouTube Reasoning Dataset Builder & Viewer")


# ------------------------------------------------------------
# Sidebar — List existing datasets
# ------------------------------------------------------------
st.sidebar.header("📁 Existing Datasets")

existing = [p.name for p in DATASET_ROOT.iterdir() if p.is_dir()]
selected_dataset = st.sidebar.selectbox("Select a Dataset", ["-- Select --"] + existing)


# ------------------------------------------------------------
# Main Panel: Dataset Generator
# ------------------------------------------------------------
st.header("🎬 Generate a Dataset from YouTube URL")

yt_url = st.text_input("Enter YouTube Video URL:")
generate_btn = st.button("🚀 Generate Dataset")


if generate_btn:
    if not yt_url.strip():
        st.error("Please enter a YouTube URL.")
    else:
        with st.spinner("Collecting transcript..."):
            collector = YTDLPTranscriptCollector("data/raw")
            vid = collector.extract_video_id(yt_url)
            collector.collect(yt_url)

        with st.spinner("Generating prompts..."):
            import subprocess
            subprocess.run([
                "python", "-m", "src.cli", "--gen-prompts", vid, "--gen-model", "gemini-2.5-flash"
            ])

        with st.spinner("Generating golden answers..."):
            generate_golden_answers(vid)

        with st.spinner("Evaluating model responses..."):
            evaluate_video(vid, model="gemini-2.5-flash", max_attempts=3)

        with st.spinner("Packaging dataset..."):
            build_dataset(vid)

        st.success(f"Dataset built successfully for video: {vid}")
        st.balloons()


# ------------------------------------------------------------
# Display Dataset
# ------------------------------------------------------------
if selected_dataset != "-- Select --":
    vpath = DATASET_ROOT / selected_dataset

    st.header(f"📂 Dataset: {selected_dataset}")

    # ------- Transcript -------
    st.subheader("📜 Transcript")
    st.json(json.loads((vpath / "transcript.json").read_text()))

    # ------- Prompts -------
    st.subheader("💡 Prompts")
    st.json(json.loads((vpath / "prompts.json").read_text()))

    # ------- Golden Answers -------
    st.subheader("🏆 Golden Answers")
    if (vpath / "golden_answers.jsonl").exists():
        ga = [json.loads(l) for l in open(vpath / "golden_answers.jsonl")]
        st.json(ga)
    else:
        st.warning("No golden answers found.")

    # ------- Model Outputs -------
    st.subheader("🤖 Model Outputs")
    if (vpath / "responses.jsonl").exists():
        mo = [json.loads(l) for l in open(vpath / "responses.jsonl")]
        st.json(mo)
    else:
        st.warning("No model outputs found.")

    # ------- Scores -------
    st.subheader("📊 Scores")
    if (vpath / "scores.csv").exists():
        df = pd.read_csv(vpath / "scores.csv")
        st.dataframe(df)
    else:
        st.warning("No score file found.")
