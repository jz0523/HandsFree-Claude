# HandsFree-Claude Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal Tk-window tool that auto-approves Claude Code tool-call permission prompts while a HandsFree-mode toggle is on, and plays an end sound when Claude Code finishes.

**Architecture:** Single window process owns `state.json`; Claude Code hooks read that file (with PID liveness) on each `PreToolUse` / `Stop` event. No daemon, no HTTP, no voice. Hybrid cherry-pick from Oi-Claude: reuse the hook-installer logic and end-sound playback idea, rewrite state/hook/UI/CLI fresh.

**Tech Stack:** Python 3.10+, CustomTkinter (UI), psutil (PID liveness), playsound3 (audio), argparse (CLI), pytest (tests). Cross-platform; primary dev on Windows 11.

**Reference spec:** [docs/superpowers/specs/2026-04-23-handsfree-claude-design.md](../specs/2026-04-23-handsfree-claude-design.md)

**Reference source repo (working, do NOT modify):** https://github.com/jz0523/Oi-Claude

---

## File Structure

New files (all created in this plan):

```
HandsFree-Claude/
├── src/handsfree_claude/
│   ├── __init__.py                  # package marker; exports __version__
│   ├── __main__.py                  # python -m handsfree_claude → cli.main()
│   ├── paths.py                     # dirs + bundled asset resolution
│   ├── state.py                     # state.json I/O + PID liveness
│   ├── config.py                    # config.json I/O
│   ├── settings_installer.py        # ~/.claude/settings.json hook install/uninstall
│   ├── audio.py                     # end-sound playback
│   ├── hook.py                      # hook entry point (PreToolUse + Stop)
│   ├── cli.py                       # run | install-hooks | uninstall-hooks | status
│   ├── ui.py                        # main window + settings dialog
│   └── assets/
│       └── end_sounds/
│           ├── default.mp3
│           ├── chime.mp3
│           └── ding.mp3
├── tests/
│   ├── __init__.py
│   ├── test_paths.py
│   ├── test_state.py
│   ├── test_config.py
│   ├── test_settings_installer.py
│   ├── test_hook.py
│   └── test_cli.py
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

Each file has one clear responsibility. `ui.py` is not unit-tested (Tk is painful to test headlessly); it's covered by the manual smoke test in Task 12.

---

## Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `src/handsfree_claude/__init__.py`
- Create: `src/handsfree_claude/__main__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "handsfree-claude"
version = "0.1.0"
description = "Auto-approve Claude Code permission prompts while a toggle is on; plays a sound on session completion."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.10"
authors = [{ name = "jz0523", email = "jimmyzhong523@gmail.com" }]
dependencies = [
  "customtkinter>=5.2",
  "pillow>=10.0",
  "psutil>=5.9",
  "playsound3>=3.0",
]

[project.optional-dependencies]
dev = ["pytest>=7", "pytest-mock>=3"]

[project.scripts]
handsfree-claude = "handsfree_claude.cli:main"
handsfree-claude-hook = "handsfree_claude.hook:main"

[project.urls]
Homepage = "https://github.com/jz0523/HandsFree-Claude"

[tool.hatch.build.targets.wheel]
packages = ["src/handsfree_claude"]

[tool.hatch.build.targets.wheel.force-include]
"src/handsfree_claude/assets" = "handsfree_claude/assets"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Write `.gitignore`**

```
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
.pytest_cache/
.venv/
venv/
.env
*.log
```

- [ ] **Step 3: Write `LICENSE` (MIT)**

```
MIT License

Copyright (c) 2026 jz0523

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 4: Write `src/handsfree_claude/__init__.py`**

```python
__version__ = "0.1.0"
```

- [ ] **Step 5: Write `src/handsfree_claude/__main__.py`**

```python
from handsfree_claude.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Write `tests/__init__.py` (empty file)**

```python
```

- [ ] **Step 7: Install and verify**

Run:
```bash
pip install -e ".[dev]"
```
Expected: installs cleanly. `handsfree-claude` and `handsfree-claude-hook` commands are registered (though they will fail until later tasks implement `cli.py` / `hook.py`).

