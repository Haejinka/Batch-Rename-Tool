from __future__ import annotations

import os
import re
from typing import Sequence

from core.models import RenameItem

INVALID_FILENAME_CHARS_PATTERN = re.compile(r"[<>:\"/\\|?*\x00-\x1F]")
WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *{f"COM{i}" for i in range(1, 10)},
    *{f"LPT{i}" for i in range(1, 10)},
}


def _has_invalid_filename_chars(value: str) -> bool:
    return INVALID_FILENAME_CHARS_PATTERN.search(value) is not None


def _is_reserved_windows_name(stem: str) -> bool:
    return stem.upper() in WINDOWS_RESERVED_NAMES


def validate_naming_inputs(
    prefix: str,
    suffix: str,
    start_number: int,
    number_padding: int,
) -> list[str]:
    errors: list[str] = []

    if not prefix.strip():
        errors.append("Prefix is required.")
    if _has_invalid_filename_chars(prefix):
        errors.append("Prefix contains invalid Windows filename characters.")
    if _has_invalid_filename_chars(suffix):
        errors.append("Suffix contains invalid Windows filename characters.")
    if start_number < 0:
        errors.append("Starting number must be 0 or greater.")
    if number_padding < 0:
        errors.append("Number padding must be 0 or greater.")
    if number_padding > 12:
        errors.append("Number padding must be 12 or less.")

    return errors


def validate_preview_items(items: Sequence[RenameItem]) -> list[str]:
    errors: list[str] = []
    if not items:
        return ["No video files were found in the selected folder."]

    source_paths_normalized = {os.path.normcase(str(item.source_path)) for item in items}

    seen_targets: dict[str, str] = {}
    duplicate_target_names: set[str] = set()

    for item in items:
        target_name = item.target_name
        target_stem = item.target_path.stem.strip(" .")
        target_key = os.path.normcase(str(item.target_path))

        if not target_stem:
            errors.append(f"Invalid target name generated for {item.source_name}.")
        if target_name.endswith(" ") or target_name.endswith("."):
            errors.append(f"Target name cannot end with a space or period: {target_name}")
        if _has_invalid_filename_chars(target_name):
            errors.append(f"Target name contains invalid characters: {target_name}")
        if _is_reserved_windows_name(target_stem):
            errors.append(f"Target name uses a reserved Windows keyword: {target_name}")

        existing_source = seen_targets.get(target_key)
        if existing_source and existing_source != item.source_name:
            duplicate_target_names.add(item.target_name)
        else:
            seen_targets[target_key] = item.source_name

        if item.target_path.exists() and target_key not in source_paths_normalized:
            errors.append(f"Target file already exists: {target_name}")

    if duplicate_target_names:
        duplicate_names = ", ".join(sorted(duplicate_target_names))
        errors.append(f"Duplicate target filenames detected: {duplicate_names}")

    deduped_errors: list[str] = []
    seen_error_messages: set[str] = set()
    for error in errors:
        if error not in seen_error_messages:
            deduped_errors.append(error)
            seen_error_messages.add(error)

    return deduped_errors
