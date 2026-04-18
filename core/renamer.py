from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence
import uuid

from core.models import RenameItem


@dataclass(frozen=True)
class RenameResult:
    renamed_count: int
    skipped_count: int
    errors: list[str]


def apply_rename_plan(items: Sequence[RenameItem]) -> RenameResult:
    actionable_items = [item for item in items if not item.is_noop]
    skipped_count = len(items) - len(actionable_items)

    if not actionable_items:
        return RenameResult(renamed_count=0, skipped_count=skipped_count, errors=[])

    batch_token = uuid.uuid4().hex
    temp_mappings: list[tuple] = []
    moved_to_target: list[tuple] = []

    try:
        # Phase 1: move each file to a unique temp name to avoid cross-collisions.
        for index, item in enumerate(actionable_items):
            temp_name = f".__rename_tool_tmp_{batch_token}_{index}{item.source_path.suffix}"
            temp_path = item.source_path.with_name(temp_name)

            while temp_path.exists():
                temp_name = (
                    f".__rename_tool_tmp_{batch_token}_{index}_{uuid.uuid4().hex[:6]}"
                    f"{item.source_path.suffix}"
                )
                temp_path = item.source_path.with_name(temp_name)

            item.source_path.rename(temp_path)
            temp_mappings.append((temp_path, item.target_path, item.source_path))

        # Phase 2: move from temp names to final targets.
        for temp_path, target_path, original_path in temp_mappings:
            temp_path.rename(target_path)
            moved_to_target.append((target_path, original_path))

        return RenameResult(
            renamed_count=len(actionable_items),
            skipped_count=skipped_count,
            errors=[],
        )

    except Exception as exc:  # pragma: no cover - exercised in manual error paths.
        rollback_errors: list[str] = []

        for temp_path, _, original_path in reversed(temp_mappings):
            try:
                if temp_path.exists():
                    temp_path.rename(original_path)
            except Exception as rollback_exc:  # pragma: no cover
                rollback_errors.append(
                    f"Rollback failed for {original_path.name}: {rollback_exc}"
                )

        for target_path, original_path in reversed(moved_to_target):
            try:
                if target_path.exists() and not original_path.exists():
                    target_path.rename(original_path)
            except Exception as rollback_exc:  # pragma: no cover
                rollback_errors.append(
                    f"Rollback failed for {original_path.name}: {rollback_exc}"
                )

        errors = [f"Rename failed: {exc}"]
        errors.extend(rollback_errors)
        return RenameResult(renamed_count=0, skipped_count=skipped_count, errors=errors)
