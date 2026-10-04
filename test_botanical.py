#!/usr/bin/env python3
"""
اختبار عناصر الرسم النباتي منفردةً وبمقاس كبير.

المنهج: نبني العنصر، نكبّره، نتحقق، نُصلح — ثم نركّب.
بناء التركيب كاملاً ثم مراجعته بصور مصغّرة هو ما أخفى العيوب سابقاً.
"""

import sys
from pathlib import Path

from artlib import write_svg, xf_all
import botanical as B

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "test_svg"

TILE = (260, 260)
TALL = (200, 300)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()

    items = [
        ("t01_rose_full", B.rose_full(100.0), TILE),
        ("t02_rose_full_rot", B.rose_full(100.0, rot=0.7), TILE),
        ("t03_rose_bud", B.rose_bud(150.0), TALL),
        ("t04_rose_leaflet", B.rose_leaflet(170.0, 44.0), TALL),
        ("t05_rose_leaf", B.rose_leaf(190.0, 1.6), (260, 300)),
        ("t06_lily", B.lily_flower(110.0), TILE),
        ("t07_lily_petal", B.lily_petal(190.0, 50.0), TALL),
        ("t08_lily_leaf", B.lily_leaf(200.0, 38.0), TALL),
    ]
    for name, shapes, canvas in items:
        write_svg(OUT / f"{name}.svg", shapes, canvas=canvas, margin=10,
                  stroke=1.25, title=name)
        print(f"{name}.svg  ({len(shapes)} عنصر)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
