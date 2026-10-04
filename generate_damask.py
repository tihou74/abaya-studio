#!/usr/bin/env python3
"""
المجموعة الرابعة: زخرفة مصمتة، أشرطة كلاسيكية متناظرة، ومتدلّيات.

مبنية على المراجع:
  1) فرع زهري مصمت متعرّج بتدرّج سماكة وحلزون — أسلوب الداماسك
  2) أشرطة كلاسيكية متناظرة وكثيفة (داماسك، أرابيسك، مفتاح يوناني، فرط هندسي)
  3) متدلّيات: خيوط نباتية رفيعة تنزل بأطوال مختلفة بأوراق وحلقات

ملاحظة تقنية: الأشكال المصمتة المتراكبة تتّحد في ظلّ واحد، فلا تتشابك
كما تتشابك المحيطات — ولذلك هذا الأسلوب أكثر تسامحاً وأنظف نتيجة.

التشغيل:  python3 generate_damask.py
"""

import json
import math
import random
from pathlib import Path

from artlib import (TAU, W_FINE, W_MAIN, W_MID, CIRC, DOT, FILLED, LINE, P,
                    filled_ribbon, mirror_x, polar, ribbon, spiral_axis,
                    taper_fn, taper_tip, tangent_of, write_svg, xf, xf_all)

ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "damask"

VINE = (200, 700)      # فرع زهري مصمت
BAND = (150, 700)      # شريط كلاسيكي
PANEL = (460, 700)     # لوح متدلّيات
TILE = (200, 200)      # عنصر منفرد

STROKE = 1.5


# ===========================================================================
# عناصر مصمتة
# ===========================================================================


def leaf_fill(length=40.0, width=13.0, bend=4.0, a=1.0, b=0.92):
    """ورقة مصمتة مدبّقة الطرف وضيّقة القاعدة."""
    return filled_ribbon(
        lambda t: (bend * math.sin(math.pi * t), -length * t),
        taper_fn(width, a, b), n=70)


def petal_fill(length=24.0, width=9.0, bend=0.0):
    return filled_ribbon(
        lambda t: (bend * math.sin(math.pi * t), -length * t),
        taper_fn(width, 0.95, 0.70), n=56)


def flower_fill(r=22.0, petals=5, rot=0.0, center=0.0):
    """زهرة مصمتة: بتلات مُعبّأة + قلب. التراكب بينها يتّحد فلا يُشوّه."""
    out = []
    base_r = r * 0.22
    half_w = r * 0.30 * math.sqrt(5.0 / petals)
    for k in range(petals):
        a = TAU * k / petals + rot
        out.append(xf(petal_fill(r - base_r, half_w), a, 1.0,
                      polar(base_r, a - math.pi / 2)))
    out.append(DOT((0, 0), center if center else r * 0.17))
    return out


def curl_fill(R=38.0, turns=1.35, phase=0.0, w0=6.5, at=(0.0, 0.0)):
    """حلزون مصمت يتلاشى طرفه — العنصر المميّز في المرجع الأول."""
    ax = spiral_axis(R, turns, phase, 0.90, at)
    return [filled_ribbon(ax, taper_tip(w0, 0.70), n=110)]


def stem_fill(axis, w0=7.0, power=0.78, tip=0.0, n=120):
    return [filled_ribbon(axis, taper_tip(w0, power, tip), n=n)]


def diamond_fill(size=9.0, ratio=0.62):
    return FILLED([(0, -size), (size * ratio, 0), (0, size),
                   (-size * ratio, 0)], smooth=False)


def floret4_fill(r=13.0, rot=0.0):
    """زهرة رباعية مصمتة — وحدة الشبكة في المرجع الثاني."""
    out = []
    for k in range(4):
        a = TAU * k / 4 + rot
        out.append(xf(petal_fill(r, r * 0.46), a, 1.0,
                      polar(r * 0.18, a - math.pi / 2)))
    return out


def palmette_fill(h=58.0, w=46.0, blades=7):
    """مروحة نخيلية (أنثيميون) مصمتة — متناظرة حول المحور الرأسي."""
    out = []
    for k in range(blades):
        u = (k - (blades - 1) / 2) / max(1, (blades - 1) / 2)
        ang = u * math.radians(66)
        ln = h * (1 - 0.34 * abs(u))
        out.append(xf(petal_fill(ln, w / blades * 0.78, bend=u * 3.0),
                      ang, 1.0, (0, 0)))
    # تجعيدتان عند القاعدة
    for side in (1, -1):
        out += curl_fill(13.0, 0.95, math.radians(90 if side > 0 else 90),
                         4.2, (side * 12.0, 7.0))
    return out


