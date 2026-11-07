"""Download the RCA Insurance Library 2-pack preview (clean PDFs + ground truth).

Licence: CC-BY-NC-4.0 (non-commercial). Fully synthetic documents.
Usage: python scripts/download_data.py [--force]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import RAW_DIR  # noqa: E402

REPO = "RootCauseAnalytics/Insurance-Library-Sample"
BASE = f"https://huggingface.co/datasets/{REPO}/resolve/main"
TREE = f"https://huggingface.co/api/datasets/{REPO}/tree/main"
META_FILES = ["README.md", "README_START_HERE.md", "ground_truth.csv", "ground_truth.jsonl", "bboxes.jsonl"]


def fetch(url: str, dest: Path, force: bool) -> None:
    if dest.exists() and not force:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r:
        dest.write_bytes(r.read())
    print(f"downloaded {dest.relative_to(RAW_DIR.parent.parent)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    for name in META_FILES:
        fetch(f"{BASE}/{name}", RAW_DIR / name, args.force)
    with urllib.request.urlopen(f"{TREE}/pdfs", timeout=60) as r:
        pdfs = [x["path"] for x in json.load(r) if x["path"].endswith(".pdf")]
    for path in pdfs:
        fetch(f"{BASE}/{path}", RAW_DIR / path, args.force)
    print(f"{len(pdfs)} PDFs in {RAW_DIR / 'pdfs'}")


if __name__ == "__main__":
    main()
