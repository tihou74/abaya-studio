#!/usr/bin/env python3
"""
المجموعة الثانية: أسلوب التطريز بالخط الرفيع (fine-line embroidery).

الخصائص المستهدفة:
  - خطوط رفيعة جداً ومتساوية تقريباً
  - زهور صغيرة بسيطة (5 بتلات مستديرة) لا ورد واقعي معقّد
  - أكاليل دائرية: جزء مزهّر + جزء مورّق + جزء منقّط أو خالٍ
  - أوراق صغيرة متبادلة على سويقات رفيعة
  - فراغ واسع وتهوية — لا كثافة

بلا أي اعتماديات خارجية. التشغيل:  python3 generate_art.py
"""

import json
import math
from pathlib import Path

from artlib import (TAU, CIRC, LINE, P, petal, polar, ribbon, taper_fn,
                    tangent_of, write_svg, xf, xf_all)

ROOT = Path(__file__).resolve().parent
ART_DIR = ROOT / "art"

SQUARE = (200, 200)
STRIP = (620, 150)

# في هذا الأسلوب السماكة تكاد تكون متساوية — التفاوت خفيف جداً فقط
WO = 1.0        # الخطوط العامة
WD = 0.82       # التفاصيل (العروق، النقاط)

STROKE = 1.15   # رفيع — هذا جوهر الأسلوب


# ===========================================================================
# عناصر أساسية صغيرة
# ===========================================================================


def small_leaf(length=14.0, width=5.2, vein=True, bend=1.2, w=WO):
    """ورقة صغيرة مدبّبة بعِرق واحد."""
    out = [ribbon(lambda t: (bend * math.sin(math.pi * t), -length * t),
                  taper_fn(width, 0.72, 0.92), n=46, w=w)]
    if vein:
        out.append(P([(0, -length * 0.08), (bend, -length * 0.55),
                      (0, -length * 0.90)], smooth=True, w=WD))
    return out


def tiny_leaf(length=8.0, width=3.2, w=WO):
    return [ribbon(lambda t: (0.6 * math.sin(math.pi * t), -length * t),
                   taper_fn(width, 0.75, 0.90), n=32, w=w)]


def flower5(r=10.0, petals=5, center=2.4, dots=False, rot=0.0, w=WO):
    """
    زهرة صغيرة بسيطة ببتلات مستديرة — العنصر الأكثر تكراراً في هذا الأسلوب.

    ملاحظة على الأبعاد: `width` في taper_fn هو *نصف* العرض، فالعرض الكامل ضِعفه.
    الوتر بين محوري بتلتين متجاورتين عند منتصف البتلة = 2·r_mid·sin(π/petals)،
    ويجب أن يبقى العرض الكامل أقل منه، وإلا تراكبت البتلات وصارت الزهرة كتلة.
    """
    out = []
    base_r = r * 0.24
    pl = r - base_r
    half_w = r * 0.27 * math.sqrt(5.0 / petals)
    for k in range(petals):
        a = TAU * k / petals + rot
        out.append(xf(petal(pl, half_w, a=0.95, b=0.68, w=w), a, 1.0,
                      polar(base_r, a - math.pi / 2)))
    if center > 0:
        out.append(CIRC((0, 0), center, w=WD))
    if dots:
        for k in range(petals):
            a = TAU * k / petals + rot + math.pi / petals
            out.append(CIRC(polar(center * 1.55, a), center * 0.34, w=WD))
    return out


def daisy(r=14.0, petals=9, center=2.6, rot=0.0, w=WO):
    """زهرة أقحوانية رفيعة البتلات."""
    out = []
    half_w = r * 0.16 * math.sqrt(9.0 / petals)
    for k in range(petals):
        a = TAU * k / petals + rot
        out.append(xf(petal(r - center, half_w, a=0.95, b=0.85, w=w), a, 1.0,
                      polar(center * 1.05, a - math.pi / 2)))
    out.append(CIRC((0, 0), center, w=WD))
    return out


def bud_small(length=11.0, width=5.0, w=WO):
    out = [ribbon(lambda t: (0, -length * t), taper_fn(width, 1.05, 0.80),
                  n=34, w=w)]
    out.append(P([(-width * 0.5, -length * 0.3), (0, -length * 0.62)],
                 smooth=True, w=WD))
    return out


def berry_sprig(n=3, r=2.6, spread=7.0, w=WO):
    """عنقود حبّات صغيرة على سويقات قصيرة."""
    out = []
    for k in range(n):
        u = (k - (n - 1) / 2) / max(1, (n - 1) / 2) if n > 1 else 0.0
        bx, by = u * spread, -spread * (1.0 - 0.35 * abs(u)) - 4
        out.append(LINE((0, 0), (bx * 0.8, by * 0.7), w=WD))
        out.append(CIRC((bx, by), r, w=w))
    return out


def sparkle(size=5.0, rays=4, w=WD):
    """نجمة لمعة صغيرة — عنصر تزييني شائع في هذا الأسلوب."""
    out = []
    for k in range(rays):
        a = TAU * k / (2 * rays) * 2 + math.pi / (2 * rays) * 0
        a = TAU * k / rays / 2
        out.append(P([polar(size, a), polar(size * 0.18, a + math.pi / 2),
                      polar(size, a + math.pi),
                      polar(size * 0.18, a - math.pi / 2)],
                     closed=True, smooth=True, w=w))
    return out