Then:
```bash
pytest --collect-only
```
Expected: `no tests ran in 0.00s` (tests dir is empty but pytest runs without error).

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .gitignore LICENSE src/ tests/
git commit -m "chore: scaffold handsfree-claude package"
```

---

## Task 2: paths.py

**Files:**
- Create: `src/handsfree_claude/paths.py`
- Test: `tests/test_paths.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_paths.py
from pathlib import Path

from handsfree_claude import paths


def test_base_dir_is_under_home():
    d = paths.base_dir()
    assert d.name == ".handsfree-claude"
    assert d.parent == Path.home()


def test_state_path_and_config_path():
    assert paths.state_path().name == "state.json"
    assert paths.state_path().parent == paths.base_dir()
    assert paths.config_path().name == "config.json"
    assert paths.config_path().parent == paths.base_dir()


def test_log_path():
    assert paths.log_path().name == "audio.log"
    assert paths.log_path().parent.name == "logs"
    assert paths.log_path().parent.parent == paths.base_dir()


def test_claude_settings_path():
    assert paths.claude_settings_path() == Path.home() / ".claude" / "settings.json"


def test_ensure_dirs_creates_base_and_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "base_dir", lambda: tmp_path / ".handsfree-claude")
    paths.ensure_dirs()
    assert (tmp_path / ".handsfree-claude").is_dir()
    assert (tmp_path / ".handsfree-claude" / "logs").is_dir()


def test_bundled_asset_returns_existing_path():
    # The default.mp3 asset is added in Task 10; until then, this test expects
    # that bundled_asset returns a Path object whose name matches the request,
    # even if the file does not yet exist.
    p = paths.bundled_asset("end_sounds/default.mp3")
    assert p.name == "default.mp3"
    assert p.parent.name == "end_sounds"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_paths.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'handsfree_claude.paths'` or similar.

- [ ] **Step 3: Write `paths.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_paths.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/handsfree_claude/paths.py tests/test_paths.py
git commit -m "feat(paths): add filesystem + bundled-asset paths"
```

---

## Task 3: state.py

**Files:**
- Create: `src/handsfree_claude/state.py`
- Test: `tests/test_state.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_state.py
import json
import os
from pathlib import Path

import pytest

from handsfree_claude import state as state_mod


@pytest.fixture
def tmp_state(tmp_path, monkeypatch):
    """Redirect paths.state_path() to a temp file."""
    target = tmp_path / "state.json"
    from handsfree_claude import paths
    monkeypatch.setattr(paths, "state_path", lambda: target)
    monkeypatch.setattr(paths, "base_dir", lambda: tmp_path)
    return target


def test_read_returns_disabled_when_file_missing(tmp_state):
    s = state_mod.read()
    assert s.enabled is False
    assert s.pid == 0


def test_read_returns_disabled_on_corrupt_json(tmp_state):
    tmp_state.write_text("{not-json", encoding="utf-8")
    s = state_mod.read()
    assert s.enabled is False
    assert s.pid == 0


def test_write_roundtrip(tmp_state):
    state_mod.write(enabled=True, pid=4242)
    raw = json.loads(tmp_state.read_text(encoding="utf-8"))
    assert raw == {"enabled": True, "pid": 4242}
    s = state_mod.read()
    assert s.enabled is True
    assert s.pid == 4242


def test_is_active_returns_false_when_disabled(tmp_state, mocker):
    state_mod.write(enabled=False, pid=os.getpid())
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    assert state_mod.is_active() is False


def test_is_active_returns_false_when_pid_dead(tmp_state, mocker):
    state_mod.write(enabled=True, pid=99999)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=False)
    assert state_mod.is_active() is False


def test_is_active_returns_true_when_enabled_and_alive(tmp_state, mocker):
    state_mod.write(enabled=True, pid=os.getpid())
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    assert state_mod.is_active() is True


