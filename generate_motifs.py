#!/usr/bin/env python3
"""
مولّد 200 رسمة "تحديد" (outline only) لتطريز/رسم أطراف العباية.

- كل رسمة ملف SVG متجهي: خطوط فقط (fill="none")، قابل للتكبير والتصغير بلا فقدان جودة.
- بلا أي مكتبات خارجية (مكتبة Python القياسية فقط).

التشغيل:  python3 generate_motifs.py
"""

import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SVG_DIR = ROOT / "svg"
TAU = math.tau

SQUARE = (200, 200)
STRIP = (620, 150)

# ----------------------------------------------------------------------------
# أساسيات هندسية
# ----------------------------------------------------------------------------


def P(points, closed=False, smooth=True):
    return {"kind": "path", "pts": [(float(x), float(y)) for x, y in points],
            "closed": closed, "smooth": smooth}


def CIRC(c, r):
    return {"kind": "circle", "c": (float(c[0]), float(c[1])), "r": float(r)}


def LINE(p1, p2):
    return P([p1, p2], closed=False, smooth=False)


def POLY(points, closed=True):
    return P(points, closed=closed, smooth=False)


def ELL(c, rx, ry, ang=0.0, n=44):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(n):
        t = TAU * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((c[0] + x * ca - y * sa, c[1] + x * sa + y * ca))
    return P(pts, closed=True, smooth=True)


def xf_pts(pts, ang=0.0, scale=1.0, at=(0.0, 0.0), flip=1):
    ca, sa = math.cos(ang) * scale, math.sin(ang) * scale
    out = []
    for x, y in pts:
        x = x * flip
        out.append((at[0] + x * ca - y * sa, at[1] + x * sa + y * ca))
    return out


def xf(shape, ang=0.0, scale=1.0, at=(0.0, 0.0), flip=1):
    if shape["kind"] == "path":
        s = dict(shape)
        s["pts"] = xf_pts(shape["pts"], ang, scale, at, flip)
        return s
    c = xf_pts([shape["c"]], ang, scale, at, flip)[0]
    return {"kind": "circle", "c": c, "r": shape["r"] * scale}


def xf_all(shapes, ang=0.0, scale=1.0, at=(0.0, 0.0), flip=1):
    return [xf(s, ang, scale, at, flip) for s in shapes]


def arc_pts(c, r, a0, a1, n=28):
    return [(c[0] + r * math.cos(a0 + (a1 - a0) * i / n),
             c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def tri_wave(x):
    """موجة مثلثية في المدى [-1, 1]"""
    return 4 * abs(x - math.floor(x + 0.5)) - 1


# ----------------------------------------------------------------------------
# الأوراق والبتلات: مُحيط من مُعامِلات
# ----------------------------------------------------------------------------


def _profile_norm(a, b):
    t = a / (a + b)
    return t ** a * (1 - t) ** b


def _half_width(t, width, a, b, norm, edge, teeth, amp):
    w = width * (t ** a * (1 - t) ** b) / norm
    if edge:
        # تلاشي تمويج الحافة عند القاعدة والقمة، وإلا تقاطعت الحدود وتشوّه الشكل
        g = amp * math.sin(math.pi * t) ** 0.6
        if edge == "crenate":
            w *= 1 + g * math.sin(teeth * TAU * t)
        elif edge == "serrate":
            w *= 1 + g * tri_wave(teeth * t)
    return w


def blade(length, width, a=0.65, b=0.95, bend=0.0, edge=None,
          teeth=9, amp=0.08, n=76):
    """
    مُحيط ورقة/بتلة مغلق. القاعدة عند (0,0) والقمة عند (bend-ish, -length).
    edge: None | 'crenate' (حافة مموّجة) | 'serrate' (حافة مسنّنة)
    """
    norm = _profile_norm(a, b)

    def mid(t):
        return (bend * math.sin(math.pi * t), -length * t)

    def half(t):
        return _half_width(t, width, a, b, norm, edge, teeth, amp)

    def normal(t):
        e = 1e-4
        t0, t1 = max(0.0, t - e), min(1.0, t + e)
        (x0, y0), (x1, y1) = mid(t0), mid(t1)
        dx, dy = x1 - x0, y1 - y0
        m = math.hypot(dx, dy) or 1.0
        return (-dy / m, dx / m)

    left, right = [], []
    for i in range(n + 1):
        t = i / n
        mx, my = mid(t)
        nx, ny = normal(t)
        w = half(t)
        left.append((mx + nx * w, my + ny * w))
        right.append((mx - nx * w, my - ny * w))
    pts = left + right[1:-1][::-1]
    return P(pts, closed=True, smooth=True)


def blade_veins(length, width, a=0.65, b=0.95, bend=0.0, pairs=5, midrib=True,
                edge=None, teeth=9, amp=0.08, reach=0.72):
    """
    عروق الورقة. تستخدم نفس تمويج الحافة المستخدم في المُحيط،
    وإلا خرجت أطراف العروق خارج حدود الورقة.
    """
    norm = _profile_norm(a, b)

    def mid(t):
        return (bend * math.sin(math.pi * t), -length * t)

    def half(t):
        return _half_width(t, width, a, b, norm, edge, teeth, amp)

    def normal(t):
        e = 1e-4
        (x0, y0), (x1, y1) = mid(max(0, t - e)), mid(min(1, t + e))
        dx, dy = x1 - x0, y1 - y0
        m = math.hypot(dx, dy) or 1.0
        return (-dy / m, dx / m)

    out = []
    if midrib:
        out.append(P([mid(i / 24 * 0.95 + 0.02) for i in range(25)], smooth=True))
    for k in range(1, pairs + 1):
        t = 0.15 + 0.62 * k / (pairs + 1)
        te = min(0.97, t + 0.13)
        for side in (1, -1):
            bx, by = mid(t)
            nx, ny = normal(t)
            mxp, myp = mid((t + te) / 2)
            nmx, nmy = normal((t + te) / 2)
            ex, ey = mid(te)
            nex, ney = normal(te)
            out.append(P([
                (bx, by),
                (mxp + side * nmx * half((t + te) / 2) * reach * 0.62,
                 myp + side * nmy * half((t + te) / 2) * reach * 0.62),
                (ex + side * nex * half(te) * reach,
                 ey + side * ney * half(te) * reach),
            ], smooth=True))
    return out


# --------------------------------------------------------------------------
# مساعدات: أوراق على منحنى، وزهرة صغيرة
# --------------------------------------------------------------------------


def tangent_of(f, t, e=2e-3):
    p0, p1 = f(max(0.0, t - e)), f(min(1.0, t + e))
    return math.atan2(p1[1] - p0[1], p1[0] - p0[0])


def curve(f, n=48):
    return P([f(i / n) for i in range(n + 1)], smooth=True)


def leaves_along(f, ts, length, width, out_deg=58, bend=5.0, taper=0.0,
                 a=0.72, b=1.0, start_side=1, stubs=True):
    """
    يضع أوراقاً بقواعدها على المنحنى f، وباتجاه مَيل المنحنى نفسه
    (وليس زاوية ثابتة) — هذا هو ما يجعلها تبدو نابتة من الفرع فعلاً.
    """
    out = []
    m = max(1, len(ts) - 1)
    for k, t in enumerate(ts):
        px, py = f(t)
        th = tangent_of(f, t)
        side = start_side if k % 2 == 0 else -start_side
        sc = 1.0 - taper * k / m
        ang = th + side * math.radians(out_deg) + math.pi / 2
        out.append(xf(blade(length * sc, width * sc, a=a, b=b, bend=side * bend),
                      ang, 1.0, (px, py)))
        if stubs:
            out.append(xf(P([(0, 0), (1.2, 4), (0, 8)], smooth=True),
                          ang, 1.0, (px, py)))
    return out


def small_flower(n=5, plen=28, pw=19, inner=9, center=5, at=(0.0, 0.0), rot=0.0):
    out = []
    petal = blade(plen, pw, a=0.9, b=0.8)
    for k in range(n):
        ang = TAU * k / n + rot
        out.append(xf(petal, ang, 1.0,
                      (at[0] + inner * math.sin(ang), at[1] - inner * math.cos(ang))))
    out.append(CIRC(at, center))
    return out


def spiral_f(R, turns, shrink=0.86, phase=0.0, at=(0.0, 0.0)):
    def f(t):
        ang = TAU * turns * t + phase
        r = R * (1 - shrink * t)
        return (at[0] + r * math.cos(ang), at[1] + r * math.sin(ang))
    return f


def stem(length=26, bend=0.0):
    return P([(bend * 0.3 * (i / 12) ** 2, length * i / 12) for i in range(13)], smooth=True)


def fan_blade(radius, lobes=5, span_deg=150, depth=0.42, n=130):
    """ورقة مفصّصة (كفّية) — دالة قطبية مع فصوص، القاعدة عند (0,0)."""
    span = math.radians(span_deg)
    pts = [(0.0, 0.0)]
    for i in range(n + 1):
        u = i / n
        th = -span / 2 + u * span - math.pi / 2
        r = radius * ((1 - depth) + depth * abs(math.sin(lobes * math.pi * u)) ** 0.55)
        pts.append((r * math.cos(th), r * math.sin(th)))
    return P(pts, closed=True, smooth=True), span, lobes


def fan_veins(radius, lobes, span_deg, depth):
    span = math.radians(span_deg)
    out = []
    for k in range(lobes):
        u = (k + 0.5) / lobes
        th = -span / 2 + u * span - math.pi / 2
        r = radius * ((1 - depth) + depth) * 0.86
        out.append(LINE((0, 0), (r * math.cos(th), r * math.sin(th))))
    return out


# ----------------------------------------------------------------------------
# كتابة SVG
# ----------------------------------------------------------------------------


def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "", "-") else s


def _catmull(pts, closed):
    n = len(pts)
    if n < 2:
        return ""
    d = [f"M{fmt(pts[0][0])},{fmt(pts[0][1])}"]
    if closed:
        seq = [(pts[(i - 1) % n], pts[i % n], pts[(i + 1) % n], pts[(i + 2) % n])
               for i in range(n)]
    else:
        ext = [pts[0]] + list(pts) + [pts[-1]]
        seq = [(ext[i - 1], ext[i], ext[i + 1], ext[i + 2]) for i in range(1, len(ext) - 2)]
    for p0, p1, p2, p3 in seq:
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{fmt(c1[0])},{fmt(c1[1])} {fmt(c2[0])},{fmt(c2[1])} "
                 f"{fmt(p2[0])},{fmt(p2[1])}")
    if closed:
        d.append("Z")
    return " ".join(d)


