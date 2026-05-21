from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from core.storage import (
    load_app_settings,
    load_custom_presets,
    save_app_settings,
    save_custom_presets,
)


class StorageTests(unittest.TestCase):
    def test_custom_preset_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            app_root = Path(temp_dir)
            presets = {
                "Client A": {"prefix": "ClientA", "suffix": ""},
                "Client B": {"prefix": "ClientB", "suffix": " (Ad)"},
            }

            save_custom_presets(app_root, presets)
            loaded = load_custom_presets(app_root, built_in_names={"Organic", "Ad"})

            self.assertEqual(loaded, presets)

    def test_ignores_invalid_or_reserved_preset_names(self) -> None:
        with TemporaryDirectory() as temp_dir:
            app_root = Path(temp_dir)
            save_custom_presets(
                app_root,
                {
                    "Organic": {"prefix": "ShouldSkip", "suffix": ""},
                    "": {"prefix": "Blank", "suffix": ""},
                    "Valid": {"prefix": "KeepMe", "suffix": ""},
                },
            )

            loaded = load_custom_presets(app_root, built_in_names={"Organic", "Ad"})
            self.assertEqual(loaded, {"Valid": {"prefix": "KeepMe", "suffix": ""}})

    def test_settings_round_trip(self) -> None:
        with TemporaryDirectory() as temp_dir:
            app_root = Path(temp_dir)
            settings = {
                "folder": "C:/exports",
                "selected_preset": "Client A",
                "prefix": "ClientA",
                "suffix": " (Ad)",
                "separator": "-",
                "start_number": "7",
                "padding": "2",
                "selected_extensions": [".mp4", ".mov"],
                "create_undo_log": True,
                "filter_query": "hook",
            }

            save_app_settings(app_root, settings)
            loaded = load_app_settings(app_root)

            self.assertEqual(loaded, settings)


if __name__ == "__main__":
    unittest.main()
