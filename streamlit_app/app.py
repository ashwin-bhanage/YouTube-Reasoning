import json
import streamlit as st
from pathlib import Path
import pandas as pd

# Base dataset location (must exist in your GitHub repo)
BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = BASE_DIR / "dataset"

def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

st.title("📊 YouTube Reasoning Prompt Dataset Viewer")

# Detect all packaged dataset folders
videos = sorted([p.name for p in DATASET_DIR.iterdir() if p.is_dir()])

if not videos:
    st.error("❌ No dataset found inside /dataset/. Upload a dataset folder.")
    st.stop()

video_id = st.selectbox("Select a video dataset:", videos)
vdir = DATASET_DIR / video_id

# --- Transcript ---
st.header("🎬 Transcript")
tpath = vdir / "transcript.json"
if tpath.exists():
    st.json(load_json(tpath))
else:
    st.warning("Transcript not found.")

# --- Prompts ---
st.header("🧠 Prompts")
ppath = vdir / "prompts.json"
if ppath.exists():
    st.json(load_json(ppath))
else:
    st.warning("Prompts not found.")

# --- Golden Answers ---
st.header("🏅 Golden Answers")
gpath = vdir / "golden_answers.jsonl"
if gpath.exists():
    st.json(load_jsonl(gpath))
else:
    st.warning("Golden answers not found.")

# --- Model Outputs ---
st.header("🤖 Model Outputs (Gemini)")
mpath = vdir / "model_outputs.jsonl"
if mpath.exists():
    st.json(load_jsonl(mpath))
else:
    st.warning("Model outputs not found.")

# --- Scores ---
st.header("📈 Evaluation Scores")
rpath = vdir / "results.csv"
if rpath.exists():
    df = pd.read_csv(rpath)
    st.dataframe(df)
else:
    st.warning("Scores file not found.")