def dots_along(f, t0, t1, count, r=1.7, w=WD):
    out = []
    for k in range(count):
        t = t0 + (t1 - t0) * (k / max(1, count - 1))
        out.append(CIRC(f(t), r, w=w))
    return out


def leaves_along_arc(f, t0, t1, count, length=14.0, width=5.2, out_deg=52,
                     alternate=True, taper=0.0, tiny_every=0, w=WO):
    """أوراق صغيرة متبادلة على منحنى، موجّهة بمَيل المنحنى."""
    out = []
    for k in range(count):
        t = t0 + (t1 - t0) * (k / max(1, count - 1)) if count > 1 else (t0 + t1) / 2
        px, py = f(t)
        th = tangent_of(f, t)
        side = (1 if k % 2 == 0 else -1) if alternate else 1
        sc = 1.0 - taper * (k / max(1, count - 1))
        ang = th + side * math.radians(out_deg) + math.pi / 2
        if tiny_every and k % tiny_every == 0:
            out += xf_all(tiny_leaf(length * 0.52 * sc, width * 0.6 * sc, w=w),
                          ang, 1.0, (px, py))
        else:
            out += xf_all(small_leaf(length * sc, width * sc, w=w),
                          ang, 1.0, (px, py))
    return out


# ===========================================================================
# أكاليل
# ===========================================================================


def circle_f(R, cx=0.0, cy=0.0):
    """معلمة الدائرة: t في [0,1] يقابل الزاوية الكاملة، بدءاً من الأعلى."""
    def f(t):
        a = -math.pi / 2 + TAU * t
        return (cx + R * math.cos(a), cy + R * math.sin(a))
    return f


def _frac(t):
    return t - math.floor(t)


def _covered(t, gaps):
    u = _frac(t)
    for g0, g1 in gaps:
        a, b = _frac(g0), _frac(g1)
        if a <= b:
            if a <= u <= b:
                return True
        else:                      # الفترة تلتفّ حول الصفر
            if u >= a or u <= b:
                return True
    return False


def ring_segments(R, spans, gaps, w=WO, step=0.0025):
    """
    يرسم حلقة الإكليل على هيئة أقواس تتخطّى مواضع الزهور.
    في هذا الأسلوب تحلّ الزهرة مكان الخط ولا يمرّ الخط داخلها.
    """
    f = circle_f(R)
    out = []
    for s0, s1 in spans:
        n = max(10, int(abs(s1 - s0) / step))
        cur = []
        for i in range(n + 1):
            t = s0 + (s1 - s0) * i / n
            if _covered(t, gaps):
                if len(cur) > 2:
                    out.append(P(cur, smooth=True, w=w))
                cur = []
            else:
                cur.append(f(t))
        if len(cur) > 2:
            out.append(P(cur, smooth=True, w=w))
    return out


def wreath(R=72.0, segments=(), ring="full", ring_w=WO):
    """
    إكليل: حلقة أساس + مقاطع موزّعة عليها.
    segments: متتالية من (نوع, t_من, t_إلى, إعدادات)
      'leaves' | 'flowers' | 'dots' | 'berries'
    ring: 'full' حلقة كاملة | 'none' بلا حلقة | (t0,t1) قوس جزئي
    """
    f = circle_f(R)
    out = []

    # تمريرة أولى: تحديد مواضع الزهور لحساب فجوات الحلقة
    gaps = []
    for kind, t0, t1, cfg in segments:
        if kind != "flowers":
            continue
        n = cfg.get("n", 3)
        sizes = cfg.get("sizes", [13, 10, 11])
        for k in range(n):
            t = t0 + (t1 - t0) * (k / max(1, n - 1)) if n > 1 else (t0 + t1) / 2
            rr = sizes[k % len(sizes)]
            half = (rr * 1.05) / (TAU * R)      # نصف الفجوة بوحدات t
            gaps.append((t - half, t + half))

    if ring == "full":
        out += ring_segments(R, [(0.0, 1.0)], gaps, w=ring_w)
    elif isinstance(ring, tuple):
        out += ring_segments(R, [ring], gaps, w=ring_w)

    for kind, t0, t1, cfg in segments:
        if kind == "leaves":
            out += leaves_along_arc(f, t0, t1, cfg.get("n", 7),
                                    cfg.get("len", 15), cfg.get("w", 5.4),
                                    cfg.get("out", 52),
                                    tiny_every=cfg.get("tiny", 0),
                                    taper=cfg.get("taper", 0.0))
        elif kind == "flowers":
            n = cfg.get("n", 3)
            sizes = cfg.get("sizes", [13, 10, 11])
            for k in range(n):
                t = t0 + (t1 - t0) * (k / max(1, n - 1)) if n > 1 else (t0 + t1) / 2
                px, py = f(t)
                rr = sizes[k % len(sizes)]
                off = cfg.get("off", 0.0)
                th = tangent_of(f, t)
                cxp = px + off * math.cos(th + math.pi / 2)
                cyp = py + off * math.sin(th + math.pi / 2)
                if cfg.get("daisy") and k % 2 == 1:
                    out += xf_all(daisy(rr * 1.05, 9, 2.5), 0.0, 1.0, (cxp, cyp))
                else:
                    out += xf_all(flower5(rr, 5, rr * 0.22,
                                          dots=cfg.get("dots", False),
                                          rot=k * 0.7),
                                  0.0, 1.0, (cxp, cyp))
            # أوراق صغيرة تحشو بين الزهور
            if cfg.get("fill_leaves", True):
                out += leaves_along_arc(f, t0 + 0.012, t1 - 0.012,
                                        max(2, n + 1), 11, 4.2, 70)
        elif kind == "dots":
            out += dots_along(f, t0, t1, cfg.get("n", 14), cfg.get("r", 1.7))
        elif kind == "berries":
            n = cfg.get("n", 3)
            for k in range(n):
                t = t0 + (t1 - t0) * (k / max(1, n - 1)) if n > 1 else (t0 + t1) / 2
                px, py = f(t)
                th = tangent_of(f, t)
                out += xf_all(berry_sprig(3, 2.5, 7.0),
                              th + math.pi / 2, 1.0, (px, py))
    return out


