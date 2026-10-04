#!/usr/bin/env python3
"""
المجموعة الثالثة: أشرطة أطراف رأسية بأسلوب نقوش التطريز اليدوي.

مبنية على المراجع المرسلة، وتضيف ما كان ناقصاً تماماً:
  - صيغة رأسية (طرف العباية الأمامي ينزل رأسياً)
  - نقاط مُعبّأة سوداء: حبّات وخرز
  - أوراق محشوّة بخطوط متوازية (مظهر تطريز الساتان)
  - سلاسل معلّقة بعناصر مُعلّقة عليها
  - وريدات صغيرة مزخرفة كثيفة التفاصيل
  - محالق حلزونية
  - اختلاف طفيف بين كل تكرار وآخر (كسر التناظر الآلي)

التشغيل:  python3 generate_bands.py
"""

import json
import math
import random
from pathlib import Path

from artlib import (TAU, W_FINE, W_MAIN, W_MID, CIRC, DOT, LINE, P, FILLED,
                    leaf_hatched, petal, polar, ribbon, taper_fn, tangent_of,
                    write_svg, xf, xf_all)

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "bands"

BAND = (150, 700)      # شريط رأسي مفرد
PANEL = (440, 700)     # لوح بعدة سلاسل
TILE = (200, 200)      # عنصر منفرد

STROKE = 1.5


# ===========================================================================
# عناصر
# ===========================================================================


def leaf_plain(length=22.0, width=7.0, bend=2.0, vein=True, w=W_MAIN):
    out = [ribbon(lambda t: (bend * math.sin(math.pi * t), -length * t),
                  taper_fn(width, 0.70, 0.95), n=54, w=w)]
    if vein:
        out.append(P([(0, -length * 0.08), (bend, -length * 0.55),
                      (0, -length * 0.92)], smooth=True, w=W_FINE))
    return out


def leaf_solid(length=20.0, width=6.5, bend=2.0):
    """ورقة مصمتة — تُستخدم في النقوش الداكنة كما في المرجع."""
    r = ribbon(lambda t: (bend * math.sin(math.pi * t), -length * t),
               taper_fn(width, 0.70, 0.95), n=54)
    return [FILLED(r["pts"])]


def berry_cluster(n=5, r=2.9, spread=9.0, seed=0):
    """
    عنقود حبّات مُعبّأة. المواضع مُزاحة قليلاً بعضو عشوائي ثابت
    حتى لا يتكرّر العنقود مطابقاً في كل مرة.
    """
    rng = random.Random(seed)
    out = []
    for k in range(n):
        a = TAU * k / n + rng.uniform(-0.2, 0.2)
        rr = spread * (0.55 + 0.45 * rng.random())
        out.append(DOT(polar(rr, a), r * rng.uniform(0.85, 1.12)))
    if n >= 4:
        out.append(DOT((0, 0), r * 0.95))
    return out


def berry_triple(r=3.0, spread=7.5):
    return [DOT(polar(spread, -math.pi / 2 + TAU * k / 3), r) for k in range(3)]


def tendril(size=16.0, turns=1.25, side=1, w=W_MAIN):
    """
    محلق حلزوني — عنصر بارز في المرجع الثاني.

    يبدأ من (0,0) ويلتفّ. اتجاهه الابتدائي في الإحداثيات المحلية ≈ (0, side)،
    لذا لتوجيهه نحو زاوية θ يجب الدوران بمقدار θ − side·π/2
    (الخطأ في هذا الحساب كان يقلب المحلق ويجعله يتراكب مع الورقة).
    """
    pts = []
    for k in range(50):
        t = k / 49
        a = side * TAU * turns * t
        rr = size * (1 - 0.80 * t)
        pts.append((rr * math.cos(a) - size, rr * math.sin(a)))
    return [P(pts, smooth=True, w=w)]


def tendril_at(theta, size=18.0, turns=1.25, side=1, at=(0.0, 0.0), w=W_MAIN):
    """يضع محلقاً بقاعدته عند `at` وباتجاه الزاوية `theta`."""
    return xf_all(tendril(size, turns, side, w), theta - side * math.pi / 2,
                  1.0, at)


