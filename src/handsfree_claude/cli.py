from __future__ import annotations

import argparse
import json
import shutil
import sys
from typing import Optional, Sequence

from handsfree_claude import paths, settings_installer, state as state_mod

HOOK_NAME = "handsfree-claude-hook"
HOOK_EVENTS = ("PreToolUse", "Stop")
HOOK_TIMEOUT_SECONDS = 5


def _resolve_hook_command() -> str:
    """Return the command string to register in Claude's settings.json.

    Prefer the absolute path to the installed console script so that Claude
    Code finds it regardless of the PATH its process inherits (on Windows,
    user-site Scripts directories are often not on system PATH)."""
    resolved = shutil.which(HOOK_NAME)
    return resolved if resolved else HOOK_NAME


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="handsfree-claude")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("run", help="Open the HandsFree Claude window")
    sub.add_parser("install-hooks", help="Register hooks in ~/.claude/settings.json")
    sub.add_parser("uninstall-hooks", help="Remove hooks from ~/.claude/settings.json")
    sub.add_parser("status", help="Show current window/hook status")

    args = parser.parse_args(argv)
    cmd = args.cmd or "run"

    if cmd == "run":
        return _cmd_run()
    if cmd == "install-hooks":
        return _cmd_install_hooks()
    if cmd == "uninstall-hooks":
        return _cmd_uninstall_hooks()
    if cmd == "status":
        return _cmd_status()
    parser.print_help()
    return 2


def _cmd_run() -> int:
    current = state_mod.read()
    if state_mod.is_active(current):
        print(
            f"HandsFree Claude is already running (PID {current.pid}).",
            file=sys.stderr,
        )
        return 1
    _launch_ui()
    return 0


def _launch_ui() -> None:
    from handsfree_claude import ui  # imported lazily so tests can mock this
    ui.run()


def _cmd_install_hooks() -> int:
    settings_path = paths.claude_settings_path()
    command = _resolve_hook_command()
    for event in HOOK_EVENTS:
        settings_installer.install_hook(
            settings_path,
            command,
            event_name=event,
            timeout_seconds=HOOK_TIMEOUT_SECONDS,
        )
    print(f"Installed hooks in {settings_path} (command: {command})")
    return 0


def _cmd_uninstall_hooks() -> int:
    settings_path = paths.claude_settings_path()
    # Remove both the bare name and the absolute-path form, so this works
    # whether hooks were installed by an older version of us or the current one.
    for command in {HOOK_NAME, _resolve_hook_command()}:
        for event in HOOK_EVENTS:
            settings_installer.uninstall_hook(
                settings_path, command, event_name=event
            )
    print(f"Removed hooks from {settings_path}")
    return 0


def _cmd_status() -> int:
    current = state_mod.read()
    if state_mod.is_active(current):
        print(f"HandsFree Claude is running (PID {current.pid}).")
    else:
        print("HandsFree Claude is not running.")
    settings_path = paths.claude_settings_path()
    installed = _hooks_installed(settings_path)
    print(f"Hooks installed: {'yes' if installed else 'no'} ({settings_path})")
    print(f"Config file: {paths.config_path()}")
    return 0


def _hooks_installed(settings_path) -> bool:
    if not settings_path.exists():
        return False
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    for event in HOOK_EVENTS:
        entries = data.get("hooks", {}).get(event, [])
        commands = [h.get("command") or "" for e in entries for h in e.get("hooks", [])]
        # Match either the bare name or any absolute path whose final component
        # resolves to our hook (Windows adds a .exe suffix via the console-script shim).
        if not any(_command_matches_hook(c) for c in commands):
            return False
    return True


def _command_matches_hook(command: str) -> bool:
    if command == HOOK_NAME:
        return True
    from pathlib import Path as _Path
    stem = _Path(command).stem.lower() if command else ""
    return stem == HOOK_NAME


if __name__ == "__main__":
    raise SystemExit(main())