def _polyline(pts, closed):
    d = [f"M{fmt(pts[0][0])},{fmt(pts[0][1])}"]
    d += [f"L{fmt(x)},{fmt(y)}" for x, y in pts[1:]]
    if closed:
        d.append("Z")
    return " ".join(d)


_NUM_RE = __import__("re").compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def shape_d(sh):
    pts = sh["pts"]
    return _catmull(pts, sh["closed"]) if sh["smooth"] else _polyline(pts, sh["closed"])


def bbox_of(dstrings, circles):
    """
    الحدود محسوبة من نقاط تحكّم بيزييه الفعلية (وليس من نقاط الإدخال).
    مُبرَّهن: منحنى بيزييه محصور دائماً داخل الغلاف المحدّب لنقاط تحكّمه،
    لذا هذه الحدود تحيط بالرسم فعلياً ولا يحدث تجاوز.
    """
    xs, ys = [], []
    for d in dstrings:
        nums = [float(v) for v in _NUM_RE.findall(d)]
        if len(nums) % 2:
            nums = nums[:-1]
        xs += nums[0::2]
        ys += nums[1::2]
    for (cx, cy), r in circles:
        xs += [cx - r, cx + r]
        ys += [cy - r, cy + r]
    return min(xs), min(ys), max(xs), max(ys)


def write_svg(path, shapes, canvas=SQUARE, margin=16, stroke=1.8, title=""):
    W, H = canvas

    dstrings, circles = [], []
    for sh in shapes:
        if sh["kind"] == "circle":
            circles.append((sh["c"], sh["r"]))
        else:
            dstrings.append(shape_d(sh))

    x0, y0, x1, y1 = bbox_of(dstrings, circles)
    bw, bh = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
    s = min((W - 2 * margin) / bw, (H - 2 * margin) / bh)
    tx = (W - bw * s) / 2 - x0 * s
    ty = (H - bh * s) / 2 - y0 * s

    body = []
    ci = 0
    di = 0
    for sh in shapes:
        if sh["kind"] == "circle":
            body.append(f'<circle cx="{fmt(sh["c"][0])}" cy="{fmt(sh["c"][1])}" '
                        f'r="{fmt(sh["r"])}"/>')
            ci += 1
        else:
            body.append(f'<path d="{dstrings[di]}"/>')
            di += 1

    svg = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}">\n'
        f'  <title>{title}</title>\n'
        f'  <g transform="translate({fmt(tx)},{fmt(ty)}) scale({s:.5f})" '
        f'fill="none" stroke="#000000" stroke-width="{stroke / s:.4f}" '
        f'stroke-linecap="round" stroke-linejoin="round">\n'
        + "".join(f"    {b}\n" for b in body)
        + "  </g>\n</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")
    return (x0 * s + tx, y0 * s + ty, x1 * s + tx, y1 * s + ty)


# ----------------------------------------------------------------------------
# 1) أوراق مفردة  (28)
# ----------------------------------------------------------------------------

LEAF_PROFILES = [
    ("ovate", "ورقة بيضية", dict(a=0.60, b=0.95, length=150, width=44)),
    ("lanceolate", "ورقة رمحية", dict(a=0.80, b=1.30, length=165, width=32)),
    ("cordate", "ورقة قلبية", dict(a=0.38, b=1.00, length=140, width=56)),
    ("obovate", "ورقة معكوسة", dict(a=1.15, b=0.62, length=150, width=46)),
    ("elliptic", "ورقة بيضاوية", dict(a=0.85, b=0.85, length=152, width=42)),
    ("linear", "ورقة شريطية", dict(a=0.95, b=0.95, length=175, width=22)),
    ("spatulate", "ورقة ملعقية", dict(a=1.45, b=0.55, length=148, width=48)),
]