WREATH_FULL = [
    # (وصف, مقاطع, الحلقة)
    ("إكليل أوراق كامل",
     (("leaves", 0.0, 0.98, {"n": 18, "len": 15, "w": 5.4, "tiny": 4}),), "full"),
    ("إكليل أوراق وزهور",
     (("flowers", 0.52, 0.86, {"n": 4, "sizes": [13, 10, 12, 9]}),
      ("leaves", 0.90, 1.44, {"n": 11, "len": 14, "w": 5.0, "tiny": 3})), "full"),
    ("إكليل زهور متفرّقة",
     (("flowers", 0.0, 0.25, {"n": 3, "sizes": [12, 9, 11]}),
      ("leaves", 0.30, 0.70, {"n": 8, "len": 14, "w": 5.0}),
      ("flowers", 0.50, 0.50, {"n": 1, "sizes": [10]}),
      ("leaves", 0.75, 0.97, {"n": 5, "len": 13, "w": 4.6})), "full"),
    ("إكليل أقحوان",
     (("flowers", 0.40, 0.92, {"n": 5, "sizes": [13, 11, 12, 10, 13],
                               "daisy": True}),
      ("leaves", 0.97, 1.36, {"n": 9, "len": 14, "w": 5.0, "tiny": 3})), "full"),
    ("إكليل أوراق مزدوج",
     (("leaves", 0.0, 0.48, {"n": 10, "len": 16, "w": 5.6}),
      ("leaves", 0.52, 0.98, {"n": 10, "len": 16, "w": 5.6})), "full"),
    ("إكليل حبّات وأوراق",
     (("berries", 0.10, 0.40, {"n": 4}),
      ("leaves", 0.46, 0.96, {"n": 11, "len": 14, "w": 5.0, "tiny": 3})), "full"),
    ("إكليل زهور كثيف",
     (("flowers", 0.0, 0.46, {"n": 5, "sizes": [12, 9, 11, 10, 12]}),
      ("flowers", 0.54, 0.96, {"n": 5, "sizes": [10, 12, 9, 11, 10]})), "full"),
    ("إكليل بزهرة واحدة كبيرة",
     (("flowers", 0.62, 0.62, {"n": 1, "sizes": [20], "dots": True,
                               "fill_leaves": False}),
      ("leaves", 0.70, 1.08, {"n": 8, "len": 15, "w": 5.2}),
      ("leaves", 0.20, 0.52, {"n": 7, "len": 13, "w": 4.6, "tiny": 3})), "full"),
    ("إكليل أوراق رفيع",
     (("leaves", 0.0, 0.97, {"n": 22, "len": 12, "w": 3.8, "tiny": 3}),), "full"),
    ("إكليل متوازن",
     (("flowers", 0.08, 0.30, {"n": 3, "sizes": [11, 13, 9]}),
      ("leaves", 0.36, 0.60, {"n": 6, "len": 14, "w": 5.0}),
      ("flowers", 0.58, 0.80, {"n": 3, "sizes": [9, 12, 10]}),
      ("leaves", 0.86, 1.04, {"n": 5, "len": 13, "w": 4.6})), "full"),
]


def build_wreath_full(i):
    title, segs, ring = WREATH_FULL[i]
    return f"wreath_full_{i + 1:02d}", title, wreath(72.0, segs, ring), SQUARE


