from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Sequence

from core.models import RenameItem


UNDO_LOG_PREFIX = "rename_undo_"


def create_undo_log_file(items: Sequence[RenameItem], folder: Path) -> Path:
    actionable_items = [item for item in items if not item.is_noop]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = folder / f"{UNDO_LOG_PREFIX}{timestamp}.json"

    # Ensure log names stay unique when multiple operations occur in one second.
    suffix_index = 1
    while log_path.exists():
        log_path = folder / f"{UNDO_LOG_PREFIX}{timestamp}_{suffix_index}.json"
        suffix_index += 1

    payload = {
        "version": 1,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "folder": str(folder),
        "entries": [
            {
                "from": item.target_name,
                "to": item.source_name,
            }
            for item in actionable_items
        ],
    }

    log_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return log_path


def load_rollback_items(log_path: Path) -> list[RenameItem]:
    payload = json.loads(log_path.read_text(encoding="utf-8"))
    folder_text = payload.get("folder")
    entries = payload.get("entries")

    if not isinstance(folder_text, str) or not folder_text.strip():
        raise ValueError("Undo log is missing a valid folder path.")
    if not isinstance(entries, list):
        raise ValueError("Undo log is missing entries.")

    folder = Path(folder_text)
    rollback_items: list[RenameItem] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Undo log entry {index} is invalid.")

        from_name = entry.get("from")
        to_name = entry.get("to")

        if not isinstance(from_name, str) or not isinstance(to_name, str):
            raise ValueError(f"Undo log entry {index} is invalid.")

        rollback_items.append(
            RenameItem(
                source_path=folder / from_name,
                target_path=folder / to_name,
            )
        )

    return rollback_items
