import subprocess, sys

video = sys.argv[1]

def run(cmd):
    print("\n>>>", cmd)
    subprocess.run(cmd, shell=True, check=True)

run(f"python -m src.cli --collect-yt {video}")
run(f"python -m src.cli --gen-prompts {video}")
run(f"python -m src.generation.golden_answer_generator --video-id {video}")
run(f"python -m src.evaluation.evaluator --video-id {video}")
run(f"python -m src.dataset.build_dataset --video-id {video}")

print("\n[OK] Pipeline completed.")
