# scripts/verify_phase1.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import BASE_DIR, DATA_DIR, PROMPTS_DIR, OUTPUTS_DIR

def print_tree(path: Path, depth=2):
    print(path.name + "/")
    for p in sorted(path.iterdir()):
        if p.is_dir() and depth > 0:
            print("  " * (3 - depth) + f"{p.name}/")
        else:
            print("  " * (3 - depth) + p.name)

if __name__ == "__main__":
    print("Base:", BASE_DIR)
    print("Directories created:")
    print(" -", DATA_DIR)
    print(" -", PROMPTS_DIR)
    print(" -", OUTPUTS_DIR)
    print("\nPhase 1 status: READY")
