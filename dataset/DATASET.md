# YouTube Reasoning Prompt Dataset — Dataset Card

## 1. Dataset Summary
This dataset is a structured benchmark for evaluating multi-step reasoning abilities of LLMs using YouTube videos.
Each video folder includes:
- Structured transcript
- Reasoning prompts
- Golden answers
- Model outputs
- Evaluation scores
- Metadata

## 2. Data Structure
dataset/<video_id>/
│── transcript.json
│── prompts.json
│── golden_answers.jsonl
│── model_outputs.jsonl
│── results.csv
│── metadata.json

## 3. Included Fields
- transcript.json → transcript + metadata
- prompts.json → prompts + guidance
- golden_answers.jsonl → correct reference answers
- model_outputs.jsonl → all model-generated answers
- results.csv → scores
- metadata.json → video metadata

## 4. License
MIT for code, CC-BY 4.0 for dataset.
