#!/usr/bin/env python3
"""
المجموعة الخامسة: فروع نباتية واقعية بالخط الرفيع — ورد وزنابق.

المنهج المختلف عن المجموعات السابقة:
  بُني كل عنصر (وردة، برعم، وُرَيقة، زنبق، ورقة) منفرداً، وكُبّر، وتحقّقنا
  منه، وأُصلح — **قبل** أي تركيب. بناء التركيب كاملاً ثم مراجعته بصور
  مصغّرة هو ما أخفى العيوب في المجموعات السابقة.

التشغيل:  python3 generate_botanical.py
"""

import json
import math
import random
from pathlib import Path

from artlib import TAU, P, tangent_of, write_svg
import botanical as B

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "botanical"

VINE = (230, 780)
TILE = (260, 260)
LEAFT = (200, 300)

STROKE = 1.25


def place(shapes, ang, at):
    return [B._rot_shift(s, ang, at) for s in shapes]


def mirror(shapes):
    out = []
    for s in shapes:
        if s["kind"] in ("path", "fill"):
            out.append({**s, "pts": [(-x, y) for x, y in s["pts"]]})
        else:
            out.append({**s, "c": (-s["c"][0], s["c"][1])})
    return out


def leaf_slots(candidates, blocked, near=0.13, drop=0.055):
    """
    يوزّع مواضع الأوراق على الساق مع تفادي الزهور.

    `blocked` قائمة (موضع, جهة) للزهور والبراعم.
    - الموضع الذي يلاصق زهرة (< drop) يُحذف.
    - الموضع القريب منها (< near) يُوضع على **الجهة المقابلة** لها.
    بدون هذا تمرّ الأوراق داخل الزهور فيصير التركيب متشابكاً.
    """
    slots = []
    for k, t in enumerate(candidates):
        if blocked:
            bt, bs = min(blocked, key=lambda b: abs(b[0] - t))
            d = abs(bt - t)
            if d < drop:
                continue
            side = -bs if d < near else (1 if k % 2 == 0 else -1)
        else:
            side = 1 if k % 2 == 0 else -1
        # تباعد أدنى بين ورقتين على الجهة نفسها، وإلا تراكبتا
        if any(abs(pt - t) < 0.13 and ps == side for pt, ps in slots):
            side = -side
        if any(abs(pt - t) < 0.085 for pt, _ in slots):
            continue
        slots.append((t, side))
    return slots


# ---------------------------------------------------------------------------
# فرع ورد رأسي
# ---------------------------------------------------------------------------


def build_rose_vine(i):
    """
    فرع ورد رأسي: ساق رفيع متعرّج + وردتان متفتّحتان + برعمان
    + أوراق مركّبة مسنّنة + أشواك صغيرة.
    """
    rng = random.Random(70 + i)
    H = 690.0
    amp = 24.0 + (i % 3) * 8.0
    cycles = 1.05 + (i % 4) * 0.14
    flip = (i % 2 == 1)

    def stem(t):
        return (amp * math.sin(TAU * cycles * t + 0.4), H * (1 - t))

    shapes = [P([stem(k / 90) for k in range(91)], smooth=True, w=B.WO)]

    # 1) تُحدَّد مواضع الزهور والبراعم وجهاتها أولاً
    if i % 2 == 0:
        roses = [(0.28, -1), (0.72, 1)]
        buds = [(0.48, 1), (0.93, -1)]
    else:
        roses = [(0.22, -1), (0.60, 1)]
        buds = [(0.42, -1), (0.86, 1)]
    blocked = roses + buds

    # 2) ثم تُوزَّع الأوراق بعيداً عنها
    for t, side in leaf_slots([0.08, 0.16, 0.35, 0.53, 0.66, 0.80, 0.97],
                              blocked):
        px, py = stem(t)
        th = tangent_of(stem, t)
        sz = 0.60 + 0.10 * rng.random()
        shapes += place(B.rose_leaf(72 * sz, sz, 5),
                        th + side * math.radians(54) + math.pi / 2, (px, py))

    # أشواك صغيرة
    for t, side in ((0.19, -1), (0.44, 1), (0.64, -1), (0.88, 1)):
        px, py = stem(t)
        th = tangent_of(stem, t)
        d = th + side * math.radians(72)
        shapes.append(P([(px, py),
                         (px + 9 * math.cos(d), py + 9 * math.sin(d))],
                        smooth=False, w=B.WV))

    # براعم على سويقات قصيرة
    for k, (t, side) in enumerate(buds):
        px, py = stem(t)
        th = tangent_of(stem, t)
        ang = th + side * math.radians(48)
        L = 44.0
        bx, by = px + L * math.cos(ang), py + L * math.sin(ang)
        shapes.append(P(
            [(px, py),
             (px + L * 0.55 * math.cos(ang) - side * 7 * math.sin(ang),
              py + L * 0.55 * math.sin(ang) + side * 7 * math.cos(ang)),
             (bx, by)], smooth=True, w=B.WO))
        shapes += place(B.rose_bud(86.0), ang + math.pi / 2, (bx, by))

    # ورود متفتّحة
    for k, (t, side) in enumerate(roses):
        px, py = stem(t)
        th = tangent_of(stem, t)
        ang = th + side * math.radians(44)
        L = 34.0
        cx, cy = px + L * math.cos(ang), py + L * math.sin(ang)
        shapes.append(P([(px, py), (cx, cy)], smooth=True, w=B.WO))
        R = 54.0 - 4 * k + rng.uniform(-3, 3)
        shapes += place(B.rose_full(R, rot=rng.uniform(0, 1.2)), 0.0,
                        (cx + 0.62 * R * math.cos(ang),
                         cy + 0.62 * R * math.sin(ang)))

    if flip:
        shapes = mirror(shapes)
    return f"rose_vine_{i + 1:02d}", "فرع ورد رأسي", shapes, VINE


