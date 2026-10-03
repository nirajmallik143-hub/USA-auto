"""
Write YouTube OAuth files from environment variables (GitHub Actions secrets).

Reads YOUTUBE_CLIENT_SECRETS_JSON and YOUTUBE_TOKEN_JSON, validates that each is JSON and writes
them to YOUTUBE_CLIENT_SECRETS_FILE / YOUTUBE_CREDENTIALS_FILE with owner-only permissions.
Secret contents are never printed.
"""

import json
import os
import sys
from pathlib import Path

TARGETS = (
    ("YOUTUBE_CLIENT_SECRETS_JSON", "YOUTUBE_CLIENT_SECRETS_FILE", "secrets/client_secrets.json"),
    ("YOUTUBE_TOKEN_JSON", "YOUTUBE_CREDENTIALS_FILE", "secrets/youtube_credentials.json"),
)


def write_credentials() -> int:
    errors = 0
    for content_var, path_var, default_path in TARGETS:
        raw = os.environ.get(content_var, "").strip()
        if not raw:
            print(f"::error::Secret {content_var} is empty or not set.")
            errors += 1
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"::error::Secret {content_var} is not valid JSON (line {e.lineno}, column {e.colno}).")
            errors += 1
            continue
        path = Path(os.environ.get(path_var) or default_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        path.chmod(0o600)
        print(f"Wrote {content_var} to {path}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(write_credentials())
