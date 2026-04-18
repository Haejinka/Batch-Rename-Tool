from pathlib import Path
import unittest

from core.naming import build_rename_items, format_sequence_number


class NamingTests(unittest.TestCase):
    def test_organic_preset_pattern(self) -> None:
        files = [Path("clip_a.mp4"), Path("clip_b.mov"), Path("clip_c.mxf")]

        items = build_rename_items(
            source_files=files,
            prefix="Reel",
            suffix="",
            start_number=1,
            number_padding=2,
        )

        self.assertEqual(
            [item.target_name for item in items],
            ["Reel_01.mp4", "Reel_02.mov", "Reel_03.mxf"],
        )

    def test_ad_preset_pattern(self) -> None:
        files = [Path("clip_a.mp4"), Path("clip_b.mp4")]

        items = build_rename_items(
            source_files=files,
            prefix="Reel",
            suffix=" (Ad)",
            start_number=1,
            number_padding=2,
        )

        self.assertEqual(
            [item.target_name for item in items],
            ["Reel_01 (Ad).mp4", "Reel_02 (Ad).mp4"],
        )

    def test_padding_zero_outputs_plain_numbers(self) -> None:
        self.assertEqual(format_sequence_number(9, 0), "9")


if __name__ == "__main__":
    unittest.main()