WREATH_PART = [
    ("إكليل جزئي — باقة أعلى اليسار",
     (("flowers", 0.74, 0.92, {"n": 4, "sizes": [14, 10, 12, 9]}),
      ("leaves", 0.60, 0.72, {"n": 4, "len": 15, "w": 5.2})), "full"),
    ("إكليل جزئي — زهور أسفل اليمين",
     (("flowers", 0.20, 0.42, {"n": 4, "sizes": [13, 10, 12, 9], "daisy": True}),
      ("leaves", 0.44, 0.56, {"n": 4, "len": 14, "w": 5.0})), "full"),
    ("إكليل جزئي — قوس مورّق يسار",
     (("leaves", 0.52, 0.96, {"n": 12, "len": 16, "w": 5.6, "tiny": 4}),),
     (0.50, 1.02)),
    ("إكليل جزئي — ثلثان مورّقان",
     (("leaves", 0.0, 0.64, {"n": 15, "len": 15, "w": 5.2, "tiny": 4}),),
     (-0.02, 0.68)),
    ("إكليل جزئي — باقة سفلية",
     (("flowers", 0.40, 0.62, {"n": 5, "sizes": [15, 11, 13, 10, 12]}),
      ("leaves", 0.30, 0.38, {"n": 3, "len": 15, "w": 5.2}),
      ("leaves", 0.64, 0.74, {"n": 3, "len": 15, "w": 5.2})), "full"),
    ("إكليل جزئي — زهور علوية",
     (("flowers", 0.88, 1.12, {"n": 4, "sizes": [13, 10, 12, 9]}),
      ("leaves", 0.76, 0.86, {"n": 3, "len": 14, "w": 5.0})), "full"),
    ("إكليل جزئي — نصف مورّق",
     (("leaves", 0.26, 0.74, {"n": 13, "len": 16, "w": 5.4, "tiny": 3}),),
     (0.24, 0.78)),
    ("إكليل جزئي — زهور وحبّات",
     (("flowers", 0.56, 0.74, {"n": 3, "sizes": [14, 10, 12]}),
      ("berries", 0.78, 0.90, {"n": 3}),
      ("leaves", 0.44, 0.52, {"n": 3, "len": 14, "w": 5.0})), "full"),
    ("إكليل جزئي — ربع مزهّر",
     (("flowers", 0.0, 0.22, {"n": 4, "sizes": [12, 9, 13, 10]}),
      ("leaves", 0.26, 0.36, {"n": 3, "len": 14, "w": 5.0})), "full"),
    ("إكليل جزئي — قوس مزدوج",
     (("leaves", 0.08, 0.40, {"n": 9, "len": 15, "w": 5.2}),
      ("leaves", 0.60, 0.92, {"n": 9, "len": 15, "w": 5.2})), (0.04, 0.96)),
    ("إكليل جزئي — زهرة كبيرة وأوراق",
     (("flowers", 0.30, 0.30, {"n": 1, "sizes": [22], "dots": True,
                               "fill_leaves": False}),
      ("leaves", 0.36, 0.58, {"n": 6, "len": 16, "w": 5.6}),
      ("leaves", 0.08, 0.24, {"n": 5, "len": 14, "w": 5.0, "tiny": 3})), "full"),
    ("إكليل جزئي — ثلاث مجموعات",
     (("flowers", 0.04, 0.14, {"n": 2, "sizes": [12, 9]}),
      ("flowers", 0.36, 0.46, {"n": 2, "sizes": [11, 13]}),
      ("flowers", 0.68, 0.78, {"n": 2, "sizes": [10, 12]}),
      ("leaves", 0.18, 0.32, {"n": 4, "len": 13, "w": 4.6}),
      ("leaves", 0.50, 0.64, {"n": 4, "len": 13, "w": 4.6})), "full"),
]


def build_wreath_part(i):
    title, segs, ring = WREATH_PART[i]
    return f"wreath_part_{i + 1:02d}", title, wreath(72.0, segs, ring), SQUARE


WREATH_DOT = [
    ("إكليل منقّط — أوراق يسار ونقاط يمين",
     (("leaves", 0.52, 0.98, {"n": 12, "len": 16, "w": 5.4, "tiny": 4}),
      ("dots", 0.04, 0.46, {"n": 16, "r": 1.8})), (0.50, 1.02)),
    ("إكليل منقّط — نصف ونصف",
     (("leaves", 0.0, 0.46, {"n": 11, "len": 15, "w": 5.2}),
      ("dots", 0.54, 0.96, {"n": 15, "r": 1.7})), (-0.02, 0.50)),
    ("إكليل منقّط — زهور ونقاط",
     (("flowers", 0.60, 0.86, {"n": 4, "sizes": [13, 10, 12, 9]}),
      ("dots", 0.04, 0.50, {"n": 17, "r": 1.7})), (0.54, 0.94)),
    ("إكليل منقّط — ثلاثة أرباع نقاط",
     (("leaves", 0.78, 1.04, {"n": 7, "len": 15, "w": 5.2}),
      ("dots", 0.10, 0.72, {"n": 22, "r": 1.6})), (0.76, 1.06)),
    ("إكليل منقّط — نقاط متباعدة",
     (("leaves", 0.30, 0.70, {"n": 10, "len": 15, "w": 5.2, "tiny": 3}),
      ("dots", 0.76, 1.24, {"n": 11, "r": 2.1})), (0.28, 0.72)),
    ("إكليل منقّط — باقة ونقاط",
     (("flowers", 0.40, 0.60, {"n": 4, "sizes": [14, 10, 12, 9], "daisy": True}),
      ("leaves", 0.30, 0.36, {"n": 2, "len": 14, "w": 5.0}),
      ("dots", 0.68, 1.26, {"n": 19, "r": 1.7})), (0.64, 1.30)),
    ("إكليل منقّط — نقاط داخلية",
     (("leaves", 0.0, 0.97, {"n": 16, "len": 13, "w": 4.4, "tiny": 3}),), "full"),
    ("إكليل منقّط — ربع مزهّر",
     (("flowers", 0.0, 0.18, {"n": 3, "sizes": [13, 10, 12]}),
      ("dots", 0.26, 0.92, {"n": 23, "r": 1.6})), (0.22, 0.96)),
]


