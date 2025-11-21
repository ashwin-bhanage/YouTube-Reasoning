# src/cli.py
import argparse
from src.collectors.yt_dlp_collector import YTDLPTranscriptCollector
from src.config import DATA_DIR, PROMPTS_DIR
from src.generation.golden_answer_generator import generate_golden_answers


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--collect-yt", type=str, help="Download transcript for a YouTube video")
    parser.add_argument("--gen-prompts", type=str, help="Generate reasoning prompts for a video ID or URL")
    parser.add_argument("--gen-model", type=str, default="models/text-bison-001", help="Gemini model to use")
    parser.add_argument("--gen-gold", type=str, help="Generate golden answers for a given video ID")

    args = parser.parse_args()

    # Phase 2: transcript collection
    if args.collect_yt:
        collector = YTDLPTranscriptCollector(DATA_DIR / "raw")
        save_path = collector.collect(args.collect_yt)
        print("Transcript saved at:", save_path)
        return

    # Phase 3: prompt generation
    if args.gen_prompts:
        from src.generation.prompt_generator import generate_prompts_for_video

        vid = args.gen_prompts

        # accept URL
        if "youtube.com" in vid or "youtu.be" in vid:
            vid = YTDLPTranscriptCollector(DATA_DIR / "raw").extract_video_id(vid)

        print("Generating prompts for:", vid)
        out = generate_prompts_for_video(vid, model=args.gen_model)
        print("Saved prompts to:", PROMPTS_DIR / f"{vid}.json")
        return

    if args.gen_gold:
        vid = args.gen_gold

    # accept full URL
        if "youtube.com" in vid or "youtu.be" in vid:
            from src.collectors.yt_dlp_collector import YTDLPTranscriptCollector
            vid = YTDLPTranscriptCollector(DATA_DIR / "raw").extract_video_id(vid)

        print(f"Generating golden answers for: {vid}")
        out = generate_golden_answers(vid, model=args.gen_model)
        print(f"Saved golden answers to: {out}")
        return

if __name__ == "__main__":
    main()
