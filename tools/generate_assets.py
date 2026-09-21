"""One-shot asset generator. Idempotent and seeded - safe to re-run.

    python tools/generate_assets.py            # everything
    python tools/generate_assets.py --only rick

Produces (originals are never touched):
    visuals/Background_v3_640x480.png  smoothed + repaletted background
    visuals/Rick_64x60.png             slimmer, furrier, cool-toned Morty
    visuals/Larissa_48x72_f1.png       Aunt Larissa, walk frame 1
    visuals/Larissa_48x72_f2.png       Aunt Larissa, walk frame 2
    visuals/food_32.png                food sprite, white box removed
    sounds/woof_rick_1.wav             Morty's bark pitched up ~4 semitones
"""

import argparse
import os
import sys
import wave

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VISUALS = os.path.join(ROOT, "visuals")
SOUNDS = os.path.join(ROOT, "sounds")

RNG = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# Background: smooth out the MS-Paint speckle, warm up the palette
# ---------------------------------------------------------------------------

def generate_background():
    src = Image.open(os.path.join(VISUALS, "Background_v2_640x480.png")).convert("RGB")
    img = src.filter(ImageFilter.MedianFilter(5))      # kills 1px paint noise
    img = img.filter(ImageFilter.GaussianBlur(0.6))    # soften remaining edges
    img = ImageEnhance.Color(img).enhance(1.10)        # a little more life
    img = ImageEnhance.Brightness(img).enhance(1.03)
    img = ImageEnhance.Contrast(img).enhance(1.04)
    # quantize to a small palette for a clean, posterized 8-bit look
    img = img.quantize(colors=48, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    img = img.convert("RGB")
    out = os.path.join(VISUALS, "Background_v3_640x480.png")
    img.save(out)
    print("wrote", out)


# ---------------------------------------------------------------------------
# Doom-style background: same backyard (sky, wall, mangal, pergola roof,
# plant trellis, bushes, grass, pavement), hellish palette
# ---------------------------------------------------------------------------

def _rgb_to_hsv_arrays(rgb):
    arr = rgb.astype(np.float32) / 255.0
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    maxc = arr.max(axis=-1)
    minc = arr.min(axis=-1)
    v = maxc
    delta = maxc - minc
    s = np.where(maxc > 0, delta / np.maximum(maxc, 1e-6), 0)
    h = np.zeros_like(v)
    mask = delta > 1e-6
    rc = np.where(mask, (maxc - r) / np.maximum(delta, 1e-6), 0)
    gc = np.where(mask, (maxc - g) / np.maximum(delta, 1e-6), 0)
    bc = np.where(mask, (maxc - b) / np.maximum(delta, 1e-6), 0)
    h = np.where((maxc == r) & mask, bc - gc, h)
    h = np.where((maxc == g) & mask, 2.0 + rc - bc, h)
    h = np.where((maxc == b) & mask, 4.0 + gc - rc, h)
    return (h / 6.0) % 1.0, s, v


def _hsv_to_rgb_arrays(h, s, v):
    i = (h * 6.0).astype(int) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)


def generate_background_doom():
    src = Image.open(os.path.join(VISUALS, "Background_v2_640x480.png")).convert("RGB")
    img = src.filter(ImageFilter.MedianFilter(5))
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    rgb = np.array(img)
    h, s, v = _rgb_to_hsv_arrays(rgb)
    H, W = v.shape

    out_h, out_s, out_v = h.copy(), s.copy(), v.copy()

    # classify the hand-painted regions by color
    outline = v < 0.22                                     # black ink lines
    yy_frac = np.repeat(np.linspace(0.0, 1.0, H)[:, None], W, axis=1)
    sky = (h > 0.40) & (h < 0.60) & (s > 0.25) & (v > 0.55)      # teal sky
    # white glare behind the top bushes belongs to the sky as well
    sky |= (s < 0.14) & (v > 0.82) & (yy_frac < 0.35)
    greens = (h > 0.16) & (h < 0.45) & (s > 0.18) & ~sky         # grass+bushes
    maroon = ((h > 0.88) | (h < 0.06)) & (s > 0.25) & ~outline   # pergola+trellis
    tans = (h >= 0.06) & (h <= 0.16) & (s > 0.18)                # shed, table, post
    bluegray = (h > 0.5) & (h < 0.72) & (s <= 0.30) & ~sky       # pavement, wall
    gray = (s <= 0.18) & ~outline & ~bluegray                    # mangal bricks, plate

    # hell sky: vertical gradient, deep blood red up top -> burnt orange low
    sky_t = np.clip(yy_frac / 0.28, 0, 1)        # the sky lives in the top ~28%
    out_h = np.where(sky, 0.012 + 0.045 * sky_t, out_h)          # red -> orange
    out_s = np.where(sky, 0.88 - 0.18 * sky_t, out_s)
    out_v = np.where(sky, (0.42 + 0.50 * sky_t) * (0.75 + 0.25 * v), out_v)

    # vegetation: dark toxic green (nukage vibes)
    out_h = np.where(greens, 0.26, out_h)
    out_s = np.where(greens, np.clip(s * 1.35, 0, 0.95), out_s)
    out_v = np.where(greens, v * 0.58, out_v)

    # pergola roof + plant trellis: deeper blood red
    out_h = np.where(maroon, 0.985, out_h)
    out_s = np.where(maroon, np.clip(s * 1.25, 0, 0.9), out_s)
    out_v = np.where(maroon, v * 0.82, out_v)

    # shed / table / post: scorched rust-brown
    out_h = np.where(tans, 0.055, out_h)
    out_s = np.where(tans, np.clip(s * 1.6, 0.50, 0.88), out_s)
    out_v = np.where(tans, v * 0.55, out_v)

    # wall + pavement: cold dark concrete with a rusty cast
    out_h = np.where(bluegray, 0.058, out_h)
    out_s = np.where(bluegray, 0.24, out_s)
    out_v = np.where(bluegray, v * 0.48, out_v)

    # mangal bricks, plate: ember-lit masonry
    out_h = np.where(gray, 0.050, out_h)
    out_s = np.where(gray, 0.42, out_s)
    out_v = np.where(gray, v * 0.62, out_v)

    out = _hsv_to_rgb_arrays(out_h, out_s, out_v)
    out[outline] = rgb[outline] * 0.6                # keep the ink lines inky

    img = Image.fromarray(out)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = img.quantize(colors=48, method=Image.MEDIANCUT, dither=Image.Dither.NONE)
    dst = os.path.join(VISUALS, "Background_v4_doom_640x480.png")
    img.convert("RGB").save(dst)
    print("wrote", dst)


