# tests/test_settings_installer.py
import json

import pytest

from handsfree_claude.settings_installer import install_hook, uninstall_hook


@pytest.fixture
def settings_file(tmp_path):
    return tmp_path / "settings.json"


def test_install_creates_settings_file(settings_file):
    install_hook(settings_file, "handsfree-claude-hook", event_name="PreToolUse")
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    entries = data["hooks"]["PreToolUse"]
    assert len(entries) == 1
    assert entries[0]["matcher"] == "*"
    assert entries[0]["hooks"][0]["command"] == "handsfree-claude-hook"
    assert entries[0]["hooks"][0]["timeout"] == 15  # default


def test_install_is_idempotent(settings_file):
    install_hook(settings_file, "handsfree-claude-hook", event_name="PreToolUse")
    install_hook(settings_file, "handsfree-claude-hook", event_name="PreToolUse")
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert len(data["hooks"]["PreToolUse"]) == 1


def test_install_preserves_foreign_hooks(settings_file):
    settings_file.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [
                {"matcher": "*", "hooks": [{"type": "command", "command": "other-tool-hook", "timeout": 10}]}
            ]
        }
    }), encoding="utf-8")
    install_hook(settings_file, "handsfree-claude-hook", event_name="PreToolUse")
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    entries = data["hooks"]["PreToolUse"]
    commands = [h["command"] for e in entries for h in e["hooks"]]
    assert "other-tool-hook" in commands
    assert "handsfree-claude-hook" in commands


def test_install_supports_multiple_events(settings_file):
    install_hook(settings_file, "handsfree-claude-hook", event_name="PreToolUse", timeout_seconds=5)
    install_hook(settings_file, "handsfree-claude-hook", event_name="Stop", timeout_seconds=5)
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert data["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"] == 5
    assert data["hooks"]["Stop"][0]["hooks"][0]["timeout"] == 5


def test_uninstall_removes_only_our_hook(settings_file):
    settings_file.write_text(json.dumps({
        "hooks": {
            "PreToolUse": [
                {"matcher": "*", "hooks": [
                    {"type": "command", "command": "other-tool-hook", "timeout": 10},
                    {"type": "command", "command": "handsfree-claude-hook", "timeout": 5},
                ]}
            ]
        }
    }), encoding="utf-8")
    uninstall_hook(settings_file, "handsfree-claude-hook", event_name="PreToolUse")
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    commands = [h["command"] for e in data["hooks"]["PreToolUse"] for h in e["hooks"]]
    assert "handsfree-claude-hook" not in commands
    assert "other-tool-hook" in commands


def test_uninstall_missing_file_is_noop(tmp_path):
    uninstall_hook(tmp_path / "nonexistent.json", "handsfree-claude-hook")
    # No exception = pass
