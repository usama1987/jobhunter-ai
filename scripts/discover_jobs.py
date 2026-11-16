"""Run from project root: python -m scripts.discover_jobs"""
from app.main import initialize
from app.discovery import run

if __name__ == "__main__":
    initialize()
    print(run())
