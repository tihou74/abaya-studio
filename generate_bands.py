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


# مُعامِل القاعدة في مُحيط الورقة:
#   a = 0.70  ورقة عريضة عند قاعدتها — مناسبة للورقة المنفردة على ساق
#   a = 1.25  ورقة ضيّقة عند قاعدتها — *ضرورية* للأوراق المتشعّبة من نقطة واحدة
# السبب: نصف العرض عند t يساوي width·t^a·(1−t)^b / norm، وبـ a=0.70 يبلغ
# نصف العرض 10.4 على مسافة 8.8 من القاعدة، أي امتداد زاوي ≈ 50° لكل ورقة،
# فورقتان تتلاقيان حتى لو فصلت بينهما 96°. وبـ a=1.25 يهبط الامتداد إلى ≈ 33°.
A_SINGLE = 0.70
A_RADIAL = 1.25


def leaf_plain(length=22.0, width=7.0, bend=2.0, vein=True, w=W_MAIN,
               a=A_SINGLE):
    out = [ribbon(lambda t: (bend * math.sin(math.pi * t), -length * t),
                  taper_fn(width, a, 0.95), n=54, w=w)]
    if vein:
        out.append(P([(0, -length * 0.08), (bend, -length * 0.55),
                      (0, -length * 0.92)], smooth=True, w=W_FINE))
    return out


def leaf_solid(length=20.0, width=6.5, bend=2.0, a=A_SINGLE):
    """ورقة مصمتة — تُستخدم في النقوش الداكنة كما في المرجع."""
    r = ribbon(lambda t: (bend * math.sin(math.pi * t), -length * t),
               taper_fn(width, a, 0.95), n=54)
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