LEAF_EDGES = [
    (None, "حافة ملساء", 0, 0.0),
    ("crenate", "حافة مموّجة", 8, 0.085),
    ("serrate", "حافة مسنّنة", 11, 0.075),
    ("crenate", "حافة مفصّصة", 5, 0.135),
]


def build_leaves_simple(i):
    prof = LEAF_PROFILES[i % 7]
    edge = LEAF_EDGES[i // 7]
    key, ar, p = prof
    ekey, ear, teeth, amp = edge
    bend = [0.0, 7.0, -6.0, 9.0][i // 7] + (i % 7) * 0.7
    shapes = [blade(p["length"], p["width"], a=p["a"], b=p["b"], bend=bend,
                    edge=ekey, teeth=teeth, amp=amp)]
    shapes += blade_veins(p["length"], p["width"], a=p["a"], b=p["b"], bend=bend,
                          pairs=4 + (i % 3), edge=ekey, teeth=teeth, amp=amp)
    shapes.append(stem(24, bend))
    return f"leaf_{key}_{i // 7 + 1}", f"{ar} — {ear}", shapes, SQUARE


# ----------------------------------------------------------------------------
# 2) أوراق مفصّصة  (12)
# ----------------------------------------------------------------------------


def build_leaves_lobed(i):
    lobes = [3, 5, 7][i % 3]
    span = [130, 150, 172][(i // 3) % 3]
    depth = [0.34, 0.46][i // 9] if i >= 9 else [0.34, 0.46, 0.40, 0.52][(i // 3) % 4]
    blade_shape, _, _ = fan_blade(150, lobes=lobes, span_deg=span, depth=depth)
    shapes = [blade_shape]
    shapes += fan_veins(150, lobes, span, depth)
    shapes.append(P([(0, 0), (2, 14), (0, 30)], smooth=True))
    return (f"leaf_lobed_{lobes}_{span}_{i}",
            f"ورقة مفصّصة {lobes} فصوص", shapes, SQUARE)


# ----------------------------------------------------------------------------
# 3) أغصان الزيتون  (24)
# ----------------------------------------------------------------------------


def build_olive(i):
    """
    غصن زيتون قُطري داخل المربع (ليملأ المساحة بدل أن يبقى شريطاً أفقياً رقيقاً)،
    بأزواج أوراق متباعدة كفايةً لئلّا تتراكم، وبحبّات زيتون واضحة.
    """
    pairs = 4 + i % 4                       # 4..7 فقط — الأكثر من ذلك يتراكم
    bow = [0.0, 24.0, -24.0, 38.0][(i // 4) % 4]
    fruits = [0, 1, 2, 3][i % 4]
    leaf_len = 62 + (i % 3) * 7
    span = 215.0
    tilt = math.radians(-30)                # الميل القُطري

    def branch(t):
        return (t * span, bow * math.sin(math.pi * t))

    shapes = [curve(branch, 44)]

    m = max(1, pairs - 1)
    for k in range(pairs):
        t = 0.14 + 0.78 * k / m if pairs > 1 else 0.5
        px, py = branch(t)
        base = tangent_of(branch, t)
        taper = 1.0 - 0.32 * t
        for side in (1, -1):
            ang = base + side * math.radians(48) + math.pi / 2
            shapes.append(xf(blade(leaf_len * taper, 11.0 * taper,
                                   a=0.9, b=0.9, bend=side * 3),
                             ang, 1.0, (px, py)))

    px, py = branch(1.0)
    shapes.append(xf(blade(leaf_len * 0.6, 10.0, a=0.9, b=0.9),
                     tangent_of(branch, 1.0) + math.pi / 2, 1.0, (px, py)))

    for n in range(fruits):
        t = 0.30 + 0.20 * n
        px, py = branch(t)
        ang = tangent_of(branch, t) + math.radians(96)   # معلّقة أسفل الغصن
        sx, sy = px + 13 * math.cos(ang), py + 13 * math.sin(ang)
        ox, oy = px + 27 * math.cos(ang), py + 27 * math.sin(ang)
        shapes.append(LINE((px, py), (sx, sy)))
        shapes.append(ELL((ox, oy), 10.0, 13.5, ang + math.pi / 2))

    shapes = xf_all(shapes, tilt)
    return (f"olive_sprig_{i + 1:02d}",
            f"غصن زيتون — {pairs} أزواج" + (f" + {fruits} حبّات" if fruits else ""),
            shapes, SQUARE)


# ----------------------------------------------------------------------------
# 4) زهور شعاعية  (26)
# ----------------------------------------------------------------------------

PETAL_KINDS = [
    ("round", dict(a=0.95, b=0.80), "بتلات مستديرة"),
    ("pointed", dict(a=0.85, b=1.45), "بتلات مدبّبة"),
    ("heart", dict(a=0.45, b=0.95), "بتلات قلبية"),
    ("narrow", dict(a=1.00, b=1.00), "بتلات رفيعة"),
]
CENTERS = ["ring", "dots", "double-ring", "star"]


def build_rosette(i):
    counts = [5, 6, 7, 8, 9, 10, 12, 16]
    n = counts[i % 8]
    kind, kp, kar = PETAL_KINDS[(i // 8) % 4]
    center_style = CENTERS[i % 4]
    # الطبقة المزدوجة تُفسد الزهور كثيرة البتلات (تصبح كتلة متشابكة)
    double = (i % 3 == 0) and n <= 10
    inner = 20 + (i % 4) * 3
    plen = 74 if n <= 8 else 64
    pw = max(10.0, 150.0 / n) * (0.8 if kind == "narrow" else 1.0)

    shapes = []
    petal = blade(plen, pw, a=kp["a"], b=kp["b"])
    for k in range(n):
        ang = TAU * k / n
        shapes.append(xf(petal, ang, 1.0, (inner * math.sin(ang), -inner * math.cos(ang))))
    if double:
        p2 = blade(plen * 0.62, pw * 0.8, a=kp["a"], b=kp["b"])
        for k in range(n):
            ang = TAU * (k + 0.5) / n
            shapes.append(xf(p2, ang, 1.0,
                             (inner * 0.75 * math.sin(ang), -inner * 0.75 * math.cos(ang))))

    r = inner * 0.92
    if center_style == "ring":
        shapes.append(CIRC((0, 0), r))
    elif center_style == "double-ring":
        shapes += [CIRC((0, 0), r), CIRC((0, 0), r * 0.58)]
    elif center_style == "dots":
        shapes.append(CIRC((0, 0), r))
        for k in range(8):
            a = TAU * k / 8
            shapes.append(CIRC((r * 0.55 * math.cos(a), r * 0.55 * math.sin(a)), r * 0.17))
    else:
        shapes.append(CIRC((0, 0), r))
        pts = []
        for k in range(12):
            a = TAU * k / 12 - math.pi / 2
            rr = r * (0.88 if k % 2 == 0 else 0.42)
            pts.append((rr * math.cos(a), rr * math.sin(a)))
        shapes.append(POLY(pts))

    return (f"flower_rosette_{n:02d}_{kind}_{i + 1:02d}",
            f"زهرة {n} بتلات — {kar}", shapes, SQUARE)


# ----------------------------------------------------------------------------
# 5) زهور خاصة  (12)
# ----------------------------------------------------------------------------


def _tulip_cup(w=34.0, h=118.0):
    """كأس التوليب الكلاسيكي: ثلاثة رؤوس وتجويفان بينها."""
    return P([
        (0, 0),
        (w * 0.72, -h * 0.34),
        (w * 0.80, -h * 0.72),            # رأس البتلة اليمنى
        (w * 0.36, -h * 0.66),            # التجويف
        (w * 0.12, -h * 0.97),
        (0, -h),                          # رأس البتلة الوسطى
        (-w * 0.12, -h * 0.97),
        (-w * 0.36, -h * 0.66),
        (-w * 0.80, -h * 0.72),
        (-w * 0.72, -h * 0.34),
    ], closed=True, smooth=True)


def _tulip(v):
    w = 48 + v * 6
    h = 112
    shapes = [_tulip_cup(w, h)]
    # خطّا فصل البتلات
    for side in (1, -1):
        shapes.append(P([(0, -6), (side * w * 0.26, -h * 0.38),
                         (side * w * 0.36, -h * 0.64)], smooth=True))
    shapes.append(P([(0, 0), (3 * (1 if v % 2 else -1), 36), (0, 74)], smooth=True))
    for side in (1, -1):
        shapes.append(xf(blade(58, 12, a=0.9, b=1.1, bend=side * 10),
                         side * math.radians(118), 1.0, (0, 42)))
    return shapes, "زهرة توليب"


def _lotus(v):
    shapes = []
    n = 5 + v * 2
    for k in range(n):
        u = (k - (n - 1) / 2) / max(1, (n - 1) / 2)
        ang = u * math.radians(74)
        shapes.append(xf(blade(104 - abs(u) * 22, 26, a=0.95, b=1.35, bend=u * 9),
                         ang, 1.0, (0, 0)))
    shapes.append(P(arc_pts((0, 10), 62, math.radians(8), math.radians(172)), smooth=True))
    return shapes, "زهرة لوتس"


def _rose(v):
    """وردة: لولب في القلب + أقواس بتلات محيطة + بتلات خارجية ملامسة للّولب."""
    shapes = []
    turns = 2.1 + v * 0.4
    pts = []
    for k in range(120):
        t = k / 119
        a = t * TAU * turns
        r = 7 + 31 * t
        pts.append((r * math.cos(a), r * math.sin(a)))
    shapes.append(P(pts, smooth=True))

    # بتلات خارجية محيطة فقط — إضافة أقواس بينها كانت تُنتج تشابكاً
    n = 5 + v
    for k in range(n):
        a = TAU * k / n + math.radians(18)
        shapes.append(xf(blade(52, 44, a=0.95, b=0.72), a, 1.0,
                         (36 * math.sin(a), -36 * math.cos(a))))
    return shapes, "وردة حلزونية"


def _carnation(v):
    """حلقات مموّجة متداخلة — الفصوص القليلة والعمق المعتدل تُعطي تمويجاً لا تسنّناً."""
    shapes = []
    lobes = 9 + v * 2
    for layer, rad in enumerate((74, 54, 34)):
        pts = []
        n = 150
        for k in range(n):
            a = TAU * k / n
            r = rad * (1 + 0.115 * math.sin(lobes * a + layer * math.pi / lobes))
            pts.append((r * math.cos(a), r * math.sin(a)))
        shapes.append(P(pts, closed=True, smooth=True))
    shapes.append(CIRC((0, 0), 13))
    return shapes, "زهرة قرنفل"


def _daisy(v):
    shapes = []
    n = 16 + v * 6
    for k in range(n):
        a = TAU * k / n
        shapes.append(xf(blade(66, 9, a=1.0, b=1.0), a, 1.0,
                         (26 * math.sin(a), -26 * math.cos(a))))
    shapes += [CIRC((0, 0), 25), CIRC((0, 0), 15)]
    for k in range(6):
        a = TAU * k / 6
        shapes.append(CIRC((14 * math.cos(a), 14 * math.sin(a)), 3.4))
    return shapes, "زهرة أقحوان"


def _bud(v):
    """برعم: دمعة + كأس (سبلات) عند القاعدة + ساق بورقتين."""
    tilt = math.radians(8 * (1 if v else -1))
    bud = xf_all([blade(92, 31, a=1.05, b=0.85, bend=5)], tilt)
    shapes = list(bud)
    # كأس الزهرة
    shapes.append(xf(P(arc_pts((0, -16), 20, math.radians(18),
                               math.radians(162)), smooth=True), tilt))
    for side in (1, -1):
        shapes.append(xf(blade(34, 11, a=1.0, b=1.15, bend=side * 6),
                         tilt + side * math.radians(34), 1.0, (0, -6)))
    shapes.append(P([(0, 0), (2, 32), (0, 66)], smooth=True))
    for side in (1, -1):
        shapes.append(xf(blade(40, 12, a=0.9, b=1.1, bend=side * 8),
                         side * math.radians(116), 1.0, (1, 40)))
    return shapes, "برعم زهرة"


SPECIAL_FLOWERS = [_tulip, _lotus, _rose, _carnation, _daisy, _bud]


def build_flower_special(i):
    fn = SPECIAL_FLOWERS[i % 6]
    v = i // 6
    shapes, ar = fn(v)
    return f"flower_{fn.__name__.strip('_')}_{v + 1}", f"{ar} {v + 1}", shapes, SQUARE


# ----------------------------------------------------------------------------
# 6) نجوم هندسية  (16)
# ----------------------------------------------------------------------------

STAR_SPECS = [
    (6, 2), (8, 3), (8, 2), (10, 3), (10, 4), (12, 5), (12, 4), (16, 5),
]


def build_star(i):
    if i < 8:
        n, k = STAR_SPECS[i]
        R = 86
        pts = [(R * math.cos(TAU * (j * k % n) / n - math.pi / 2),
                R * math.sin(TAU * (j * k % n) / n - math.pi / 2))
               for j in range(n // math.gcd(n, k))]
        shapes = [POLY(pts)]
        if math.gcd(n, k) > 1:
            shapes = []
            for off in range(math.gcd(n, k)):
                pts = [(R * math.cos(TAU * ((j * k + off) % n) / n - math.pi / 2),
                        R * math.sin(TAU * ((j * k + off) % n) / n - math.pi / 2))
                       for j in range(n // math.gcd(n, k))]
                shapes.append(POLY(pts))
        shapes.append(CIRC((0, 0), R))
        name, ar = f"star_{n}_{k}", f"نجمة {n} رؤوس متشابكة"
    else:
        n = [6, 8, 10, 12, 8, 12, 16, 10][i - 8]
        inner = [0.42, 0.48, 0.55, 0.60, 0.62, 0.46, 0.70, 0.38][i - 8]
        R = 88
        pts = []
        for j in range(2 * n):
            a = TAU * j / (2 * n) - math.pi / 2
            r = R if j % 2 == 0 else R * inner
            pts.append((r * math.cos(a), r * math.sin(a)))
        shapes = [POLY(pts), CIRC((0, 0), R * inner * 0.78)]
        if i % 2:
            shapes.append(CIRC((0, 0), R))
        name, ar = f"star_points_{n}_{i}", f"نجمة {n} أطراف"
    return name, ar, shapes, SQUARE


# ----------------------------------------------------------------------------
# 7) شبكات هندسية  (12)
# ----------------------------------------------------------------------------


def build_lattice(i):
    S = 180
    h = S / 2
    shapes = []
    if i == 0:                                           # شبكة معيّنات
        # معيّنات مرسومة كأشكال مغلقة ومحصورة داخل المربع
        # (الخطوط القُطرية الممتدّة سابقاً كانت تُخرج الحدود وتضغط الرسم)
        cell = 45.0
        for row in range(-2, 3):
            for col in range(-2, 3):
                cx = col * cell + (cell / 2 if row % 2 else 0)
                cy = row * cell
                if abs(cx) > h - 10 or abs(cy) > h - 10:
                    continue
                r = cell * 0.5
                shapes.append(POLY([(cx, cy - r), (cx + r, cy),
                                    (cx, cy + r), (cx - r, cy)]))
        shapes.append(POLY([(-h, -h), (h, -h), (h, h), (-h, h)]))
        ar = "شبكة معيّنات"
    elif i == 1:                                         # مربعات متداخلة مدوّرة
        # كل مربع يلامس أضلاع الذي قبله: دوران 45° وتقليص بمعامل 1/‏√2
        s = 88.0
        for k in range(5):
            a = math.radians(k * 45)
            shapes.append(POLY(xf_pts([(-s, -s), (s, -s), (s, s), (-s, s)], a)))
            s /= math.sqrt(2)
        ar = "مربعات متداخلة"
    elif i == 2:                                         # بلاط سداسي
        r = 30
        for row in range(-2, 3):
            for col in range(-2, 3):
                cx = col * r * 1.5
                cy = row * r * math.sqrt(3) + (col % 2) * r * math.sqrt(3) / 2
                if abs(cx) > 70 or abs(cy) > 74:
                    continue
                shapes.append(POLY([(cx + r * math.cos(TAU * k / 6),
                                     cy + r * math.sin(TAU * k / 6)) for k in range(6)]))
        ar = "بلاط سداسي"
    elif i == 3:                                         # شبكة مثلثات
        step = 36
        for row in range(-2, 3):
            y0, y1 = row * step, (row + 1) * step
            for col in range(-3, 3):
                x = col * step
                shapes.append(POLY([(x, y0), (x + step, y0), (x + step / 2, y1)]))
                shapes.append(POLY([(x + step / 2, y1), (x + step * 1.5, y1), (x + step, y0)]))
        ar = "شبكة مثلثات"
    elif i == 4:                                         # دوائر متشابكة
        r = 34
        for row in range(-2, 3):
            for col in range(-2, 3):
                cx, cy = col * r, row * r * math.sqrt(3) / 2
                if row % 2:
                    cx += r / 2
                if math.hypot(cx, cy) > 78:
                    continue
                shapes.append(CIRC((cx, cy), r))
        ar = "دوائر متشابكة"
    elif i == 5:                                         # حراشف
        r = 24
        for row in range(7):
            y = -84 + row * r * 1.05
            off = (r if row % 2 else 0)
            for col in range(-3, 4):
                cx = col * 2 * r + off
                if abs(cx) > 92:
                    continue
                shapes.append(P(arc_pts((cx, y), r, math.pi, TAU, n=20), smooth=True))
        ar = "حراشف مقوّسة"
    elif i == 6:                                         # شيفرون
        for row in range(-3, 4):
            y = row * 26
            pts = []
            for col in range(-3, 4):
                pts.append((col * 30, y + (13 if col % 2 else -13)))
            shapes.append(POLY(pts, closed=False))
        ar = "صفوف شيفرون"
    elif i == 7:                                         # تضفير سلّة
        # خلايا متبادلة الاتجاه (رقعة شطرنج) بدل أشرطة متقاطعة تُنتج تشابكاً
        cell = 44.0
        for r_ in range(4):
            for c_ in range(4):
                x0 = -88 + c_ * cell
                y0 = -88 + r_ * cell
                shapes.append(POLY([(x0, y0), (x0 + cell, y0),
                                    (x0 + cell, y0 + cell), (x0, y0 + cell)]))
                for j in range(1, 4):
                    o = j * cell / 4
                    if (r_ + c_) % 2 == 0:
                        shapes.append(LINE((x0, y0 + o), (x0 + cell, y0 + o)))
                    else:
                        shapes.append(LINE((x0 + o, y0), (x0 + o, y0 + cell)))
        ar = "تضفير سلّة"
    elif i == 8:                                         # زجزاج مزدوج
        for row in range(-3, 4):
            for ph in (0, 1):
                pts = [(c * 24, row * 26 + ph * 8 + (11 if c % 2 else -11))
                       for c in range(-4, 5)]
                shapes.append(POLY(pts, closed=False))
        ar = "زجزاج مزدوج"
    elif i == 9:                                         # أمواج
        for row in range(-3, 4):
            pts = [(x, row * 26 + 9 * math.sin(x / 15)) for x in range(-90, 91, 5)]
            shapes.append(P(pts, smooth=True))
        ar = "أمواج متوازية"
    elif i == 10:                                        # مثمّن ومربع
        for row in range(-1, 2):
            for col in range(-1, 2):
                cx, cy = col * 62, row * 62
                r = 27
                shapes.append(POLY([(cx + r * math.cos(TAU * k / 8 + math.pi / 8),
                                     cy + r * math.sin(TAU * k / 8 + math.pi / 8))
                                    for k in range(8)]))
                shapes.append(POLY([(cx + 31, cy + 31), (cx + 44, cy + 31),
                                    (cx + 44, cy + 44), (cx + 31, cy + 44)]))
        ar = "مثمّنات ومربعات"
    else:                                                # نقاط ومعيّنات
        for row in range(-2, 3):
            for col in range(-2, 3):
                cx, cy = col * 42, row * 42
                shapes.append(POLY([(cx, cy - 16), (cx + 16, cy), (cx, cy + 16), (cx - 16, cy)]))
                shapes.append(CIRC((cx + 21, cy + 21), 4.5))
        ar = "معيّنات ونقاط"
    return f"geo_lattice_{i + 1:02d}", ar, shapes, SQUARE


# ----------------------------------------------------------------------------
# 8) أقواس ووريدات  (10)
# ----------------------------------------------------------------------------


def build_arcs(i):
    shapes = []
    if i < 4:                                  # ثلاثية/رباعية/خماسية/ثمانية الفصوص
        n = [3, 4, 5, 8][i]
        R, r = 54, 40
        for k in range(n):
            a = TAU * k / n - math.pi / 2
            shapes.append(CIRC((R * math.cos(a), R * math.sin(a)), r))
        shapes.append(CIRC((0, 0), 16))
        ar = f"وريدة {n} فصوص"
        name = f"geo_foil_{n}"
    elif i == 4:                               # دائرة مسنّنة
        for rad, lobes in ((80, 16), (58, 12), (36, 8)):
            pts = [(rad * (1 + 0.1 * math.cos(lobes * TAU * t / 100)) * math.cos(TAU * t / 100),
                    rad * (1 + 0.1 * math.cos(lobes * TAU * t / 100)) * math.sin(TAU * t / 100))
                   for t in range(100)]
            shapes.append(P(pts, closed=True, smooth=True))
        ar, name = "دوائر مموّجة متداخلة", "geo_scallop_rings"
    elif i == 5:                               # أقواس متداخلة
        for k, rad in enumerate((84, 66, 48, 30)):
            shapes.append(P(arc_pts((0, 40), rad, math.pi, TAU), smooth=True))
            shapes.append(LINE((-rad, 40), (-rad, 40 + 26 - k * 2)))
            shapes.append(LINE((rad, 40), (rad, 40 + 26 - k * 2)))
        ar, name = "أقواس متداخلة", "geo_nested_arches"
    elif i == 6:                               # قوس مدبّب (محراب) — بمركزين
        ys = 60.0
        for sc in (1.0, 0.76, 0.52):
            Wh = 72.0 * sc                     # نصف الفتحة
            d = Wh * 0.5                       # إزاحة المركزين
            R = Wh + d                         # نصف قطر القوسين
            th_max = math.acos(d / R)
            # النصف الأيمن: مركزه (-d, ys)، من نقطة الارتكاز حتى القمة
            right = [(-d + R * math.cos(th_max * k / 26),
                      ys - R * math.sin(th_max * k / 26)) for k in range(27)]
            left = [(-x, y) for x, y in right]
            # من ارتكاز اليسار -> القمة -> ارتكاز اليمين (بلا قفزة تُنتج خطاً شارداً)
            shapes.append(P(left + right[::-1][1:], smooth=True))
            shapes.append(LINE((-Wh, ys), (-Wh, ys + 30 * sc)))
            shapes.append(LINE((Wh, ys), (Wh, ys + 30 * sc)))
        shapes.append(LINE((-86, ys + 34), (86, ys + 34)))
        ar, name = "قوس مدبّب", "geo_pointed_arch"
    elif i == 7:                               # قوس حصان
        # القوس الحصاني يتجاوز نصف الدائرة: 160° -> 380° (مروراً بالقمة 270°)
        # ونقاط الارتكاز أسفل الخط الأفقي، وهو ما يميّزه عن القوس النصفي.
        a0, a1 = math.radians(160), math.radians(380)
        for rad in (76, 58, 40):
            shapes.append(P(arc_pts((0, 10), rad, a0, a1, n=56), smooth=True))
        for a in (a0, a1):
            for rad in (76, 58, 40):
                px, py = rad * math.cos(a), 10 + rad * math.sin(a)
                shapes.append(LINE((px, py), (px, py + 26)))
        ar, name = "قوس حصاني", "geo_horseshoe"
    elif i == 8:                               # وريدة أقواس مُحرابية
        # الأقواس السابقة كانت على نفس المركز ونفس نصف القطر فأعادت رسم الدائرة ذاتها.
        # الآن: حِجاب مموّج للداخل بين الأشعّة.
        n, R = 12, 84.0
        for k in range(n):
            a0, a1 = TAU * k / n, TAU * (k + 1) / n
            am = (a0 + a1) / 2
            shapes.append(P([(R * math.cos(a0), R * math.sin(a0)),
                             (R * 0.70 * math.cos(am), R * 0.70 * math.sin(am)),
                             (R * math.cos(a1), R * math.sin(a1))], smooth=True))
            shapes.append(LINE((30 * math.cos(a0), 30 * math.sin(a0)),
                               (R * math.cos(a0), R * math.sin(a0))))
        shapes += [CIRC((0, 0), R), CIRC((0, 0), 30)]
        ar, name = "وريدة أقواس", "geo_arc_rosette"
    else:                                      # أصداف متراكبة
        for row in range(4):
            off = 26 if row % 2 else 0
            for col in range(-2, 3):
                cx = col * 52 + off
                if abs(cx) > 88:
                    continue
                shapes.append(P(arc_pts((cx, row * 46 - 69), 26,
                                        math.pi, TAU, n=22), smooth=True))
                shapes.append(P(arc_pts((cx, row * 46 - 69), 13,
                                        math.pi, TAU, n=16), smooth=True))
        ar, name = "أصداف متراكبة", "geo_shells"
    return f"{name}_{i + 1:02d}", ar, shapes, SQUARE


# ----------------------------------------------------------------------------
# 9) زوايا  (20)
# ----------------------------------------------------------------------------


def build_corner(i):
    kind = i // 4
    v = i % 4
    shapes = []
    A = 165.0

    if kind == 0:                                  # زاوية بفرع وأوراق
        def f(t):
            return (A - A * t, A * t * t)
        shapes.append(curve(f, 30))
        nleaf = 5 + v
        ts = [0.10 + 0.74 * k / max(1, nleaf - 1) for k in range(nleaf)]
        shapes += leaves_along(f, ts, 50, 15, out_deg=56, bend=5, taper=0.30)
        shapes += small_flower(5, 30, 20, 10, 5, at=f(0.0), rot=math.radians(20))
        ar = "زاوية بفرع وأوراق"

    elif kind == 1:                                # كتيفة هندسية
        for k in range(3 + v):
            o = k * 13
            shapes.append(POLY([(A - o, o), (o, o), (o, A - o)], closed=False))
        shapes.append(POLY([(26, 26), (46, 26), (46, 46), (26, 46)]))
        shapes.append(CIRC((36, 36), 7))
        for j in range(3):
            shapes.append(CIRC((A - 16 - j * 20, 16), 5))
            shapes.append(CIRC((16, A - 16 - j * 20), 5))
        ar = "كتيفة زاوية هندسية"

    elif kind == 2:                                # قوس زاوية بتجعيدتين
        m = 18.0
        R = A - m
        # ربع قوس مركزه (A,A) يمرّ بـ (m,A) و (A,m) وينحني نحو الزاوية
        def f(t):
            a = math.pi + (math.pi / 2) * t
            return (A + R * math.cos(a), A + R * math.sin(a))
        shapes.append(curve(f, 34))
        ts = [0.16 + 0.68 * k / (3 + v) for k in range(4 + v)]
        shapes += leaves_along(f, ts, 46, 15, out_deg=92, bend=5, start_side=-1)
        # تجعيدة عند كل طرف، باتجاه مَيل المنحنى
        for t_end, sgn in ((0.0, -1), (1.0, 1)):
            px, py = f(t_end)
            th = tangent_of(f, t_end)
            sp = spiral_f(26, 0.85, 0.80, phase=th + sgn * math.pi / 2)
            o = sp(0.0)
            shapes.append(curve(lambda u, sp=sp, px=px, py=py, o=o:
                                (px + sp(u)[0] - o[0], py + sp(u)[1] - o[1]), 26))
        shapes += small_flower(6, 26, 18, 9, 5, at=f(0.5))
        ar = "قوس زاوية بتجعيدتين"

    elif kind == 3:                                # رشّة أوراق
        # القواعد موزّعة على ساق قصير (لا كلها من نقطة واحدة) فيقلّ التراكب
        n = 5 + v
        shapes.append(P([(10, 10), (30, 26), (46, 46)], smooth=True))
        for k in range(n):
            u = k / max(1, n - 1)
            a = math.radians(4 + 82 * u)
            ln = 122 - 30 * abs(u - 0.5) * 2
            bx = 10 + 30 * (1 - u) * 0.8
            by = 10 + 30 * u * 0.8
            shapes.append(xf(blade(ln, 13, a=0.8, b=1.1, bend=7),
                             a - math.pi / 2, 1.0, (bx, by)))
        shapes.append(CIRC((10, 10), 8))
        ar = "رشّة أوراق زاوية"

    else:                                          # زاوية بزهرة وساقين
        cx = cy = 44.0
        shapes += small_flower(6, 36, 24, 14, 7, at=(cx, cy))
        nleaf = 2 + (v // 2)                       # 2..3 فقط — الأكثر يزدحم
        for along_x in (True, False):
            def f(t, ax=along_x):
                # ساق ينطلق من الزهرة نحو طرف الذراع بانحناء لطيف
                x = cx + (A - cx) * t
                y = cy - 20 * math.sin(math.pi * t) - (cy - 14) * t
                return (x, y) if ax else (y, x)
            shapes.append(curve(f, 26))
            ts = [0.46 + 0.42 * k / max(1, nleaf - 1) for k in range(nleaf)]
            shapes += leaves_along(f, ts, 42, 13, out_deg=58, bend=5,
                                   start_side=1 if along_x else -1)
        ar = "زاوية بزهرة وساقين"

    return f"corner_{kind + 1}_{v + 1}", f"{ar} {v + 1}", shapes, SQUARE


# ----------------------------------------------------------------------------
# 10) أشرطة أطراف  (26)
# ----------------------------------------------------------------------------


def _border_unit(kind, i, v):
    """يُرجع (شكل الوحدة, طول الوحدة, عدد التكرارات)"""
    step = 100.0
    reps = 6

    if kind == 0:                                  # فرع متعرّج بأوراق
        def unit(k):
            out = [P([(x, 26 * math.sin(math.pi * x / step)) for x in
                      [j * step / 20 for j in range(21)]], smooth=True)]
            for j, t in enumerate((0.25, 0.75)):
                x = t * step
                y = 26 * math.sin(math.pi * t)
                side = 1 if j % 2 == 0 else -1
                out.append(xf(blade(42 + v * 6, 14, a=0.7, b=1.0, bend=5),
                              math.radians(90 + side * 62), 1.0, (x, y)))
            return out
        return unit, step, reps, "فرع متعرّج بأوراق"

    if kind == 1:                                  # موجة بزهور
        def unit(k):
            out = [P([(x, 18 + 22 * math.sin(TAU * x / step)) for x in
                      [j * step / 24 for j in range(25)]], smooth=True)]
            # الزهرة مرفوعة فوق الموجة مع ساق قصير، بدل أن تمرّ الموجة داخلها
            out.append(LINE((step / 2, 18), (step / 2, -14)))
            out += small_flower(5, 28, 19, 10, 6, at=(step / 2, -32))
            return out
        return unit, step, reps, "موجة بزهور"

    if kind == 2:                                  # سلسلة معيّنات
        def unit(k):
            s = 30 + v * 6
            out = [POLY([(step / 2, -s), (step / 2 + s, 0), (step / 2, s), (step / 2 - s, 0)])]
            out.append(POLY([(step / 2, -s * 0.5), (step / 2 + s * 0.5, 0),
                             (step / 2, s * 0.5), (step / 2 - s * 0.5, 0)]))
            out.append(LINE((step / 2 + s, 0), (step / 2 + step - s, 0)))
            return out
        return unit, step, reps, "سلسلة معيّنات"

    if kind == 3:                                  # ميندر (مفتاح يوناني)
        # الوحدة تبدأ وتنتهي على نفس المستوى (y=-u) ليتّصل التكرار بلا قطع
        def unit(k):
            u = step / 5
            return [POLY([(0, -u), (0, 2 * u), (4 * u, 2 * u), (4 * u, -u),
                          (u, -u), (u, u), (3 * u, u), (3 * u, 0),
                          (2 * u, 0), (2 * u, -2 * u), (5 * u, -2 * u),
                          (5 * u, -u)], closed=False)]
        return unit, step, 6, "مفتاح يوناني"

    if kind == 4:                                  # أقواس مع نقاط
        def unit(k):
            out = [P(arc_pts((step / 2, 0), step / 2, math.pi, TAU, n=26), smooth=True)]
            out.append(CIRC((step / 2, -step / 2 - 14), 7))
            out.append(LINE((step / 2, -step / 2), (step / 2, -step / 2 - 7)))
            return out
        return unit, step, 6, "أقواس ونقاط"

    if kind == 5:                                  # تكرار غصن زيتون
        def unit(k):
            out = [LINE((0, 0), (step, 0))]
            # زوجان فقط بتباعد أوسع — ثلاثة أزواج كانت تتراكم وتُخفي الحبّة
            for j in range(2):
                x = 22 + j * 40
                for side in (1, -1):
                    out.append(xf(blade(42, 10, a=0.9, b=0.9, bend=side * 3),
                                  math.radians(90 + side * 50), 1.0, (x, 0)))
            out.append(LINE((step - 18, 0), (step - 18, 13)))
            out.append(ELL((step - 18, 24), 9, 12))
            return out
        return unit, step, 6, "تكرار غصن زيتون"

    if kind == 6:                                  # زجزاج ومثلثات
        def unit(k):
            out = [POLY([(0, 32), (step / 2, -32), (step, 32)], closed=False)]
            out.append(POLY([(step / 2 - 14, 32), (step / 2, 4), (step / 2 + 14, 32)]))
            return out
        return unit, step, 6, "زجزاج ومثلثات"

    if kind == 7:                                  # دوائر متشابكة
        # نصف القطر أكبر من نصف الخطوة، فتتقاطع الدوائر فعلاً (وبلا شرطة شاردة)
        def unit(k):
            r = step * 0.62
            return [CIRC((step / 2, 0), r), CIRC((step / 2, 0), r * 0.52)]
        return unit, step, 6, "دوائر متشابكة"

    if kind == 8:                                  # بيضيات متشابكة
        def unit(k):
            return [ELL((step / 2, 0), step * 0.66, 24),
                    ELL((step / 2, 0), step * 0.40, 13)]
        return unit, step, 6, "بيضيات متشابكة"

    if kind == 9:                                  # مراوح نخيل
        def unit(k):
            out = []
            n = 7 + v * 2
            for j in range(n):
                u = (j - (n - 1) / 2) / max(1, (n - 1) / 2)
                out.append(xf(blade(54 - abs(u) * 12, 11, a=0.95, b=1.1),
                              u * math.radians(62), 1.0, (step / 2, 24)))
            out.append(P(arc_pts((step / 2, 24), 16, math.pi, TAU, n=16), smooth=True))
            out.append(LINE((0, 30), (step, 30)))
            return out
        return unit, step, 6, "مراوح نخيل"

    if kind == 10:                                 # قلوب متكررة
        def unit(k):
            out = [LINE((0, 36), (step, 36))]
            # قلب مغلق قاعدته ملامسة لخط الأساس
            out.append(P([(step / 2, 34),
                          (step / 2 + 36, 2), (step / 2 + 30, -26),
                          (step / 2 + 11, -22), (step / 2, -4),
                          (step / 2 - 11, -22), (step / 2 - 30, -26),
                          (step / 2 - 36, 2)], closed=True, smooth=True))
            out.append(LINE((step / 2, 34), (step / 2, 44)))
            return out
        return unit, step, 6, "قلوب متكررة"

    if kind == 11:                                 # غيوش
        def unit(k):
            out = []
            for ph in (0, math.pi):
                out.append(P([(x, 26 * math.sin(TAU * x / step + ph)) for x in
                              [j * step / 24 for j in range(25)]], smooth=True))
            out.append(CIRC((step / 4, 0), 7))
            out.append(CIRC((3 * step / 4, 0), 7))
            return out
        return unit, step, 6, "غيوش متقاطع"

    # kind == 12                                   # توليب متكرر
    def unit(k):
        out = [LINE((0, 44), (step, 44))]
        out.append(xf(_tulip_cup(28, 62), 0, 1.0, (step / 2, 26)))
        out.append(LINE((step / 2, 26), (step / 2, 44)))
        for side in (1, -1):
            out.append(xf(blade(26, 9, a=0.9, b=1.1, bend=side * 5),
                          side * math.radians(116), 1.0, (step / 2, 38)))
        return out
    return unit, step, 6, "توليب متكرر"


def build_border(i):
    kind = i % 13
    v = i // 13
    unit, step, reps, ar = _border_unit(kind, i, v)
    reps = reps + (1 if v else 0)
    shapes = []
    for k in range(reps):
        for sh in unit(k):
            shapes.append(xf(sh, 0.0, 1.0, (k * step, 0.0)))
    return f"border_{kind + 1:02d}_{v + 1}", f"شريط طرف — {ar}", shapes, STRIP


# ----------------------------------------------------------------------------
# 11) فروع وحلزونات  (14)
# ----------------------------------------------------------------------------


def build_scroll(i):
    kind = i // 4 if i < 12 else 3
    v = i % 4
    shapes = []

    if kind == 0:                                 # حلزون بأوراق
        turns = 1.35 + v * 0.22
        f = spiral_f(92, turns, 0.86)
        shapes.append(curve(f, 60))
        n = 4 + v
        ts = [0.06 + 0.66 * k / max(1, n - 1) for k in range(n)]
        # الأوراق تخرج شعاعياً للخارج (لا بزاوية ثابتة عشوائية)
        for k, t in enumerate(ts):
            px, py = f(t)
            rad_out = math.atan2(py, px)
            shapes.append(xf(blade(50 - 5 * k, 16 - k, a=0.72, b=1.05, bend=6),
                             rad_out + math.radians(16) + math.pi / 2, 1.0, (px, py)))
        shapes += small_flower(5, 22, 15, 8, 4, at=f(1.0))   # يملأ قلب الحلزون
        ar = "حلزون بأوراق"

    elif kind == 1:                               # فرع S
        def f(t):
            x = -95 + 190 * t
            return (x, 64 * math.sin(math.pi * x / 95))
        shapes.append(curve(f, 44))
        n = 5 + v
        ts = [0.10 + 0.74 * k / (n - 1) for k in range(n)]
        shapes += leaves_along(f, ts, 48, 16, out_deg=60, bend=6)
        shapes += small_flower(5, 30, 20, 10, 5, at=f(1.0))
        ar = "فرع متموّج S"

    elif kind == 2:                               # تجعيدة مزدوجة
        for side in (1, -1):
            f = spiral_f(74, 1.3 + v * 0.18, 0.84,
                         phase=0.0 if side > 0 else math.pi,
                         at=(side * 46.0, 0.0))
            shapes.append(curve(f, 48))
        shapes.append(P([(-46, 0), (-22, -26), (0, -34), (22, -26), (46, 0)], smooth=True))
        for side in (1, -1):
            shapes.append(xf(blade(44, 15, a=0.78, b=1.0, bend=side * 6),
                             side * math.radians(52), 1.0, (side * 22, -26)))
        shapes += small_flower(6, 24, 17, 9, 5, at=(0.0, -40.0))
        ar = "تجعيدة مزدوجة"

    else:                                         # نخلة أرابيسك متناظرة
        # ساق مركزي، وتجعيدتان متناظرتان، وأوراق تتبع مَيل كل تجعيدة، وزهرة في القمة
        shapes.append(P([(0, 86), (0, 20), (0, -6)], smooth=True))
        for side in (1, -1):
            def g(t, s=side):
                u = t
                r = 26 + 56 * u
                a = math.radians(-78) * (1 - u) + math.radians(28) * u
                return (s * r * math.cos(a), 10 + r * math.sin(a))
            shapes.append(curve(g, 30))
            ts = [0.22 + 0.62 * k / (1 + v) for k in range(2 + v)]
            shapes += leaves_along(g, ts, 46, 15, out_deg=62, bend=6,
                                   start_side=side)
        shapes += small_flower(6, 34, 22, 12, 6, at=(0.0, -24.0))
        ar = "أرابيسك متناظر"

    return f"scroll_{kind + 1}_{v + 1}_{i}", f"{ar} {v + 1}", shapes, SQUARE


# ----------------------------------------------------------------------------
# السجل والتشغيل
# ----------------------------------------------------------------------------

FAMILIES = [
    ("أوراق مفردة", build_leaves_simple, 28),
    ("أوراق مفصّصة", build_leaves_lobed, 12),
    ("أغصان زيتون", build_olive, 24),
    ("زهور شعاعية", build_rosette, 26),
    ("زهور خاصة", build_flower_special, 12),
    ("نجوم هندسية", build_star, 16),
    ("شبكات هندسية", build_lattice, 12),
    ("أقواس ووريدات", build_arcs, 10),
    ("زوايا", build_corner, 20),
    ("أشرطة أطراف", build_border, 26),
    ("فروع وحلزونات", build_scroll, 14),
]


def main():
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    for old in SVG_DIR.glob("*.svg"):
        old.unlink()

    index = []
    num = 0
    for fam_ar, builder, count in FAMILIES:
        for i in range(count):
            num += 1
            name, title_ar, shapes, canvas = builder(i)
            fname = f"{num:03d}_{name}.svg"
            margin = 14 if canvas is SQUARE else 16
            write_svg(SVG_DIR / fname, shapes, canvas=canvas, margin=margin,
                      stroke=1.9 if canvas is SQUARE else 2.2,
                      title=f"{num:03d} — {title_ar}")
            index.append({
                "num": num, "file": fname, "title": title_ar,
                "family": fam_ar, "wide": canvas is not SQUARE,
                "elements": len(shapes),
            })

    (ROOT / "index.json").write_text(
        __import__("json").dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"تم توليد {num} ملف SVG في {SVG_DIR}")
    for fam_ar, _, count in FAMILIES:
        print(f"  - {fam_ar}: {count}")
    return index


if __name__ == "__main__":
    main()