# ---------------------------------------------------------------------------
# فرع زنابق رأسي
# ---------------------------------------------------------------------------


def build_lily_vine(i):
    rng = random.Random(170 + i)
    H = 690.0
    amp = 22.0 + (i % 3) * 9.0
    cycles = 0.95 + (i % 4) * 0.13
    flip = (i % 2 == 1)

    def stem(t):
        return (amp * math.sin(TAU * cycles * t + 0.7), H * (1 - t))

    shapes = [P([stem(k / 90) for k in range(91)], smooth=True, w=B.WO)]

    lilies = ([(0.32, -1), (0.78, 1)] if i % 2 == 0
              else [(0.26, -1), (0.64, 1)])

    for t, side in leaf_slots([0.06, 0.14, 0.22, 0.44, 0.54, 0.70, 0.88, 0.98],
                              lilies, near=0.16, drop=0.075):
        px, py = stem(t)
        th = tangent_of(stem, t)
        L = rng.uniform(76, 100)
        shapes += place(B.lily_leaf(L, L * 0.19, bend=side * 7),
                        th + side * math.radians(56) + math.pi / 2, (px, py))

    for k, (t, side) in enumerate(lilies):
        px, py = stem(t)
        th = tangent_of(stem, t)
        ang = th + side * math.radians(42)
        L = 38.0
        cx, cy = px + L * math.cos(ang), py + L * math.sin(ang)
        shapes.append(P([(px, py), (cx, cy)], smooth=True, w=B.WO))
        R = 60.0 - 5 * k
        shapes += place(B.lily_flower(R, rot=rng.uniform(0, 1.0)), 0.0,
                        (cx + 0.58 * R * math.cos(ang),
                         cy + 0.58 * R * math.sin(ang)))

    if flip:
        shapes = mirror(shapes)
    return f"lily_vine_{i + 1:02d}", "فرع زنابق رأسي", shapes, VINE


# ---------------------------------------------------------------------------
# عناصر منفردة
# ---------------------------------------------------------------------------


def build_single(i):
    if i == 0:
        return "rose_open", "وردة متفتّحة", B.rose_full(108.0), TILE
    if i == 1:
        return ("rose_open_b", "وردة متفتّحة ٢",
                B.rose_full(108.0, rot=0.9), TILE)
    if i == 2:
        shapes = B.rose_full(100.0, rings=(
            (3, 0.34, 0.54, 0.0), (5, 0.48, 0.76, 0.0), (5, 0.70, 1.0, 0.02)))
        return "rose_open_c", "وردة متفتّحة ٣", shapes, TILE
    if i == 3:
        return "rose_bud", "برعم ورد", B.rose_bud(170.0), LEAFT
    if i == 4:
        return "lily_open", "زنبق", B.lily_flower(112.0), TILE
    if i == 5:
        return ("lily_open_b", "زنبق ٢",
                B.lily_flower(112.0, rot=0.6), TILE)
    if i == 6:
        return ("rose_leaf", "ورقة ورد مركّبة",
                B.rose_leaf(200.0, 1.55, 5), (280, 300))
    return ("lily_leaf", "ورقة زنبق", B.lily_leaf(230.0, 44.0, bend=12),
            LEAFT)


FAMILIES = [
    ("فروع ورد رأسية", build_rose_vine, 6),
    ("فروع زنابق رأسية", build_lily_vine, 6),
    ("عناصر منفردة", build_single, 8),
]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.svg"):
        old.unlink()

    index = []
    num = 0
    for fam, builder, count in FAMILIES:
        for i in range(count):
            num += 1
            name, title, shapes, canvas = builder(i)
            fname = f"R{num:03d}_{name}.svg"
            write_svg(OUT_DIR / fname, shapes, canvas=canvas, margin=10,
                      stroke=STROKE, title=f"R{num:03d} — {title}")
            index.append({"num": num, "file": fname, "title": title,
                          "family": fam, "wide": False,
                          "tall": canvas == VINE, "elements": len(shapes)})

    (ROOT / "index_botanical.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"تم توليد {num} رسمة في {OUT_DIR}")
    for fam, _, c in FAMILIES:
        print(f"  - {fam}: {c}")
    return index


if __name__ == "__main__":
    main()
