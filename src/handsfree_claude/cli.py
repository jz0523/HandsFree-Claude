from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Optional, Sequence

from handsfree_claude import paths, settings_installer, state as state_mod

HOOK_NAME = "handsfree-claude-hook"
HOOK_EVENTS = ("PreToolUse", "Stop")
HOOK_TIMEOUT_SECONDS = 5
CONFLICTING_STEMS = ("oi-claude-hook",)  # prior tools whose hooks we warn about


def _resolve_hook_command() -> str:
    """Return the command string to register in Claude's settings.json.

    Prefer the absolute path to the installed console script so that Claude
    Code finds it regardless of the PATH its process inherits (on Windows,
    user-site Scripts directories are often not on system PATH).

    On Windows, Claude Code runs the hook through bash, which treats
    backslashes as escape characters — so a path like
    C:\\Users\\x\\Scripts\\foo.EXE arrives at the exec call as
    C:Usersx Scriptsfoo.EXE and fails. Normalize to forward slashes,
    which bash and the Windows loader both handle correctly."""
    resolved = shutil.which(HOOK_NAME)
    if not resolved:
        return HOOK_NAME
    if sys.platform == "win32":
        return resolved.replace("\\", "/")
    return resolved


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
    # Scrub any prior handsfree-claude-hook entries (old path forms, bare name,
    # path variants from a different Python environment) so we don't stack up
    # duplicates when the user re-runs install-hooks or reinstalls the package.
    removed = _scrub_hooks_by_stem(settings_path, HOOK_NAME)
    # Warn about known-conflicting hooks (e.g., Oi-Claude) but don't auto-remove;
    # the user may have installed them intentionally.
    conflicts = _find_hooks_by_stems(settings_path, CONFLICTING_STEMS)
    for event in HOOK_EVENTS:
        settings_installer.install_hook(
            settings_path,
            command,
            event_name=event,
            timeout_seconds=HOOK_TIMEOUT_SECONDS,
        )
    print(f"Installed hooks in {settings_path} (command: {command})")
    if removed:
        print(f"Scrubbed {removed} stale handsfree-claude-hook entr"
              f"{'y' if removed == 1 else 'ies'}.")
    if conflicts:
        print(
            "Warning: detected hook(s) from a prior tool that may conflict "
            "(they run alongside ours and can cause unexpected prompts):"
        )
        for event, cmd in conflicts:
            print(f"  - {event}: {cmd}")
        print(
            "If you no longer use that tool, remove these entries from\n"
            f"  {settings_path}\nor run its uninstaller."
        )
    return 0


def _cmd_uninstall_hooks() -> int:
    settings_path = paths.claude_settings_path()
    removed = _scrub_hooks_by_stem(settings_path, HOOK_NAME)
    print(
        f"Removed {removed} hook entr{'y' if removed == 1 else 'ies'} "
        f"from {settings_path}"
    )
    return 0


def _scrub_hooks_by_stem(settings_path, stem: str) -> int:
    """Remove every hook whose command's filename stem matches `stem`.

    Returns the number of entries removed. A safe noop if the settings
    file is missing or has no hooks section.
    """
    if not settings_path.exists():
        return 0
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return 0
    removed = 0
    target = stem.lower()
    for event, entries in list(hooks.items()):
        new_entries = []
        for entry in entries:
            kept = []
            for h in entry.get("hooks", []):
                cmd = h.get("command") or ""
                if Path(cmd).stem.lower() == target or cmd == stem:
                    removed += 1
                    continue
                kept.append(h)
            if kept:
                new_entry = dict(entry)
                new_entry["hooks"] = kept
                new_entries.append(new_entry)
        hooks[event] = new_entries
    if removed:
        settings_path.write_text(
            json.dumps(data, indent=2), encoding="utf-8"
        )
    return removed


def _find_hooks_by_stems(settings_path, stems) -> list[tuple[str, str]]:
    """Return [(event_name, command), ...] for hooks matching any given stem."""
    if not settings_path.exists():
        return []
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return []
    targets = {s.lower() for s in stems}
    out: list[tuple[str, str]] = []
    for event, entries in hooks.items():
        for entry in entries:
            for h in entry.get("hooks", []):
                cmd = h.get("command") or ""
                if Path(cmd).stem.lower() in targets or cmd.lower() in targets:
                    out.append((event, cmd))
    return out


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
    target = HOOK_NAME.lower()
    for event in HOOK_EVENTS:
        entries = data.get("hooks", {}).get(event, [])
        commands = [h.get("command") or "" for e in entries for h in e.get("hooks", [])]
        if not any(Path(c).stem.lower() == target or c == HOOK_NAME for c in commands):
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(main())
