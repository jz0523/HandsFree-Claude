# HandsFree-Claude Design Spec

**Date:** 2026-04-23
**Status:** Design approved, pending implementation plan

## Goal

Simplify the Oi-Claude codebase into a developer-friendly tool that does one thing: auto-approve Claude Code tool-call permission prompts while a small on/off window is toggled on, and play a sound when a Claude Code session completes. Drop everything else from Oi-Claude (daemon, HTTP server, voice recognition, trust-mode time windows).

Reference repository (working original): https://github.com/jz0523/Oi-Claude

## Scope

### In scope

- A small always-on-top Tk window with: app name label, status light, on/off toggle button, settings gear button.
- **HandsFree mode** (renamed from Oi-Claude's "trust mode") has no time span: stays on until the user turns it off or closes the window.
- A Claude Code `PreToolUse` hook that auto-approves when HandsFree mode is on.
- A Claude Code `Stop` hook that plays an end sound when HandsFree mode is on and the user hasn't muted.
- A Settings panel with: end-sound selection (from bundled options), custom sound file picker, mute toggle.
- CLI commands to run the window, install hooks, uninstall hooks, show status.

### Out of scope (removed from Oi-Claude)

- Daemon process / background HTTP server / token auth.
- Voice recognition (Vosk, sounddevice, the "oi"/"no"/"cancel" voice commands).
- Time-bounded trust mode / progress bar / preset durations.
- oi-cat mascot / GIF animation / animated status pulsing.
- `quiet_tools` allowlist, listen timeout, mic device selection.
- Model downloader.

## Architecture

### Topology

```
┌──────────────────────────────┐       ┌──────────────────────────────┐
│  handsfree-claude window     │       │  Claude Code session         │
│  (Tk / CustomTkinter)        │       │                              │
│                              │       │  ┌─ PreToolUse event ────┐   │
│  toggle → writes:            │       │  │ handsfree-claude-hook │───┼───┐
│  ~/.handsfree-claude/        │       │  └───────────────────────┘   │   │
│     state.json               │       │                              │   │
│     {enabled, pid}           │       │  ┌─ Stop event ──────────┐   │   │
│                              │◄──────┤  │ handsfree-claude-hook │───┼───┤
│                              │  read │  └───────────────────────┘   │   │
└──────────────────────────────┘       └──────────────────────────────┘   │
                                                                          │
              ┌───────────────────────────────────────────────────────────┘
              ▼
     hook decides based on state.json + PID liveness check:
     - PreToolUse: emit {"decision": "allow"} if enabled+alive, else no-op
     - Stop: fire-and-forget audio subprocess if enabled+alive+unmuted
```

**Key simplification over Oi-Claude:** the window is the only long-lived process. There is no daemon and no HTTP server. The hook is a short-lived subprocess spawned by Claude Code that reads a JSON file on disk and exits.

### Module layout

```
HandsFree-Claude/
├── src/handsfree_claude/
│   ├── __init__.py
│   ├── __main__.py              # python -m handsfree_claude → cli.main()
│   ├── cli.py                   # run | install-hooks | uninstall-hooks | status
│   ├── ui.py                    # Tk window + Settings dialog
│   ├── state.py                 # state.json read/write + PID liveness
│   ├── hook.py                  # hook entry point; branches on PreToolUse vs Stop
│   ├── config.py                # config.json read/write
│   ├── audio.py                 # end-sound playback (voice code stripped)
│   ├── paths.py                 # ~/.handsfree-claude/ paths + bundled assets
│   ├── settings_installer.py    # registers hooks in ~/.claude/settings.json
│   └── assets/
│       └── end_sounds/
│           ├── default.mp3
│           ├── chime.mp3
│           └── ding.mp3
├── tests/
│   ├── test_state.py
│   ├── test_config.py
│   ├── test_hook.py
│   └── test_settings_installer.py
├── pyproject.toml
├── README.md
└── LICENSE
```

### Cherry-picks from Oi-Claude

The following files are reused from Oi-Claude because they already work and are not coupled to the daemon model:

| File | How it's reused |
|---|---|
| `settings_installer.py` | **Verbatim.** Called twice on install — once for `PreToolUse`, once for `Stop`. |
| `paths.py` | Adapted. Point at `~/.handsfree-claude/` instead of `~/.oi-claude/`. Bundled-asset lookup pattern preserved. |
| `audio.py` | **Stripped.** Keep end-sound playback and preview functions. Remove all voice-recognition functions, sound-device selection, listen loops. |
| `config.py` | Schema simplified (see below); file-I/O pattern preserved. |

Everything else is written fresh. In particular, `state.py`, `hook.py`, `ui.py`, and `cli.py` are new — the Oi-Claude versions are too coupled to the daemon/HTTP/token/voice model to cleanly strip.

## Data Model

### State file — `~/.handsfree-claude/state.json`

Written by the window process whenever the toggle is flipped, and once at exit (to set `enabled: false`).

```json
{
  "enabled": true,
  "pid": 12345
}
```

- `enabled` — boolean. True when the user has toggled HandsFree mode on.
- `pid` — integer. The window process's PID. Used by the hook for liveness check.

**Liveness rule:** the hook treats the state as `enabled=true` only if `psutil.pid_exists(pid)` returns True. If the file says `enabled=true` but the PID is dead (crash, force-quit), the hook treats it as disabled. The next `handsfree-claude run` overwrites the stale file.

### Config file — `~/.handsfree-claude/config.json`

Written only by the Settings dialog (on Save) and by the main window (on close, for `window_position`).

```json
{
  "end_sound_file": "default.mp3",
  "custom_sound_path": null,
  "mute_sound": false,
  "window_position": [100, 100]
}
```

- `end_sound_file` — filename of a bundled sound in `assets/end_sounds/`. Used when `custom_sound_path` is null.
- `custom_sound_path` — absolute path to a user-supplied `.mp3` or `.wav`. When non-null and the file exists, overrides `end_sound_file`.
- `mute_sound` — when true, the Stop hook no-ops on audio.
- `window_position` — `[x, y]` of the main window. Persisted on close.

Defaults are applied in-memory when fields are missing from an older config; the file is re-saved on the next `save()` call.

## UI

### Main window

- Size: ~340×180, always-on-top, minimum size enforced.
- Three visible elements: app name, status light + label, toggle button. Settings gear in the corner.
- No mascot, no GIF, no animation.

```
┌──────────────────────────────────────────┐
│  HandsFree Claude                   ⚙    │
│                                           │
│       ●  HandsFree mode: OFF              │
│                                           │
│       [        Turn ON        ]           │
└──────────────────────────────────────────┘
```

**Status light — two states only:**

| State | Color | Label |
|---|---|---|
| Off | Gray `#9ca3af` | "HandsFree mode: OFF" |
| On  | Green `#22c55e` | "HandsFree mode: ON" |

**Toggle button:**
- Single primary button. Label reads "Turn ON" when off, "Turn OFF" when on.
- Clicking it immediately writes the new state to `state.json`.
- No debouncing needed — file writes are cheap and the hook reads atomically.

**Window-close behavior:**
- Write `state.json` with `enabled: false` before destroying the window.
- Persist `window_position` to `config.json`.
- Process exits cleanly.

### Settings dialog

- Modal, ~400×280, always-on-top.
- Opened by clicking the gear in the main window.

```
┌── HandsFree Claude — Settings ──────────────┐
│                                              │
│  End sound:  [ Default           ▾ ]  [▶]    │
│                                              │
│  Custom sound file:                          │
│  [ /path/to/mysound.mp3    ] [Browse…] [Clear] │
│                                              │
│  ☐ Mute sound                                │
│                                              │
│                          [ Cancel ] [ Save ] │
└──────────────────────────────────────────────┘
```

- **End sound dropdown** — populated from files in `assets/end_sounds/`. Labels are derived from filenames (e.g. `default.mp3` → "Default"). When a custom sound is set, this dropdown is visually dimmed but still readable.
- **Custom sound file** — "Browse…" opens `tkinter.filedialog.askopenfilename` filtered to `.mp3;.wav`. "Clear" sets `custom_sound_path` to null. Path is displayed truncated from the left if too long.
- **Mute sound** — when checked, `config.mute_sound = true`.
- **Preview (▶)** — plays whichever sound is currently effective (custom path wins over dropdown). Stops any previous preview first.
- **Save** — writes to `config.json`, closes dialog. **Cancel** — discards unsaved changes, closes dialog.

## Hooks

### Installation

`settings_installer.py` from Oi-Claude is used verbatim. `install-hooks` calls it twice:

```python
install_hook(settings_path, "handsfree-claude-hook", event_name="PreToolUse", timeout_seconds=5)
install_hook(settings_path, "handsfree-claude-hook", event_name="Stop",       timeout_seconds=5)
```

Timeout is 5s (down from Oi-Claude's 15s) because we no longer do voice capture. Matcher is `"*"` (all tools).

### Hook entry point — `handsfree-claude-hook`

Declared in `pyproject.toml` under `[project.scripts]`. Reads one JSON event from stdin, dispatches on `hook_event_name`.

**PreToolUse branch:**
1. Load `state.json`. If missing/corrupt, exit 0 silently.
2. If `enabled` is false, exit 0 silently.
3. If `psutil.pid_exists(pid)` is false, exit 0 silently.
4. Emit to stdout: `{"decision": "allow", "reason": "HandsFree mode active"}`. Exit 0.

**Stop branch:**
1. Load `state.json`. If not enabled or PID dead, exit 0 silently.
2. Load `config.json`. If `mute_sound`, exit 0 silently.
3. Resolve effective sound file: `custom_sound_path` if set and exists, else `assets/end_sounds/<end_sound_file>`. If neither resolves, log and exit 0.
4. Spawn a detached subprocess: `python -m handsfree_claude.audio <filepath>`. Do not wait.
5. Exit 0 immediately.

### Claude Code `settings.json` shape after install

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "handsfree-claude-hook", "timeout": 5 }] }
    ],
    "Stop": [
      { "matcher": "*", "hooks": [{ "type": "command", "command": "handsfree-claude-hook", "timeout": 5 }] }
    ]
  }
}
```

## Audio

- **Library:** the same library Oi-Claude uses in `audio.py` (to be confirmed when the file is read during the implementation plan; likely `pygame.mixer` or similar). Whatever it is, we keep it to avoid introducing a new audio dep.
- **Playback path:** the Stop hook spawns `python -m handsfree_claude.audio <path>` as a detached background process so the hook returns in milliseconds. The subprocess loads the file, plays to completion, exits.
- **Preview path:** `SettingsDialog` calls a synchronous `audio.play_end_sound_preview(path)` and can stop it with `audio.stop_end_sound_preview()`.
- **Failure handling:** audio errors are swallowed and logged to `~/.handsfree-claude/logs/audio.log`. The hook must never fail Claude Code.

## CLI

Entry point: `handsfree-claude` (declared in `pyproject.toml` scripts).

| Command | Behavior |
|---|---|
| `handsfree-claude` (no args) | Alias for `run`. |
| `handsfree-claude run` | Opens the window. Refuses to start if `state.json` has a live PID (prints "HandsFree Claude is already running (PID N)"). |
| `handsfree-claude install-hooks` | Registers PreToolUse + Stop hooks in `~/.claude/settings.json`. Idempotent. |
| `handsfree-claude uninstall-hooks` | Removes both hook entries. Leaves other hooks untouched. |
| `handsfree-claude status` | Prints: running-or-not (with PID if alive), hooks installed/not, config location. |

Hidden entry point: `handsfree-claude-hook` → `handsfree_claude.hook:main`. This is what Claude Code invokes.

## Edge Cases

| Scenario | Behavior |
|---|---|
| `state.json` missing | Hook exits 0 silently (falls through to normal Claude prompt). |
| `state.json` corrupt JSON | Same as missing. |
| `state.json` has `enabled=true` but PID dead | Hook treats as disabled. Next `run` overwrites the file. |
| User runs `handsfree-claude` while a live window exists | Second instance errors out with PID of existing. |
| User closes window while a Claude session is active | `state.json` rewritten with `enabled=false` on exit; in-flight PreToolUse events after that get a normal prompt. |
| Custom sound file was set but has been deleted | Fall back to `end_sound_file` from bundled assets. Log warning. |
| User runs `install-hooks` twice | Second call is a no-op (idempotent per existing `settings_installer.py`). |
| Hooks installed but HandsFree Claude never launched | Hook sees no state file → exits 0 silently. Hooks can live permanently in Claude settings. |
| Audio playback subprocess fails | Error logged to `~/.handsfree-claude/logs/audio.log`. Hook already returned 0. |

## Testing

**Unit tests (`pytest`):**
- `test_state.py` — round-trip read/write; PID liveness with mocked `psutil.pid_exists`; corrupt-file handling; missing-file handling.
- `test_config.py` — defaults applied when fields missing; save/load round-trip; custom_sound_path null and non-null.
- `test_hook.py` — PreToolUse emits allow when enabled+alive; emits nothing when disabled / PID dead / file missing. Stop spawns audio subprocess when enabled+unmuted; no subprocess when muted or disabled.
- `test_settings_installer.py` — idempotency; preserves foreign hooks on other events; uninstall only removes matching command.

**Manual smoke test (covers UI):**
1. `pip install -e .` then `handsfree-claude install-hooks`.
2. `handsfree-claude` → window opens.
3. Toggle on → status light green.
4. Run a Claude Code session that uses a tool → verify no permission prompt and tool ran.
5. Wait for Claude to finish → verify end sound plays.
6. Open Settings → change end sound, preview, save → verify persistence.
7. Set a custom sound → preview → save → trigger a Stop → verify custom plays.
8. Check Mute → trigger a Stop → verify silence.
9. Close window → verify `state.json` has `enabled: false`.
10. Run a Claude session with window closed → verify normal permission prompt.

## Dependencies

Declared in `pyproject.toml`:

- `customtkinter` — same Tk wrapper Oi-Claude uses.
- `pillow` — window icon (minor; can drop if not needed).
- `psutil` — cross-platform PID liveness.
- Audio library matching Oi-Claude's existing choice (confirmed during implementation).
- `pytest` (dev-only).

Python 3.10+. Cross-platform (Windows / macOS / Linux), primary development on Windows 11.

## Open Questions

None remaining at design time. The audio library choice is deferred to the implementation plan, where `audio.py` will be read in full and the existing dependency preserved.