def rosette_small(R=20.0, spokes=12, rings=3, dots=True, w=W_MAIN):
    """وريدة صغيرة مزخرفة: حلقات + أشعّة + حلقة نقاط."""
    out = [CIRC((0, 0), R, w=w), CIRC((0, 0), R * 0.62, w=W_MID)]
    if rings >= 3:
        out.append(CIRC((0, 0), R * 0.26, w=W_MID))
    for k in range(spokes):
        a = TAU * k / spokes
        out.append(LINE(polar(R * 0.62, a), polar(R * 0.96, a), w=W_FINE))
    if dots:
        for k in range(spokes):
            a = TAU * k / spokes + math.pi / spokes
            out.append(DOT(polar(R * 0.44, a), R * 0.072))
    out.append(DOT((0, 0), R * 0.10))
    return out


def diamond_ornament(size=14.0, inner=True, w=W_MAIN):
    """معيّن مزخرف بنقطة في الوسط — متكرّر في المرجع الأول."""
    out = [P([(0, -size), (size * 0.72, 0), (0, size), (-size * 0.72, 0)],
             closed=True, smooth=False, w=w)]
    if inner:
        out.append(P([(0, -size * 0.55), (size * 0.40, 0), (0, size * 0.55),
                      (-size * 0.40, 0)], closed=True, smooth=False, w=W_MID))
    out.append(DOT((0, 0), size * 0.13))
    return out


def lotus_sprig(h=26.0, w_=18.0, w=W_MAIN):
    """سعفة/لوتس صغيرة — عنصر مُعلّق في المرجع الأول."""
    out = []
    for u in (-1, 0, 1):
        ln = h * (0.72 if u else 1.0)
        out += xf_all(leaf_plain(ln, ln * 0.30, bend=u * 2.5, vein=False, w=w),
                      u * math.radians(34), 1.0, (0, 0))
    out.append(LINE((0, 0), (0, w_ * 0.42), w=W_MID))
    return out


def bell_ornament(size=13.0, w=W_MAIN):
    """عنصر مُعلّق مدبّب (قطرة)."""
    r = ribbon(lambda t: (0, -size * 1.5 * t),
               taper_fn(size * 0.52, 1.1, 0.72), n=44, w=w)
    return [r, DOT((0, -size * 0.75), size * 0.14)]


# ===========================================================================
# محاور رأسية
# ===========================================================================


def vline(x=0.0, y0=0.0, y1=640.0):
    def f(t):
        return (x, y0 + (y1 - y0) * t)
    return f


def vwave(x=0.0, y0=0.0, y1=640.0, amp=18.0, cycles=5.0, phase=0.0):
    def f(t):
        return (x + amp * math.sin(TAU * cycles * t + phase),
                y0 + (y1 - y0) * t)
    return f


def vzigzag_pts(x=0.0, y0=0.0, y1=640.0, amp=20.0, steps=14):
    return [(x + (amp if k % 2 else -amp), y0 + (y1 - y0) * k / steps)
            for k in range(steps + 1)]


# ===========================================================================
# أشرطة رأسية بأوراق وحبّات
# ===========================================================================