# ===========================================================================
# 1) فروع زهرية مصمتة
# ===========================================================================


def build_vine(i):
    rng = random.Random(400 + i)
    H = 600.0
    dirn = 1 if i % 2 == 0 else -1
    amp = 24.0 + (i % 3) * 9.0
    cycles = 1.15 + (i % 4) * 0.16
    w0 = 7.0 + (i % 2) * 1.2

    def axis(t):
        return (dirn * amp * math.sin(TAU * cycles * t), H * (1 - t))

    shapes = list(stem_fill(axis, w0, 0.74))

    # حلزون في الأسفل — السمة المميّزة للمرجع
    base = axis(0.02)
    shapes += curl_fill(34.0 + (i % 3) * 6, 1.4, math.radians(dirn * 60),
                        5.4, (base[0] - dirn * 26, base[1] - 34))
    shapes += stem_fill(lambda t: (base[0] - dirn * 26 * t,
                                   base[1] - 34 * t), 5.0, 0.6, 3.0, n=40)

    n_br = 5 + i % 3
    for k in range(n_br):
        t = 0.12 + 0.80 * k / max(1, n_br - 1)
        px, py = axis(t)
        th = tangent_of(axis, t)
        side = 1 if k % 2 == 0 else -1
        blen = (74 - 24 * t) * rng.uniform(0.9, 1.1)
        bang = th + side * math.radians(52)
        bbow = rng.uniform(10, 20) * side

        def br(u, px=px, py=py, bang=bang, blen=blen, bbow=bbow):
            r = blen * u
            x, y = px + r * math.cos(bang), py + r * math.sin(bang)
            d = bbow * math.sin(math.pi * u)
            return (x - d * math.sin(bang), y + d * math.cos(bang))

        shapes += stem_fill(br, w0 * 0.52, 0.80, n=60)

        # أوراق على الفرع
        for j, u in enumerate((0.34, 0.66)):
            lx, ly = br(u)
            lth = tangent_of(br, u)
            lside = 1 if j % 2 == 0 else -1
            ln = (34 - 8 * t) * rng.uniform(0.9, 1.12)
            shapes.append(xf(leaf_fill(ln, ln * 0.34, bend=lside * 4),
                             lth + lside * math.radians(54) + math.pi / 2,
                             1.0, (lx, ly)))
        # زهرة عند طرف الفرع
        fr = (23 - 5 * t) * rng.uniform(0.9, 1.1)
        shapes += xf_all(flower_fill(fr, 5, rng.uniform(0, 1.2)),
                         0.0, 1.0, br(1.0))
        # محلق صغير مقابل
        if k % 2 == 1:
            shapes += curl_fill(16.0, 1.0, th - side * math.radians(40),
                                3.4, (px, py))

    # أوراق على الساق الرئيسي
    for u in (0.22, 0.46, 0.70, 0.90):
        lx, ly = axis(u)
        lth = tangent_of(axis, u)
        ln = 30 - 8 * u
        shapes.append(xf(leaf_fill(ln, ln * 0.34, bend=-4),
                         lth - math.radians(58) + math.pi / 2, 1.0, (lx, ly)))

    # زهرة في القمة
    shapes += xf_all(flower_fill(19, 5, 0.4), 0.0, 1.0, axis(1.0))
    return f"vine_{i + 1:02d}", "فرع زهري مصمت", shapes, VINE


# ===========================================================================
# 2) أشرطة كلاسيكية متناظرة
# ===========================================================================


def rules(half_w=58.0, y0=10.0, y1=690.0, w=W_MID):
    """الخطان الرأسيان الحادّان على جانبي الشريط."""
    return [LINE((-half_w, y0), (-half_w, y1), w=w),
            LINE((half_w, y0), (half_w, y1), w=w)]


