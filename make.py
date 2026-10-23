"""Convenience launcher for a safe preview run in Pydroid 3."""

import os
from pathlib import Path
import sys


def main():
    os.chdir(Path(__file__).resolve().parent)
    os.environ["YOUTUBE_DRY_RUN"] = "true"

    from src.preflight import check_ffmpeg

    ffmpeg = check_ffmpeg()
    if not ffmpeg.ok:
        print(
            f"❌ Cannot start preview: {ffmpeg.message}. "
            "On Pydroid 3, set FFMPEG_BINARY to an executable FFmpeg path."
        )
        raise SystemExit(1)

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
