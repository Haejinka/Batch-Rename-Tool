from __future__ import annotations

from core.models import RenameItem


def preview_item_matches_query(item: RenameItem, query: str) -> bool:
    normalized_query = query.strip().lower()
    if not normalized_query:
        return True

    return (
        normalized_query in item.source_name.lower()
        or normalized_query in item.target_name.lower()
    )
