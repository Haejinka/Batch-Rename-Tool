from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from core.models import RenameItem
from core.renamer import apply_rename_plan


class RenamerTests(unittest.TestCase):
    def test_renames_files_and_preserves_extensions(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source_one = folder / "clip_a.mp4"
            source_two = folder / "clip_b.mov"
            source_one.touch()
            source_two.touch()

            items = [
                RenameItem(source_path=source_one, target_path=folder / "Reel_01.mp4"),
                RenameItem(source_path=source_two, target_path=folder / "Reel_02.mov"),
            ]

            result = apply_rename_plan(items)

            self.assertEqual(result.renamed_count, 2)
            self.assertFalse(result.errors)
            self.assertTrue((folder / "Reel_01.mp4").exists())
            self.assertTrue((folder / "Reel_02.mov").exists())

    def test_handles_name_swaps_safely(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            file_a = folder / "A.mp4"
            file_b = folder / "B.mp4"
            file_a.touch()
            file_b.touch()

            items = [
                RenameItem(source_path=file_a, target_path=folder / "B.mp4"),
                RenameItem(source_path=file_b, target_path=folder / "A.mp4"),
            ]

            result = apply_rename_plan(items)

            self.assertEqual(result.renamed_count, 2)
            self.assertFalse(result.errors)
            self.assertTrue((folder / "A.mp4").exists())
            self.assertTrue((folder / "B.mp4").exists())

    def test_noop_items_are_skipped(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source = folder / "clip.mp4"
            source.touch()

            items = [RenameItem(source_path=source, target_path=source)]
            result = apply_rename_plan(items)

            self.assertEqual(result.renamed_count, 0)
            self.assertEqual(result.skipped_count, 1)
            self.assertFalse(result.errors)


if __name__ == "__main__":
    unittest.main()
