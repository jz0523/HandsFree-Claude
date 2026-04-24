from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
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
