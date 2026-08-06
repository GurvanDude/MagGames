from pathlib import Path

CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"


def latest_run_dir() -> Path:
    runs = [d for d in CHECKPOINT_DIR.iterdir() if d.is_dir()] if CHECKPOINT_DIR.exists() else []
    if not runs:
        raise FileNotFoundError("aucun run trouve dans checkpoints/ - lance train.py d'abord")
    return max(runs, key=lambda d: d.stat().st_mtime)
