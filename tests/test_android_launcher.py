import os
import sys
from types import ModuleType, SimpleNamespace

import make
import pytest


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
    preflight = ModuleType("src.preflight")
    preflight.check_ffmpeg = lambda: SimpleNamespace(ok=True)
    monkeypatch.setitem(sys.modules, "src.cli", cli)
    monkeypatch.setitem(sys.modules, "src.preflight", preflight)
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


def test_launcher_exits_with_ffmpeg_guidance(monkeypatch, tmp_path, capsys):
    launcher_root = tmp_path / "project"
    launcher_root.mkdir()
    launcher = launcher_root / "make.py"
    launcher.touch()
    preflight = ModuleType("src.preflight")
    preflight.check_ffmpeg = lambda: SimpleNamespace(
        ok=False, message="ffmpeg is unavailable"
    )
    monkeypatch.setitem(sys.modules, "src.preflight", preflight)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("YOUTUBE_DRY_RUN", "false")
    monkeypatch.setattr(make, "__file__", str(launcher))

    with pytest.raises(SystemExit) as error:
        make.main()

    assert error.value.code == 1
    message = capsys.readouterr().out
    assert "ffmpeg is unavailable" in message
    assert "FFMPEG_BINARY" in message