def test_clear_writes_disabled(tmp_state):
    state_mod.write(enabled=True, pid=4242)
    state_mod.clear()
    s = state_mod.read()
    assert s.enabled is False
    assert s.pid == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'handsfree_claude.state'`.

- [ ] **Step 3: Write `state.py`**

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import psutil

from handsfree_claude import paths


@dataclass(frozen=True)
class State:
    enabled: bool
    pid: int


def read() -> State:
    p = paths.state_path()
    if not p.exists():
        return State(enabled=False, pid=0)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return State(enabled=False, pid=0)
    return State(
        enabled=bool(data.get("enabled", False)),
        pid=int(data.get("pid", 0) or 0),
    )


def write(*, enabled: bool, pid: int) -> None:
    paths.ensure_dirs()
    p = paths.state_path()
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(
        json.dumps({"enabled": enabled, "pid": pid}, indent=2),
        encoding="utf-8",
    )
    tmp.replace(p)


def clear() -> None:
    write(enabled=False, pid=0)


def is_active(current: Optional[State] = None) -> bool:
    s = current if current is not None else read()
    if not s.enabled:
        return False
    if s.pid <= 0:
        return False
    return psutil.pid_exists(s.pid)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_state.py -v`
Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/handsfree_claude/state.py tests/test_state.py
git commit -m "feat(state): add state.json I/O with PID liveness"
```

---

## Task 4: config.py

**Files:**
- Create: `src/handsfree_claude/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
import json

import pytest

from handsfree_claude import config as config_mod


@pytest.fixture
def tmp_config(tmp_path, monkeypatch):
    target = tmp_path / "config.json"
    from handsfree_claude import paths
    monkeypatch.setattr(paths, "config_path", lambda: target)
    monkeypatch.setattr(paths, "base_dir", lambda: tmp_path)
    return target


def test_load_returns_defaults_when_file_missing(tmp_config):
    cfg = config_mod.load()
    assert cfg.end_sound_file == "default.mp3"
    assert cfg.custom_sound_path is None
    assert cfg.mute_sound is False
    assert cfg.window_position == (100, 100)


def test_load_returns_defaults_on_corrupt_json(tmp_config):
    tmp_config.write_text("{bad", encoding="utf-8")
    cfg = config_mod.load()
    assert cfg.end_sound_file == "default.mp3"


def test_save_and_reload_roundtrip(tmp_config):
    cfg = config_mod.Config(
        end_sound_file="chime.mp3",
        custom_sound_path="/tmp/custom.mp3",
        mute_sound=True,
        window_position=(250, 300),
    )
    config_mod.save(cfg)
    raw = json.loads(tmp_config.read_text(encoding="utf-8"))
    assert raw["end_sound_file"] == "chime.mp3"
    assert raw["custom_sound_path"] == "/tmp/custom.mp3"
    assert raw["mute_sound"] is True
    assert raw["window_position"] == [250, 300]

    cfg2 = config_mod.load()
    assert cfg2.end_sound_file == "chime.mp3"
    assert cfg2.custom_sound_path == "/tmp/custom.mp3"
    assert cfg2.mute_sound is True
    assert cfg2.window_position == (250, 300)


def test_load_tolerates_unknown_fields(tmp_config):
    tmp_config.write_text(
        json.dumps({"end_sound_file": "ding.mp3", "legacy_field": 123}),
        encoding="utf-8",
    )
    cfg = config_mod.load()
    assert cfg.end_sound_file == "ding.mp3"


def test_load_fills_missing_fields_with_defaults(tmp_config):
    tmp_config.write_text(
        json.dumps({"end_sound_file": "ding.mp3"}),
        encoding="utf-8",
    )
    cfg = config_mod.load()
    assert cfg.end_sound_file == "ding.mp3"
    assert cfg.mute_sound is False
    assert cfg.window_position == (100, 100)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `config.py`**

```python
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from typing import Optional

from handsfree_claude import paths


@dataclass
class Config:
    end_sound_file: str = "default.mp3"
    custom_sound_path: Optional[str] = None
    mute_sound: bool = False
    window_position: tuple[int, int] = (100, 100)


def load() -> Config:
    p = paths.config_path()
    if not p.exists():
        return Config()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Config()
    known = {f.name for f in fields(Config)}
    kwargs = {k: v for k, v in raw.items() if k in known}
    if "window_position" in kwargs and isinstance(kwargs["window_position"], list):
        kwargs["window_position"] = tuple(kwargs["window_position"])
    return Config(**{**asdict(Config()), **kwargs})


def save(cfg: Config) -> None:
    paths.ensure_dirs()
    data = asdict(cfg)
    data["window_position"] = list(data["window_position"])
    p = paths.config_path()
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_config.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/handsfree_claude/config.py tests/test_config.py
git commit -m "feat(config): add config.json I/O"
```

---

## Task 5: settings_installer.py

