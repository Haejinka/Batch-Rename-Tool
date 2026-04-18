from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from core.models import RenameItem
from core.validator import validate_naming_inputs, validate_preview_items


class ValidatorTests(unittest.TestCase):
    def test_rejects_invalid_prefix_characters(self) -> None:
        errors = validate_naming_inputs(
            prefix="Reel*",
            suffix="",
            start_number=1,
            number_padding=2,
        )
        self.assertTrue(any("Prefix contains invalid" in error for error in errors))

    def test_detects_duplicate_target_names(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source_one = folder / "a.mp4"
            source_two = folder / "b.mp4"
            source_one.touch()
            source_two.touch()

            duplicate_target = folder / "Reel_01.mp4"
            items = [
                RenameItem(source_path=source_one, target_path=duplicate_target),
                RenameItem(source_path=source_two, target_path=duplicate_target),
            ]

            errors = validate_preview_items(items)
            self.assertTrue(any("Duplicate target filenames" in error for error in errors))

    def test_detects_existing_file_collision(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            source_file = folder / "source.mp4"
            source_file.touch()

            occupied_target = folder / "Reel_01.mp4"
            occupied_target.touch()

            items = [
                RenameItem(source_path=source_file, target_path=occupied_target),
            ]

            errors = validate_preview_items(items)
            self.assertTrue(any("Target file already exists" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
