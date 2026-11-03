"""Prepare an icon for the site: remove a white background connected to
the image edges, crop to the visible content, and pad to a square.

Usage: python scripts/prep_icon.py <input> <output.png> [size]
"""
import sys
from collections import deque
from PIL import Image

src, dst = sys.argv[1], sys.argv[2]
size = int(sys.argv[3]) if len(sys.argv) > 3 else 256

im = Image.open(src).convert('RGBA')
w, h = im.size
px = im.load()

def whiteish(p):
    return p[3] < 10 or min(p[:3]) > 235

# Flood-fill near-white pixels from the edges (keeps white *inside* shapes).
bg = bytearray(w * h)
queue = deque()
for x in range(w):
    queue.extend([(x, 0), (x, h - 1)])
for y in range(h):
    queue.extend([(0, y), (w - 1, y)])
while queue:
    x, y = queue.popleft()
    i = y * w + x
    if bg[i] or not whiteish(px[x, y]):
        continue
    bg[i] = 1
    for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if 0 <= nx < w and 0 <= ny < h and not bg[ny * w + nx]:
            queue.append((nx, ny))

# Background -> transparent; anti-aliased fringe next to it -> "colour to alpha" against white.
for y in range(h):
    for x in range(w):
        if bg[y * w + x]:
            px[x, y] = (0, 0, 0, 0)
            continue
        near_bg = any(
            0 <= x + dx < w and 0 <= y + dy < h and bg[(y + dy) * w + x + dx]
            for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)
        )
        if near_bg:
            r, g, b, a = px[x, y]
            alpha = max(255 - r, 255 - g, 255 - b) / 255
            if alpha <= 0:
                px[x, y] = (0, 0, 0, 0)
                continue
            un = lambda c: max(0, min(255, round((c - 255 * (1 - alpha)) / alpha)))
            px[x, y] = (un(r), un(g), un(b), round(a * alpha))

# Crop to visible content and pad to a square.
box = im.getchannel('A').point(lambda a: 255 if a > 8 else 0).getbbox() or (0, 0, w, h)
im = im.crop(box)
side = max(im.size)
square = Image.new('RGBA', (side, side), (0, 0, 0, 0))
square.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
square.resize((size, size), Image.LANCZOS).save(dst)
print(f'{src} -> {dst} (cropped {box})')
