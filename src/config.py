# src/config.py
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()  # loads .env into env

ROOT = Path(__file__).resolve().parents[1]  # project root
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROMPTS_DIR = ROOT / "prompts"
MODELS_OUTPUT_DIR = ROOT / "models_outputs"
NOTEBOOKS_DIR = ROOT / "notebooks"

# ensure directories exist
for p in (DATA_DIR, RAW_DIR, PROMPTS_DIR, MODELS_OUTPUT_DIR, NOTEBOOKS_DIR):
    p.mkdir(parents=True, exist_ok=True)

# Keys (read from environment)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_GENAI_KEY") or ""
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY") or ""

# Other constants
DEFAULT_GEMINI_MODEL = os.getenv("DEFAULT_GEMINI_MODEL", "gemini-2.5-flash")
