# HandsFree Claude

> Auto-approve Claude Code tool-call permissions with one click, and get a sound when your session finishes.

**Read in:** English · [简体中文](README.zh.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB.svg)](https://www.python.org/downloads/)
[![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#platform-prerequisites)

A minimal always-on-top Tk window that auto-approves Claude Code tool-call permission prompts while **HandsFree mode** is on, and plays a sound when Claude finishes a session. No daemon, no HTTP server, no voice recognition.

Derived from [Oi-Claude](https://github.com/jz0523/Oi-Claude), stripped down to only the pieces most people actually use.

---

## How it looks

```
┌───────────────────────────────────────┐
│  HandsFree Claude              ⚙      │
│                                        │
│       ●  HandsFree mode: ON            │
│                                        │
│       [       Turn OFF       ]         │
└───────────────────────────────────────┘
```

Three elements: name, status light (gray = off, green = on), toggle. Gear opens settings.

---

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux
- [Claude Code](https://claude.com/claude-code) installed (CLI or VS Code extension)

### Platform prerequisites

| Platform | What you need |
|---|---|
| **Windows** | Nothing extra — the python.org installer ships Tk. |
| **macOS** | A Tk-enabled Python. The python.org installer works; Homebrew's bare `python3` does not. Install `brew install python-tk@3.12` (or your version) if needed. |
| **Linux** | The system Tk package: `sudo apt install python3-tk` (Debian/Ubuntu) or `sudo dnf install python3-tkinter` (Fedora). |

---

## Install

```bash
git clone https://github.com/jz0523/HandsFree-Claude.git
cd HandsFree-Claude
pip install -e .
handsfree-claude install-hooks
```

Then **fully restart any running Claude Code session** — Claude Code reads `~/.claude/settings.json` at startup and does not hot-reload hooks.

### Windows: if `handsfree-claude` isn't found

Python's user-site `Scripts` directory isn't always on PATH. Pick one:

**A. Use the module form (works anywhere):**

```powershell
python -m handsfree_claude install-hooks
python -m handsfree_claude
```

**B. Add the Scripts directory to your user PATH (one-time fix):**

```powershell
$scriptsDir = "$([Environment]::GetFolderPath('ApplicationData'))\Python\Python$(python -c 'import sys;print(str(sys.version_info.major)+str(sys.version_info.minor))')\Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$scriptsDir*") {
  [Environment]::SetEnvironmentVariable("Path", "$userPath;$scriptsDir", "User")
}
```

Then close and reopen PowerShell.

### Coming from Oi-Claude

If you used the predecessor [Oi-Claude](https://github.com/jz0523/Oi-Claude), uninstall its hooks first (`oi-claude uninstall-hooks`). `handsfree-claude install-hooks` also detects leftover `oi-claude-hook` entries and prints a warning — the two tools have overlapping matchers and shouldn't both be registered.

---

## Use

Open the window:

```bash
handsfree-claude
```

Toggle HandsFree mode **on** → subsequent Claude Code tool prompts auto-approve and an end-sound plays when Claude finishes responding.
Toggle **off**, or close the window, → prompts behave normally again.

---

## Settings

Click the gear icon:

- **End sound** — pick one of the bundled sounds.
- **Custom sound file** — browse to your own `.mp3` or `.wav`. Overrides the dropdown.
- **Mute sound** — keeps auto-approval on but silences the end-of-session sound.

---

## Commands

| Command | What it does |
|---|---|
| `handsfree-claude` | Open the window (same as `run`). |
| `handsfree-claude install-hooks` | Register hooks in `~/.claude/settings.json`. Idempotent; scrubs stale entries. |
| `handsfree-claude uninstall-hooks` | Remove every variant of our hook. |
| `handsfree-claude status` | Show whether the window is running and whether hooks are installed. |

---

## How it works

- The window owns `~/.handsfree-claude/state.json` with `{enabled, pid}`.
- Two Claude Code hooks (`PreToolUse`, `Stop`) invoke `handsfree-claude-hook` as a short-lived subprocess.
- The hook reads the state file. If `enabled=true` **and** the window PID is still alive (`psutil.pid_exists`), it emits a `PreToolUse` `permissionDecision: "allow"` response, or fires a detached subprocess to play the end sound on `Stop`. Otherwise it exits silently.
- Closing the window writes `enabled=false` and clears the PID, so nothing stays auto-approved after close.

On Windows, the installer writes the hook command with forward slashes because Claude Code pipes hook commands through Git Bash, which eats backslashes as escape characters.

---

## Troubleshooting

**Still being asked for permission with HandsFree mode ON.**

1. Confirm the status light is green and `~/.handsfree-claude/state.json` shows `"enabled": true` with your window's PID.
2. Confirm the hook is registered: `handsfree-claude status` should say `Hooks installed: yes`.
3. **Fully restart your Claude Code session.** Hooks are loaded once at startup.
4. Still not working? Enable diagnostic logging:

   ```bash
   # macOS / Linux
   export HANDSFREE_CLAUDE_DEBUG=1

   # Windows PowerShell
   $env:HANDSFREE_CLAUDE_DEBUG = "1"
   ```

   Restart Claude Code, trigger a tool call, then check `~/.handsfree-claude/logs/hook.log`. It records every invocation, the raw stdin, and the decision. Attach that log if you file an issue.

**Auto-approval stops when I close the window.**

That's intended. Closing is an explicit off-switch — HandsFree never persists an "on" state across launches.

---

## Development

```bash
pip install -e ".[dev]"
pytest
```

47 unit tests cover state I/O, PID-liveness, config I/O, hook dispatch, CLI commands, and installer idempotency. The Tk UI is exercised by a manual smoke test.

---

## License

[MIT](LICENSE)