def build_wreath_dot(i):
    title, segs, ring = WREATH_DOT[i]
    shapes = wreath(72.0, segs, ring)
    if i == 6:        # حلقة نقاط داخلية إضافية
        shapes += dots_along(circle_f(56.0), 0.0, 0.96, 26, 1.5)
    return f"wreath_dots_{i + 1:02d}", title, shapes, SQUARE


# ===========================================================================
# زوايا نباتية
# ===========================================================================


def corner_spray(i):
    """
    زاوية نباتية رفيعة: ساق منحنٍ من الزاوية، أوراق متبادلة،
    وزهور صغيرة عند الطرف أو الوسط.
    """
    A = 168.0
    shapes = []
    style = i % 6
    v = i // 6

    def stem(t):
        # من أعلى اليمين إلى أسفل اليسار بانحناء لطيف نحو الزاوية
        return (A - A * t, A * (t ** 2.1))

    if style == 0:        # أوراق فقط
        shapes.append(P([stem(k / 30) for k in range(31)], smooth=True, w=WO))
        shapes += leaves_along_arc(stem, 0.06, 0.94, 13 + v * 2, 17, 5.8,
                                   52, tiny_every=4, taper=0.25)
    elif style == 1:      # أوراق + زهور عند الطرف
        shapes.append(P([stem(k / 30) for k in range(31)], smooth=True, w=WO))
        # الأوراق تمتدّ حتى الزهور فتتداخل معها — الفجوة تجعل الزهرة تبدو منفصلة
        shapes += leaves_along_arc(stem, 0.09, 0.94, 11 + v, 16, 5.4, 54,
                                   taper=0.2)
        shapes += xf_all(flower5(20, 5, 4.2, dots=True), 0.0, 1.0, stem(0.03))
        shapes += xf_all(flower5(13, 5, 2.8, rot=0.6), 0.0, 1.0, stem(0.15))
        shapes += xf_all(bud_small(12, 5.2), math.radians(196), 1.0, stem(0.23))
    elif style == 2:      # باقة في الزاوية
        # سويقات منحنية لا مستقيمة — الخطوط المستقيمة المشعّة تبدو جافة وآلية
        for k, (ang, ln, bow) in enumerate(((16, 122, 16.0), (44, 140, -12.0),
                                           (70, 116, 14.0))):
            def f(t, a=math.radians(ang), L=ln, bw=bow):
                r = L * t
                px, py = 12 + r * math.cos(a), 12 + r * math.sin(a)
                # إزاحة عرضية تتلاشى عند الطرفين تُنتج انحناءً لطيفاً
                d = bw * math.sin(math.pi * t)
                return (px - d * math.sin(a), py + d * math.cos(a))
            shapes.append(P([f(j / 22) for j in range(23)], smooth=True, w=WO))
            shapes += leaves_along_arc(f, 0.26, 0.92, 5 + v, 15, 5.2, 56)
            shapes += xf_all(flower5(15 + k * 2, 5, 3.2, rot=k * 0.6),
                             0.0, 1.0, f(1.0))
        shapes += xf_all(berry_sprig(3, 2.6, 8), math.radians(42), 1.0, (30, 30))
    elif style == 3:      # غصنان متقابلان
        for sgn, rot in ((1, 0.0), (-1, math.pi / 2)):
            def f(t, r=rot):
                x = A - A * t
                y = A * (t ** 2.1)
                return (x, y) if r == 0 else (y, x)
            shapes.append(P([f(k / 28) for k in range(29)], smooth=True, w=WO))
            shapes += leaves_along_arc(f, 0.10, 0.92, 9 + v, 15, 5.2, 54,
                                       taper=0.25)
        shapes += xf_all(flower5(15, 5, 3.2, dots=True), 0.0, 1.0, (30, 30))
    elif style == 4:      # أوراق + زهرة + نقاط ولمعات
        shapes.append(P([stem(k / 30) for k in range(31)], smooth=True, w=WO))
        shapes += leaves_along_arc(stem, 0.14, 0.90, 10 + v, 16, 5.4, 52)
        shapes += xf_all(flower5(18, 5, 3.8, dots=True), 0.0, 1.0, stem(0.05))
        shapes += dots_along(stem, 0.94, 1.0, 3, 1.9)
        # اللمعات قريبة من الزهرة لا متفرّقة عشوائياً
        for dx, dy, s in ((26, 20, 6.2), (6, 34, 4.4), (34, 44, 5.0)):
            px, py = stem(0.05)
            shapes += xf_all(sparkle(s), 0.0, 1.0, (px - dx, py + dy))
    else:                 # زهور متدرّجة على قوس
        def f(t):
            a = math.radians(14) + t * math.radians(62)
            return (10 + 150 * math.cos(a), 10 + 150 * math.sin(a))
        shapes.append(P([f(k / 24) for k in range(25)], smooth=True, w=WO))
        shapes += leaves_along_arc(f, 0.04, 0.96, 9 + v, 15, 5.2, 58)
        for k, t in enumerate((0.16, 0.5, 0.84)):
            shapes += xf_all(flower5(16 - k * 2, 5, 3.0, rot=k * 0.8),
                             0.0, 1.0, f(t))
    return f"corner_{i + 1:02d}", "زاوية نباتية رفيعة", shapes, SQUARE


