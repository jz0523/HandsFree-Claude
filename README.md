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
