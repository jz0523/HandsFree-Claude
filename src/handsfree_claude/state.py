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
