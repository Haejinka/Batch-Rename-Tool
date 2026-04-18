from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PRESETS_FILENAME = ".rename_tool_presets.json"
SETTINGS_FILENAME = ".rename_tool_settings.json"


def _read_json_file(path: Path) -> Any:
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_custom_presets(app_root: Path, built_in_names: set[str]) -> dict[str, dict[str, str]]:
    path = app_root / PRESETS_FILENAME
    payload = _read_json_file(path)
    if not isinstance(payload, dict):
        return {}

    presets: dict[str, dict[str, str]] = {}
    for name, value in payload.items():
        if not isinstance(name, str):
            continue

        clean_name = name.strip()
        if not clean_name or clean_name in built_in_names:
            continue

        if not isinstance(value, dict):
            continue

        prefix = value.get("prefix")
        suffix = value.get("suffix", "")
        if not isinstance(prefix, str) or not isinstance(suffix, str):
            continue
        if not prefix.strip():
            continue

        presets[clean_name] = {
            "prefix": prefix,
            "suffix": suffix,
        }

    return presets


def save_custom_presets(app_root: Path, custom_presets: dict[str, dict[str, str]]) -> None:
    payload: dict[str, dict[str, str]] = {}
    for name, preset in custom_presets.items():
        prefix = preset.get("prefix", "")
        suffix = preset.get("suffix", "")
        if not name.strip() or not prefix.strip():
            continue
        payload[name] = {
            "prefix": prefix,
            "suffix": suffix,
        }

    path = app_root / PRESETS_FILENAME
    _write_json_file(path, payload)


def load_app_settings(app_root: Path) -> dict[str, Any]:
    path = app_root / SETTINGS_FILENAME
    payload = _read_json_file(path)
    if not isinstance(payload, dict):
        return {}
    return payload


def save_app_settings(app_root: Path, settings: dict[str, Any]) -> None:
    path = app_root / SETTINGS_FILENAME
    _write_json_file(path, settings)
