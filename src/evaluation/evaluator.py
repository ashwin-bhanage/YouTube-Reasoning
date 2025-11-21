# src/evaluation/evaluator.py
"""
Gemini-only evaluator (Option 2: Full Evaluation Metadata)

Reads: prompts/<video_id>.json
Writes:
 - models_outputs/<video_id>_gemini.jsonl  (raw model outputs with metadata)
 - models_outputs/<video_id>_results.csv   (aggregated scores)

Behavior:
 - Uses google.generativeai (gemini-2.5-flash by default)
 - Retries up to `max_attempts` on short/invalid responses or API errors
 - On final retry issues a short self-correction instruction to the model
"""

import json
import time
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

import google.generativeai as genai
from src.config import PROMPTS_DIR, MODELS_OUTPUT_DIR, GOOGLE_API_KEY

# -----------------------
# Defaults / Tunables
# -----------------------
DEFAULT_MODEL = "gemini-2.5-flash"
SELF_CORRECT_PROMPT = (
    "Your previous answer was too short or missing logical steps. "
    "Please rewrite the answer as a concise paragraph (3-6 sentences) "
    "that includes clear multi-step reasoning and explicitly links claims to evidence."
)
MIN_TOKENS = 30                # very rough length check (words)
BACKOFF_BASE = 1.5             # exponential backoff base (seconds)
DEFAULT_MAX_ATTEMPTS = 3       # default max attempts (including original + retries)

# -----------------------
# Initialize Gemini
# -----------------------
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set in environment (.env).")
genai.configure(api_key=GOOGLE_API_KEY)


# -----------------------
# Utilities
# -----------------------
def _load_prompts(video_id: str) -> Dict[str, Any]:
    path = PROMPTS_DIR / f"{video_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Prompts file not found at: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_sleep(attempt: int, base: float = BACKOFF_BASE):
    # simple exponential backoff
    time.sleep(base ** max(0, attempt))


# -----------------------
# Gemini wrapper with retries + self-correction
# -----------------------
def call_gemini_once(prompt_text: str, model_name: str) -> str:
    """Single call to Gemini free API. Returns text (may be empty)."""
    model = genai.GenerativeModel(model_name)
    user_message = {"role": "user", "parts": [{"text": prompt_text}]}
    resp = model.generate_content([user_message])
    return getattr(resp, "text", "") or ""


def call_gemini_with_retries(
    prompt_text: str,
    model_name: str = DEFAULT_MODEL,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_tokens: int = MIN_TOKENS,
    pause_seconds: float = 0.6
) -> str:
    """
    Try model up to max_attempts. If replies are too short or placeholder-like,
    retry. After attempts, perform a self-correction call that asks the model to
    improve the previous response. Returns the final textual response.
    """
    raw_responses: List[str] = []
    last_exc: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            if attempt == 1:
                out = call_gemini_once(prompt_text, model_name)
            else:
                # include previous response to help refinement
                prev = raw_responses[-1] if raw_responses else ""
                refine_prompt = (
                    "Previous answer:\n"
                    f"{prev}\n\n"
                    "Please improve this answer. Provide a concise, well-structured paragraph "
                    "that directly answers the prompt below and includes explicit multi-step reasoning.\n\n"
                    "PROMPT:\n"
                    f"{prompt_text}\n\n"
                    "Return only the improved answer text."
                )
                out = call_gemini_once(refine_prompt, model_name)

            raw_responses.append(out or "")
            cleaned = (out or "").strip()
            length_ok = len(cleaned.split()) >= min_tokens
            not_placeholder = not any(token in cleaned.lower() for token in ["i'm not sure", "i do not know", "cannot determine", "no data", "unable to"])
            if length_ok and not_placeholder:
                return cleaned
            else:
                # too short or contains placeholder -> retry
                last_exc = ValueError("Response too short or placeholder")
        except Exception as e:
            last_exc = e

        # backoff before next attempt
        _safe_sleep(attempt)
        time.sleep(pause_seconds)

    # final self-correct attempt (stronger instruction)
    correction_prompt = (
        prompt_text
        + "\n\nSELF-CORRECTION INSTRUCTION: "
        + SELF_CORRECT_PROMPT
        + " Return only the corrected answer (no JSON or extra commentary)."
    )
    try:
        corrected = call_gemini_once(correction_prompt, model_name)
        corrected_clean = (corrected or "").strip()
        # accept even if shorter than min_tokens/2 as last resort
        if corrected_clean:
            return corrected_clean
        # if empty, return last raw response
        return raw_responses[-1] if raw_responses else ""
    except Exception:
        # raise the last exception if available, else return last response or empty
        if last_exc:
            raise last_exc
        return raw_responses[-1] if raw_responses else ""


# -----------------------
# Scoring heuristics (simple, noisy proxies)
# -----------------------
def score_reasoning_depth(output: str) -> int:
    if not output:
        return 1
    connectors = sum(output.lower().count(tok) for tok in ["because", "therefore", "thus", "hence", "so", "thereby", "inference", "imply"])
    sentences = max(1, len([s for s in output.split(".") if s.strip()]))
    score = 1 + min(4, connectors + (sentences - 1))
    return max(1, min(5, score))


