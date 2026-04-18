from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RenameItem:
    source_path: Path
    target_path: Path

    @property
    def source_name(self) -> str:
        return self.source_path.name

    @property
    def target_name(self) -> str:
        return self.target_path.name

    @property
    def is_noop(self) -> bool:
        return self.source_path == self.target_path
