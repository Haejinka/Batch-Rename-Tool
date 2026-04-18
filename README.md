# Export Batch Renamer

Desktop tool for renaming batch-exported videos with consistent client-friendly names.

## Features

- Modern dark-mode desktop UI with a creative-suite style layout
- Left sidebar for navigation and file-type tools
- Top toolbar for rename controls and preset actions
- Main workspace area for filtered preview and batch selection
- Pick a folder containing exported videos
- Detect supported video files in that folder (`.mp4`, `.mov`, `.mxf`, `.avi`, `.mkv`, `.wmv`, `.webm`, `.m4v`, `.mpg`, `.mpeg`, `.ts`, `.mts`, `.m2ts`)
- Include or exclude extension types per job with checkboxes
- Preview old and new names before applying changes
- Search/filter preview rows by original or new filename
- Select exactly which files to rename from the preview list
- Invert selection for visible filtered rows
- Rename everything in one click
- Optionally write an undo log and rollback in one click
- Save custom presets and reuse them later
- Remember last-used app settings between sessions
- Preserve each file's original extension
- Customize:
  - Prefix text
  - Optional suffix text
  - Starting number
  - Number padding
- Built-in presets:
  - Organic: `Reel_01`, `Reel_02`, `Reel_03`
  - Ad: `Reel_01 (Ad)`, `Reel_02 (Ad)`, `Reel_03 (Ad)`

## Run

1. Open a terminal in this folder.
2. Run:

```powershell
python app.py
```

## Tests

Run unit tests:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## Build Windows EXE

Build a standalone GUI executable (no Python required on target machine):

```powershell
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "ExportBatchRenamer" --icon "assets/app.ico" --add-data "assets/app.ico;assets" app.py
```

Output:

- `dist/ExportBatchRenamer.exe`

## Notes

- Preview table uses alternating row styling, clear include/exclude states, and smoother scrolling.
- Files are ordered with cycle-aware natural sorting before numbering.
- Example order: `HOOK 1`, `HOOK 2`, ..., `HOOK 6`, then `HOOK 1_1`, `HOOK 2_1`, ...
- Collision policy is strict: rename is blocked if any target filename already exists outside the selected batch.
- You must keep at least one extension type selected when generating a preview.
- Use `Filter` + `Invert Selection` to quickly isolate and flip large subsets.
- In preview, click the `Include` column, or highlight rows and use `Include Highlighted` / `Exclude Highlighted`.
- For fast subset workflows, highlight a large group and click `Use Highlighted Only`.
- You can multi-select rows with Ctrl+Click or Shift+Click.
- Undo log files are saved in the selected folder as `rename_undo_YYYYMMDD_HHMMSS.json`.
- Custom presets are stored in `.rename_tool_presets.json` in the app folder.
- App settings are stored in `.rename_tool_settings.json` in the app folder.
- App enforces single-instance mode on Windows; launching it again focuses the existing window.
- Rename uses a two-phase temporary move internally to safely handle cross-renames.