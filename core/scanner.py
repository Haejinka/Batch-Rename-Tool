from __future__ import annotations

from pathlib import Path
import re

from core.config import VIDEO_EXTENSIONS


_CYCLE_SUFFIX_PATTERN = re.compile(r"^(?P<base>.+?)_(?P<cycle>\d+)$")
_NATURAL_TOKEN_PATTERN = re.compile(r"\d+|\D+")


def _natural_sort_tokens(value: str) -> tuple[tuple[int, int | str], ...]:
    tokens: list[tuple[int, int | str]] = []
    for token in _NATURAL_TOKEN_PATTERN.findall(value.lower()):
        if token.isdigit():
            tokens.append((0, int(token)))
        else:
            tokens.append((1, token))
    return tuple(tokens)


def _split_cycle_suffix(stem: str, all_stems: set[str]) -> tuple[str, int]:
    match = _CYCLE_SUFFIX_PATTERN.match(stem)
    if not match:
        return stem, 0

    base_stem = match.group("base")
    if base_stem not in all_stems:
        return stem, 0

    return base_stem, int(match.group("cycle"))


def _sort_key(path: Path, all_stems: set[str]) -> tuple:
    base_stem, cycle_number = _split_cycle_suffix(path.stem, all_stems)
    return (
        cycle_number,
        _natural_sort_tokens(base_stem),
        _natural_sort_tokens(path.suffix),
        _natural_sort_tokens(path.name),
        path.name,
    )


def discover_video_files(folder: Path, allowed_extensions: set[str] | None = None) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        return []

    extensions = VIDEO_EXTENSIONS if allowed_extensions is None else allowed_extensions
    normalized_extensions = {ext.lower() for ext in extensions}

    files = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in normalized_extensions
    ]

    all_stems = {path.stem for path in files}
    return sorted(files, key=lambda path: _sort_key(path, all_stems))
