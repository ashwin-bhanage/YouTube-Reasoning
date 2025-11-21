import json
import streamlit as st
from pathlib import Path
import pandas as pd

DATASET_DIR = Path("dataset")

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

st.title("📊 YouTube Reasoning Dataset Viewer")

videos = [p.name for p in DATASET_DIR.iterdir() if p.is_dir()]
video_id = st.selectbox("Select video:", videos)

vpath = DATASET_DIR / video_id

st.header("Transcript")
st.json(load_json(vpath / "transcript.json"))

st.header("Prompts")
st.json(load_json(vpath / "prompts.json"))

st.header("Golden Answers")
ga = [json.loads(l) for l in open(vpath / "golden_answers.jsonl")]
st.json(ga)

st.header("Model Outputs")
mo = [json.loads(l) for l in open(vpath / "model_outputs.jsonl")]
st.json(mo)

st.header("Scores")
df = pd.read_csv(vpath / "results.csv")
st.dataframe(df)
