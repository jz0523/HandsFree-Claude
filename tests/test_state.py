# tests/test_state.py
import json
import os
from pathlib import Path

import pytest

from handsfree_claude import state as state_mod


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    """Redirect paths.state_path() to a temp file."""
    target = tmp_path / "state.json"
    from handsfree_claude import paths
    monkeypatch.setattr(paths, "state_path", lambda: target)
    monkeypatch.setattr(paths, "base_dir", lambda: tmp_path)
    return target


def test_read_returns_disabled_when_file_missing(tmp_state):
    s = state_mod.read()
    assert s.enabled is False
    assert s.pid == 0


def test_read_returns_disabled_on_corrupt_json(tmp_state):
    tmp_state.write_text("{not-json", encoding="utf-8")
    s = state_mod.read()
    assert s.enabled is False
    assert s.pid == 0


def test_write_roundtrip(tmp_state):
    state_mod.write(enabled=True, pid=4242)
    raw = json.loads(tmp_state.read_text(encoding="utf-8"))
    assert raw == {"enabled": True, "pid": 4242}
    s = state_mod.read()
    assert s.enabled is True
    assert s.pid == 4242


def test_is_active_returns_false_when_disabled(tmp_state, mocker):
    state_mod.write(enabled=False, pid=os.getpid())
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    assert state_mod.is_active() is False


def test_is_active_returns_false_when_pid_dead(tmp_state, mocker):
    state_mod.write(enabled=True, pid=99999)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=False)
    assert state_mod.is_active() is False


def test_is_active_returns_true_when_enabled_and_alive(tmp_state, mocker):
    state_mod.write(enabled=True, pid=os.getpid())
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    assert state_mod.is_active() is True


def test_clear_writes_disabled(tmp_state):
    state_mod.write(enabled=True, pid=4242)
    state_mod.clear()
    s = state_mod.read()
    assert s.enabled is False
    assert s.pid == 0