# ---------------------------------------------------------------------------
# Rick: Morty's geometry, slimmed, cool-toned, with a furry outline
# ---------------------------------------------------------------------------

def _shift_hue(rgba, hue_shift=0.55, sat_mult=0.65):
    """Rotate hue / damp saturation of all opaque pixels (vectorized HSV)."""
    arr = rgba.astype(np.float32) / 255.0
    r, g, b, a = arr[..., 0], arr[..., 1], arr[..., 2], arr[..., 3]
    maxc = np.max(arr[..., :3], axis=-1)
    minc = np.min(arr[..., :3], axis=-1)
    v = maxc
    delta = maxc - minc
    s = np.where(maxc > 0, delta / np.maximum(maxc, 1e-6), 0)
    # hue
    h = np.zeros_like(maxc)
    mask = delta > 1e-6
    rc = np.where(mask, (maxc - r) / np.maximum(delta, 1e-6), 0)
    gc = np.where(mask, (maxc - g) / np.maximum(delta, 1e-6), 0)
    bc = np.where(mask, (maxc - b) / np.maximum(delta, 1e-6), 0)
    h = np.where((maxc == r) & mask, bc - gc, h)
    h = np.where((maxc == g) & mask, 2.0 + rc - bc, h)
    h = np.where((maxc == b) & mask, 4.0 + gc - rc, h)
    h = (h / 6.0) % 1.0

    h = (h + hue_shift) % 1.0
    s = np.clip(s * sat_mult, 0, 1)

    # hsv -> rgb
    i = (h * 6.0).astype(int)
    f = h * 6.0 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    i = i % 6
    out_r = np.choose(i, [v, q, p, p, t, v])
    out_g = np.choose(i, [t, v, v, q, p, p])
    out_b = np.choose(i, [p, p, t, v, v, q])
    out = np.stack([out_r, out_g, out_b, a], axis=-1)
    return (out * 255).astype(np.uint8)


