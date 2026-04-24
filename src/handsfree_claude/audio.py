from __future__ import annotations

import logging
import os
from pathlib import Path
from threading import Lock
from typing import Optional

from handsfree_claude import config as config_mod, paths

logger = logging.getLogger(__name__)

_BUNDLED_DIR = "end_sounds"
_FALLBACK_FILENAME = "default.mp3"

_preview_lock = Lock()
_preview_handle = None  # playsound3 Sound object, or None


def list_end_sounds() -> list[tuple[str, str]]:
    """Return [(filename, label), ...] for bundled end-sound files.

    Labels are derived from filenames: "default.mp3" -> "Default".
    """
    assets_root = paths.bundled_asset(_BUNDLED_DIR)
    if not assets_root.exists() or not assets_root.is_dir():
        return []
    out: list[tuple[str, str]] = []
    for p in sorted(assets_root.iterdir()):
        if p.suffix.lower() in {".mp3", ".wav"}:
            out.append((p.name, _label_for(p.name)))
    return out


def _label_for(filename: str) -> str:
    stem = Path(filename).stem
    return stem.replace("_", " ").replace("-", " ").title()


def effective_sound_path(cfg: Optional[config_mod.Config] = None) -> Optional[Path]:
    """Pick the sound file to play: custom override > bundled end_sound_file > fallback.

    Returns None if no playable file can be resolved.
    """
    c = cfg if cfg is not None else config_mod.load()
    if c.custom_sound_path:
        p = Path(c.custom_sound_path)
        if p.exists():
            return p
        logger.warning("custom_sound_path does not exist, falling back: %s", p)
    bundled = paths.bundled_asset(f"{_BUNDLED_DIR}/{c.end_sound_file}")
    if bundled.exists():
        return bundled
    fallback = paths.bundled_asset(f"{_BUNDLED_DIR}/{_FALLBACK_FILENAME}")
    if fallback.exists():
        return fallback
    return None


def play_end_sound_blocking(path: Path) -> None:
    """Play a sound synchronously. Errors are logged and swallowed."""
    try:
        from playsound3 import playsound  # type: ignore
        playsound(str(path), block=True)
    except Exception as exc:
        _log_error(f"playsound failed for {path}: {exc}")


def play_end_sound_preview(path: Path) -> None:
    """Play a sound asynchronously for Settings preview. Cancels any previous preview."""
    global _preview_handle
    stop_end_sound_preview()
    try:
        from playsound3 import playsound  # type: ignore
        with _preview_lock:
            _preview_handle = playsound(str(path), block=False)
    except Exception as exc:
        _log_error(f"preview failed for {path}: {exc}")


def stop_end_sound_preview() -> None:
    """Stop any in-flight preview."""
    global _preview_handle
    with _preview_lock:
        if _preview_handle is not None:
            try:
                _preview_handle.stop()
            except Exception:
                pass
            _preview_handle = None


def _log_error(message: str) -> None:
    try:
        paths.ensure_dirs()
        with open(paths.log_path(), "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        # Last-resort: swallow. Hook must never fail Claude Code.
        pass


def _cli_entry() -> int:
    """Entry point used by the Stop hook subprocess.

    Called as: `python -m handsfree_claude.audio <path>`
    """
    import sys
    if len(sys.argv) < 2:
        return 1
    path = Path(sys.argv[1])
    if not path.exists():
        _log_error(f"audio cli: file does not exist: {path}")
        return 1
    play_end_sound_blocking(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_entry())