def build_band_vine(i):
    """
    شريط رأسي: ساق متعرّج + أوراق متبادلة + عناقيد حبّات.
    كل تكرار يختلف قليلاً عن الذي قبله (حجم الورقة وميلها ومواضع الحبّات).
    """
    rng = random.Random(500 + i)
    style = i % 6
    v = i // 6
    y0, y1 = 20.0, 660.0
    hatch = v == 1                       # النسخة الثانية بأوراق محشوّة

    shapes = []
    if style == 0:                       # ساق مستقيم، أوراق وعناقيد متبادلة
        f = vline(0.0, y0, y1)
        shapes.append(P([f(k / 40) for k in range(41)], smooth=True, w=W_MAIN))
        n = 9
        for k in range(n):
            t = 0.04 + 0.92 * k / (n - 1)
            px, py = f(t)
            if k % 2 == 0:
                for side in (1, -1):
                    ln = 30 * rng.uniform(0.9, 1.1)
                    ang = math.radians(-90 + side * 44) + math.pi / 2
                    leaf = (leaf_hatched(ln, ln * 0.31, lines=7)
                            if hatch else leaf_plain(ln, ln * 0.31))
                    shapes += xf_all(leaf, ang, 1.0, (px, py))
            else:
                shapes += xf_all(berry_cluster(5, 3.0, 10.0, seed=i * 31 + k),
                                 0.0, 1.0, (px, py))
        title = "ساق بأوراق وعناقيد"

    elif style == 1:                     # ساق متموّج رفيع بأوراق صغيرة وحبّات
        f = vwave(0.0, y0, y1, 22.0, 4.0)
        shapes.append(P([f(k / 90) for k in range(91)], smooth=True, w=W_MAIN))
        n = 16
        for k in range(n):
            t = 0.03 + 0.94 * k / (n - 1)
            px, py = f(t)
            th = tangent_of(f, t)
            side = 1 if k % 2 == 0 else -1
            ln = 22 * rng.uniform(0.85, 1.15)
            ang = th + side * math.radians(52) + math.pi / 2
            leaf = (leaf_hatched(ln, ln * 0.33, lines=5)
                    if hatch else leaf_plain(ln, ln * 0.33))
            shapes += xf_all(leaf, ang, 1.0, (px, py))
            if k % 3 == 2:
                shapes += xf_all(berry_triple(2.6, 6.5),
                                 0.0, 1.0,
                                 (px - side * 16, py + rng.uniform(-4, 4)))
        title = "ساق متموّج بأوراق وحبّات"

    elif style == 2:                     # أوراق كثيفة متقابلة + ثلاثيات نقاط
        f = vline(0.0, y0, y1)
        shapes.append(P([f(k / 40) for k in range(41)], smooth=True, w=W_MAIN))
        n = 13
        for k in range(n):
            t = 0.03 + 0.94 * k / (n - 1)
            px, py = f(t)
            for side in (1, -1):
                ln = 27 * rng.uniform(0.92, 1.08)
                ang = math.radians(-90 + side * 48) + math.pi / 2
                leaf = (leaf_hatched(ln, ln * 0.30, lines=6)
                        if hatch else leaf_plain(ln, ln * 0.30))
                shapes += xf_all(leaf, ang, 1.0, (px, py))
            if k < n - 1:
                my = (py + f(t + 0.94 / (n - 1))[1]) / 2
                shapes += xf_all(berry_triple(2.5, 6.0), rng.uniform(0, 1),
                                 1.0, (0, my))
        title = "أوراق متقابلة وثلاثيات نقاط"

    elif style == 3:                     # أوراق ومحالق حلزونية
        f = vwave(0.0, y0, y1, 14.0, 3.0)
        shapes.append(P([f(k / 90) for k in range(91)], smooth=True, w=W_MAIN))
        n = 12
        for k in range(n):
            t = 0.04 + 0.92 * k / (n - 1)
            px, py = f(t)
            th = tangent_of(f, t)
            side = 1 if k % 2 == 0 else -1
            ln = 28 * rng.uniform(0.9, 1.1)
            ang = th + side * math.radians(50) + math.pi / 2
            leaf = (leaf_hatched(ln, ln * 0.31, lines=6)
                    if hatch else leaf_plain(ln, ln * 0.31))
            shapes += xf_all(leaf, ang, 1.0, (px, py))
            # المحلق يخرج من الجهة المقابلة للورقة
            shapes += tendril_at(th - side * math.radians(58),
                                 20 * rng.uniform(0.85, 1.15), 1.25,
                                 -side, (px, py))
        title = "أوراق ومحالق حلزونية"

    elif style == 4:                     # ساق زجزاج بأوراق وحبّات
        pts = vzigzag_pts(0.0, y0, y1, 22.0, 13)
        shapes.append(P(pts, smooth=True, w=W_MAIN))
        for k, (px, py) in enumerate(pts):
            side = 1 if px > 0 else -1
            ln = 30 * rng.uniform(0.9, 1.1)
            ang = math.radians(-90 + side * 52) + math.pi / 2
            leaf = (leaf_hatched(ln, ln * 0.31, lines=7)
                    if hatch else leaf_plain(ln, ln * 0.31))
            shapes += xf_all(leaf, ang, 1.0, (px, py))
            if k % 2 == 0:
                shapes += xf_all(berry_triple(2.7, 6.8), 0.0, 1.0,
                                 (px + side * 4, py + 16))
        title = "ساق زجزاج بأوراق وحبّات"

    else:                                # أوراق مصمتة وعناقيد كبيرة
        f = vline(0.0, y0, y1)
        shapes.append(P([f(k / 40) for k in range(41)], smooth=True, w=W_MAIN))
        n = 11
        for k in range(n):
            t = 0.03 + 0.94 * k / (n - 1)
            px, py = f(t)
            if k % 2 == 0:
                for side in (1, -1):
                    ln = 28 * rng.uniform(0.9, 1.1)
                    ang = math.radians(-90 + side * 46) + math.pi / 2
                    shapes += xf_all(leaf_solid(ln, ln * 0.30),
                                     ang, 1.0, (px, py))
            else:
                shapes += xf_all(berry_cluster(6, 3.2, 11.0, seed=i * 17 + k),
                                 0.0, 1.0, (px, py))
        title = "أوراق مصمتة وعناقيد"

    if hatch:
        title += " — أوراق محشوّة"
    return f"band_vine_{i + 1:02d}", f"شريط رأسي — {title}", shapes, BAND


