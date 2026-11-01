"""Builds the sprite reels, strips, patch thumbnail and grain texture used by the film. Re-run after changing a manifest."""
import random
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FRAMES = ROOT / "assets" / "frames"
OUT = ROOT / "assets" / "reels"
OUT.mkdir(parents=True, exist_ok=True)

REEL_TILE = (640, 320)
REEL_COLS = 6
REELS = {
    "reel-642": ("route-2640642", range(0, 30)),
    "reel-648": ("route-2640648", range(0, 30)),
    "reel-638a": ("route-2640638", range(0, 30)),
    "reel-632c": ("route-2640632", range(40, 72)),
    "reel-638c": ("route-2640638", range(57, 89)),
}


def frame(route, index):
    return Image.open(FRAMES / route / f"{index * 20:06d}.png").convert("RGB")


def build_reel(name, route, indices):
    indices = list(indices)
    rows = -(-len(indices) // REEL_COLS)
    sheet = Image.new("RGB", (REEL_TILE[0] * REEL_COLS, REEL_TILE[1] * rows))
    for slot, index in enumerate(indices):
        tile = frame(route, index).resize(REEL_TILE, Image.LANCZOS)
        sheet.paste(tile, ((slot % REEL_COLS) * REEL_TILE[0], (slot // REEL_COLS) * REEL_TILE[1]))
    sheet.save(OUT / f"{name}.jpg", quality=86)


def build_strip(name, route, indices, tile=(256, 128)):
    indices = list(indices)
    strip = Image.new("RGB", (tile[0] * len(indices), tile[1]))
    for slot, index in enumerate(indices):
        strip.paste(frame(route, index).resize(tile, Image.LANCZOS), (slot * tile[0], 0))
    strip.save(OUT / f"{name}.jpg", quality=86)


def black_patch_box(image):
    pixels = image.load()
    xs, ys = [], []
    for y in range(0, image.height):
        for x in range(0, image.width):
            if pixels[x, y] == (0, 0, 0):
                xs.append(x)
                ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def build_patch_thumb():
    image = frame("route-2640632", 2)
    left, top, right, bottom = black_patch_box(image)
    centre_x, centre_y = (left + right) // 2, (top + bottom) // 2
    half = max(right - left, bottom - top) // 2 + 70
    box = (centre_x - half, centre_y - half, centre_x + half, centre_y + half)
    image.crop(box).resize((160, 160), Image.LANCZOS).save(OUT / "patch-thumb.jpg", quality=90)
    return (left, top, right, bottom)


def build_grain():
    rng = random.Random(7)
    size = 256
    grain = Image.new("L", (size, size))
    grain.putdata([rng.randint(0, 255) for _ in range(size * size)])
    grain.save(ROOT / "assets" / "grain.png")


if __name__ == "__main__":
    for reel_name, (route_name, index_range) in REELS.items():
        build_reel(reel_name, route_name, index_range)
    build_strip("strip-632", "route-2640632", range(60, 72))
    build_strip("strip-642", "route-2640642", range(18, 30))
    print("patch box", build_patch_thumb())
    build_grain()
