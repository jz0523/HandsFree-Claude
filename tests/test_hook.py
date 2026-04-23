# tests/test_hook.py
import io
import json

import pytest

from handsfree_claude import hook as hook_mod


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    from handsfree_claude import paths
    monkeypatch.setattr(paths, "base_dir", lambda: tmp_path)
    monkeypatch.setattr(paths, "state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(paths, "config_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr(paths, "log_path", lambda: tmp_path / "logs" / "audio.log")
    return tmp_path


def _run_with_stdin(payload: dict, monkeypatch) -> tuple[int, str]:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    captured = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured)
    rc = hook_mod.main()
    return rc, captured.getvalue()


def test_pretooluse_noop_when_state_missing(tmp_home, monkeypatch):
    rc, out = _run_with_stdin(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"}, monkeypatch
    )
    assert rc == 0
    assert out == ""


def test_pretooluse_noop_when_disabled(tmp_home, monkeypatch):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=False, pid=0)
    rc, out = _run_with_stdin(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"}, monkeypatch
    )
    assert rc == 0
    assert out == ""


def test_pretooluse_noop_when_pid_dead(tmp_home, monkeypatch, mocker):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=True, pid=99999)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=False)
    rc, out = _run_with_stdin(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"}, monkeypatch
    )
    assert rc == 0
    assert out == ""


def test_pretooluse_emits_allow_when_active(tmp_home, monkeypatch, mocker):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=True, pid=12345)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    rc, out = _run_with_stdin(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"}, monkeypatch
    )
    assert rc == 0
    data = json.loads(out)
    assert data["decision"] == "allow"
    assert "HandsFree" in data["reason"]


def test_stop_no_subprocess_when_disabled(tmp_home, monkeypatch, mocker):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=False, pid=0)
    spawn = mocker.patch("handsfree_claude.hook._spawn_audio_subprocess")
    rc, out = _run_with_stdin(
        {"hook_event_name": "Stop"}, monkeypatch
    )
    assert rc == 0
    assert spawn.call_count == 0


def test_stop_no_subprocess_when_muted(tmp_home, monkeypatch, mocker):
    from handsfree_claude import state as state_mod
    from handsfree_claude import config as config_mod
    state_mod.write(enabled=True, pid=12345)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    config_mod.save(config_mod.Config(mute_sound=True))
    spawn = mocker.patch("handsfree_claude.hook._spawn_audio_subprocess")
    rc, _ = _run_with_stdin({"hook_event_name": "Stop"}, monkeypatch)
    assert rc == 0
    assert spawn.call_count == 0


def test_stop_spawns_subprocess_when_active_and_unmuted(tmp_home, monkeypatch, mocker):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=True, pid=12345)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    # Pretend there's a playable sound file.
    fake_path = tmp_home / "sound.mp3"
    fake_path.write_bytes(b"fake")
    mocker.patch(
        "handsfree_claude.audio.effective_sound_path", return_value=fake_path
    )
    spawn = mocker.patch("handsfree_claude.hook._spawn_audio_subprocess")
    rc, _ = _run_with_stdin({"hook_event_name": "Stop"}, monkeypatch)
    assert rc == 0
    assert spawn.call_count == 1
    assert spawn.call_args[0][0] == fake_path


def test_unknown_event_is_noop(tmp_home, monkeypatch):
    rc, out = _run_with_stdin(
        {"hook_event_name": "Weird"}, monkeypatch
    )
    assert rc == 0
    assert out == ""


def test_malformed_stdin_is_noop(monkeypatch, tmp_home):
    monkeypatch.setattr("sys.stdin", io.StringIO("not-json"))
    captured = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured)
    rc = hook_mod.main()
    assert rc == 0
    assert captured.getvalue() == ""
