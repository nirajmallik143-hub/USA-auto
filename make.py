"""Convenience launcher for a safe preview run in Pydroid 3."""

import os
from pathlib import Path
import sys


def main():
    os.chdir(Path(__file__).resolve().parent)
    os.environ["YOUTUBE_DRY_RUN"] = "true"
    sys.argv = [
        "src.cli",
        "generate-one",
        "--format",
        "shorts",
        "--preview",
    ]

    from src.cli import main as cli_main

    cli_main()


if __name__ == "__main__":
    main()
