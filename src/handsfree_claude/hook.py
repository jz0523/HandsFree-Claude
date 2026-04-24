from __future__ import annotations

import datetime as _dt
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from handsfree_claude import audio, config as config_mod, paths, state as state_mod

_DEBUG_ENV_VAR = "HANDSFREE_CLAUDE_DEBUG"


def _debug_enabled() -> bool:
    return os.environ.get(_DEBUG_ENV_VAR, "").strip() not in ("", "0", "false", "False")


def _debug(message: str) -> None:
    if not _debug_enabled():
        return
    try:
        paths.ensure_dirs()
        log = paths.base_dir() / "logs" / "hook.log"
        stamp = _dt.datetime.now().isoformat(timespec="seconds")
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{stamp} {message}\n")
    except Exception:
        pass


def _read_event() -> Optional[dict]:
    try:
        raw = sys.stdin.read()
        _debug(f"stdin raw ({len(raw)} chars): {raw[:500]!r}")
        if not raw.strip():
            return None
        return json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        _debug(f"_read_event failed: {exc}")
        return None


def _handle_pretooluse() -> int:
    if not state_mod.is_active():
        return 0
    payload = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "HandsFree mode active",
        }
    }
    sys.stdout.write(json.dumps(payload))
    return 0


def _handle_stop() -> int:
    if not state_mod.is_active():
        return 0
    cfg = config_mod.load()
    if cfg.mute_sound:
        return 0
    sound_path = audio.effective_sound_path(cfg)
    if sound_path is None:
        return 0
    _spawn_audio_subprocess(sound_path)
    return 0


def _spawn_audio_subprocess(sound_path: Path) -> None:
    """Fire-and-forget: launch a detached process to play the sound."""
    try:
        kwargs: dict = {
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform == "win32":
            # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            kwargs["creationflags"] = 0x00000008 | 0x00000200
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(
            [sys.executable, "-m", "handsfree_claude.audio", str(sound_path)],
            **kwargs,
        )
    except Exception:
        # Hook must never fail Claude Code.
        pass


def main() -> int:
    event = _read_event()
    if not isinstance(event, dict):
        _debug("no/invalid event -> exit 0")
        return 0
    name = event.get("hook_event_name")
    s = state_mod.read()
    active = state_mod.is_active(s)
    _debug(
        f"event={name!r} state(enabled={s.enabled}, pid={s.pid}) active={active} "
        f"keys={list(event.keys())}"
    )
    if name == "PreToolUse":
        rc = _handle_pretooluse()
        _debug(f"PreToolUse handled, rc={rc}")
        return rc
    if name == "Stop":
        rc = _handle_stop()
        _debug(f"Stop handled, rc={rc}")
        return rc
    _debug(f"unknown event {name!r} -> exit 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
