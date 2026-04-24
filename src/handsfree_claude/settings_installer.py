from __future__ import annotations

import json
import os
from pathlib import Path

MATCHER = "*"
TIMEOUT_SECONDS = 15


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Claude Code settings at {path} is not valid JSON: {exc}. "
            "Fix it by hand before running this command."
        ) from exc


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def install_hook(
    settings_path: Path,
    hook_command: str,
    *,
    event_name: str = "PreToolUse",
    timeout_seconds: int = TIMEOUT_SECONDS,
) -> None:
    """Install a hook under the given event. Idempotent. Preserves foreign hooks."""
    data = _load(settings_path)
    hooks = data.setdefault("hooks", {})
    entries = hooks.setdefault(event_name, [])

    for entry in entries:
        for h in entry.get("hooks", []):
            if h.get("command") == hook_command:
                return

    entries.append({
        "matcher": MATCHER,
        "hooks": [{
            "type": "command",
            "command": hook_command,
            "timeout": timeout_seconds,
        }],
    })
    _save(settings_path, data)


def uninstall_hook(
    settings_path: Path,
    hook_command: str,
    *,
    event_name: str = "PreToolUse",
) -> None:
    """Remove entries whose command equals hook_command under event_name."""
    if not settings_path.exists():
        return
    data = _load(settings_path)
    entries = data.get("hooks", {}).get(event_name, [])
    new_entries = []
    for entry in entries:
        remaining = [h for h in entry.get("hooks", []) if h.get("command") != hook_command]
        if remaining:
            new_entry = dict(entry)
            new_entry["hooks"] = remaining
            new_entries.append(new_entry)
    data.setdefault("hooks", {})[event_name] = new_entries
    _save(settings_path, data)
