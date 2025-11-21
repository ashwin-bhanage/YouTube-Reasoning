import subprocess
from pathlib import Path
import sys

file = Path(sys.argv[1])
urls = [l.strip() for l in file.read_text().splitlines() if l.strip()]

for url in urls:
    print(f"\n=== Processing {url} ===")
    subprocess.run(f"python scripts/run_all.py {url}", shell=True, check=True)
