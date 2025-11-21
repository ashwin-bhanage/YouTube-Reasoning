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
from sklearn.feature_extraction.text import TfidfVectorizer

# initialize Gemini client
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
else:
    genai.configure(api_key=None)


def _load_transcript(video_id: str) -> Dict:
    path = DATA_DIR / "raw" / f"{video_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Transcript not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_headlines_and_keywords(transcript_obj, top_n=8):
    text = " ".join(
        seg["text"] if isinstance(seg, dict) else str(seg)
        for seg in transcript_obj.get("transcript", [])
    )
    return _extract_keywords_tfidf(text, top_n)


def _craft_system_prompt(title: str, channel: str, keywords: List[str]) -> str:
    """The ruleset that guides prompt creation."""
    keywords_str = ", ".join(keywords)
    return f"""
You are a dataset-generation assistant. Produce 3 to 5 reasoning-heavy prompts based on a YouTube video.

Video title: "{title}"
Channel: "{channel}"
Themes/keywords: {keywords_str}

Rules:
- Return ONLY a JSON array (no intro).
- Each item must include: prompt_id, prompt, domain (tech|education|psychology|science|general), difficulty (easy|medium|hard).
- Prompts: 1–2 sentences each, must force multi-step reasoning (comparison, inference, causal reasoning, synthesis, etc).
- No verbatim recall prompts.
- Avoid repeated phrasing; vary structure.
- Each prompt must include a 1–2 sentence "golden answer guidance" field explaining what the answer should contain.
"""


def generate_prompts_for_video(video_id: str, n_prompts_hint: int = 4, model: str = "gemini-2.5-flash") -> Dict:
    """Main generator function."""

    transcript_obj = _load_transcript(video_id)
    title = transcript_obj.get("title", video_id)
    channel = transcript_obj.get("channel", "unknown")
    keywords = _extract_headlines_and_keywords(transcript_obj, top_n=8)

    system_instruction = _craft_system_prompt(title, channel, keywords)

    # small excerpt to ground generation
    excerpt = ""
    for seg in transcript_obj.get("transcript", [])[:6]:
        if isinstance(seg, dict):
            excerpt += " " + seg.get("text", "")
        else:
            excerpt += " " + str(seg)
    excerpt = excerpt.strip()

    user_section = (
        f"Context excerpt (~6 segments): \"{excerpt[:600]}\"\n\n"
        f"Generate {n_prompts_hint} prompts following the rules strictly."
    )

    # Merge into one message (Gemini 2.x requires user/model roles only)
    full_prompt = f"""
[INSTRUCTION]
{system_instruction}

[CONTEXT]
{user_section}

Return ONLY the JSON array with no explanation.
"""

    gemini_model = genai.GenerativeModel(model)

    response = gemini_model.generate_content(
        [
            {
                "role": "user",
                "parts": [{"text": full_prompt}]
            }
        ]
    )

    raw_text = response.text

    # extract JSON array
    m = re.search(r"(\[.*\])", raw_text, flags=re.DOTALL)
    if not m:
        raise ValueError("Gemini did not return JSON array. Raw response:\n" + raw_text[:1500])

    json_text = m.group(1)
    prompts = json.loads(json_text)

    # Normalize
    for i, p in enumerate(prompts, start=1):
        p.setdefault("prompt_id", i)
        p["prompt"] = p["prompt"].strip()
        p.setdefault("domain", "general")
        p.setdefault("difficulty", "medium")
        p["generated_at"] = datetime.utcnow().isoformat()
        p["generator_model"] = model

    # Save file
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

def _extract_keywords_tfidf(text: str, top_n: int = 10):
    vectorizer = TfidfVectorizer(stop_words="english", max_features=2000)
    tfidf = vectorizer.fit_transform([text])
    scores = tfidf.toarray()[0]
    vocab = vectorizer.get_feature_names_out()
    top_ids = scores.argsort()[::-1][:top_n]
    return [vocab[i] for i in top_ids]
