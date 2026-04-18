from __future__ import annotations

from pathlib import Path
from typing import Sequence

from core.models import RenameItem


def format_sequence_number(number: int, padding: int) -> str:
    if padding <= 0:
        return str(number)
    return str(number).zfill(padding)


def build_target_filename(
    prefix: str,
    number: int,
    padding: int,
    suffix: str,
    extension: str,
) -> str:
    sequence = format_sequence_number(number, padding)
    return f"{prefix}_{sequence}{suffix}{extension}"


def build_rename_items(
    source_files: Sequence[Path],
    prefix: str,
    suffix: str,
    start_number: int,
    number_padding: int,
) -> list[RenameItem]:
    items: list[RenameItem] = []
    number = start_number

    for source_file in source_files:
        target_name = build_target_filename(
            prefix=prefix,
            number=number,
            padding=number_padding,
            suffix=suffix,
            extension=source_file.suffix,
        )
        items.append(
            RenameItem(
                source_path=source_file,
                target_path=source_file.with_name(target_name),
            )
        )
        number += 1

    return items