# ===========================================================================
# سلاسل معلّقة
# ===========================================================================


def strand(x=0.0, y0=20.0, y1=660.0, bead_gap=16.0, bead_r=2.5,
           ornaments=(), seed=0):
    """
    سلسلة رأسية: خرز مُعبّأ متتابع، وعناصر مُعلّقة عند مواضع محدّدة.
    ornaments: متتالية من (نسبة_الموضع, دالة_بناء)
    """
    rng = random.Random(seed)
    out = []
    spans = []          # الفترات التي يشغلها عنصر مُعلّق (لا نضع خرزاً فيها)
    for pos, maker in ornaments:
        y = y0 + (y1 - y0) * pos
        built = maker()
        out += xf_all(built, 0.0, 1.0, (x, y))
        ext = 0.0
        for s in built:
            if s["kind"] in ("circle", "dot"):
                ext = max(ext, abs(s["c"][1]) + s["r"])
            else:
                ext = max(ext, max(abs(py) for _, py in s["pts"]))
        spans.append((y - ext - 5, y + ext + 5))

    y = y0
    while y <= y1:
        if not any(a <= y <= b for a, b in spans):
            out.append(DOT((x, y), bead_r * rng.uniform(0.75, 1.15)))
        y += bead_gap * rng.uniform(0.92, 1.08)
    # خط رابط رقيق يمرّ بين الخرز في الفراغات
    segs = []
    cur = [y0]
    for a, b in sorted(spans):
        cur.append(a)
        segs.append((cur[0], cur[-1]))
        cur = [b]
    segs.append((cur[0], y1))
    for a, b in segs:
        if b - a > 8:
            out.append(LINE((x, a), (x, b), w=W_FINE))
    return out


def _ornament_set(seed):
    rng = random.Random(seed)
    pool = [
        lambda: rosette_small(rng.uniform(16, 22), rng.choice([10, 12, 14])),
        lambda: diamond_ornament(rng.uniform(12, 16)),
        lambda: lotus_sprig(rng.uniform(22, 30)),
        lambda: bell_ornament(rng.uniform(11, 15)),
        lambda: berry_cluster(5, 3.0, 10.0, seed=seed),
        lambda: [s for s in rosette_small(14, 8, rings=2)],
    ]
    rng.shuffle(pool)
    return pool


def build_strand(i):
    """سلسلة معلّقة مفردة."""
    pool = _ornament_set(900 + i)
    n_orn = 3 + i % 3
    positions = [0.12 + 0.76 * k / max(1, n_orn - 1) for k in range(n_orn)]
    orns = [(p, pool[k % len(pool)]) for k, p in enumerate(positions)]
    shapes = strand(0.0, 20.0, 660.0, 15.0 + (i % 3) * 3, 2.6,
                    tuple(orns), seed=900 + i)
    return (f"strand_{i + 1:02d}", "سلسلة معلّقة بعناصر", shapes, BAND)


def build_panel(i):
    """لوح بعدة سلاسل متجاورة — كما في المرجع الأول."""
    n_str = 5
    gap = 86.0
    shapes = []
    for k in range(n_str):
        x = (k - (n_str - 1) / 2) * gap
        pool = _ornament_set(1300 + i * 13 + k)
        n_orn = 3 + (k + i) % 3
        offset = 0.06 * ((k * 7 + i * 3) % 5)
        positions = [min(0.93, 0.10 + offset + 0.74 * j / max(1, n_orn - 1))
                     for j in range(n_orn)]
        orns = [(p, pool[j % len(pool)]) for j, p in enumerate(positions)]
        shapes += strand(x, 20.0, 660.0, 15.0 + ((k + i) % 3) * 3, 2.5,
                         tuple(orns), seed=1300 + i * 13 + k)
    return (f"panel_{i + 1:02d}", "لوح سلاسل متجاورة", shapes, PANEL)


# ===========================================================================
# عناصر منفردة
# ===========================================================================


