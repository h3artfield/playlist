"""Build Schedule Builder icons for Windows (.ico), installer wizard art, and favicons."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "packaging" / "windows"
WEB_PUBLIC = ROOT / "scheduler-ui" / "public"
SOURCE_PNG = ASSET_DIR / "ScheduleBuilder.png"
OUTPUT_ICO = ASSET_DIR / "ScheduleBuilder.ico"
INSTALLER_LARGE_BMP = ASSET_DIR / "WizardImageLarge.bmp"
INSTALLER_SMALL_BMP = ASSET_DIR / "WizardImageSmall.bmp"
ICO_SIZES = (256, 128, 64, 48, 32, 16)
WEB_FAVICON_SIZES = (32, 180)
INSTALLER_LARGE_SIZE = (164, 314)
INSTALLER_SMALL_SIZE = (55, 58)
BRAND_BG_RGBA = (15, 23, 42, 255)


def _square_canvas(img, image_module) -> tuple:
    width, height = img.size
    side = max(width, height)
    canvas = image_module.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - width) // 2, (side - height) // 2), img)
    return canvas, width, height, side


def _write_installer_wizard_images(canvas, image_module) -> None:
    """Inno Setup modern wizard: 164x314 left banner, 55x58 top-right logo."""
    large = image_module.new("RGBA", INSTALLER_LARGE_SIZE, BRAND_BG_RGBA)
    logo_large = canvas.resize((132, 132), image_module.Resampling.LANCZOS)
    large.paste(logo_large, ((INSTALLER_LARGE_SIZE[0] - 132) // 2, 72), logo_large)

    small = image_module.new("RGBA", INSTALLER_SMALL_SIZE, BRAND_BG_RGBA)
    logo_small = canvas.resize((46, 46), image_module.Resampling.LANCZOS)
    small.paste(
        logo_small,
        ((INSTALLER_SMALL_SIZE[0] - 46) // 2, (INSTALLER_SMALL_SIZE[1] - 46) // 2),
        logo_small,
    )

    for surface, path in ((large, INSTALLER_LARGE_BMP), (small, INSTALLER_SMALL_BMP)):
        flat = image_module.new("RGB", surface.size, BRAND_BG_RGBA[:3])
        flat.paste(surface, mask=surface.split()[3])
        flat.save(path, format="BMP")
        print(f"Wrote {path}")


def main() -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("Install Pillow: python -m pip install Pillow") from exc

    if not SOURCE_PNG.is_file():
        raise SystemExit(f"Missing source icon: {SOURCE_PNG}")

    img = Image.open(SOURCE_PNG).convert("RGBA")
    canvas, width, height, side = _square_canvas(img, Image)

    icons = [canvas.resize((size, size), Image.Resampling.LANCZOS) for size in ICO_SIZES]
    icons[0].save(
        OUTPUT_ICO,
        format="ICO",
        sizes=[(icon.width, icon.height) for icon in icons],
        append_images=icons[1:],
    )
    print(f"Wrote {OUTPUT_ICO} ({width}x{height} source -> square {side}px)")
    _write_installer_wizard_images(canvas, Image)

    WEB_PUBLIC.mkdir(parents=True, exist_ok=True)
    favicon_ico = WEB_PUBLIC / "favicon.ico"
    icons[0].save(
        favicon_ico,
        format="ICO",
        sizes=[(icon.width, icon.height) for icon in icons],
        append_images=icons[1:],
    )
    print(f"Wrote {favicon_ico}")

    for size in WEB_FAVICON_SIZES:
        resized = canvas.resize((size, size), Image.Resampling.LANCZOS)
        if size == 32:
            out = WEB_PUBLIC / "favicon-32.png"
        else:
            out = WEB_PUBLIC / "apple-touch-icon.png"
        resized.save(out, format="PNG")
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()