**Files:**
- Create: `src/handsfree_claude/settings_installer.py`
- Test: `tests/test_settings_installer.py`

This is lifted from Oi-Claude (proven code) with no logic changes.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_settings_installer.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `settings_installer.py`**

```python
from __future__ import annotations

import json
import os
from pathlib import Path

MATCHER = "*"
TIMEOUT_SECONDS = 15


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_settings_installer.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/handsfree_claude/settings_installer.py tests/test_settings_installer.py
git commit -m "feat(installer): register and remove Claude Code hooks (from Oi-Claude)"
```

---

## Task 6: audio.py

**Files:**
- Create: `src/handsfree_claude/audio.py`

Audio playback is hard to assert headlessly, so this task ships without unit tests — it's exercised by the hook tests (Task 7, mocked) and the manual smoke test (Task 12). Keep the module small.

- [ ] **Step 1: Write `audio.py`**

```python
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
```

- [ ] **Step 2: Commit (no tests yet for this module)**

```bash
git add src/handsfree_claude/audio.py
git commit -m "feat(audio): end-sound playback and preview"
```

---

## Task 7: hook.py

**Files:**
- Create: `src/handsfree_claude/hook.py`
- Test: `tests/test_hook.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_hook.py
import io
import json
import sys
from pathlib import Path

import pytest

from handsfree_claude import hook as hook_mod


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    from handsfree_claude import paths
    monkeypatch.setattr(paths, "base_dir", lambda: tmp_path)
    monkeypatch.setattr(paths, "state_path", lambda: tmp_path / "state.json")
    monkeypatch.setattr(paths, "config_path", lambda: tmp_path / "config.json")
    monkeypatch.setattr(paths, "log_path", lambda: tmp_path / "logs" / "audio.log")
    return tmp_path


def _run_with_stdin(payload: dict, monkeypatch) -> tuple[int, str]:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    captured = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured)
    rc = hook_mod.main()
    return rc, captured.getvalue()


def test_pretooluse_noop_when_state_missing(tmp_home, monkeypatch):
    rc, out = _run_with_stdin(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"}, monkeypatch
    )
    assert rc == 0
    assert out == ""


def test_pretooluse_noop_when_disabled(tmp_home, monkeypatch):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=False, pid=0)
    rc, out = _run_with_stdin(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"}, monkeypatch
    )
    assert rc == 0
    assert out == ""


def test_pretooluse_noop_when_pid_dead(tmp_home, monkeypatch, mocker):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=True, pid=99999)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=False)
    rc, out = _run_with_stdin(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"}, monkeypatch
    )
    assert rc == 0
    assert out == ""


def test_pretooluse_emits_allow_when_active(tmp_home, monkeypatch, mocker):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=True, pid=12345)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    rc, out = _run_with_stdin(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash"}, monkeypatch
    )
    assert rc == 0
    data = json.loads(out)
    assert data["decision"] == "allow"
    assert "HandsFree" in data["reason"]


def test_stop_no_subprocess_when_disabled(tmp_home, monkeypatch, mocker):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=False, pid=0)
    spawn = mocker.patch("handsfree_claude.hook._spawn_audio_subprocess")
    rc, out = _run_with_stdin(
        {"hook_event_name": "Stop"}, monkeypatch
    )
    assert rc == 0
    assert spawn.call_count == 0


def test_stop_no_subprocess_when_muted(tmp_home, monkeypatch, mocker):
    from handsfree_claude import state as state_mod
    from handsfree_claude import config as config_mod
    state_mod.write(enabled=True, pid=12345)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    config_mod.save(config_mod.Config(mute_sound=True))
    spawn = mocker.patch("handsfree_claude.hook._spawn_audio_subprocess")
    rc, _ = _run_with_stdin({"hook_event_name": "Stop"}, monkeypatch)
    assert rc == 0
    assert spawn.call_count == 0


def test_stop_spawns_subprocess_when_active_and_unmuted(tmp_home, monkeypatch, mocker):
    from handsfree_claude import state as state_mod
    state_mod.write(enabled=True, pid=12345)
    mocker.patch("handsfree_claude.state.psutil.pid_exists", return_value=True)
    # Pretend there's a playable sound file.
    fake_path = tmp_home / "sound.mp3"
    fake_path.write_bytes(b"fake")
    mocker.patch(
        "handsfree_claude.audio.effective_sound_path", return_value=fake_path
    )
    spawn = mocker.patch("handsfree_claude.hook._spawn_audio_subprocess")
    rc, _ = _run_with_stdin({"hook_event_name": "Stop"}, monkeypatch)
    assert rc == 0
    assert spawn.call_count == 1
    assert spawn.call_args[0][0] == fake_path


def test_unknown_event_is_noop(tmp_home, monkeypatch):
    rc, out = _run_with_stdin(
        {"hook_event_name": "Weird"}, monkeypatch
    )
    assert rc == 0
    assert out == ""


def test_malformed_stdin_is_noop(monkeypatch, tmp_home):
    monkeypatch.setattr("sys.stdin", io.StringIO("not-json"))
    captured = io.StringIO()
    monkeypatch.setattr("sys.stdout", captured)
    rc = hook_mod.main()
    assert rc == 0
    assert captured.getvalue() == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_hook.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `hook.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_hook.py -v`
Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/handsfree_claude/hook.py tests/test_hook.py
git commit -m "feat(hook): PreToolUse auto-approve + Stop end-sound dispatch"
```