def berry_bunch(rows=(3, 2, 1), r=3.2, gap=7.6):
    """
    عنقود منتظم كعنقود العنب: صفوف متناقصة ومتداخلة.
    الترتيب المنتظم أنظف من التوزيع العشوائي الذي يُخرج بقعاً متفرّقة.
    """
    out = []
    for ri, count in enumerate(rows):
        y = ri * gap * 0.88
        for k in range(count):
            x = (k - (count - 1) / 2) * gap
            out.append(DOT((x, y), r))
    return out


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
        out += xf_all(leaf_plain(ln, ln * 0.30, bend=u * 2.5, vein=False, w=w,
                                 a=A_RADIAL),
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
                    leaf = (leaf_hatched(ln, ln * 0.31, a=A_RADIAL, lines=7)
                            if hatch else leaf_plain(ln, ln * 0.31, a=A_RADIAL))
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
                leaf = (leaf_hatched(ln, ln * 0.30, a=A_RADIAL, lines=6)
                        if hatch else leaf_plain(ln, ln * 0.30, a=A_RADIAL))
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
                    shapes += xf_all(leaf_solid(ln, ln * 0.30, a=A_RADIAL),
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
    """
    سلسلة معلّقة مفردة.
    الكثافة: 5–7 عناصر على السلسلة. ثلاثة عناصر فقط تترك خطّ خرز طويلاً فارغاً
    ولا تُشبه المرجع.
    """
    pool = _ornament_set(900 + i)
    n_orn = 5 + i % 3
    jitter = random.Random(700 + i)
    positions = []
    for k in range(n_orn):
        base = 0.08 + 0.84 * k / max(1, n_orn - 1)
        positions.append(min(0.95, max(0.05, base + jitter.uniform(-0.03, 0.03))))
    orns = [(p, pool[k % len(pool)]) for k, p in enumerate(positions)]
    shapes = strand(0.0, 20.0, 660.0, 14.0 + (i % 3) * 2.5, 2.6,
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
        n_orn = 4 + (k + i) % 3
        offset = 0.05 * ((k * 7 + i * 3) % 5)
        positions = [min(0.93, 0.08 + offset + 0.78 * j / max(1, n_orn - 1))
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
    """
    عناصر منفردة — ثمانية تصاميم مختلفة فعلاً (لا أربعة مكرّرة).

    قاعدة صريحة: **لا تقاطع بين العناصر المحشوّة بالخطوط.**
    تقاطع ورقتين محشوّتين يُنتج تشابك خطوط لا يُقرأ. ولذلك:
      - الأوراق المتعدّدة تُربط على سويقة بارتفاعات مختلفة لا من نقطة واحدة
      - الأوراق المتقابلة تتجه جهتين متعاكستين فلا تتلاقى
      - لا أوراق فوق بتلات الزهرة — تُنقل إلى الساق أسفلها
    """
    shapes = []

    if i == 0:          # ثلاث أوراق محشوّة على سويقة بارتفاعات مختلفة
        shapes.append(LINE((0, 92), (0, 24), w=W_MAIN))
        shapes += xf_all(leaf_hatched(72, 20, a=A_RADIAL, lines=9),
                         0.0, 1.0, (0, 24))
        # القاعدتان على ارتفاعين مختلفين — لا من نقطة واحدة
        for side, y in ((1, 46), (-1, 62)):
            shapes += xf_all(leaf_hatched(52, 14, a=A_RADIAL, lines=7),
                             side * math.radians(56), 1.0, (0, y))
        shapes += xf_all(berry_bunch((3, 2), 3.2, 7.6), 0.0, 1.0, (0, 100))
        title = "ثلاث أوراق محشوّة وعنقود"

    elif i == 1:        # ورقتان متقابلتان محشوّتان + حبّات
        shapes.append(LINE((0, 92), (0, 8), w=W_MAIN))
        for side in (1, -1):
            shapes += xf_all(leaf_hatched(62, 17, a=A_RADIAL, lines=8),
                             side * math.radians(58), 1.0, (0, 44))
        shapes += xf_all(leaf_hatched(46, 13, a=A_RADIAL, lines=6),
                         0.0, 1.0, (0, 8))
        shapes += xf_all(berry_triple(3.4, 8.5), 0.0, 1.0, (0, 80))
        title = "ورقتان متقابلتان محشوّتان"

    elif i == 2:        # زهرة خمسية بوريدة — بلا أي ورقة فوق البتلات
        for k in range(5):
            a = TAU * k / 5
            shapes.append(xf(petal(46, 13, a=0.95, b=0.68), a, 1.0,
                             polar(14, a - math.pi / 2)))
        shapes += rosette_small(13, 10, rings=2)
        title = "زهرة خمسية بوريدة"

    elif i == 3:        # زهرة على ساق بورقتين أسفلها
        shapes += xf_all([xf(petal(42, 12, a=0.95, b=0.68), TAU * k / 5, 1.0,
                             polar(13, TAU * k / 5 - math.pi / 2))
                          for k in range(5)], 0.0, 1.0, (0, -22))
        shapes += xf_all(rosette_small(12, 8, rings=2), 0.0, 1.0, (0, -22))
        shapes.append(LINE((0, -8), (0, 100), w=W_MAIN))
        for side, y in ((1, 32), (-1, 64)):
            shapes += xf_all(leaf_hatched(46, 12, a=A_RADIAL, lines=6),
                             side * math.radians(64), 1.0, (0, y))
        title = "زهرة على ساق بورقتين"

    elif i == 4:        # عنقود حبّات كبير بورقتين فوقه
        shapes += xf_all(berry_bunch((3, 3, 2, 1), 3.6, 8.6), 0.0, 1.0, (0, 20))
        shapes.append(LINE((0, 16), (0, -20), w=W_MAIN))
        for side in (1, -1):
            shapes += xf_all(leaf_plain(46, 13, a=A_RADIAL),
                             side * math.radians(56), 1.0, (0, -6))
        title = "عنقود حبّات بورقتين"

    elif i == 5:        # وريدة بأربع أوراق متباعدة 90°
        shapes += rosette_small(30, 14, rings=3)
        for k in range(4):
            a = TAU * k / 4 + math.pi / 4
            shapes += xf_all(leaf_plain(42, 12, a=A_RADIAL), a, 1.0,
                             polar(32, a - math.pi / 2))
        for k in range(4):
            a = TAU * k / 4
            shapes.append(DOT(polar(40, a), 2.8))
        title = "وريدة بأربع أوراق"

    elif i == 6:        # سعفة لوتس بمعيّن مُعلّق
        # ثلاث وريقات بقواعد ضيّقة وزوايا واسعة فلا تتراكب
        for u, ln in ((0, 76), (1, 58), (-1, 58)):
            shapes += xf_all(leaf_plain(ln, ln * 0.26, bend=u * 3.0,
                                        vein=True, a=A_RADIAL),
                             u * math.radians(44), 1.0, (0, 22))
        shapes.append(LINE((0, 22), (0, 66), w=W_MAIN))
        shapes.append(DOT((0, 38), 3.0))
        shapes += xf_all(diamond_ornament(14), 0.0, 1.0, (0, 84))
        title = "سعفة لوتس بمعيّن"

    else:               # غصن بمحلقين متناظرين وحبّات
        shapes += xf_all(leaf_plain(58, 16, bend=0.0, a=A_RADIAL),
                         0.0, 1.0, (0, 26))
        shapes.append(LINE((0, 26), (0, 98), w=W_MAIN))
        # المحالق تخرج يميناً ويساراً. الزاوية ±28° تشير للجهة نفسها
        # (كلتاهما نحو اليمين)؛ الصحيح 20° و160°.
        for side, theta in ((1, math.radians(20)), (-1, math.radians(160))):
            shapes += tendril_at(theta, 20, 1.15, side, (0, 50))
        shapes += xf_all(berry_triple(3.2, 8.0), 0.0, 1.0, (0, 86))
        title = "غصن بمحلقين وحبّات"

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
