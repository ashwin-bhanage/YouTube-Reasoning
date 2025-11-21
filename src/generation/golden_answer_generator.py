# src/generation/golden_answer_generator.py

import json
from pathlib import Path
from datetime import datetime
import google.generativeai as genai
from src.config import GOOGLE_API_KEY, PROMPTS_DIR

genai.configure(api_key=GOOGLE_API_KEY)

def _load_prompts(video_id: str):
    path = PROMPTS_DIR / f"{video_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"[ERROR] No prompts found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def _golden_prompt_template(prompt_text: str, guidance: str):
    return f"""
You are generating a **gold-standard reference answer** for a reasoning dataset.

PROMPT:
{prompt_text}

GUIDANCE:
{guidance}

Write a **concise, 3–6 sentence** answer that:
- follows the guidance exactly
- includes multi-step reasoning
- states causal relationships
- avoids fluff or emotional tone
- is deterministic and unambiguous
"""

def generate_golden_answers(video_id: str, model: str = "gemini-2.5-flash"):
    print(f"[INFO] Generating golden answers for: {video_id}")

    data = _load_prompts(video_id)
    prompts = data.get("prompts", [])

    if not prompts:
        raise RuntimeError("[ERROR] No prompts found inside the prompt file.")

    model_obj = genai.GenerativeModel(model)

    out_file = PROMPTS_DIR / f"{video_id}_gold.jsonl"
    golden_answers = []

    for item in prompts:
        pid = item.get("prompt_id")
        prompt_text = item.get("prompt")
        guidance = item.get("golden_answer_guidance", "")

        print(f"[INFO] Generating gold answer for prompt_id={pid}...")

        messages = [
            {
                "role": "user",
                "parts": [
                    {"text": _golden_prompt_template(prompt_text, guidance)}
                ]
            }
        ]

        try:
            resp = model_obj.generate_content(messages)
            answer = (resp.text or "").strip()

            if not answer:
                print(f"[WARN] Empty answer returned for prompt_id={pid}")
        except Exception as e:
            print(f"[ERROR] Gemini generation failed for prompt {pid}: {e}")
            answer = ""

        golden_answers.append({
            "prompt_id": pid,
            "prompt": prompt_text,
            "domain": item.get("domain", ""),
            "difficulty": item.get("difficulty", ""),
            "golden_answer": answer,
            "generated_at": datetime.utcnow().isoformat(),
            "model": model
        })

    # Write file
    out_file.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in golden_answers),
        encoding="utf-8"
    )

    print(f"[SUCCESS] Golden answers saved to: {out_file}")
    return out_file


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True)
    parser.add_argument("--model", default="gemini-2.5-flash")
    args = parser.parse_args()

    generate_golden_answers(args.video_id, model=args.model)
