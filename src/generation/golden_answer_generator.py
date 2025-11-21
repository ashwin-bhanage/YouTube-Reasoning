# src/generation/golden_answer_generator.py

import json
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from src.config import GOOGLE_API_KEY, PROMPTS_DIR, DATA_DIR

genai.configure(api_key=GOOGLE_API_KEY)


def _load_prompts(video_id: str):
    path = PROMPTS_DIR / f"{video_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"No prompts found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _golden_prompt_template(prompt_text: str, guidance: str):
    return f"""
You are generating a **gold-standard reference answer** for a reasoning evaluation dataset.

PROMPT:
{prompt_text}

GUIDANCE (what must be included):
{guidance}

Write a **concise, 3–6 sentence** answer that:
- follows the guidance exactly
- includes multi-step logical reasoning
- states clear causal relationships
- avoids fluff, vagueness, or emotional tone
- is deterministic and fact-based
- is suitable as a gold reference for LLM evaluation
"""


def generate_golden_answers(video_id: str, model: str = "gemini-2.5-flash"):
    data = _load_prompts(video_id)
    prompts = data["prompts"]

    model_obj = genai.GenerativeModel(model)

    golden_answers = []

    for item in prompts:
        p = item["prompt"]
        g = item.get("golden_answer_guidance", "")

        messages = [
            {"role": "user", "parts": _golden_prompt_template(p, g)}
        ]

        resp = model_obj.generate_content(messages)

        answer = resp.text.strip()

        golden_answers.append({
            "prompt_id": item["prompt_id"],
            "prompt": p,
            "domain": item["domain"],
            "difficulty": item["difficulty"],
            "golden_answer": answer,
            "generated_at": datetime.utcnow().isoformat(),
            "model": model
        })

    # Save as prompts/<video_id>_gold.jsonl
    out_path = PROMPTS_DIR / f"{video_id}_gold.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for row in golden_answers:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    return out_path
