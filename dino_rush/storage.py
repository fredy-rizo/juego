"""Persistencia sencilla del récord y las preferencias."""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

from .config import DEFAULT_SAVE, SAVE_PATH


def _save_path() -> Path:
    override = os.environ.get("DINO_RUSH_SAVE")
    return Path(override).expanduser() if override else SAVE_PATH


def load_save() -> dict[str, Any]:
    data = deepcopy(DEFAULT_SAVE)
    path = _save_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            for key, default in DEFAULT_SAVE.items():
                value = raw.get(key, default)
                if isinstance(default, bool):
                    data[key] = bool(value)
                elif isinstance(default, int):
                    try:
                        data[key] = max(0, int(value))
                    except (TypeError, ValueError):
                        data[key] = default
                else:
                    data[key] = value
    except (OSError, ValueError, TypeError):
        pass
    data["best_level"] = max(1, int(data.get("best_level", 1)))
    return data


def write_save(data: dict[str, Any]) -> None:
    path = _save_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(path)
    except OSError:
        # Un récord no debe impedir que el juego siga funcionando.
        pass
