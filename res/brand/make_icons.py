#!/usr/bin/env python3
"""Regenerate every app/tray icon of the client from the brand logo.

Inputs (in res/brand/):
  logo.png       required. Full-colour square app icon, 1024x1024 or larger.
  logo-mono.png  optional. White glyph on a transparent background, used for
                 the tray and the Android notification icon. If missing, a
                 white silhouette of logo.png's opaque pixels is used.
  logo.svg       optional. Vector version shown inside the app. If missing,
                 logo.png is embedded in an SVG wrapper.

Usage (from the repository root):  python3 res/brand/make_icons.py
Needs Pillow:  pip install pillow
"""
import base64
import io
import os
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BRAND = os.path.join(ROOT, "res", "brand")


def p(*parts):
    return os.path.join(ROOT, *parts)


def load(name):
    path = os.path.join(BRAND, name)
    return Image.open(path).convert("RGBA") if os.path.isfile(path) else None


def fit(img, size):
    return img.resize((size, size), Image.LANCZOS)


def save_png(img, size, *path):
    fit(img, size).save(p(*path))


def tint(mono, rgb):
    """Recolour a glyph, keeping its alpha."""
    out = Image.new("RGBA", mono.size, rgb + (0,))
    out.putalpha(mono.getchannel("A"))
    return out


def padded(img, canvas, inner):
    """Centre img scaled to `inner` px on a transparent `canvas` px square."""
    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    off = (canvas - inner) // 2
    out.alpha_composite(fit(img, inner), (off, off))
    return out


def main():
    logo = load("logo.png")
    if logo is None:
        sys.exit("res/brand/logo.png not found")
    if logo.width != logo.height:
        sys.exit("logo.png must be square")
    mono = load("logo-mono.png")
    if mono is None:
        alpha = logo.getchannel("A").point(lambda a: 255 if a > 127 else 0)
        mono = Image.new("RGBA", logo.size, (255, 255, 255, 0))
        mono.putalpha(alpha)
    white = tint(mono, (255, 255, 255))
    black = tint(mono, (0, 0, 0))

    # Desktop (Rust + Linux packages)
    save_png(logo, 1024, "res", "icon.png")
    save_png(logo, 1024, "res", "mac-icon.png")
    for s in (32, 64, 128):
        save_png(logo, s, "res", f"{s}x{s}.png")
    save_png(logo, 256, "res", "128x128@2x.png")
    logo.save(p("res", "icon.ico"), sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
    logo.save(p("res", "tray-icon.ico"), sizes=[(16, 16), (24, 24), (32, 32)])
    # macOS menu bar uses these as template images (only alpha matters)
    save_png(black, 60, "res", "mac-tray-dark-x2.png")
    save_png(black, 48, "res", "mac-tray-light-x2.png")

    # Windows Flutter runner
    logo.save(p("flutter", "windows", "runner", "resources", "app_icon.ico"),
              sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])

    # macOS app bundle
    logo.save(p("flutter", "macos", "Runner", "AppIcon.icns"))

    # In-app logo
    svg = os.path.join(BRAND, "logo.svg")
    if os.path.isfile(svg):
        data = open(svg, encoding="utf-8").read()
    else:
        buf = io.BytesIO()
        fit(logo, 256).save(buf, "PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        data = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">'
                f'<image width="256" height="256" href="data:image/png;base64,{b64}"/></svg>')
    for name in ("icon.svg",):
        open(p("flutter", "assets", name), "w", encoding="utf-8").write(data)
    open(p("res", "logo.svg"), "w", encoding="utf-8").write(data)
    open(p("res", "scalable.svg"), "w", encoding="utf-8").write(data)

    # Android
    android = ("flutter", "android", "app", "src", "main", "res")
    for folder, base in (("mdpi", 48), ("hdpi", 72), ("xhdpi", 96),
                         ("xxhdpi", 144), ("xxxhdpi", 192)):
        d = android + (f"mipmap-{folder}",)
        save_png(logo, base, *d, "ic_launcher.png")
        save_png(logo, base, *d, "ic_launcher_round.png")
        fg = base * 9 // 4  # 108dp canvas, logo kept in the 72dp safe zone
        padded(logo, fg, fg * 2 // 3).save(p(*d, "ic_launcher_foreground.png"))
        save_png(white, base // 2, *d, "ic_stat_logo.png")

    # iOS
    ios = ("flutter", "ios", "Runner", "Assets.xcassets", "AppIcon.appiconset")
    flat = Image.new("RGBA", logo.size, (255, 255, 255, 255))
    flat.alpha_composite(logo)  # App Store rejects transparent icons
    flat = flat.convert("RGB")
    for f in os.listdir(p(*ios)):
        if f.startswith("Icon-App-") and f.endswith(".png"):
            dims, scale = f[len("Icon-App-"):-4].split("@")
            px = round(float(dims.split("x")[0]) * int(scale[:-1]))
            flat.resize((px, px), Image.LANCZOS).save(p(*ios, f))

    print("Icons regenerated.")


if __name__ == "__main__":
    main()
