from __future__ import annotations

from io import BytesIO
from pathlib import Path
import argparse
import subprocess
import shutil

from PIL import Image

try:
    import cairosvg
except Exception:  # pragma: no cover - depends on local cairo runtime.
    cairosvg = None

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional fallback dependency.
    sync_playwright = None


DEFAULT_SVG = Path("assets/batch-rename-icon.svg")
DEFAULT_ICO = Path("assets/app.ico")
ICON_SIZES = [16, 24, 32, 40, 48, 64, 128, 256]
RENDER_SIZE = 1024


def _find_edge_executable() -> str | None:
    candidates = [
        "msedge",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    ]

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        path_candidate = Path(candidate)
        if path_candidate.exists():
            return str(path_candidate)

    return None


def _render_svg_with_cairosvg(svg_path: Path) -> bytes:
    if cairosvg is None:
        raise RuntimeError("CairoSVG is not available in this environment.")

    return cairosvg.svg2png(
        url=str(svg_path.resolve()),
        output_width=RENDER_SIZE,
        output_height=RENDER_SIZE,
    )


def _render_svg_with_playwright(svg_path: Path) -> bytes:
    if sync_playwright is None:
        raise RuntimeError("Playwright is not available in this environment.")

    errors: list[str] = []
    with sync_playwright() as playwright:
        launchers = [
            (
                "msedge",
                lambda: playwright.chromium.launch(channel="msedge", headless=True),
            ),
            (
                "chromium",
                lambda: playwright.chromium.launch(headless=True),
            ),
        ]

        for browser_name, launcher in launchers:
            browser = None
            try:
                browser = launcher()
                page = browser.new_page(
                    viewport={"width": RENDER_SIZE, "height": RENDER_SIZE}
                )
                page.goto(svg_path.resolve().as_uri(), wait_until="networkidle")
                return page.screenshot(type="png", omit_background=True)
            except Exception as exc:
                errors.append(f"{browser_name}: {exc}")
            finally:
                if browser is not None:
                    browser.close()

    raise RuntimeError("Playwright SVG render failed: " + " | ".join(errors))


def _render_svg_with_edge(svg_path: Path) -> bytes:
    edge_executable = _find_edge_executable()
    if not edge_executable:
        raise RuntimeError("Could not locate Microsoft Edge for SVG rendering fallback.")

    output_png = svg_path.with_suffix(".render.png")
    command = [
        edge_executable,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--default-background-color=00000000",
        f"--window-size={RENDER_SIZE},{RENDER_SIZE}",
        f"--screenshot={output_png}",
        svg_path.resolve().as_uri(),
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "Edge SVG render failed: "
            + (completed.stderr.strip() or completed.stdout.strip() or "unknown error")
        )

    if not output_png.exists():
        raise RuntimeError("Edge completed but PNG output was not created.")

    try:
        return output_png.read_bytes()
    finally:
        output_png.unlink(missing_ok=True)


def _render_svg(svg_path: Path) -> bytes:
    errors: list[str] = []
    renderers = [
        ("cairosvg", _render_svg_with_cairosvg),
        ("playwright", _render_svg_with_playwright),
        ("edge", _render_svg_with_edge),
    ]

    for renderer_name, renderer in renderers:
        try:
            return renderer(svg_path)
        except Exception as exc:
            errors.append(f"{renderer_name}: {exc}")

    raise RuntimeError("All SVG renderers failed: " + " || ".join(errors))


def _normalize_icon_canvas(image: Image.Image) -> Image.Image:
    alpha_bbox = image.getchannel("A").getbbox()
    if alpha_bbox:
        image = image.crop(alpha_bbox)

    max_side = max(image.size)
    square = Image.new("RGBA", (max_side, max_side), (0, 0, 0, 0))
    square.paste(image, ((max_side - image.width) // 2, (max_side - image.height) // 2), image)
    return square


def generate_icon(svg_path: Path, ico_path: Path) -> None:
    if not svg_path.exists():
        raise FileNotFoundError(f"SVG not found: {svg_path}")

    png_bytes = _render_svg(svg_path)
    base_image = Image.open(BytesIO(png_bytes)).convert("RGBA")
    base_image = _normalize_icon_canvas(base_image)
    ico_path.parent.mkdir(parents=True, exist_ok=True)
    base_image.save(
        ico_path,
        format="ICO",
        sizes=[(size, size) for size in ICON_SIZES],
    )



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Windows ICO from an SVG source."
    )
    parser.add_argument(
        "--svg",
        type=Path,
        default=DEFAULT_SVG,
        help="Path to source SVG file",
    )
    parser.add_argument(
        "--ico",
        type=Path,
        default=DEFAULT_ICO,
        help="Path to output ICO file",
    )
    return parser.parse_args()



def main() -> None:
    args = parse_args()
    generate_icon(args.svg, args.ico)
    print(f"Generated icon: {args.ico.resolve()}")


if __name__ == "__main__":
    main()
