from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from handsfree_claude import paths, settings_installer, state as state_mod

HOOK_COMMAND = "handsfree-claude-hook"
HOOK_EVENTS = ("PreToolUse", "Stop")
HOOK_TIMEOUT_SECONDS = 5


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
    for event in HOOK_EVENTS:
        settings_installer.install_hook(
            settings_path,
            HOOK_COMMAND,
            event_name=event,
            timeout_seconds=HOOK_TIMEOUT_SECONDS,
        )
    print(f"Installed hooks in {settings_path}")
    return 0


def _cmd_uninstall_hooks() -> int:
    settings_path = paths.claude_settings_path()
    for event in HOOK_EVENTS:
        settings_installer.uninstall_hook(
            settings_path, HOOK_COMMAND, event_name=event
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
        commands = [h.get("command") for e in entries for h in e.get("hooks", [])]
        if HOOK_COMMAND not in commands:
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