---

## Task 8: cli.py

**Files:**
- Create: `src/handsfree_claude/cli.py`
- Test: `tests/test_cli.py`

`run` launches the UI — that can't be unit-tested headlessly, so `run` is covered by the manual smoke test (Task 12). The other three subcommands are unit-tested.

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write `cli.py`**

```python
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
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_cli.py -v`
Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/handsfree_claude/cli.py tests/test_cli.py
git commit -m "feat(cli): run / install-hooks / uninstall-hooks / status"
```

---

## Task 9: ui.py (main window)

**Files:**
- Create: `src/handsfree_claude/ui.py`

UI is not unit-tested; covered by manual smoke test in Task 12.

- [ ] **Step 1: Write `ui.py`**

```python
from __future__ import annotations

import logging
import os
from typing import Optional

import customtkinter as ctk

from handsfree_claude import audio, config as config_mod, paths, state as state_mod

logger = logging.getLogger(__name__)

WINDOW_TITLE = "HandsFree Claude"
WINDOW_SIZE = (340, 180)
SETTINGS_SIZE = (400, 300)

COLOR_OFF = "#9ca3af"   # gray
COLOR_ON = "#22c55e"    # green

POLL_INTERVAL_MS = 400   # re-read state in case something else updated it


def run() -> None:
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")
    app = MainWindow()
    app.mainloop()


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self._cfg = config_mod.load()
        self._alive = True
        self._pid = os.getpid()

        self.title(WINDOW_TITLE)
        self.attributes("-topmost", True)
        x, y = self._cfg.window_position
        self.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}+{x}+{y}")
        self.minsize(*WINDOW_SIZE)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Start OFF — the window being open does not mean HandsFree is on.
        state_mod.write(enabled=False, pid=self._pid)
        self._enabled = False

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=16, pady=14)

        # Row 1: title + settings gear
        top_row = ctk.CTkFrame(outer, fg_color="transparent")
        top_row.pack(fill="x")
        ctk.CTkLabel(
            top_row,
            text=WINDOW_TITLE,
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(
            top_row,
            text="⚙",  # gear
            width=32,
            height=28,
            font=ctk.CTkFont(size=16),
            command=self._open_settings,
        ).pack(side="right")

        # Row 2: status light + label
        status_row = ctk.CTkFrame(outer, fg_color="transparent")
        status_row.pack(fill="x", pady=(16, 12))
        self._light = ctk.CTkLabel(
            status_row,
            text="",
            width=14,
            height=14,
            corner_radius=7,
            fg_color=COLOR_OFF,
        )
        self._light.pack(side="left", padx=(0, 10))
        self._status_label = ctk.CTkLabel(
            status_row,
            text="HandsFree mode: OFF",
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        self._status_label.pack(side="left", fill="x", expand=True)

        # Row 3: toggle button
        self._toggle_button = ctk.CTkButton(
            outer,
            text="Turn ON",
            height=36,
            command=self._toggle,
        )
        self._toggle_button.pack(fill="x")

        self._schedule_poll()

    def _toggle(self) -> None:
        self._enabled = not self._enabled
        state_mod.write(enabled=self._enabled, pid=self._pid)
        self._refresh_ui()

    def _refresh_ui(self) -> None:
        if self._enabled:
            self._light.configure(fg_color=COLOR_ON)
            self._status_label.configure(text="HandsFree mode: ON")
            self._toggle_button.configure(text="Turn OFF")
        else:
            self._light.configure(fg_color=COLOR_OFF)
            self._status_label.configure(text="HandsFree mode: OFF")
            self._toggle_button.configure(text="Turn ON")

    def _schedule_poll(self) -> None:
        if not self._alive:
            return
        s = state_mod.read()
        if s.enabled != self._enabled:
            self._enabled = s.enabled
            self._refresh_ui()
        self.after(POLL_INTERVAL_MS, self._schedule_poll)

    def _open_settings(self) -> None:
        SettingsDialog(self, self._cfg, on_save=self._apply_cfg)

    def _apply_cfg(self, cfg: config_mod.Config) -> None:
        self._cfg = cfg
        config_mod.save(cfg)

    def _on_close(self) -> None:
        self._alive = False
        try:
            self._cfg.window_position = (self.winfo_x(), self.winfo_y())
            config_mod.save(self._cfg)
        except Exception as exc:
            logger.warning("failed to persist window position: %s", exc)
        state_mod.clear()
        self.destroy()


class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, cfg: config_mod.Config, on_save) -> None:
        super().__init__(parent)
        self._original_cfg = cfg
        self._working_cfg = config_mod.Config(
            end_sound_file=cfg.end_sound_file,
            custom_sound_path=cfg.custom_sound_path,
            mute_sound=cfg.mute_sound,
            window_position=cfg.window_position,
        )
        self._on_save = on_save

        self.title("HandsFree Claude — Settings")
        self.attributes("-topmost", True)
        self.geometry(f"{SETTINGS_SIZE[0]}x{SETTINGS_SIZE[1]}")
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=16, pady=16)

        # End sound dropdown
        self._end_sounds: list[tuple[str, str]] = audio.list_end_sounds()
        labels_to_files = {lbl: fn for fn, lbl in self._end_sounds}
        files_to_labels = {fn: lbl for fn, lbl in self._end_sounds}
        default_label = files_to_labels.get(cfg.end_sound_file, "Default")
        self._labels_to_files = labels_to_files

        ctk.CTkLabel(frame, text="End sound:", anchor="w").grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        self._end_sound_var = ctk.StringVar(value=default_label)
        self._end_sound_menu = ctk.CTkOptionMenu(
            frame,
            values=[lbl for _, lbl in self._end_sounds] or ["Default"],
            variable=self._end_sound_var,
            width=180,
        )
        self._end_sound_menu.grid(row=1, column=0, sticky="w", pady=(0, 4))
        ctk.CTkButton(
            frame, text="▶ Preview", width=90, command=self._preview
        ).grid(row=1, column=1, sticky="e", padx=(8, 0), pady=(0, 4))

        # Custom sound
        ctk.CTkLabel(frame, text="Custom sound file:", anchor="w").grid(
            row=2, column=0, sticky="w", pady=(12, 4)
        )
        self._custom_var = ctk.StringVar(value=cfg.custom_sound_path or "")
        self._custom_entry = ctk.CTkEntry(frame, textvariable=self._custom_var)
        self._custom_entry.grid(row=3, column=0, sticky="ew", pady=(0, 4))
        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=3, column=1, sticky="e", padx=(8, 0), pady=(0, 4))
        ctk.CTkButton(
            btn_row, text="Browse…", width=80, command=self._browse
        ).pack(side="left")
        ctk.CTkButton(
            btn_row, text="Clear", width=60, command=self._clear_custom
        ).pack(side="left", padx=(4, 0))

        # Mute
        self._mute_var = ctk.BooleanVar(value=cfg.mute_sound)
        ctk.CTkCheckBox(
            frame, text="Mute sound", variable=self._mute_var
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(16, 0))

        # Save/Cancel
        button_row = ctk.CTkFrame(frame, fg_color="transparent")
        button_row.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(24, 0))
        button_row.columnconfigure(0, weight=1)
        ctk.CTkButton(
            button_row, text="Cancel", width=80, command=self._on_cancel
        ).grid(row=0, column=1, padx=(0, 8))
        ctk.CTkButton(
            button_row, text="Save", width=80, command=self._on_save_clicked
        ).grid(row=0, column=2)

        frame.columnconfigure(0, weight=1)

    def _browse(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self,
            title="Choose end sound",
            filetypes=[("Audio files", "*.mp3 *.wav"), ("All files", "*.*")],
        )
        if path:
            self._custom_var.set(path)

    def _clear_custom(self) -> None:
        self._custom_var.set("")

    def _preview(self) -> None:
        cfg = self._build_working_cfg()
        p = audio.effective_sound_path(cfg)
        if p is None:
            return
        audio.play_end_sound_preview(p)

    def _build_working_cfg(self) -> config_mod.Config:
        filename = self._labels_to_files.get(
            self._end_sound_var.get(), self._working_cfg.end_sound_file
        )
        return config_mod.Config(
            end_sound_file=filename,
            custom_sound_path=self._custom_var.get().strip() or None,
            mute_sound=bool(self._mute_var.get()),
            window_position=self._working_cfg.window_position,
        )

    def _on_save_clicked(self) -> None:
        audio.stop_end_sound_preview()
        self._on_save(self._build_working_cfg())
        self.destroy()

    def _on_cancel(self) -> None:
        audio.stop_end_sound_preview()
        self.destroy()
