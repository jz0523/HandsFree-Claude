from __future__ import annotations

from importlib import resources
from pathlib import Path


def base_dir() -> Path:
    return Path.home() / ".handsfree-claude"


def state_path() -> Path:
    return base_dir() / "state.json"


def config_path() -> Path:
    return base_dir() / "config.json"


def log_path() -> Path:
    return base_dir() / "logs" / "audio.log"


def claude_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def ensure_dirs() -> None:
    base_dir().mkdir(parents=True, exist_ok=True)
    (base_dir() / "logs").mkdir(parents=True, exist_ok=True)


def bundled_asset(relative_path: str) -> Path:
    """Resolve a file bundled under src/handsfree_claude/assets/.

    `relative_path` is relative to the assets dir, e.g. "end_sounds/default.mp3".
    Returns a Path whether or not the file currently exists — callers must check.
    """
    parts = relative_path.split("/")
    # Fast path for editable installs: walk up from this file.
    here = Path(__file__).resolve().parent
    candidate = here.joinpath("assets", *parts)
    if candidate.exists():
        return candidate
    # Fallback: traverse from the parent package (works without assets/__init__.py).
    try:
        root = resources.files("handsfree_claude")
        res = root.joinpath("assets", *parts)
        with resources.as_file(res) as real:
            return Path(real)
    except (ModuleNotFoundError, FileNotFoundError):
        pass
    # Return the editable-install candidate even if it doesn't exist yet; callers decide.
    return candidate
