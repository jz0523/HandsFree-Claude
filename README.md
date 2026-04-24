# HandsFree Claude

A minimal Tk window that auto-approves Claude Code tool-call permission prompts while "HandsFree mode" is toggled on, and plays a sound when Claude finishes a session.

Derived from [Oi-Claude](https://github.com/jz0523/Oi-Claude), stripped down to just the auto-approval + end-sound behavior — no daemon, no HTTP, no voice recognition.

## Requirements

- Python 3.10+
- macOS, Linux, or Windows
- [Claude Code](https://claude.com/claude-code) installed (CLI or VS Code extension)

### Platform prerequisites

- **Windows** — nothing extra; tkinter ships with the python.org installer.
- **macOS** — use a Python that was built with Tk support. The python.org installer works; Homebrew's bare `python3` does not (install `brew install python-tk@3.12` or equivalent for your version).
- **Linux** — install the system Tk package if needed (`sudo apt install python3-tk` on Debian/Ubuntu; `sudo dnf install python3-tkinter` on Fedora).

## Install

```bash
git clone https://github.com/jz0523/HandsFree-Claude.git
cd HandsFree-Claude
pip install -e .
handsfree-claude install-hooks
```

After installing hooks, **fully restart any running Claude Code session** (quit the CLI or reload the VS Code window). Claude Code reads `~/.claude/settings.json` at startup and does not hot-reload hooks.

### Windows: if `handsfree-claude` isn't found

Python's user-site Scripts directory isn't always on PATH. Two options:

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

If you used the predecessor [Oi-Claude](https://github.com/jz0523/Oi-Claude), uninstall its hooks first (`oi-claude uninstall-hooks`) or let `handsfree-claude install-hooks` warn you — it detects leftover `oi-claude-hook` entries in your Claude settings and prints them. The two tools have overlapping hook matchers and shouldn't both be registered.

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
handsfree-claude uninstall-hooks # remove hooks (all path variants)
handsfree-claude status          # show running/installed state
```

## How it works

- The window owns `~/.handsfree-claude/state.json` with `{enabled, pid}`.
- Two Claude Code hooks (`PreToolUse`, `Stop`) invoke `handsfree-claude-hook` as a short-lived subprocess.
- The hook reads the state file. If `enabled=true` and the window PID is alive, it emits a `PreToolUse` `permissionDecision: allow` response, or fires off a detached subprocess to play the end sound on `Stop`.
- Closing the window writes `enabled=false` and clears the PID, so nothing stays auto-approved after close.

On Windows, the installer writes the hook path using forward slashes because Claude Code pipes hook commands through Git Bash, which eats backslashes as escape characters.

## Troubleshooting

**"Still being asked for permission even with HandsFree mode ON."**
1. Confirm the status light is green and `~/.handsfree-claude/state.json` shows `"enabled": true` with your window's PID.
2. Confirm the hook is registered: `handsfree-claude status` should say `Hooks installed: yes`.
3. **Restart your Claude Code session.** Hooks are loaded once at startup — a running session won't pick up new settings.
4. Still not working? Enable diagnostic logging:

   ```bash
   # macOS/Linux
   export HANDSFREE_CLAUDE_DEBUG=1
   # Windows PowerShell
   $env:HANDSFREE_CLAUDE_DEBUG = "1"
   ```

   Restart Claude Code, trigger a tool call, then check `~/.handsfree-claude/logs/hook.log`. You'll see every invocation, the raw stdin Claude Code sent, and the decision. File an issue with that log attached.

**"Cross-session approvals stop working after I close the window."**
That's intended. Closing the window is an explicit off-switch — HandsFree never persists an "on" state across launches.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