def build_classic(i):
    kind = i % 7
    v = i // 7
    HW = 56.0
    y0, y1 = 14.0, 686.0
    span = y1 - y0
    shapes = list(rules(HW, y0, y1))

    if kind == 0:                      # شبكة زهرات رباعية قُطرية
        step = 42.0 + v * 6
        rows = int(span / step) + 1
        for r in range(rows):
            y = y0 + 8 + r * step
            if y > y1 - 8:
                break
            for c in (-1, 1):
                x = c * step * 0.42
                if r % 2:
                    x = 0.0
                    if c > 0:
                        continue
                shapes += xf_all(floret4_fill(12.0 + v, math.radians(45)),
                                 0.0, 1.0, (x, y))
            if r % 2 == 0:
                for c in (-1, 1):
                    shapes.append(xf(diamond_fill(5.5), 0.0, 1.0,
                                     (c * HW * 0.74, y + step / 2)))
        title = "شبكة زهرات رباعية"

    elif kind == 1:                    # أرابيسك متناظر دقيق
        step = 74.0 + v * 10
        n = int(span / step)
        for k in range(n):
            y = y0 + 16 + k * step
            unit = []
            for side in (1, -1):
                unit += curl_fill(17.0, 1.15, math.radians(side * 100),
                                  3.6, (side * 15.0, y))
                unit.append(xf(leaf_fill(26, 7.5, bend=side * 3),
                               side * math.radians(34), 1.0,
                               (side * 7.0, y - 10)))
            unit.append(xf(diamond_fill(9.0, 0.55), 0.0, 1.0, (0, y + 24)))
            unit.append(DOT((0, y - 26), 3.0))
            shapes += unit
        title = "أرابيسك متناظر"

    elif kind == 2:                    # سلسلة حلقات متشابكة
        # حلقة مصمتة = قطع ناقص بخط سميك. والتشابك يحصل لأن الخطوة
        # أصغر من ارتفاع الحلقة، فتتقاطع كل حلقة مع التي تليها.
        ry = 26.0 + v * 4
        rx = HW * 0.62
        step = ry * 1.30
        n = int(span / step)
        for k in range(n):
            y = y0 + ry + k * step
            if y + ry > y1:
                break
            shapes.append(P([(rx * math.cos(TAU * j / 56),
                              y + ry * math.sin(TAU * j / 56))
                             for j in range(56)], closed=True, smooth=True,
                            w=2.6))
            shapes.append(DOT((0, y), 3.4))
        title = "سلسلة حلقات متشابكة"

    elif kind == 3:                    # مراوح نخيلية متكرّرة
        step = 92.0 + v * 12
        n = int(span / step)
        for k in range(n):
            y = y0 + 20 + k * step
            flip = -1 if (v and k % 2) else 1
            shapes += xf_all(palmette_fill(54, 44, 7),
                             0.0 if flip > 0 else math.pi, 1.0, (0, y + 46))
            shapes.append(xf(diamond_fill(7.0), 0.0, 1.0, (0, y)))
        title = "مراوح نخيلية متكرّرة"

    elif kind == 4:                    # مفتاح يوناني متّصل
        # وحدة الميندر الكلاسيكية: خط واحد متّصل يبدأ وينتهي على المستوى نفسه
        # فيتّصل التكرار بلا قطع. الإحداثيات أصلاً (امتداد، عَرض) ثم تُقلب رأسياً.
        u = HW * 0.42
        unit = [(0, -u), (0, 2 * u), (4 * u, 2 * u), (4 * u, -u),
                (u, -u), (u, u), (3 * u, u), (3 * u, 0),
                (2 * u, 0), (2 * u, -2 * u), (5 * u, -2 * u), (5 * u, -u)]
        period = 5 * u
        run = 6.0
        while y0 + run + period <= y1:
            pts = [(across, y0 + run + along) for along, across in unit]
            shapes.append(P(pts, closed=False, smooth=False, w=3.0))
            run += period
        title = "مفتاح يوناني"

    elif kind == 5:                    # فرط لولبي مربّع
        # لولب مربّع في كل خلية، باتجاه متبادل، موصولان بقطعة قصيرة
        cell = (2 * HW) * 0.80
        c = cell
        rows = int(span / (c * 1.06))
        spiral = [(0.14, 0.86), (0.14, 0.14), (0.86, 0.14), (0.86, 0.86),
                  (0.44, 0.86), (0.44, 0.44), (0.64, 0.44)]
        for r in range(rows):
            y = y0 + 6 + r * c * 1.06
            if y + c > y1:
                break
            flip = 1 if r % 2 == 0 else -1
            pts = [(flip * (sx - 0.5) * c, y + sy * c) for sx, sy in spiral]
            shapes.append(P(pts, closed=False, smooth=False, w=3.0))
            if r + 1 < rows and y + c * 1.06 + c <= y1:
                shapes.append(LINE((flip * (0.14 - 0.5) * c, y + 0.86 * c),
                                   (-flip * (0.14 - 0.5) * c,
                                    y + c * 1.06 + 0.14 * c), w=3.0))
        title = "فرط لولبي مربّع"

    else:                              # معيّنات وورقات متناوبة
        step = 46.0 + v * 8
        n = int(span / step)
        for k in range(n):
            y = y0 + 12 + k * step
            if k % 2 == 0:
                shapes.append(xf(diamond_fill(14.0, 0.58), 0.0, 1.0, (0, y)))
                for side in (1, -1):
                    shapes.append(DOT((side * 26, y), 3.2))
            else:
                for side in (1, -1):
                    shapes.append(xf(leaf_fill(30, 9, bend=side * 3),
                                     side * math.radians(62), 1.0, (0, y)))
                shapes.append(DOT((0, y), 3.0))
        title = "معيّنات وورقات متناوبة"

    return f"classic_{i + 1:02d}", f"شريط كلاسيكي — {title}", shapes, BAND


