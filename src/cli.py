# src/cli.py

import argparse
from src.collectors.yt_dlp_collector import YTDLPTranscriptCollector
from src.generation.prompt_generator import generate_prompts_for_video
from src.config import DATA_DIR, PROMPTS_DIR

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--collect-yt", type=str, help="Download transcript from YouTube URL")
    parser.add_argument("--gen-prompts", type=str, help="Generate reasoning prompts for video_id or URL")
    parser.add_argument("--gen-model", type=str, default="gemini-2.5-flash", help="Gemini model to use")

    args = parser.parse_args()

    # -------------------------
    # PHASE 1: TRANSCRIPT COLLECTION
    # -------------------------
    if args.collect_yt:
        collector = YTDLPTranscriptCollector(DATA_DIR / "raw")
        vid = args.collect_yt
        video_id = collector.extract_video_id(vid)
        print(f"[1] Collecting transcript for: {video_id}")
        collector.collect(vid)
        print("Saved transcript to:", DATA_DIR / "raw" / f"{video_id}.json")
        return

    # -------------------------
    # PHASE 2: PROMPT GENERATION
    # -------------------------
    if args.gen_prompts:
        vid = args.gen_prompts

        # Accept full URL or ID
        if "youtube.com" in vid or "youtu.be" in vid:
            vid = YTDLPTranscriptCollector(DATA_DIR / "raw").extract_video_id(vid)

        print("Generating prompts for:", vid)
        out = generate_prompts_for_video(vid, model=args.gen_model)
        print("Saved prompts to:", PROMPTS_DIR / f"{vid}.json")
        return


if __name__ == "__main__":
    main()