def build_rosette(i):
    specs = [(70, 12, 3), (70, 16, 3), (70, 10, 2), (70, 20, 3),
             (70, 14, 3), (70, 8, 2), (70, 18, 3), (70, 24, 3)]
    R, spokes, rings = specs[i]
    shapes = rosette_small(R, spokes, rings)
    # حلقة خارجية مسنّنة ناعمة
    if i % 2 == 0:
        pts = []
        for k in range(160):
            a = TAU * k / 160
            rr = R * (1.14 + 0.055 * math.sin(spokes * a))
            pts.append(polar(rr, a))
        shapes.append(P(pts, closed=True, smooth=True, w=W_MID))
    else:
        for k in range(spokes):
            a = TAU * k / spokes + math.pi / spokes
            shapes.append(DOT(polar(R * 1.18, a), R * 0.055))
        shapes.append(CIRC((0, 0), R * 1.10, w=W_FINE))
    return f"rosette_{i + 1:02d}", "وريدة صغيرة مزخرفة", shapes, TILE


def build_cluster(i):
    """عنقود أوراق وحبّات منفرد — عنصر يُستخدم مفرداً أو مُعلّقاً."""
    rng = random.Random(2000 + i)
    shapes = []
    style = i % 4
    if style == 0:
        for u in (-1, 0, 1):
            ln = 70 if u == 0 else 56
            shapes += xf_all(leaf_hatched(ln, ln * 0.30, lines=9),
                             u * math.radians(36), 1.0, (0, 40))
        shapes += xf_all(berry_cluster(6, 5.0, 17.0, seed=i), 0.0, 1.0, (0, 58))
        title = "عنقود أوراق محشوّة"
    elif style == 1:
        f = vwave(0.0, -60.0, 70.0, 16.0, 1.4)
        shapes.append(P([f(k / 40) for k in range(41)], smooth=True, w=W_MAIN))
        for k in range(7):
            t = 0.06 + 0.88 * k / 6
            px, py = f(t)
            th = tangent_of(f, t)
            side = 1 if k % 2 == 0 else -1
            ln = 34 * rng.uniform(0.9, 1.1)
            shapes += xf_all(leaf_plain(ln, ln * 0.32),
                             th + side * math.radians(50) + math.pi / 2,
                             1.0, (px, py))
        shapes += xf_all(berry_triple(4.0, 10.0), 0.0, 1.0, f(0.02))
        title = "غصن رأسي بأوراق"
    elif style == 2:
        for k in range(5):
            a = TAU * k / 5
            # petal() يُرجع شكلاً واحداً لا قائمة
            shapes.append(xf(petal(44, 16, a=0.95, b=0.68), a, 1.0,
                             polar(13, a - math.pi / 2)))
        shapes += rosette_small(13, 10, rings=2)
        for u in (-1, 1):
            shapes += xf_all(leaf_hatched(46, 14, lines=7),
                             u * math.radians(132), 1.0, (0, 20))
        title = "زهرة بوريدة وأوراق محشوّة"
    else:
        shapes += lotus_sprig(76, 48)
        shapes += xf_all(berry_triple(4.2, 11.0), 0.0, 1.0, (0, 34))
        shapes.append(LINE((0, 20), (0, 62), w=W_MAIN))
        shapes += xf_all(diamond_ornament(14), 0.0, 1.0, (0, 78))
        title = "سعفة بمعيّن وحبّات"
    return f"cluster_{i + 1:02d}", title, shapes, TILE


# ===========================================================================
# السجل
# ===========================================================================

FAMILIES = [
    ("أشرطة رأسية بأوراق وحبّات", build_band_vine, 12),
    ("سلاسل معلّقة", build_strand, 8),
    ("ألواح سلاسل", build_panel, 4),
    ("وريدات صغيرة", build_rosette, 8),
    ("عناقيد وعناصر", build_cluster, 8),
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
            fname = f"B{num:03d}_{name}.svg"
            write_svg(OUT_DIR / fname, shapes, canvas=canvas, margin=10,
                      stroke=STROKE, title=f"B{num:03d} — {title}")
            index.append({"num": num, "file": fname, "title": title,
                          "family": fam, "wide": canvas == PANEL,
                          "tall": canvas == BAND, "elements": len(shapes)})

    (ROOT / "index_bands.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"تم توليد {num} رسمة في {OUT_DIR}")
    for fam, _, c in FAMILIES:
        print(f"  - {fam}: {c}")
    return index


if __name__ == "__main__":
    main()
