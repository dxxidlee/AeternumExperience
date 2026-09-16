#!/usr/bin/env python3
"""Build a grayscale sprite atlas + on-demand plate JPEGs from IMG/."""
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageEnhance, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "IMG")
OUT = os.path.join(ROOT, "media")
PLATES = os.path.join(OUT, "plates")

CELL_W, CELL_H = 192, 144
COLS, ROWS = 16, 16
PLATE_MAX = 1280


def gray(im):
    g = ImageOps.grayscale(im)
    return ImageEnhance.Contrast(g).enhance(1.06)


def load_limited(path, max_side):
    im = Image.open(path)
    try:
        im.draft("L", (max_side, max_side))
    except Exception:
        pass
    im.load()
    return gray(im)


def process(i):
    name = f"{i:03d} copy.jpg"
    path = os.path.join(SRC, name)
    if not os.path.isfile(path):
        return i, None, None
    tile_src = load_limited(path, 512)
    tile = ImageOps.fit(tile_src, (CELL_W, CELL_H), Image.Resampling.LANCZOS)
    plate = load_limited(path, PLATE_MAX)
    plate.thumbnail((PLATE_MAX, PLATE_MAX), Image.Resampling.LANCZOS)
    plate_path = os.path.join(PLATES, f"{i:03d}.jpg")
    plate.save(plate_path, "JPEG", quality=80, optimize=True, progressive=True)
    return i, tile, os.path.getsize(plate_path)


def main():
    os.makedirs(PLATES, exist_ok=True)
    atlas = Image.new("L", (COLS * CELL_W, ROWS * CELL_H), 244)
    tiles = {}
    n = 0
    bytes_plates = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = [ex.submit(process, i) for i in range(1, 257)]
        for fut in as_completed(futs):
            i, tile, sz = fut.result()
            n += 1
            if tile is None:
                print(f"missing {i:03d}")
                continue
            tiles[i] = tile
            bytes_plates += sz or 0
            if n % 32 == 0:
                print(f"processed {n}/256")
    for i, tile in tiles.items():
        idx = i - 1
        col, row = idx % COLS, idx // COLS
        atlas.paste(tile, (col * CELL_W, row * CELL_H))
    atlas_path = os.path.join(OUT, "atlas.jpg")
    atlas.save(atlas_path, "JPEG", quality=78, optimize=True, progressive=True)
    print(f"atlas {os.path.getsize(atlas_path)/1e6:.2f} MB")
    print(f"plates {bytes_plates/1e6:.2f} MB")
    print("done")


if __name__ == "__main__":
    main()