def score_factual_accuracy(output: str, gold: str) -> int:
    if not output or not gold:
        return 3
    out_tokens = set([w.strip(".,;:()\"'").lower() for w in output.split() if len(w) > 3])
    gold_tokens = set([w.strip(".,;:()\"'").lower() for w in gold.split() if len(w) > 3])
    if not gold_tokens:
        return 3
    overlap = len(out_tokens & gold_tokens) / max(1, len(gold_tokens))
    if overlap > 0.6:
        return 5
    if overlap > 0.4:
        return 4
    if overlap > 0.25:
        return 3
    if overlap > 0.1:
        return 2
    return 1


def score_coherence(output: str) -> int:
    if not output:
        return 1
    sentences = [s.strip() for s in output.split(".") if s.strip()]
    words = output.split()
    if len(sentences) >= 3 and len(words) > 40:
        return 5
    if len(sentences) >= 2 and len(words) > 20:
        return 4
    if len(sentences) == 1 and len(words) > 10:
        return 3
    if len(words) > 5:
        return 2
    return 1


# -----------------------
# Main evaluation flow
# -----------------------
def evaluate_video(video_id: str, model: str = DEFAULT_MODEL, max_attempts: int = DEFAULT_MAX_ATTEMPTS) -> Path:
    prompts_obj = _load_prompts(video_id)
    prompts = prompts_obj.get("prompts", [])
    keywords = prompts_obj.get("keywords", [])

    MODELS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_out_path = MODELS_OUTPUT_DIR / f"{video_id}_gemini.jsonl"
    results_csv_path = MODELS_OUTPUT_DIR / f"{video_id}_results.csv"

    rows_for_csv: List[Dict[str, Any]] = []

    with raw_out_path.open("w", encoding="utf-8") as rawf:
        for item in prompts:
            pid = item.get("prompt_id")
            prompt_text = item.get("prompt", "")
            domain = item.get("domain", "")
            difficulty = item.get("difficulty", "")
            guide = item.get("golden_answer_guidance", "")

            # Build short context excerpt if transcript is present
            excerpt = ""
            if "transcript" in prompts_obj:
                excerpt = " ".join(
                    seg.get("text", "") if isinstance(seg, dict) else str(seg)
                    for seg in prompts_obj.get("transcript", [])[:6]
                )

            full_prompt = (
                f"Context excerpt: {excerpt}\n\n"
                f"Task prompt: {prompt_text}\n\n"
                f"Guidance (what golden answer should include): {guide}\n\n"
                "Provide a concise paragraph answer (3-6 sentences) that addresses the task with clear multi-step reasoning."
            )

            try:
                response_text = call_gemini_with_retries(full_prompt, model_name=model, max_attempts=max_attempts)
            except Exception as e:
                response_text = ""
                print(f"[WARN] Model call failed for prompt {pid}: {e}")

            # Write raw output line
            raw_record = {
                "video_id": video_id,
                "prompt_id": pid,
                "prompt": prompt_text,
                "domain": domain,
                "difficulty": difficulty,
                "model": model,
                "response": response_text,
                "keywords": keywords,
                "excerpt": (excerpt or "")[:1000],
                "generated_at": datetime.utcnow().isoformat()
            }
            rawf.write(json.dumps(raw_record, ensure_ascii=False) + "\n")

            # Load golden if present
            gold_answer = ""
            golds_path = PROMPTS_DIR / f"{video_id}_gold.jsonl"
            if golds_path.exists():
                with golds_path.open("r", encoding="utf-8") as gf:
                    for line in gf:
                        try:
                            row = json.loads(line)
                            if row.get("prompt_id") == pid:
                                gold_answer = row.get("golden_answer", "")
                                break
                        except Exception:
                            continue

            # Score with heuristics
            rd = score_reasoning_depth(response_text)
            fa = score_factual_accuracy(response_text, gold_answer)
            cc = score_coherence(response_text)

            rows_for_csv.append({
                "video_id": video_id,
                "prompt_id": pid,
                "model": model,
                "reasoning_depth": rd,
                "factual_accuracy": fa,
                "coherence": cc
            })

    # Save CSV
    with results_csv_path.open("w", newline="", encoding="utf-8") as cf:
        writer = csv.DictWriter(cf, fieldnames=["video_id", "prompt_id", "model", "reasoning_depth", "factual_accuracy", "coherence"])
        writer.writeheader()
        for r in rows_for_csv:
            writer.writerow(r)

    return results_csv_path


# -----------------------
# CLI
# -----------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--video-id", required=True, help="Video ID to evaluate")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Gemini model to use")
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS, help="Retry attempts")

    args = parser.parse_args()

    print(f"Evaluating video: {args.video_id} with model {args.model} ...")
    out = evaluate_video(
        args.video_id,
        model=args.model,
        max_attempts=args.max_attempts,
    )

    print("Done. Results CSV saved at:", out)