```

- [ ] **Step 2: Quick import sanity check**

Run: `python -c "from handsfree_claude import ui"`
Expected: no output, no error. (If it errors on `customtkinter`, you missed `pip install -e ".[dev]"`.)

- [ ] **Step 3: Run all tests to ensure nothing regressed**

Run: `pytest -v`
Expected: all tests still PASS (UI has no tests; we're just checking nothing else broke).

- [ ] **Step 4: Commit**

```bash
git add src/handsfree_claude/ui.py
git commit -m "feat(ui): minimal main window + settings dialog"
```

---

## Task 10: Bundled end-sound assets

**Files:**
- Create: `src/handsfree_claude/assets/end_sounds/default.mp3`
- Create: `src/handsfree_claude/assets/end_sounds/chime.mp3`
- Create: `src/handsfree_claude/assets/end_sounds/ding.mp3`

- [ ] **Step 1: Source the three MP3 files**

Options, in order of preference:
- **A.** Download the existing `end_sound*.mp3` files from the Oi-Claude repo and rename as needed. The repo at https://github.com/jz0523/Oi-Claude ships end sounds under `src/oi_claude/assets/`. Pick three distinct ones; rename to `default.mp3`, `chime.mp3`, `ding.mp3`.
- **B.** Download three short CC0 notification sounds from https://freesound.org or https://mixkit.co (filter by "notification", "chime", "ding"). Each should be ≤2 seconds and <30 KB.

Place them at the paths above. File format must be MP3 (`.mp3`) so `playsound3` works cross-platform.

- [ ] **Step 2: Verify asset discovery**

Run:
```bash
python -c "from handsfree_claude import audio; print(audio.list_end_sounds())"
```
Expected: a list of three `(filename, label)` tuples, e.g. `[('chime.mp3', 'Chime'), ('default.mp3', 'Default'), ('ding.mp3', 'Ding')]`.

- [ ] **Step 3: Re-run tests**

Run: `pytest -v`
Expected: all tests still PASS (asset presence doesn't affect unit tests since they mock paths).

- [ ] **Step 4: Commit**

```bash
git add src/handsfree_claude/assets/end_sounds/
git commit -m "feat(assets): bundle default/chime/ding end sounds"
```

---

## Task 11: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`**

