# YouTube Reasoning Prompt Dataset
A full pipeline: **transcript extraction → prompt generation → golden answers → evaluation → dataset packaging → Streamlit UI**
This project builds a complete reasoning dataset from YouTube videos using transcripts + Gemini-generated prompts, golden answers, model evaluations, and a Streamlit browser.

---

## 🚀 Features

### 1️⃣ Transcript Extraction (yt-dlp)
- Supports all subtitle formats: `vtt`, `srt`, `json3`, `srv1-3`, `ttml`, `xml`
- Parses into clean segments
- Extracts metadata: *title, channel, upload date, duration, views, tags…*

### 2️⃣ Prompt Generation (Gemini 2.5 Flash)
- Generates **3–5 multi-step reasoning prompts**
- Adds: domain, difficulty, guidance for golden answer

### 3️⃣ Golden Answer Generation
- Produces **high-quality ground-truth answers** for each prompt

### 4️⃣ Evaluation System
- Gemini 2.5 Flash answers each prompt
- Retry + self-correction logic
- Scores:
  1. reasoning depth
  2. factual accuracy
  3. coherence

### 5️⃣ Dataset Packaging
Folder structure:
```text
dataset/<VIDEO_ID>/
  transcript.json
  prompts.json
  golden_answers.jsonl
  model_outputs.jsonl
  results.csv
```

Also generates:
```
dataset/manifest.json
```

### 6️⃣ Streamlit Dataset Viewer
Interactive UI displays:
```text
transcripts
prompts
golden answers
evaluated model responses
scoring tables
```

---

## 📂 Project Structure
```text
youtube-reasoning-prompt-dataset/
├─ data/raw/
├─ prompts/
├─ models_outputs/
├─ dataset/
│   └─ manifest.json
├─ streamlit_app/
│   └─ app.py
├─ src/
│   ├─ collectors/
│   │   └─ yt_dlp_collector.py
│   ├─ generation/
│   │   ├─ prompt_generator.py
│   │   └─ golden_answer_generator.py
│   ├─ evaluation/
│   │   └─ evaluator.py
│   ├─ dataset/
│   │   └─ build_dataset.py
│   ├─ cli.py
│   └─ config.py
└─ README.md
```

---

## 🛠️ Installation

Clone repo:
```bash
git clone https://github.com/YOUR_USERNAME/youtube-reasoning-prompt-dataset.git
cd youtube-reasoning-prompt-dataset
```

Create virtual environment:
```bash
python -m venv vir
vir\Scripts\activate      # Windows
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Set your Gemini API key — create `.env`:
```bash
GOOGLE_API_KEY=your_api_key_here
```

---

## 📌 Usage Guide

### Phase 1 — Transcript Collection
```bash
python -m src.cli --collect-yt https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Phase 2 — Prompt Generation
```bash
python -m src.cli --gen-prompts dQw4w9WgXcQ --gen-model gemini-2.5-flash
```

### Phase 3 — Generate Golden Answers
```bash
python -m src.generation.golden_answer_generator --video-id dQw4w9WgXcQ
```

### Phase 4 — Evaluate Prompt Responses
```bash
python -m src.evaluation.evaluator --video-id dQw4w9WgXcQ --model gemini-2.5-flash --max-attempts 3
```

### Phase 5 — Build Final Dataset
```bash
python -m src.dataset.build_dataset --video-id dQw4w9WgXcQ
```

---

## 🎨 Streamlit Viewer

Run locally:
```bash
streamlit run streamlit_app/app.py
```

This will show:
- transcript
- prompts
- golden answers
- model outputs
- scoring metrics

---

## 🌐 Deployment (Streamlit Cloud)

1. Push repo to GitHub
2. Visit: https://share.streamlit.io
3. Select your repository
4. Set entrypoint:
   ```bash
   streamlit_app/app.py
   ```
5. Add env variable:
   ```bash
   GOOGLE_API_KEY
   ```

Your Streamlit dataset viewer deploys instantly.

---

## 📦 Example Dataset
```text
dataset/<VIDEO_ID>/
```
