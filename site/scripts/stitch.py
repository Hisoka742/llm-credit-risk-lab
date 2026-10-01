"""Join the viewport segments written by capture.mjs into one full-page image per run."""

import json
import sys
from pathlib import Path

from PIL import Image

seg = Path(sys.argv[1]) / "seg"
for meta in sorted(seg.glob("*.json")):
    name = meta.stem
    info = json.loads(meta.read_text())
    scale = info["scale"]
    parts = [Image.open(seg / f"{name}-{i:03d}.png") for i in range(len(info["tops"]))]
    out = Image.new("RGB", (parts[0].width, round(info["total"] * scale)))
    for top, im in zip(info["tops"], parts, strict=True):
        out.paste(im, (0, round(top * scale)))  # the last segment overlaps the one before it
    out.save(seg.parent / f"{name}.png")
    print(name, out.size, f"{len(parts)} segments")
