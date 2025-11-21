# scripts/verify_phase2.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import RAW_DIR, PROMPTS_DIR
from src.collectors.yt_dlp_collector import YTDLPTranscriptCollector

def main():
    print("RAW_DIR:", RAW_DIR)
    print("PROMPTS_DIR:", PROMPTS_DIR)
    c = YTDLPTranscriptCollector(RAW_DIR)
    print("Collector class loaded:", c.__class__.__name__)

    # quick check: does yt-dlp exist on PATH?
    import shutil
    if not shutil.which("yt-dlp"):
        print("ERROR: yt-dlp not found on PATH. Install it (pip install yt-dlp or download binary).")
        sys.exit(2)

    # check sample files
    sample = list(RAW_DIR.glob("*.json"))
    print("Existing raw json transcripts:", len(sample))
    if sample:
        print("Sample transcript file:", sample[0].name)

    print("Basic checks passed. You can now run CLI commands.")

if __name__ == "__main__":
    main()