# ===========================================================================
# 3) متدلّيات
# ===========================================================================


def build_hanging(i):
    """
    خيوط نباتية تنزل من الأعلى بأطوال مختلفة — كستارة اللبلاب.
    خطوط رفيعة (لا مصمتة) مطابقةً للمرجع الثالث.
    """
    rng = random.Random(800 + i)
    n_str = 7 + i % 4
    W = 420.0
    shapes = []
    for k in range(n_str):
        x0 = -W / 2 + W * (k + 0.5) / n_str + rng.uniform(-10, 10)
        L = rng.uniform(0.45, 1.0) * 630.0
        amp = rng.uniform(8, 20)
        cyc = rng.uniform(1.1, 2.0)
        ph = rng.uniform(0, TAU)

        def f(t, x0=x0, L=L, amp=amp, cyc=cyc, ph=ph):
            # السعة تزداد نحو الأسفل: الخيط المتدلّي يتحرّك طرفه أكثر
            return (x0 + amp * t ** 1.3 * math.sin(TAU * cyc * t + ph),
                    10.0 + L * t)

        shapes.append(P([f(j / 70) for j in range(71)], smooth=True, w=W_MID))

        n_leaf = int(L / 30)
        for j in range(n_leaf):
            # تبدأ الأوراق من أعلى الخيط تقريباً: البداية عند 0.08 كانت
            # تترك قطعة ساق عارية في أعلى كل خيط فيظهر صفّ خطوط فارغ
            t = 0.015 + 0.975 * j / max(1, n_leaf - 1)
            px, py = f(t)
            th = tangent_of(f, t)
            side = 1 if j % 2 == 0 else -1
            ln = rng.uniform(10, 19) * (1 - 0.25 * t)
            shapes.append(xf(leaf_fill(ln, ln * rng.uniform(0.26, 0.34),
                                       bend=side * 1.5, a=1.25),
                             th + side * math.radians(rng.uniform(48, 68))
                             + math.pi / 2, 1.0, (px, py)))
            # حلقات صغيرة مفرّغة متفرّقة
            if rng.random() < 0.34:
                shapes.append(CIRC((px - side * rng.uniform(8, 13),
                                    py + rng.uniform(2, 7)),
                                   rng.uniform(3.0, 4.8), w=W_MID))
        # طرف متلاشٍ
        shapes.append(DOT(f(1.0), 1.8))
    return f"hanging_{i + 1:02d}", "متدلّيات نباتية", shapes, PANEL


# ===========================================================================
# 4) عناصر داماسك منفردة
# ===========================================================================


