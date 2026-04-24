# tests/test_config.py
import json

import pytest

from handsfree_claude import config as config_mod


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    target = tmp_path / "config.json"
    from handsfree_claude import paths
    monkeypatch.setattr(paths, "config_path", lambda: target)
    monkeypatch.setattr(paths, "base_dir", lambda: tmp_path)
    return target


def test_load_returns_defaults_when_file_missing(tmp_config):
    cfg = config_mod.load()
    assert cfg.end_sound_file == "default.mp3"
    assert cfg.custom_sound_path is None
    assert cfg.mute_sound is False
    assert cfg.window_position == (100, 100)


def test_load_returns_defaults_on_corrupt_json(tmp_config):
    tmp_config.write_text("{bad", encoding="utf-8")
    cfg = config_mod.load()
    assert cfg.end_sound_file == "default.mp3"


def test_save_and_reload_roundtrip(tmp_config):
    cfg = config_mod.Config(
        end_sound_file="chime.mp3",
        custom_sound_path="/tmp/custom.mp3",
        mute_sound=True,
        window_position=(250, 300),
    )
    config_mod.save(cfg)
    raw = json.loads(tmp_config.read_text(encoding="utf-8"))
    assert raw["end_sound_file"] == "chime.mp3"
    assert raw["custom_sound_path"] == "/tmp/custom.mp3"
    assert raw["mute_sound"] is True
    assert raw["window_position"] == [250, 300]

    cfg2 = config_mod.load()
    assert cfg2.end_sound_file == "chime.mp3"
    assert cfg2.custom_sound_path == "/tmp/custom.mp3"
    assert cfg2.mute_sound is True
    assert cfg2.window_position == (250, 300)


def test_load_tolerates_unknown_fields(tmp_config):
    tmp_config.write_text(
        json.dumps({"end_sound_file": "ding.mp3", "legacy_field": 123}),
        encoding="utf-8",
    )
    cfg = config_mod.load()
    assert cfg.end_sound_file == "ding.mp3"


def test_load_fills_missing_fields_with_defaults(tmp_config):
    tmp_config.write_text(
        json.dumps({"end_sound_file": "ding.mp3"}),
        encoding="utf-8",
    )
    cfg = config_mod.load()
    assert cfg.end_sound_file == "ding.mp3"
    assert cfg.mute_sound is False
    assert cfg.window_position == (100, 100)
