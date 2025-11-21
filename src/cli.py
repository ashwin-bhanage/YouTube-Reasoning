# src/cli.py
import argparse
from src.config import BASE_DIR

def main():
    parser = argparse.ArgumentParser(description="YouTube Reasoning Prompt Dataset CLI")
    parser.add_argument("--verify", action="store_true", help="Run phase 1 verification")
    args = parser.parse_args()

    if args.verify:
        from scripts.verify_phase1 import print_tree
        print_tree(BASE_DIR)

if __name__ == "__main__":
    main()
