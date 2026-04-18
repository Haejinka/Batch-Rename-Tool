from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from core.models import RenameItem
from core.renamer import apply_rename_plan
from core.undo_log import create_undo_log_file, load_rollback_items


class UndoLogTests(unittest.TestCase):
    def test_create_and_load_undo_log(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source = folder / "HOOK 1.mp4"
            source.touch()

            items = [
                RenameItem(source_path=source, target_path=folder / "Reel_01.mp4"),
            ]

            log_path = create_undo_log_file(items, folder)
            rollback_items = load_rollback_items(log_path)

            self.assertTrue(log_path.exists())
            self.assertEqual(len(rollback_items), 1)
            self.assertEqual(rollback_items[0].source_name, "Reel_01.mp4")
            self.assertEqual(rollback_items[0].target_name, "HOOK 1.mp4")

    def test_undo_log_roundtrip_restores_original_names(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            original_files = [folder / "HOOK 1.mp4", folder / "HOOK 2.mp4"]
            for file_path in original_files:
                file_path.touch()

            rename_items = [
                RenameItem(source_path=original_files[0], target_path=folder / "Reel_01.mp4"),
                RenameItem(source_path=original_files[1], target_path=folder / "Reel_02.mp4"),
            ]

            rename_result = apply_rename_plan(rename_items)
            self.assertFalse(rename_result.errors)

            log_path = create_undo_log_file(rename_items, folder)
            rollback_items = load_rollback_items(log_path)
            rollback_result = apply_rename_plan(rollback_items)

            self.assertFalse(rollback_result.errors)
            self.assertTrue((folder / "HOOK 1.mp4").exists())
            self.assertTrue((folder / "HOOK 2.mp4").exists())


if __name__ == "__main__":
    unittest.main()
