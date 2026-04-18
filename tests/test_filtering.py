from pathlib import Path
import unittest

from core.filtering import preview_item_matches_query
from core.models import RenameItem


class FilteringTests(unittest.TestCase):
    def test_empty_query_matches_all(self) -> None:
        item = RenameItem(
            source_path=Path("HOOK 1.mp4"),
            target_path=Path("Reel_01.mp4"),
        )
        self.assertTrue(preview_item_matches_query(item, ""))
        self.assertTrue(preview_item_matches_query(item, "   "))

    def test_query_matches_source_or_target_case_insensitive(self) -> None:
        item = RenameItem(
            source_path=Path("HOOK 1.mp4"),
            target_path=Path("Reel_01 (Ad).mp4"),
        )

        self.assertTrue(preview_item_matches_query(item, "hook"))
        self.assertTrue(preview_item_matches_query(item, "REEL_01"))
        self.assertTrue(preview_item_matches_query(item, "(ad)"))
        self.assertFalse(preview_item_matches_query(item, "client-x"))


if __name__ == "__main__":
    unittest.main()