# ===========================================================================
# إطارات بزوايا نباتية
# ===========================================================================


def build_frame(i):
    """إطار مستطيل رفيع مزدوج + نبات في زاويتين متقابلتين."""
    W, H = 150.0, 180.0
    gap = 7.0
    shapes = [
        P([(-W / 2, -H / 2), (W / 2, -H / 2), (W / 2, H / 2), (-W / 2, H / 2)],
          closed=True, smooth=False, w=WO),
        P([(-W / 2 + gap, -H / 2 + gap), (W / 2 - gap, -H / 2 + gap),
           (W / 2 - gap, H / 2 - gap), (-W / 2 + gap, H / 2 - gap)],
          closed=True, smooth=False, w=WD),
    ]
    corners = [(-1, -1), (1, 1)] if i % 2 == 0 else [(-1, -1)]
    nleaf = 8 + (i // 2) * 2
    for sx, sy in corners:
        cx, cy = sx * W / 2, sy * H / 2

        def f(t, sx=sx, sy=sy, cx=cx, cy=cy):
            return (cx - sx * 86 * t, cy + sy * 70 * (t ** 2.2))
        shapes.append(P([f(k / 24) for k in range(25)], smooth=True, w=WO))
        shapes += leaves_along_arc(f, 0.10, 0.92, nleaf, 15, 5.2, 54,
                                   taper=0.25)
        shapes += xf_all(flower5(14, 5, 3.0, dots=True), 0.0, 1.0, f(0.04))
        shapes += xf_all(flower5(10, 5, 2.2), 0.0, 1.0, f(0.22))
        if i >= 4:
            shapes += xf_all(berry_sprig(3, 2.4, 7),
                             math.atan2(sy, -sx), 1.0, f(0.52))
    return f"frame_{i + 1:02d}", "إطار بزوايا نباتية", shapes, SQUARE


# ===========================================================================
# أغصان رفيعة
# ===========================================================================


def build_sprig(i):
    shapes = []
    style = i % 5
    v = i // 5
    L = 180.0

    if style == 0:        # غصن مستقيم بأوراق متبادلة
        def f(t):
            return (0, L * 0.5 - L * t)
        shapes.append(P([f(k / 24) for k in range(25)], smooth=True, w=WO))
        shapes += leaves_along_arc(f, 0.06, 0.92, 13 + v * 2, 18, 6.0, 52,
                                   tiny_every=5)
        shapes += xf_all(tiny_leaf(12, 4.4), math.pi, 1.0, f(0.04))
    elif style == 1:      # غصن منحنٍ بزهرة في القمة
        def f(t):
            return (22 * math.sin(math.pi * t * 0.8), L * 0.5 - L * t)
        shapes.append(P([f(k / 26) for k in range(27)], smooth=True, w=WO))
        shapes += leaves_along_arc(f, 0.22, 0.94, 10 + v, 17, 5.6, 54,
                                   taper=0.3)
        shapes += xf_all(flower5(19, 5, 4.0, dots=True), 0.0, 1.0, f(0.06))
    elif style == 2:      # سنبلة أوراق متقابلة
        # العدد السابق (16–19 زوجاً) كان يتراكب حتى يصير سلّماً مصمتاً.
        # المسافة بين الأزواج يجب أن تتجاوز عرض الورقة.
        n_pairs = 8 + v
        def f(t):
            return (0, L * 0.5 - L * t)
        shapes.append(P([f(k / 24) for k in range(25)], smooth=True, w=WO))
        for k in range(n_pairs):
            t = 0.08 + 0.80 * k / max(1, n_pairs - 1)
            px, py = f(t)
            ln = 17 - 5 * t
            for side in (1, -1):
                shapes += xf_all(small_leaf(ln, ln * 0.33, vein=False),
                                 side * math.radians(46) + math.pi, 1.0,
                                 (px, py))
        shapes += xf_all(small_leaf(15, 5.0, vein=False), math.pi, 1.0, f(0.03))
    elif style == 3:      # غصن بحبّات
        def f(t):
            return (16 * math.sin(math.pi * t * 0.9), L * 0.5 - L * t)
        shapes.append(P([f(k / 26) for k in range(27)], smooth=True, w=WO))
        shapes += leaves_along_arc(f, 0.30, 0.94, 8 + v, 16, 5.4, 54)
        for t in (0.06, 0.14, 0.22):
            px, py = f(t)
            shapes += xf_all(berry_sprig(3, 3.0, 9),
                             tangent_of(f, t) + math.pi / 2, 1.0, (px, py))
    else:                 # غصن بزهور متدرّجة
        def f(t):
            return (26 * math.sin(math.pi * t * 0.75), L * 0.5 - L * t)
        shapes.append(P([f(k / 26) for k in range(27)], smooth=True, w=WO))
        shapes += leaves_along_arc(f, 0.34, 0.96, 8 + v, 16, 5.4, 56)
        for k, t in enumerate((0.05, 0.17, 0.29)):
            shapes += xf_all(flower5(17 - k * 3, 5, 3.4 - k * 0.5, rot=k),
                             0.0, 1.0, f(t))
        shapes += xf_all(bud_small(13, 5.6), math.radians(150), 1.0, f(0.40))
    return f"sprig_{i + 1:02d}", "غصن رفيع", shapes, (150, 200)


# ===========================================================================
# باقات صغيرة
# ===========================================================================


def build_posy(i):
    """باقة صغيرة: سويقات متجمّعة من نقطة واحدة تتفتّح كمروحة."""
    shapes = []
    base = (0.0, 80.0)
    n_stem = 5 + i % 3
    spread = math.radians(74 + (i % 2) * 14)
    flower_at = [0, 2, 4] if i % 2 == 0 else [1, 3]

    for k in range(n_stem):
        u = (k - (n_stem - 1) / 2) / max(1, (n_stem - 1) / 2)
        ang = -math.pi / 2 + u * spread / 2
        L = 128 - 22 * abs(u)
        bow = 13.0 * (1 if k % 2 == 0 else -1) * (0.45 + abs(u))
        # القواعد متباعدة قليلاً لا كلها من نقطة واحدة (تُنتج شكل قدم الغراب)
        bx = base[0] + u * 5.0

        def f(t, ang=ang, L=L, bw=bow, bx=bx):
            r = L * t
            px, py = bx + r * math.cos(ang), base[1] + r * math.sin(ang)
            # إزاحة عرضية تتلاشى عند الطرفين = انحناء لطيف بدل خط مستقيم جافّ
            d = bw * math.sin(math.pi * t)
            return (px - d * math.sin(ang), py + d * math.cos(ang))

        shapes.append(P([f(j / 22) for j in range(23)], smooth=True, w=WO))
        if k in flower_at:
            shapes += leaves_along_arc(f, 0.34, 0.78, 3, 14, 4.8, 56)
            shapes += xf_all(flower5(15 - abs(u) * 3, 5, 3.0, rot=k * 0.6),
                             0.0, 1.0, f(1.0))
        else:
            shapes += leaves_along_arc(f, 0.30, 0.94, 5, 15, 5.2, 54,
                                       taper=0.2)
            shapes += xf_all(small_leaf(13, 4.4), ang + math.pi / 2 + math.pi,
                             1.0, f(1.0))
    # رِباط الباقة: شريطان منحنيان وذيلان — لا صندوق بأرجل
    for dy in (74.0, 81.0):
        shapes.append(P([(-11, dy), (0, dy + 2.4), (11, dy)], smooth=True, w=WO))
    shapes.append(P([(-4, 83), (-11, 92), (-9, 101)], smooth=True, w=WD))
    shapes.append(P([(4, 83), (12, 91), (11, 100)], smooth=True, w=WD))
    return f"posy_{i + 1:02d}", "باقة صغيرة", shapes, (170, 200)


# ===========================================================================
# زهور مفردة
# ===========================================================================


def build_single(i):
    """
    زهور مفردة نظيفة.
    القاعدة التي خُرقت سابقاً: لا تُوضع أوراق *بين* البتلات ولا طبقة ثانية
    تتقاطع مع الأولى — فذلك يُنتج تشابكاً. الأوراق تُوضع أسفل الزهرة فقط،
    والطبقة الداخلية تبقى داخل نطاق قواعد البتلات الخارجية.
    """
    shapes = []
    if i == 0:                                   # خمسية كبيرة بسيطة
        shapes += flower5(76, 5, 13, dots=True)
        title = "زهرة خمسية مفردة"
    elif i == 1:                                 # أقحوانة
        shapes += daisy(78, 13, 14)
        for k in range(10):
            a = TAU * k / 10
            shapes.append(CIRC(polar(8, a), 1.9, w=WD))
        title = "أقحوانة مفردة"
    elif i == 2:                                 # طبقتان متداخلتان بانتظام
        shapes += flower5(76, 6, 0, rot=0.0)
        # الطبقة الداخلية أصغر من قواعد البتلات الخارجية (76·0.24 ≈ 18)
        shapes += flower5(17, 6, 3.2, rot=math.pi / 6)
        title = "زهرة بطبقتين"
    elif i == 3:                                 # ثمانية ببتلات رفيعة
        shapes += daisy(78, 8, 15)
        for k in range(8):
            a = TAU * k / 8 + math.pi / 8
            shapes.append(CIRC(polar(9, a), 2.2, w=WD))
        title = "زهرة ثمانية"
    elif i == 4:                                 # زهرة بساق وورقتين
        shapes += flower5(58, 5, 11, dots=True)
        shapes.append(P([(0, 14), (5, 58), (0, 104)], smooth=True, w=WO))
        # الأوراق على الساق أسفل الزهرة — لا تلامس البتلات
        shapes += xf_all(small_leaf(40, 14), math.radians(126), 1.0, (4, 56))
        shapes += xf_all(small_leaf(34, 12), math.radians(-126), 1.0, (2, 76))
        title = "زهرة بساق وورقتين"
    else:                                        # تشكيلة ثلاث زهور متباعدة
        shapes += flower5(44, 5, 9, dots=True)
        shapes += xf_all(flower5(26, 5, 5.4, rot=0.5), 0.0, 1.0, (58, -40))
        shapes += xf_all(flower5(21, 5, 4.4, rot=1.1), 0.0, 1.0, (-54, -34))
        shapes.append(P([(0, 0), (34, -26), (58, -40)], smooth=True, w=WD))
        shapes.append(P([(0, 0), (-32, -22), (-54, -34)], smooth=True, w=WD))
        shapes += xf_all(small_leaf(32, 11), math.radians(58), 1.0, (-22, 24))
        shapes += xf_all(small_leaf(28, 10), math.radians(-58), 1.0, (24, 28))
        shapes += xf_all(berry_sprig(3, 2.8, 9), math.radians(96), 1.0, (0, 34))
        title = "تشكيلة ثلاث زهور"
    return f"single_{i + 1:02d}", title, shapes, SQUARE


# ===========================================================================
# أشرطة رفيعة
# ===========================================================================


def build_band(i):
    shapes = []
    step = 100.0
    reps = 6

    for k in range(reps):
        ox = k * step
        if i == 0:        # فرع متعرّج بأوراق
            def f(t, ox=ox):
                x = ox + step * t
                return (x, 26 * math.sin(TAU * t))
            shapes.append(P([f(j / 24) for j in range(25)], smooth=True, w=WO))
            shapes += leaves_along_arc(f, 0.08, 0.92, 5, 15, 5.2, 54)
        elif i == 1:      # أوراق وزهرة متبادلة
            shapes.append(LINE((ox, 0), (ox + step, 0), w=WO))
            def f(t, ox=ox):
                return (ox + step * t, 0)
            shapes += leaves_along_arc(f, 0.10, 0.70, 4, 16, 5.4, 52)
            shapes += xf_all(flower5(14, 5, 3.0, rot=k * 0.5), 0.0, 1.0,
                             (ox + step * 0.86, -8))
        elif i == 2:      # نقاط وأوراق
            def f(t, ox=ox):
                return (ox + step * t, 16 * math.sin(math.pi * t))
            shapes.append(P([f(j / 20) for j in range(21)], smooth=True, w=WO))
            shapes += leaves_along_arc(f, 0.18, 0.82, 3, 15, 5.2, 58)
            shapes += dots_along(f, 0.92, 1.0, 2, 1.9)
        elif i == 3:      # زهور متباعدة بأوراق
            shapes.append(LINE((ox, 10), (ox + step, 10), w=WD))
            def f(t, ox=ox):
                return (ox + step * t, 10)
            shapes += leaves_along_arc(f, 0.14, 0.44, 3, 15, 5.2, 56)
            shapes += leaves_along_arc(f, 0.62, 0.90, 3, 15, 5.2, 56)
            shapes += xf_all(flower5(16, 5, 3.4, dots=True), 0.0, 1.0,
                             (ox + step * 0.53, -4))
        elif i == 4:      # سنبلة
            shapes.append(LINE((ox, 0), (ox + step, 0), w=WO))
            for j in range(7):
                t = 0.08 + 0.84 * j / 6
                px = ox + step * t
                for side in (1, -1):
                    shapes += xf_all(tiny_leaf(13, 4.6),
                                     side * math.radians(50) + math.pi / 2,
                                     1.0, (px, 0))
        else:             # حبّات وأوراق
            def f(t, ox=ox):
                return (ox + step * t, 20 * math.sin(TAU * t + math.pi))
            shapes.append(P([f(j / 24) for j in range(25)], smooth=True, w=WO))
            shapes += leaves_along_arc(f, 0.12, 0.60, 3, 14, 5.0, 56)
            shapes += xf_all(berry_sprig(3, 2.6, 8), math.pi / 2, 1.0, f(0.82))
    return f"band_{i + 1:02d}", "شريط رفيع", shapes, STRIP


# ===========================================================================
# السجل
# ===========================================================================

ART_FAMILIES = [
    ("أكاليل كاملة", build_wreath_full, 10),
    ("أكاليل جزئية", build_wreath_part, 12),
    ("أكاليل منقّطة", build_wreath_dot, 8),
    ("زوايا نباتية", corner_spray, 12),
    ("إطارات بزوايا", build_frame, 6),
    ("أغصان رفيعة", build_sprig, 10),
    ("باقات صغيرة", build_posy, 8),
    ("زهور مفردة", build_single, 6),
    ("أشرطة رفيعة", build_band, 6),
]


def main():
    ART_DIR.mkdir(parents=True, exist_ok=True)
    for old in ART_DIR.glob("*.svg"):
        old.unlink()

    index = []
    num = 0
    for fam, builder, count in ART_FAMILIES:
        for i in range(count):
            num += 1
            name, title, shapes, canvas = builder(i)
            fname = f"A{num:03d}_{name}.svg"
            write_svg(ART_DIR / fname, shapes, canvas=canvas, margin=12,
                      stroke=STROKE * (1.25 if canvas == STRIP else 1.0),
                      title=f"A{num:03d} — {title}")
            index.append({"num": num, "file": fname, "title": title,
                          "family": fam, "wide": canvas == STRIP,
                          "elements": len(shapes)})

    (ROOT / "index_art.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"تم توليد {num} رسمة في {ART_DIR}")
    for fam, _, c in ART_FAMILIES:
        print(f"  - {fam}: {c}")
    return index


if __name__ == "__main__":
    main()
