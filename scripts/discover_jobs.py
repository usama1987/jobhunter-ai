"""Run from project root: python -m scripts.discover_jobs"""
import argparse
from app.main import initialize
from app.discovery import run as run_remotive
from app.himalayas import run as run_himalayas

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--himalayas-pages", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.himalayas_pages <= 10:
        parser.error("--himalayas-pages must be 1-10")
    initialize()
    for name, func in (("Remotive", lambda: run_remotive()),
                       ("Himalayas", lambda: run_himalayas(pages=args.himalayas_pages))):
        try:
            print(name, func())
        except Exception as exc:
            print(f"{name} discovery failed: {type(exc).__name__}: {exc}")