def generate_rick():
    morty = Image.open(os.path.join(VISUALS, "Morty_64x60.png")).convert("RGBA")
    w, h = morty.size

    # 1. slimmer: squeeze to 78% width, re-center on the original canvas
    slim_w = int(w * 0.78)
    slim = morty.resize((slim_w, h), Image.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(slim, ((w - slim_w) // 2, 0))

    # 2. cool grey-blue coat instead of Morty's warm tones
    arr = np.array(canvas)
    arr = _shift_hue(arr, hue_shift=0.50, sat_mult=0.85)

    # 3. fur: jagged 1-2 px tufts sticking out of the silhouette
    alpha = arr[..., 3]
    solid = alpha > 96
    out = arr.copy()
    H, W = solid.shape
    for y in range(2, H - 1):           # skip the very top (ears stay crisp)
        xs = np.where(solid[y])[0]
        if len(xs) == 0:
            continue
        for edge_x, direction in ((xs.min(), -1), (xs.max(), 1)):
            if RNG.uniform() < 0.45:    # not every row sprouts a tuft
                length = int(RNG.integers(1, 3))
                color = arr[y, edge_x, :3]
                for k in range(1, length + 1):
                    tx = edge_x + direction * k
                    if 0 <= tx < W and not solid[y, tx]:
                        out[y, tx, :3] = color
                        out[y, tx, 3] = 255
    Image.fromarray(out).save(os.path.join(VISUALS, "Rick_64x60.png"))
    print("wrote", os.path.join(VISUALS, "Rick_64x60.png"))


# ---------------------------------------------------------------------------
# Aunt Larissa: hand-coded pixel grid, 12x18 logical pixels at 4x = 48x72
# ---------------------------------------------------------------------------

LARISSA_PALETTE = {
    "H": (158, 142, 130),   # grey bun
    "S": (232, 184, 144),   # skin
    "E": (60, 40, 30),      # eyes
    "D": (122, 79, 158),    # purple dress
    "A": (242, 233, 220),   # apron
    "B": (90, 58, 40),      # shoes
    ".": None,
}

LARISSA_BODY = [
    "....HHHH....",
    "...HHHHHH...",
    "..HHHHHHHH..",
    "...SSSSSS...",
    "...SESSES...",
    "...SSSSSS...",
    "....SSSS....",
    "...DDDDDD...",
    "..DDDDDDDD..",
    ".SDDAAAADDS.",
    ".SDDAAAADDS.",
    "..DDAAAADD..",
    "..DDDDDDDD..",
    "..DDDDDDDD..",
    ".DDDDDDDDDD.",
    ".DDDDDDDDDD.",
]

LARISSA_LEGS = {
    "f1": ["...S....S...",
           "..BB....BB.."],
    "f2": ["....S..S....",
           "...BB..BB..."],
}


def generate_larissa():
    for frame, legs in LARISSA_LEGS.items():
        grid = LARISSA_BODY + legs
        scale = 10  # 12x18 grid -> 120x180 (auntie towers over the dogs)
        img = Image.new("RGBA", (12 * scale, 18 * scale), (0, 0, 0, 0))
        px = img.load()
        for gy, row in enumerate(grid):
            for gx, ch in enumerate(row):
                color = LARISSA_PALETTE[ch]
                if color is None:
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        px[gx * scale + dx, gy * scale + dy] = (*color, 255)
        out = os.path.join(VISUALS, f"Larissa_120x180_{frame}.png")
        img.save(out)
        print("wrote", out)


# ---------------------------------------------------------------------------
# Rick's bark: Morty's, resampled to play ~25% faster (about +4 semitones)
# ---------------------------------------------------------------------------

def generate_rick_bark():
    src_path = os.path.join(SOUNDS, "woof_morty_1.wav")
    with wave.open(src_path, "rb") as wav:
        params = wav.getparams()
        frames = wav.readframes(params.nframes)
    assert params.sampwidth == 2, "expected 16-bit PCM"
    samples = np.frombuffer(frames, dtype=np.int16)
    if params.nchannels == 2:
        samples = samples.reshape(-1, 2)

    factor = 0.8  # new duration = 80% -> pitch up ~3.9 semitones
    n_out = int(len(samples) * factor)
    idx = np.clip((np.arange(n_out) / factor).astype(int), 0, len(samples) - 1)
    out = samples[idx]

    dst_path = os.path.join(SOUNDS, "woof_rick_1.wav")
    with wave.open(dst_path, "wb") as wav:
        wav.setnchannels(params.nchannels)
        wav.setsampwidth(params.sampwidth)
        wav.setframerate(params.framerate)
        wav.writeframes(out.astype(np.int16).tobytes())
    print("wrote", dst_path)


# ---------------------------------------------------------------------------
# Food: strip the white product-photo box, crop, 32x32 with transparency
# ---------------------------------------------------------------------------

def generate_food():
    src = Image.open(os.path.join(VISUALS, "8853301006071_compressed copy.jpg")).convert("RGB")
    arr = np.array(src).astype(np.int16)
    near_white = (arr > 225).all(axis=-1)
    rgba = np.dstack([arr.astype(np.uint8), np.where(near_white, 0, 255).astype(np.uint8)])
    img = Image.fromarray(rgba, "RGBA")
    bbox = img.getbbox()
    img = img.crop(bbox)
    # pad to square so the 32x32 resize keeps proportions
    side = max(img.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
    square = square.resize((32, 32), Image.LANCZOS)
    out = os.path.join(VISUALS, "food_32.png")
    square.save(out)
    print("wrote", out)


# ---------------------------------------------------------------------------

GENERATORS = {
    "background": generate_background,
    "doom": generate_background_doom,
    "rick": generate_rick,
    "larissa": generate_larissa,
    "bark": generate_rick_bark,
    "food": generate_food,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=sorted(GENERATORS), default=None)
    args = parser.parse_args()
    targets = [args.only] if args.only else list(GENERATORS)
    for name in targets:
        GENERATORS[name]()


if __name__ == "__main__":
    sys.exit(main())
