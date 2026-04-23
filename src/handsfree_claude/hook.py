from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from handsfree_claude import audio, config as config_mod, state as state_mod


def _read_event() -> Optional[dict]:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return None
        return json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None


def _handle_pretooluse() -> int:
    if not state_mod.is_active():
        return 0
    payload = {"decision": "allow", "reason": "HandsFree mode active"}
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
        return 0
    name = event.get("hook_event_name")
    if name == "PreToolUse":
        return _handle_pretooluse()
    if name == "Stop":
        return _handle_stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
