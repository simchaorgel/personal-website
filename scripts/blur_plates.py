"""
Find number plates in photos and pixelate them.

Setup (once):
    pip install open-image-models onnxruntime pillow numpy
    (the detector model, ~30 MB, downloads automatically on first run)

Usage:
    python scripts/blur_plates.py PHOTOS...                  # dry run: just report what it finds
    python scripts/blur_plates.py PHOTOS... --preview DIR    # save copies with the plates boxed, to check
    python scripts/blur_plates.py PHOTOS... --out DIR        # save pixelated copies to DIR
    python scripts/blur_plates.py PHOTOS... --in-place       # overwrite the originals

PHOTOS can be image files or folders (not searched recursively).

Extra options:
    --box X1,Y1,X2,Y2   also pixelate this area (pixels, in the upright image), for anything
                        the detector missed. Repeatable. Only makes sense with one photo.
    --conf 0.3          detection confidence threshold (lower = finds more, more false hits)
    --pad 0.15          extra margin around each plate, as a fraction of its size
    --blocks 3          how many mosaic blocks tall each plate becomes (fewer = chunkier)
    --tile 1024         also scan the photo in tiles this big, to catch small distant plates
                        (0 = whole photo only: faster, but misses small plates)

Every saved image is also rotated upright and stripped of all metadata (EXIF, GPS, etc.).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageOps

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MODEL = 'yolo-v9-s-608-license-plate-end2end'  # the most accurate of the bundled plate models


def find_images(paths):
    for p in map(Path, paths):
        if p.is_dir():
            yield from sorted(f for f in p.iterdir() if f.suffix.lower() in EXTENSIONS)
        elif p.is_file():
            yield p
        else:
            print(f'skip: {p} (not found)', file=sys.stderr)


def load_detector(conf):
    import warnings

    warnings.filterwarnings('ignore', category=DeprecationWarning)
    from open_image_models import create_detector

    return create_detector(MODEL, conf_thresh=conf)


def detect_once(detector, bgr, ox=0, oy=0):
    return [(x1 + ox, y1 + oy, x2 + ox, y2 + oy, r.confidence)
            for r in detector.predict(bgr)
            for x1, y1, x2, y2 in [r.bounding_box.xyxy]]


def tiles(size, tile, overlap=0.25):
    """Top-left corners of overlapping tiles covering a length of `size`."""
    if size <= tile:
        return [0]
    step = int(tile * (1 - overlap))
    starts = list(range(0, size - tile, step))
    return starts + [size - tile]


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0


def contains(a, b, slack=0.8):
    """True if most of box b lies inside box a."""
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return ix * iy >= slack * (b[2] - b[0]) * (b[3] - b[1])


def plate_shaped(box, size):
    """Plates are wider than tall, and never a big part of the photo."""
    w, h = box[2] - box[0], box[3] - box[1]
    return h > 0 and 1.2 <= w / h <= 8 and w <= size[0] * 0.5


def detect(detector, image, tile):
    """
    Returns [(x1, y1, x2, y2, confidence)] for each plate in a PIL image.

    The model looks at a 608px version of whatever it's given, so in a big photo
    a distant plate shrinks to a few pixels. So it also scans overlapping tiles
    at near full resolution, then merges duplicates.
    """
    bgr = np.asarray(image)[:, :, ::-1].copy()  # the detector expects OpenCV-style BGR
    found = detect_once(detector, bgr)
    if tile:
        h, w = bgr.shape[:2]
        for y in tiles(h, tile):
            for x in tiles(w, tile):
                found += detect_once(detector, bgr[y:y + tile, x:x + tile], x, y)

    found = [b for b in found if plate_shaped(b, image.size)]
    found.sort(key=lambda b: -b[4])
    kept = []
    for b in found:
        if not any(iou(k, b) > 0.3 or contains(k, b) or contains(b, k) for k in kept):
            kept.append(b)
    return kept


def padded(box, pad, size):
    x1, y1, x2, y2 = box[:4]
    px, py = (x2 - x1) * pad, (y2 - y1) * pad
    w, h = size
    return (max(0, round(x1 - px)), max(0, round(y1 - py)), min(w, round(x2 + px)), min(h, round(y2 + py)))


def pixelate(image, box, blocks):
    """Shrink the area to a few blocks and scale it back up with hard edges: the classic mosaic."""
    x1, y1, x2, y2 = box
    if x2 - x1 < 2 or y2 - y1 < 2:
        return
    region = image.crop(box)
    block = max(1, (y2 - y1) / blocks)
    small = region.resize((max(1, round((x2 - x1) / block)), max(1, blocks)), Image.BILINEAR)
    image.paste(small.resize(region.size, Image.NEAREST), box)


def save_clean(image, path):
    """Save with no metadata at all (rebuilt from raw pixels)."""
    clean = Image.frombytes(image.mode, image.size, image.tobytes())
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in {'.jpg', '.jpeg'}:
        clean.save(path, 'JPEG', quality=95, subsampling=2, optimize=True)
    else:
        clean.save(path)


def parse_box(text):
    try:
        x1, y1, x2, y2 = (int(v) for v in text.split(','))
    except ValueError:
        raise argparse.ArgumentTypeError('expected X1,Y1,X2,Y2')
    return (x1, y1, x2, y2, 1.0)


def main():
    ap = argparse.ArgumentParser(description='Find and pixelate number plates.')
    ap.add_argument('photos', nargs='+')
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--out', type=Path, help='save pixelated copies here')
    mode.add_argument('--in-place', action='store_true', help='overwrite the originals')
    ap.add_argument('--preview', type=Path, help='save copies with detected plates boxed in red')
    ap.add_argument('--box', type=parse_box, action='append', default=[], help='extra area to pixelate')
    ap.add_argument('--conf', type=float, default=0.3)
    ap.add_argument('--pad', type=float, default=0.15)
    ap.add_argument('--blocks', type=int, default=3)
    ap.add_argument('--tile', type=int, default=1024)
    args = ap.parse_args()

    images = list(find_images(args.photos))
    if args.box and len(images) != 1:
        ap.error('--box only works with a single photo')

    detector = load_detector(args.conf)
    total = 0

    for path in images:
        image = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
        plates = detect(detector, image, args.tile) + args.box
        total += len(plates)
        found = ', '.join(f'{c:.0%} at {x1},{y1}-{x2},{y2}' for x1, y1, x2, y2, c in plates)
        print(f'{path.name}: {len(plates)} plate(s){"  " + found if plates else ""}')

        if args.preview:
            marked = image.copy()
            draw = ImageDraw.Draw(marked)
            width = max(3, image.width // 400)
            for p in plates:
                draw.rectangle(padded(p, args.pad, image.size), outline=(255, 0, 0), width=width)
            save_clean(marked, args.preview / path.name)

        if args.out or args.in_place:
            for p in plates:
                pixelate(image, padded(p, args.pad, image.size), args.blocks)
            save_clean(image, path if args.in_place else args.out / path.name)

    print(f'\n{total} plate(s) in {len(images)} image(s)')
    if not (args.out or args.in_place):
        print('dry run: nothing saved (use --out DIR or --in-place)' if not args.preview else 'previews saved')


if __name__ == '__main__':
    main()
