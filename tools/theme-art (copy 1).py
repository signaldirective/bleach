#!/usr/bin/env python3
"""
Generate the image assets for the bleach theme.

    preview.png        1800x1012  the thumbnail the theme picker shows
    unlock.png          800x188   boot / lock screen mark, transparent
    preview-unlock.png  1920x1080 the boot screen as omarchy renders it

preview.png is a mock-up rather than a screenshot: a poster with the shell bar
and one window drawn over it, so the thumbnail shows the palette as well as the
art. Every colour comes from colors.toml through omarchy-theme-color.

Usage:
    python3 tools/theme-art.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
COLORS = ROOT / "colors.toml"
PREVIEW = ROOT / "preview.png"
UNLOCK = ROOT / "unlock.png"
PREVIEW_UNLOCK = ROOT / "preview-unlock.png"
POSTER = ROOT / "backgrounds" / "01.jpg"

PLYMOUTH_ASSETS = Path("/usr/share/omarchy/default/plymouth")
PREVIEW_SIZE = (1800, 1012)
SANS_BOLD = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
SANS_CONDENSED_BOLD = "/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf"
MONO = "/usr/share/fonts/TTF/DejaVuSansMono.ttf"


def palette() -> dict[str, str]:
    out = subprocess.run(["omarchy-theme-color", "--file", str(COLORS), "--all"],
                         capture_output=True, text=True, check=True).stdout
    return dict(l.split("\t") for l in out.strip().splitlines())


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    for candidate in (path, MONO, SANS_BOLD):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    raise SystemExit("no usable font")


def rgb(h: str) -> tuple[int, int, int]:
    c = h.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def rgba(h: str, a: int) -> tuple[int, int, int, int]:
    return rgb(h) + (a,)


# ------------------------------------------------------------------ preview

def terminal_lines(p: dict[str, str]) -> list[tuple[str, str]]:
    return [
        ("you@omarchy  ~/themes/bleach", p["muted"]),
        ("$ omarchy theme set bleach", p["green"]),
        ("applying bleach…", p["foreground"]),
        ("", p["foreground"]),
        ("~/themes/bleach tree", p["accent"]),
        ("colors.toml        ink, paper, and the posters' magenta", p["foreground"]),
        ("backgrounds/       four duotone posters", p["foreground"]),
        ("unlock.png         the mark", p["foreground"]),
        ("", p["foreground"]),
        ("+ 92% of the art's colour sits between 300° and 360°", p["bright_green"]),
        ("- so the theme answers it instead of copying it", p["bright_red"]),
        ("! warning: hollow in the sixth district", p["yellow"]),
        ("? hint: a shihakusho is black for a reason", p["cyan"]),
    ]


def draw_bar(img, d, p):
    height = 30
    d.rectangle([0, 0, img.width, height], fill=p["background"])
    d.line([(0, height), (img.width, height)], fill=p["lighter_background"])
    fs = font(MONO, 15)
    d.text((18, 7), "1  2  3  4", font=fs, fill=p["foreground"])
    title = "bleach"
    d.text(((img.width - d.textlength(title, font=fs)) / 2, 7), title, font=fs, fill=p["accent"])
    right = "88%   Sun Oct 18   16:45"
    d.text((img.width - d.textlength(right, font=fs) - 18, 7), right, font=fs, fill=p["muted"])


def draw_window(img, p):
    w, h = 1120, 480
    x = (img.width - w) // 2
    y = 250

    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([x, y + 8, x + w, y + h + 8], radius=18,
                                             fill=(0, 0, 0, 210))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(26)))

    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x, y, x + w, y + h], radius=14, fill=p["background"],
                        outline=p["accent"], width=2)
    d.line([(x + 1, y + 42), (x + w - 1, y + 42)], fill=p["lighter_background"])
    fs = font(MONO, 15)
    d.text((x + 18, y + 13), "bleach — fish", font=fs, fill=p["muted"])
    dots = "● ● ●"
    d.text((x + w - d.textlength(dots, font=fs) - 18, y + 13), dots, font=fs,
           fill=p["dark_foreground"])

    f = font(MONO, 17)
    ty = y + 66
    for text, colour in terminal_lines(p):
        if text:
            d.text((x + 26, ty), text, font=f, fill=colour)
        ty += 27
    d.rectangle([x + 20, ty + 4, x + 34, ty + 22], fill=p["accent"])
    return img


def build_preview(p):
    wall = Image.open(POSTER).convert("RGB").resize(PREVIEW_SIZE, Image.LANCZOS)
    img = wall.convert("RGBA")
    draw_bar(img, ImageDraw.Draw(img), p)
    img = draw_window(img, p)
    img.convert("RGB").save(PREVIEW)
    print(f"  preview.png        {PREVIEW_SIZE[0]}x{PREVIEW_SIZE[1]}")


# ------------------------------------------------------------------- unlock

def fit_text(canvas: Image.Image, text: str, fnt: ImageFont.FreeTypeFont,
             target_h: float, dx: int = 0, dy: int = 0, weight_passes: int = 6,
             colour=(255, 255, 255, 255), condense: float = 1.0) -> tuple[int, int]:
    """Draw `text` centred on `canvas`, scaled to occupy `target_h` of its height.

    Measures the glyphs and scales them to fit rather than trusting font
    metrics: that is what keeps a boot logo off the edges of its canvas.
    Returns the (width, height) the text ended up.
    """
    cw, ch = canvas.size
    big = cw
    scratch = Image.new("RGBA", (big, ch * 2), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scratch)
    for i in range(weight_passes):                      # fake the weight
        sd.text((big // 4 + i, ch // 2 + i), text, font=fnt, fill=colour)
    bbox = scratch.getbbox()
    glyphs = scratch.crop(bbox)
    scale = (ch * target_h) / glyphs.height
    glyphs = glyphs.resize((max(1, int(glyphs.width * scale * condense)),
                            max(1, int(glyphs.height * scale))), Image.LANCZOS)
    pos = ((cw - glyphs.width) // 2 + dx, (ch - glyphs.height) // 2 + dy)
    canvas.alpha_composite(glyphs, pos)
    return glyphs.size


def build_unlock(p):
    """BLEACH struck through by a blade, the gesture the posters make.

    Drawn at 4x and reduced once at the end: a boot logo is the one place in
    the theme where a soft edge is unforgivable.
    """
    W, H = 800, 188
    S = 4
    cw, ch = W * S, H * S
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    paper = rgba(p["bright_foreground"], 255)

    tw, th = fit_text(canvas, "BLEACH", font(SANS_CONDENSED_BOLD, int(600 * 1.0)),
                      0.72, weight_passes=6, colour=paper, condense=0.86)

    d = ImageDraw.Draw(canvas)
    accent = rgba(p["accent"], 255)
    # A blade rather than a bar: pointed at both ends, running lower-left to
    # upper-right through the middle of the word, as the posters slash theirs.
    blade_h = int(26 * S)
    top = ch // 2 + int(th * 0.62)
    rise = int(ch * 0.30)
    d.polygon([(int(cw * 0.035), top),
               (int(cw * 0.40), top - int(rise * 0.42) - blade_h // 2),
               (int(cw * 0.97), top - rise),
               (int(cw * 0.90), top - rise + blade_h),
               (int(cw * 0.40), top - int(rise * 0.42) + blade_h // 2)],
              fill=accent)

    canvas.resize((W, H), Image.LANCZOS).save(UNLOCK)
    print(f"  unlock.png         {W}x{H}  (wordmark {tw // S}x{th // S})")


def build_unlock_kanji(p):
    """Alternate mark for comparison: 死神 in the same treatment."""
    W, H = 800, 188
    S = 4
    cw, ch = W * S, H * S
    cjk = "/usr/share/fonts/noto-cjk/NotoSansCJK-Black.ttc"
    if not Path(cjk).exists():
        return
    canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    # CJK sits high in its em box; nudge it down a touch
    fit_text(canvas, "死神", ImageFont.truetype(cjk, int(300 * S), index=0),
             0.62, dy=int(4 * S), weight_passes=1,
             colour=rgba(p["bright_foreground"], 255))

    d = ImageDraw.Draw(canvas)
    accent = rgba(p["accent"], 255)
    blade_h = int(24 * S)
    top = ch // 2 - int(60 * S)
    rise = int(ch * 0.26)
    d.polygon([(int(cw * 0.06), top),
               (int(cw * 0.40), top - int(rise * 0.35) - blade_h // 2),
               (int(cw * 0.96), top - rise),
               (int(cw * 0.90), top - rise + blade_h),
               (int(cw * 0.40), top - int(rise * 0.35) + blade_h // 2)],
              fill=accent)

    canvas.resize((W, H), Image.LANCZOS).save("/tmp/opencode/bleach-unlock-kanji.png")
    print("  (alternate) /tmp/opencode/bleach-unlock-kanji.png")


def build_preview_unlock(p):
    """Mirrors `omarchy plymouth preview`, minus the image viewer it opens."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        logo = Image.open(UNLOCK)
        text = p["accent"]
        for name in ("bullet", "entry", "lock"):
            subprocess.run(["magick", PLYMOUTH_ASSETS / f"{name}.png", "-channel", "RGB",
                            "+level-colors", f"{text},{text}", tmp / f"{name}.png"], check=True)
        entry = Image.open(tmp / "entry.png")
        lock_h = int(entry.height * 0.8)
        lock_w = int(84 * lock_h / 96)
        subprocess.run(["magick", tmp / "lock.png", "-resize", f"{lock_w}x{lock_h}",
                        tmp / "lock-scaled.png"], check=True)

        logo_x, logo_y = (1920 - logo.width) // 2, (1080 - logo.height) // 2
        entry_x, entry_y = (1920 - entry.width) // 2, logo_y + logo.height + 40
        lock_x = entry_x - lock_w - 15
        lock_y = entry_y + entry.height // 2 - lock_h // 2
        bullet_y = entry_y + entry.height // 2 - 4

        args = ["magick", "-size", "1920x1080", f"xc:{p['background']}",
                UNLOCK, "-geometry", f"+{logo_x}+{logo_y}", "-composite",
                tmp / "entry.png", "-geometry", f"+{entry_x}+{entry_y}", "-composite",
                tmp / "lock-scaled.png", "-geometry", f"+{lock_x}+{lock_y}", "-composite"]
        for i in range(4):
            args += ["(", tmp / "bullet.png", "-resize", "7x7", ")", "-geometry",
                     f"+{entry_x + 20 + i * 12}+{bullet_y}", "-composite"]
        args += [PREVIEW_UNLOCK]
        subprocess.run(args, check=True)
    print("  preview-unlock.png 1920x1080")


def main() -> int:
    p = palette()
    print("bleach theme art:")
    build_preview(p)
    build_unlock(p)
    build_unlock_kanji(p)
    build_preview_unlock(p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
