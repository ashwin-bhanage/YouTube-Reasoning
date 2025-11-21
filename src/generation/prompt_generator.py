"""
Prompt generator using Google Gemini (google.generativeai).
Generates 3-5 multi-step reasoning prompts per video and writes JSON file to prompts/.
"""

import json
import re
from pathlib import Path
from typing import List, Dict
from datetime import datetime

import google.generativeai as genai
from src.config import PROMPTS_DIR, DATA_DIR, GOOGLE_API_KEY

# initialize Gemini
genai.configure(api_key=GOOGLE_API_KEY)


def _load_transcript(video_id: str) -> Dict:
    path = DATA_DIR / "raw" / f"{video_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Transcript not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_headlines_and_keywords(transcript_obj, top_n=8):
    """
    Lightweight keyword extractor using frequency (no sklearn).
    """
    text = " ".join(
        seg["text"] if isinstance(seg, dict) else str(seg)
        for seg in transcript_obj.get("transcript", [])
    ).lower()

    stopwords = {
        "the","and","to","a","of","in","that","is","it","you","i","we","this","for","on","are",
        "be","with","as","was","have","but","not","your","from","they","their","our","will"
    }

    words = re.findall(r"[a-z]{3,}", text)
    freq = {}
    for w in words:
        if w in stopwords:
            continue
        freq[w] = freq.get(w, 0) + 1

    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]


def _craft_system_prompt(title: str, channel: str, keywords: List[str]) -> str:
    keywords_str = ", ".join(keywords)
    return f"""
You are a dataset-generation assistant. Produce 3 to 5 reasoning-heavy prompts based on a YouTube video.

Video title: "{title}"
Channel: "{channel}"
Themes/keywords: {keywords_str}

Rules:
- Return ONLY a JSON array.
- Each item must include: prompt_id, prompt, domain (tech|education|psychology|science|general), difficulty (easy|medium|hard), and golden_answer_guidance.
- Prompts must require multi-step reasoning (comparison, inference, causal reasoning, synthesis, critique).
- Avoid simple recall or fact listing.
- Prompts must be 1–2 sentences.
- Golden guidance must be 1–2 sentences describing what a correct answer must include.
- No repeated phrasing.
"""


def generate_prompts_for_video(video_id: str, n_prompts_hint: int = 4, model: str = "gemini-2.5-flash") -> Dict:
    transcript_obj = _load_transcript(video_id)
    title = transcript_obj.get("title", video_id)
    channel = transcript_obj.get("channel", "unknown")
    keywords = _extract_headlines_and_keywords(transcript_obj)

    system_instruction = _craft_system_prompt(title, channel, keywords)

    # excerpt to ground model
    excerpt = " ".join(
        seg.get("text", "") if isinstance(seg, dict) else str(seg)
        for seg in transcript_obj.get("transcript", [])[:6]
    ).strip()

    user_section = (
        f"Context excerpt (~6 segments): \"{excerpt[:600]}\"\n\n"
        f"Generate {n_prompts_hint} prompts following the rules."
    )

    full_prompt = f"""
[INSTRUCTION]
{system_instruction}

[CONTEXT]
{user_section}

Return ONLY the JSON array.
"""

    gemini_model = genai.GenerativeModel(model)

    response = gemini_model.generate_content([
        {
            "role": "user",
            "parts": [{"text": full_prompt}]
        }
    ])

    raw_text = response.text

    # extract JSON array
    m = re.search(r"(\[.*\])", raw_text, flags=re.DOTALL)
    if not m:
        raise ValueError("Gemini did not return JSON array. Raw response:\n" + raw_text[:1500])

    prompts = json.loads(m.group(1))

    # normalize prompts
    for i, p in enumerate(prompts, start=1):
        p.setdefault("prompt_id", f"{video_id}_prompt_{i}")
        p["prompt"] = p["prompt"].strip()
        p.setdefault("domain", "general")
        p.setdefault("difficulty", "medium")
        p["generated_at"] = datetime.utcnow().isoformat()
        p["generator_model"] = model

    # save
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    out = {
        "video_id": video_id,
        "title": title,
        "channel": channel,
        "keywords": keywords,
        "prompts": prompts,
        "generated_at": datetime.utcnow().isoformat(),
        "generator": {"provider": "gemini", "model": model},
    }

    out_path = PROMPTS_DIR / f"{video_id}.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")

    return out
