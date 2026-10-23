import os
import sys
from types import ModuleType

import make


def test_launcher_sets_project_directory_and_forces_preview(monkeypatch, tmp_path):
    launcher_root = tmp_path / "project"
    launcher_root.mkdir()
    launcher = launcher_root / "make.py"
    launcher.touch()
    cli = ModuleType("src.cli")
    observed = {}

    def run_cli():
        observed["cwd"] = os.getcwd()
        observed["dry_run"] = os.environ["YOUTUBE_DRY_RUN"]
        observed["argv"] = sys.argv[:]

    cli.main = run_cli
    monkeypatch.setitem(sys.modules, "src.cli", cli)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("YOUTUBE_DRY_RUN", "false")
    monkeypatch.setattr(make, "__file__", str(launcher))

    make.main()

    assert observed["cwd"] == str(launcher_root)
    assert observed["dry_run"] == "true"
    assert observed["argv"] == [
        "src.cli",
        "generate-one",
        "--format",
        "shorts",
        "--preview",
    ]