````markdown
# HandsFree Claude

A minimal Tk window that auto-approves Claude Code tool-call permission prompts while "HandsFree mode" is toggled on, and plays a sound when Claude finishes a session.

Derived from [Oi-Claude](https://github.com/jz0523/Oi-Claude), stripped down to just the auto-approval + end-sound behavior — no daemon, no HTTP, no voice recognition.

## Requirements

- Python 3.10+
- macOS, Linux, or Windows
- [Claude Code](https://claude.com/claude-code) CLI installed

## Install

```bash
git clone https://github.com/jz0523/HandsFree-Claude.git
cd HandsFree-Claude
pip install -e .
handsfree-claude install-hooks
```

## Use

Open the window:

```bash
handsfree-claude
```

The window shows three things: the app name, a status light (gray = off, green = on), and a big toggle button. Click the gear icon for settings.

Toggle HandsFree mode **on** and any subsequent Claude Code permission prompt auto-approves. When Claude finishes responding, the configured end sound plays.

Toggle **off** — or close the window — and prompts behave normally again.

## Settings

Click the gear icon:
- **End sound** — pick one of the bundled sounds.
- **Custom sound file** — browse to your own `.mp3` or `.wav`. Overrides the dropdown.
- **Mute sound** — keeps auto-approval on but silences the end-of-session sound.

## Commands

```
handsfree-claude                 # open the window
handsfree-claude install-hooks   # register hooks in ~/.claude/settings.json
handsfree-claude uninstall-hooks # remove hooks
handsfree-claude status          # show running/installed state
```

## How it works

- The window owns `~/.handsfree-claude/state.json` with `{enabled, pid}`.
- Two Claude Code hooks (`PreToolUse`, `Stop`) invoke `handsfree-claude-hook` as a short-lived subprocess.
- The hook reads the state file. If `enabled=true` and the window PID is alive, it emits `{"decision": "allow"}` on `PreToolUse` or fires off a detached subprocess to play the end sound on `Stop`.
- Closing the window writes `enabled=false` and clears the PID, so nothing stays auto-approved after close.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README"
```

---

## Task 12: Manual smoke test

No files. This is the end-to-end check. Work through each item and note any failures as follow-up fixes.

- [ ] **Step 1: Clean install**

```bash
pip install -e ".[dev]"
handsfree-claude install-hooks
handsfree-claude status
```
Expected: `status` reports "not running" and "Hooks installed: yes".

- [ ] **Step 2: Open the window**

Run: `handsfree-claude`
Expected: 340×180 window opens, title "HandsFree Claude" at top-left, gear icon at top-right, gray status light, "HandsFree mode: OFF", button labeled "Turn ON".

- [ ] **Step 3: Toggle on**

Click "Turn ON".
Expected: status light turns green, label reads "HandsFree mode: ON", button now reads "Turn OFF".
Verify: `cat ~/.handsfree-claude/state.json` shows `"enabled": true` and a real PID.

- [ ] **Step 4: Verify auto-approval in Claude Code**

In a separate terminal, run a Claude Code command that triggers a tool call requiring approval (e.g. a Bash command). Expected: no permission prompt appears; the tool runs immediately.

- [ ] **Step 5: Verify end sound**

Wait for Claude to finish responding.
Expected: the configured end sound plays once.

- [ ] **Step 6: Exercise Settings**

Click gear → change end sound → click Preview (should play selected sound) → Save.
Trigger another Claude session end.
Expected: the newly selected sound plays.

- [ ] **Step 7: Custom sound**

Reopen Settings → Browse… → pick an MP3 you have on disk → Preview (your sound plays) → Save → trigger a session end.
Expected: your custom sound plays.

- [ ] **Step 8: Mute**

Settings → check Mute → Save → trigger a session end.
Expected: no sound; auto-approval still works.

- [ ] **Step 9: Toggle off**

Click "Turn OFF".
Expected: `state.json` shows `"enabled": false`; next Claude tool call prompts normally.

- [ ] **Step 10: Close window**

Close the window.
Expected: `state.json` shows `"enabled": false, "pid": 0`; next Claude tool call prompts normally.

- [ ] **Step 11: Double-launch refusal**

Reopen with `handsfree-claude`, then from a second shell run `handsfree-claude` again.
Expected: second invocation exits 1 with "HandsFree Claude is already running (PID N)." on stderr. First window unaffected.

- [ ] **Step 12: Final commit (if any fixes were made during smoke test)**

If you fixed any bugs during the smoke test:
```bash
git add -A
git commit -m "fix: smoke test issues"
```
Otherwise, the branch is ready.

---

## Dependencies summary

From `pyproject.toml`:
- `customtkinter>=5.2` — window framework (Oi-Claude's choice, works well on Windows).
- `pillow>=10.0` — used by customtkinter for image handling.
- `psutil>=5.9` — cross-platform `pid_exists`.
- `playsound3>=3.0` — cross-platform MP3/WAV playback.
- `pytest>=7` / `pytest-mock>=3` — dev-only.

No HTTP, no voice recognition, no model downloads.