def build_unit(i):
    shapes = []
    if i == 0:
        shapes += palmette_fill(100, 86, 9)
        title = "مروحة نخيلية مصمتة"
    elif i == 1:
        # نصف أيمن ثم انعكاسه — يضمن تناظراً تاماً
        half = []
        half += stem_fill(lambda t: (54 * t, 24 - 52 * t ** 1.4), 8.0, 0.75,
                          n=60)
        half += curl_fill(30, 1.25, math.radians(140), 6.0, (54.0, -28.0))
        half.append(xf(leaf_fill(38, 12), math.radians(52) + math.pi / 2,
                       1.0, (30.0, -2.0)))
        shapes += half + mirror_x(half)
        shapes += xf_all(flower_fill(30, 5), 0.0, 1.0, (0, 20))
        shapes.append(xf(diamond_fill(13), 0.0, 1.0, (0, 54)))
        title = "حلزونان وزهرة"
    elif i == 2:
        shapes += flower_fill(66, 6, 0.0)
        for k in range(6):
            a = TAU * k / 6 + math.pi / 6
            shapes.append(xf(leaf_fill(40, 12), a, 1.0,
                             polar(30, a - math.pi / 2)))
        title = "زهرة سداسية مصمتة"
    elif i == 3:
        shapes += xf_all(floret4_fill(34, math.radians(45)), 0.0, 1.0, (0, 0))
        for k in range(4):
            a = TAU * k / 4
            shapes.append(xf(diamond_fill(12, 0.5), 0.0, 1.0, polar(50, a)))
        title = "زهرة رباعية ومعيّنات"
    elif i == 4:
        # حلزون أرقّ وأقل لفّاً، والأوراق على جهته الخارجية لتبقى ظاهرة
        ax = spiral_axis(62, 1.15, math.radians(200), 0.86)
        shapes += [filled_ribbon(ax, taper_tip(6.5, 0.72), n=130)]
        for u in (0.12, 0.40, 0.68):
            px, py = ax(u)
            out_ang = math.atan2(py, px)      # شعاعياً للخارج
            shapes.append(xf(leaf_fill(40, 12),
                             out_ang + math.pi / 2, 1.0, (px, py)))
        shapes += xf_all(flower_fill(22, 5), 0.0, 1.0, ax(0.0))
        title = "حلزون مصمت بأوراق"
    elif i == 5:
        # فرع أيمن كامل ثم انعكاسه، وكلّه يلامس الزهرة المركزية
        half = []
        half += stem_fill(lambda t: (76 * t, -30 * math.sin(math.pi * t)),
                          7.0, 0.78, n=60)
        for u, sgn in ((0.40, 1), (0.70, -1)):
            px, py = 76 * u, -30 * math.sin(math.pi * u)
            half.append(xf(leaf_fill(34, 11),
                           sgn * math.radians(62) + math.pi / 2, 1.0,
                           (px, py)))
        half += xf_all(flower_fill(17, 5), 0.0, 1.0, (76.0, 0.0))
        shapes += half + mirror_x(half)
        shapes += xf_all(flower_fill(28, 6), 0.0, 1.0, (0, 0))
        title = "فرعان متناظران بزهرة"
    elif i == 6:
        # المروحتان متلامستان عند القاعدة فتُقرآن وحدة واحدة
        shapes += xf_all(palmette_fill(74, 62, 7), 0.0, 1.0, (0, 16))
        shapes += xf_all(palmette_fill(50, 46, 5), math.pi, 1.0, (0, 20))
        shapes.append(xf(diamond_fill(11, 0.7), 0.0, 1.0, (0, 18)))
        title = "مروحتان متقابلتان"
    else:
        for k in range(8):
            a = TAU * k / 8
            shapes.append(xf(leaf_fill(54, 15, a=1.25), a, 1.0,
                             polar(16, a - math.pi / 2)))
        shapes += flower_fill(26, 8)
        title = "نجمة أوراق مصمتة"
    return f"unit_{i + 1:02d}", title, shapes, TILE



# ===========================================================================
# السجل
# ===========================================================================

FAMILIES = [
    ("فروع زهرية مصمتة", build_vine, 10),
    ("أشرطة كلاسيكية", build_classic, 14),
    ("متدلّيات", build_hanging, 8),
    ("عناصر داماسك", build_unit, 8),
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
            fname = f"D{num:03d}_{name}.svg"
            write_svg(OUT_DIR / fname, shapes, canvas=canvas, margin=10,
                      stroke=STROKE, title=f"D{num:03d} — {title}")
            index.append({"num": num, "file": fname, "title": title,
                          "family": fam, "wide": canvas == PANEL,
                          "tall": canvas in (BAND, VINE),
                          "elements": len(shapes)})

    (ROOT / "index_damask.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"تم توليد {num} رسمة في {OUT_DIR}")
    for fam, _, c in FAMILIES:
        print(f"  - {fam}: {c}")
    return index


if __name__ == "__main__":
    main()
