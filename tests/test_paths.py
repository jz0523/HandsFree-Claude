# tests/test_paths.py
from pathlib import Path

from handsfree_claude import paths


def test_base_dir_is_under_home():
    d = paths.base_dir()
    assert d.name == ".handsfree-claude"
    assert d.parent == Path.home()


def test_state_path_and_config_path():
    assert paths.state_path().name == "state.json"
    assert paths.state_path().parent == paths.base_dir()
    assert paths.config_path().name == "config.json"
    assert paths.config_path().parent == paths.base_dir()


def test_log_path():
    assert paths.log_path().name == "audio.log"
    assert paths.log_path().parent.name == "logs"
    assert paths.log_path().parent.parent == paths.base_dir()


def test_claude_settings_path():
    assert paths.claude_settings_path() == Path.home() / ".claude" / "settings.json"


def test_ensure_dirs_creates_base_and_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "base_dir", lambda: tmp_path / ".handsfree-claude")
    paths.ensure_dirs()
    assert (tmp_path / ".handsfree-claude").is_dir()
    assert (tmp_path / ".handsfree-claude" / "logs").is_dir()


def test_bundled_asset_returns_existing_path():
    # The default.mp3 asset is added in Task 10; until then, this test expects
    # that bundled_asset returns a Path object whose name matches the request,
    # even if the file does not yet exist.
    p = paths.bundled_asset("end_sounds/default.mp3")
    assert p.name == "default.mp3"
    assert p.parent.name == "end_sounds"
