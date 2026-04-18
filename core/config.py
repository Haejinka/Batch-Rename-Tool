"""Shared configuration for the batch renamer app."""

VIDEO_EXTENSION_ORDER = [
    ".mp4",
    ".mov",
    ".mxf",
    ".avi",
    ".mkv",
    ".wmv",
    ".webm",
    ".m4v",
    ".mpg",
    ".mpeg",
    ".ts",
    ".mts",
    ".m2ts",
]
VIDEO_EXTENSIONS = set(VIDEO_EXTENSION_ORDER)

PRESETS = {
    "Organic": {"prefix": "Reel", "suffix": ""},
    "Ad": {"prefix": "Reel", "suffix": " (Ad)"},
}

CUSTOM_PRESET = "Custom"
PRESET_NAMES = [*PRESETS.keys(), CUSTOM_PRESET]

DEFAULT_START_NUMBER = 1
DEFAULT_NUMBER_PADDING = 2
DEFAULT_PREFIX = PRESETS["Organic"]["prefix"]
DEFAULT_SUFFIX = PRESETS["Organic"]["suffix"]
