import streamlit as st
from pathlib import Path
import json
import pandas as pd

# ---- Pipeline imports ----
from src.collectors.yt_dlp_collector import YTDLPTranscriptCollector
from src.generation.prompt_generator import generate_prompts_for_video
from src.generation.golden_answer_generator import generate_golden_answers
from src.evaluation.evaluator import evaluate_video
from src.dataset.build_dataset import build_dataset

DATASET_DIR = Path("dataset")
DATA_DIR = Path("data/raw")

st.set_page_config(page_title="YouTube Reasoning Dataset", layout="wide")
st.title("🎬 YouTube Reasoning Dataset Builder & Viewer")

# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def extract_video_id(url: str) -> str:
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return url.strip()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ---------------------------------------------------------
# Sidebar – build section
# ---------------------------------------------------------
st.sidebar.header("🛠 Build Dataset")

yt_url = st.sidebar.text_input("Enter YouTube URL")

if st.sidebar.button("Generate Dataset"):

    if not yt_url.strip():
        st.sidebar.error("Enter a valid YouTube link")
        st.stop()

    vid = extract_video_id(yt_url)
    st.sidebar.info(f"Video ID detected: **{vid}**")

    # ==== Phase 1: Transcript ====
    st.write("📥 **Collecting transcript...**")
    try:
        collector = YTDLPTranscriptCollector(DATA_DIR)
        collector.collect(yt_url)
        st.success("Transcript collected.")
    except Exception as e:
        st.error(f"Transcript failed: {e}")
        st.stop()

    # ==== Phase 2: Prompts ====
    st.write("🧩 **Generating prompts...**")
    try:
        generate_prompts_for_video(vid, model="gemini-2.5-flash")
        st.success("Prompts generated.")
    except Exception as e:
        st.error(f"Prompt generation failed: {e}")
        st.stop()

    # ==== Phase 3: Golden answers ====
    st.write("🏆 **Generating golden answers...**")
    try:
        generate_golden_answers(vid)
        st.success("Golden answers generated.")
    except Exception as e:
        st.error(f"Golden answer generation failed: {e}")
        st.stop()

    # ==== Phase 4: Evaluation ====
    st.write("🤖 **Evaluating model responses...**")
    try:
        evaluate_video(vid)
        st.success("Evaluation complete.")
    except Exception as e:
        st.error(f"Evaluation failed: {e}")
        st.stop()

    # ==== Phase 5: Build dataset ====
    st.write("📦 **Packaging dataset...**")
    try:
        build_dataset(vid)
        st.success(f"Dataset packaged under `dataset/{vid}`")
    except Exception as e:
        st.error(f"Dataset build failed: {e}")
        st.stop()

    st.success("🎉 All steps completed successfully!")


# ---------------------------------------------------------
# Dataset Viewer
# ---------------------------------------------------------

st.header("📂 Browse Existing Datasets")

datasets = [p.name for p in DATASET_DIR.iterdir() if p.is_dir()]
if not datasets:
    st.info("No datasets found yet. Generate one from the sidebar.")
    st.stop()

selected = st.selectbox("Choose a dataset", datasets)

vpath = DATASET_DIR / selected

st.subheader("📜 Transcript")
st.json(load_json(vpath / "transcript.json"))

st.subheader("🧩 Prompts")
st.json(load_json(vpath / "prompts.json"))

st.subheader("🏆 Golden Answers")
ga_path = vpath / "golden_answers.jsonl"
if ga_path.exists():
    ga = [json.loads(l) for l in open(ga_path, "r", encoding="utf-8")]
    st.json(ga)
else:
    st.warning("No golden answers found.")

st.subheader("🤖 Model Outputs")
mo_path = vpath / "model_outputs.jsonl"
if mo_path.exists():
    mo = [json.loads(l) for l in open(mo_path, "r", encoding="utf-8")]
    st.json(mo)
else:
    st.warning("No model output file found.")

st.subheader("📊 Scores")
csv_path = vpath / "results.csv"
if csv_path.exists():
    df = pd.read_csv(csv_path)
    st.dataframe(df)
else:
    st.warning("No scoring file found.")
