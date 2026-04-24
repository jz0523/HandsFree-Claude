# tests/test_cli.py
import json

import pytest

from handsfree_claude import cli as cli_mod


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    from handsfree_claude import paths
    monkeypatch.setattr(paths, "base_dir", lambda: tmp_path)
    monkeypatch.setattr(paths, "state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(paths, "config_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr(paths, "log_path", lambda: tmp_path / "logs" / "audio.log")
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    monkeypatch.setattr(paths, "claude_settings_path", lambda: claude_dir / "settings.json")
    # Force bare-name registration so tests don't depend on whether the hook
    # console script is currently installed on PATH in the test environment.
    monkeypatch.setattr(cli_mod, "_resolve_hook_command", lambda: cli_mod.HOOK_NAME)
    return tmp_path


def test_install_hooks_writes_both_events(tmp_home, capsys):
    rc = cli_mod.main(["install-hooks"])
    assert rc == 0
    from handsfree_claude import paths
    data = json.loads(paths.claude_settings_path().read_text(encoding="utf-8"))
    assert "PreToolUse" in data["hooks"]
    assert "Stop" in data["hooks"]
    for event in ("PreToolUse", "Stop"):
        cmds = [h["command"] for e in data["hooks"][event] for h in e["hooks"]]
        assert "handsfree-claude-hook" in cmds


def test_install_hooks_is_idempotent(tmp_home):
    cli_mod.main(["install-hooks"])
    cli_mod.main(["install-hooks"])
    from handsfree_claude import paths
    data = json.loads(paths.claude_settings_path().read_text(encoding="utf-8"))
    for event in ("PreToolUse", "Stop"):
        cmds = [h["command"] for e in data["hooks"][event] for h in e["hooks"]]
        assert cmds.count("handsfree-claude-hook") == 1


def test_uninstall_hooks_removes_both_events(tmp_home):
    cli_mod.main(["install-hooks"])
    rc = cli_mod.main(["uninstall-hooks"])
    assert rc == 0
    from handsfree_claude import paths
    data = json.loads(paths.claude_settings_path().read_text(encoding="utf-8"))
    for event in ("PreToolUse", "Stop"):
        cmds = [h["command"] for e in data["hooks"].get(event, []) for h in e["hooks"]]
        assert "handsfree-claude-hook" not in cmds


def test_status_reports_not_running_when_state_absent(tmp_home, capsys):
    rc = cli_mod.main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "not running" in out.lower()


def test_status_reports_running_when_pid_alive(tmp_home, capsys, mocker):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=True, pid=12345)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    rc = cli_mod.main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "running" in out.lower()
    assert "12345" in out


def test_status_reports_hooks_installed(tmp_home, capsys):
    cli_mod.main(["install-hooks"])
    rc = cli_mod.main(["status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "hooks installed" in out.lower()


def test_run_refuses_when_live_instance_exists(tmp_home, capsys, mocker):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=True, pid=12345)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    rc = cli_mod.main(["run"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "already running" in err.lower()
    assert "12345" in err


def test_no_args_defaults_to_run(tmp_home, mocker):
    # When no live instance exists, `run` would open a Tk window.
    # Mock the UI entry so the test doesn't actually open a window.
    ui_launch = mocker.patch("handsfree_claude.cli._launch_ui")
    rc = cli_mod.main([])
    assert rc == 0
    assert ui_launch.call_count == 1
