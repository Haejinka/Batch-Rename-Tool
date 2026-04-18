from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from core.scanner import discover_video_files


class ScannerTests(unittest.TestCase):
    def test_cycle_suffix_files_sort_after_primary_cycle(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            for name in (
                "HOOK 1.mp4",
                "HOOK 1_1.mp4",
                "HOOK 2.mp4",
                "HOOK 2_1.mp4",
                "HOOK 3.mp4",
                "HOOK 3_1.mp4",
            ):
                (folder / name).touch()

            ordered_files = discover_video_files(folder)

            self.assertEqual(
                [path.name for path in ordered_files],
                [
                    "HOOK 1.mp4",
                    "HOOK 2.mp4",
                    "HOOK 3.mp4",
                    "HOOK 1_1.mp4",
                    "HOOK 2_1.mp4",
                    "HOOK 3_1.mp4",
                ],
            )

    def test_filters_extensions_and_uses_natural_sort(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            for name in ("clip_10.mp4", "clip_2.mp4", "clip_1.MOV", "notes.txt"):
                (folder / name).touch()

            ordered_files = discover_video_files(folder)

            self.assertEqual(
                [path.name for path in ordered_files],
                ["clip_1.MOV", "clip_2.mp4", "clip_10.mp4"],
            )

    def test_supports_common_video_file_types(self) -> None:
        with TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            for name in (
                "a.avi",
                "b.MKV",
                "c.webm",
                "d.m4v",
                "e.mpg",
                "f.MPEG",
                "g.ts",
                "h.mts",
                "i.m2ts",
                "ignore.jpg",
                "ignore.txt",
            ):
                (folder / name).touch()

            ordered_files = discover_video_files(folder)

            self.assertEqual(
                [path.name for path in ordered_files],
                ["a.avi", "b.MKV", "c.webm", "d.m4v", "e.mpg", "f.MPEG", "g.ts", "h.mts", "i.m2ts"],
            )


if __name__ == "__main__":
    unittest.main()
