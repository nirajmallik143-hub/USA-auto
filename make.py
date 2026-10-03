"""Interactive Android/Pydroid launcher for a safe video preview."""

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ["YOUTUBE_DRY_RUN"] = "true"

from src.cli import main as run_cli
from src.config import VideoTopic


def choose(prompt, options, default):
    print(prompt)
    for number, option in enumerate(options, start=1):
        print(f"{number}. {option}")
    answer = input(f"Choose 1-{len(options)} (default {default}): ").strip()
    try:
        selection = int(answer)
        if 1 <= selection <= len(options):
            return options[selection - 1]
    except ValueError:
        pass
    return default


def main():
    video_format = choose("Video format:", ["shorts", "long"], "shorts")
    topics = [topic.value for topic in VideoTopic]
    topic = choose("Video topic:", topics, topics[0])
    sys.argv = [
        "make.py",
        "generate-one",
        "--format",
        video_format,
        "--topic",
        topic,
        "--preview",
    ]
    run_cli()


if __name__ == "__main__":
    main()
