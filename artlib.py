#!/usr/bin/env python3
"""
مكتبة رسم فنّي للمجموعة الثانية (رسومات واقعية).

الفروق الجوهرية عن مكتبة المجموعة الأولى:
  1. سماكات خطوط متعددة: محيط خارجي ثقيل + تفاصيل داخلية رقيقة.
     (هذا أكبر عامل يجعل الرسمة تبدو مرسومة بيد لا مُولّدة آلياً)
  2. ribbon(): شريط حول محور حرّ — يسمح بمحاور ملتفّة (بوتيه، بتلات مجعّدة، محالق).
  3. حواف مكشكشة لا تتلاشى عند القمة — البتلة الحقيقية مجعّدة عند حافتها.
  4. اهتزاز خفيف (jitter) ناعم يكسر التناظر الآلي.

بلا أي اعتماديات خارجية — مكتبة Python القياسية فقط.
"""

import math
import random
import re

TAU = math.tau

# مستويات سماكة الخط (مضروبة في السماكة الأساسية)
W_MAIN = 1.0      # المحيط الخارجي
W_MID = 0.62      # حدود البتلات الداخلية
W_FINE = 0.40     # العروق والتفاصيل الدقيقة


# ---------------------------------------------------------------------------
# أشكال أوّلية
# ---------------------------------------------------------------------------


def P(points, closed=False, smooth=True, w=W_MAIN):
    return {"kind": "path", "pts": [(float(x), float(y)) for x, y in points],
            "closed": closed, "smooth": smooth, "w": w}


def CIRC(c, r, w=W_MAIN):
    return {"kind": "circle", "c": (float(c[0]), float(c[1])), "r": float(r), "w": w}


def DOT(c, r):
    """نقطة مُعبّأة سوداء — الحبّات والخرز في نقوش التطريز تكون مصمتة."""
    return {"kind": "dot", "c": (float(c[0]), float(c[1])), "r": float(r),
            "w": W_MAIN}


def FILLED(points, smooth=True):
    """شكل مغلق مُعبّأ (للأوراق المصمتة والعناصر الصغيرة)."""
    return {"kind": "fill", "pts": [(float(x), float(y)) for x, y in points],
            "closed": True, "smooth": smooth, "w": W_MAIN}


def filled_ribbon(axis, half, n=120, smooth=True):
    """
    شريط مصمت حول محور حرّ — الأساس في الزخرفة المصمتة:
    ساق يتدرّج في السماكة، وفرع ينتهي بسنّ، وحلزون يتلاشى طرفه.

    ميزة مهمة: الأشكال المصمتة المتراكبة تتّحد في ظلّ واحد،
    بخلاف المحيطات التي تتشابك خطوطها عند التراكب.
    """
    return FILLED(ribbon(axis, half, n=n)["pts"], smooth=smooth)


def taper_tip(w0, power=0.78, tip=0.0):
    """نصف عرض يتدرّج من w0 عند t=0 إلى `tip` عند t=1 — لساق أو فرع."""
    def f(t):
        t = min(1.0, max(0.0, t))
        return tip + (w0 - tip) * (1 - t) ** power
    return f


def spiral_axis(R, turns=1.35, phase=0.0, shrink=0.88, at=(0.0, 0.0)):
    """محور حلزوني: يبدأ من المحيط وينتهي عند القلب."""
    def f(t):
        a = phase + TAU * turns * t
        r = R * (1 - shrink * t)
        return (at[0] + r * math.cos(a), at[1] + r * math.sin(a))
    o = f(0.0)
    return lambda t: (f(t)[0] - o[0] + at[0], f(t)[1] - o[1] + at[1])


def LINE(p1, p2, w=W_MAIN):
    return P([p1, p2], closed=False, smooth=False, w=w)


def POLY(points, closed=True, w=W_MAIN):
    return P(points, closed=closed, smooth=False, w=w)


def ELL(c, rx, ry, ang=0.0, n=48, w=W_MAIN):
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for i in range(n):
        t = TAU * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((c[0] + x * ca - y * sa, c[1] + x * sa + y * ca))
    return P(pts, closed=True, smooth=True, w=w)


def arc(c, r, a0, a1, n=32, w=W_MAIN):
    return P([(c[0] + r * math.cos(a0 + (a1 - a0) * i / n),
              c[1] + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)],
             smooth=True, w=w)


def ell_arc(c, rx, ry, a0, a1, rot=0.0, n=32, w=W_MAIN):
    ca, sa = math.cos(rot), math.sin(rot)
    pts = []
    for i in range(n + 1):
        t = a0 + (a1 - a0) * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((c[0] + x * ca - y * sa, c[1] + x * sa + y * ca))
    return P(pts, smooth=True, w=w)


def polar(r, a):
    return (r * math.cos(a), r * math.sin(a))


# ---------------------------------------------------------------------------
# تحويلات
# ---------------------------------------------------------------------------


def xf_pts(pts, ang=0.0, scale=1.0, at=(0.0, 0.0), flip=1):
    ca, sa = math.cos(ang) * scale, math.sin(ang) * scale
    return [(at[0] + (x * flip) * ca - y * sa, at[1] + (x * flip) * sa + y * ca)
            for x, y in pts]


def xf(shape, ang=0.0, scale=1.0, at=(0.0, 0.0), flip=1):
    if shape["kind"] in ("path", "fill"):
        s = dict(shape)
        s["pts"] = xf_pts(shape["pts"], ang, scale, at, flip)
        return s
    s = dict(shape)
    s["c"] = xf_pts([shape["c"]], ang, scale, at, flip)[0]
    s["r"] = shape["r"] * scale
    return s


def xf_all(shapes, ang=0.0, scale=1.0, at=(0.0, 0.0), flip=1):
    return [xf(s, ang, scale, at, flip) for s in shapes]


def mirror_x(shapes):
    """نسخة معكوسة أفقياً — لبناء التشكيلات المتناظرة."""
    return [xf(s, 0.0, 1.0, (0.0, 0.0), -1) for s in shapes]


# ---------------------------------------------------------------------------
# محاور وأشرطة
# ---------------------------------------------------------------------------


def normal_of(axis, t, e=1e-3):
    p0, p1 = axis(max(0.0, t - e)), axis(min(1.0, t + e))
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    m = math.hypot(dx, dy) or 1.0
    return (-dy / m, dx / m)


def tangent_of(axis, t, e=1e-3):
    p0, p1 = axis(max(0.0, t - e)), axis(min(1.0, t + e))
    return math.atan2(p1[1] - p0[1], p1[0] - p0[0])


def ribbon(axis, half, n=96, w=W_MAIN, closed=True):
    """
    شريط مغلق حول محور حرّ: axis(t)->(x,y) و half(t)->نصف العرض.
    يسمح بمحاور ملتفّة (بوتيه ومحالق وبتلات مجعّدة) لا مجرّد انحناء بسيط.
    """
    left, right = [], []
    for i in range(n + 1):
        t = i / n
        px, py = axis(t)
        nx, ny = normal_of(axis, t)
        h = half(t)
        left.append((px + nx * h, py + ny * h))
        right.append((px - nx * h, py - ny * h))
    # حذف النقاط المتطابقة عند الطرفين إن كان العرض صفراً هناك
    pts = list(left)
    tail = right[::-1]
    if half(1.0) < 1e-6:
        tail = tail[1:]
    if half(0.0) < 1e-6:
        tail = tail[:-1]
    return P(pts + tail, closed=closed, smooth=True, w=w)


def _profile_norm(a, b):
    """أقصى قيمة لـ t^a·(1-t)^b تحدث عند t = a/(a+b) — للمعايرة إلى 1."""
    t0 = a / (a + b)
    return t0 ** a * (1 - t0) ** b


def taper_fn(width, a=0.6, b=0.9, ruffle=0.0, waves=5, phase=0.0,
             tip=0.0, base=0.0):
    """
    دالة نصف العرض: profile = t^a (1-t)^b مُعاير إلى 1.
    ruffle: تكشكش الحافة — لا يتلاشى عند القمة (خلاف عروق الورقة)،
            لأن حافة البتلة الحقيقية مجعّدة تماماً عند طرفها.
    tip/base: نصف عرض إضافي عند الطرفين (لطرف غير مدبّب).
    """
    t0 = a / (a + b)
    norm = t0 ** a * (1 - t0) ** b

    def f(t):
        t = min(1.0, max(0.0, t))
        h = width * (t ** a * (1 - t) ** b) / norm
        if ruffle:
            h *= 1 + ruffle * math.sin(waves * TAU * t + phase)
        h += tip * t + base * (1 - t)
        return max(0.0, h)
    return f


def arc_axis(c, r, a0, a1):
    def f(t):
        a = a0 + (a1 - a0) * t
        return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))
    return f


def curl_axis(length, curl=1.5, tilt=-math.pi / 2, tighten=0.62):
    """
    محور ملتفّ: يبدأ مستقيماً ثم يلتفّ حلزونياً — أساس شكل البوتيه
    وأطراف البتلات المنكفئة.
    """
    def f(t):
        a = tilt + curl * math.pi * (t ** 1.45)
        r = length * (1 - tighten * t)
        x0, y0 = length * math.cos(tilt), length * math.sin(tilt)
        return (r * math.cos(a) - x0 * 0 + 0, r * math.sin(a) - y0 * 0 + 0)
    # إعادة ضبط البداية إلى نقطة الأصل
    o = f(0.0)
    return lambda t: (f(t)[0] - o[0], f(t)[1] - o[1])


def smooth_noise(seed, octaves=3):
    """ضجيج ناعم في المدى [-1,1] لكسر التناظر الآلي بلطف."""
    rng = random.Random(seed)
    comps = [(rng.uniform(1.0, 2.2) * (k + 1), rng.uniform(0, TAU),
              1.0 / (k + 1)) for k in range(octaves)]
    scale = sum(c[2] for c in comps)

    def f(t):
        return sum(amp * math.sin(freq * TAU * t + ph)
                   for freq, ph, amp in comps) / scale
    return f


def jittered(axis, seed, amount=1.6):
    """يضيف اهتزازاً عرضياً خفيفاً على المحور ليبدو مرسوماً بيد."""
    nz = smooth_noise(seed)

    def f(t):
        px, py = axis(t)
        nx, ny = normal_of(axis, t)
        d = amount * nz(t) * math.sin(math.pi * min(1.0, max(0.0, t))) ** 0.5
        return (px + nx * d, py + ny * d)
    return f


# ---------------------------------------------------------------------------
# بتلات
# ---------------------------------------------------------------------------


def petal(length, width, a=0.85, b=0.95, bend=0.0, ruffle=0.0, waves=4,
          phase=0.0, w=W_MAIN, n=88, seed=None, jitter=0.0):
    """بتلة مفردة: القاعدة عند (0,0) والطرف نحو -y."""
    def axis(t):
        return (bend * math.sin(math.pi * t), -length * t)
    ax = jittered(axis, seed or 0, jitter) if jitter else axis
    return ribbon(ax, taper_fn(width, a, b, ruffle, waves, phase), n=n, w=w)


def petal_curled(length, width, curl=0.55, side=1, ruffle=0.0, waves=4,
                 w=W_MAIN, n=92):
    """
    بتلة بطرف منكفئ — السمة المميّزة لبتلة الوردة الحقيقية:
    المحور يميل ثم ينثني عند الطرف.
    """
    def axis(t):
        a = -math.pi / 2 + side * curl * (t ** 1.7)
        r = length * t
        return (r * math.cos(a) * 1.0, r * math.sin(a))
    return ribbon(axis, taper_fn(width, 0.80, 1.0, ruffle, waves), n=n, w=w)


def leaf_hatched(length, width, a=0.68, b=0.95, bend=2.0, lines=9,
                 reach=0.90, midrib=True, w=W_MAIN, wh=W_FINE, n=72,
                 lean=0.13):
    """
    ورقة محشوّة بخطوط متوازية — مظهر تطريز الساتان (satin stitch).

    الخطوط تمتدّ من العِرق الأوسط إلى الحافة وتميل نحو القمة بمقدار `lean`،
    وهو ما يمنحها إحساس الخياطة لا إحساس التظليل الهندسي.
    """
    norm = _profile_norm(a, b)

    def mid(t):
        return (bend * math.sin(math.pi * t), -length * t)

    def half(t):
        t = min(1.0, max(0.0, t))
        return width * (t ** a * (1 - t) ** b) / norm

    def nrm(t):
        e = 1e-3
        p0, p1 = mid(max(0.0, t - e)), mid(min(1.0, t + e))
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        m = math.hypot(dx, dy) or 1.0
        return (-dy / m, dx / m)

    out = [ribbon(mid, half, n=n, w=w)]
    if midrib:
        out.append(P([mid(0.04 + 0.92 * i / 18) for i in range(19)],
                     smooth=True, w=wh))
    for k in range(lines):
        # تبدأ خطوط الحشو بعد القاعدة (0.22) لا من عندها:
        # تكدّس الخطوط عند نقطة التشعّب يُنتج ضجيجاً بصرياً
        t = 0.22 + 0.70 * k / max(1, lines - 1)
        te = min(0.985, t + lean)
        bx, by = mid(t)
        ex, ey = mid(te)
        nx, ny = nrm(te)
        he = half(te) * reach
        for side in (1, -1):
            out.append(P([(bx, by), (ex + side * nx * he, ey + side * ny * he)],
                         smooth=False, w=wh))
    return out


def petal_edge(r_in, r_out, ang, spread, bulge=1.03, ruffle=0.0, waves=3,
               w=W_MID, n=30):
    """
    حافة بتلة مفتوحة (قوس) — هكذا تُرسم الوردة من الأعلى في الرسم الواقعي:
    لا نرسم البتلة كاملة، بل حافتها الظاهرة فقط فوق البتلة التي تحتها.
    """
    pts = []
    for i in range(n + 1):
        u = i / n
        a = ang + (u - 0.5) * 2 * spread
        # شكل الحافة: مرتفعة في الوسط ومنخفضة عند الجانبين
        k = math.cos((u - 0.5) * math.pi)
        rr = r_in + (r_out - r_in) * (k ** 0.72) * bulge
        if ruffle:
            rr *= 1 + ruffle * math.sin(waves * TAU * u)
        pts.append(polar(rr, a))
    return P(pts, smooth=True, w=w)


# ---------------------------------------------------------------------------
# كتابة SVG (بسماكات متعددة)
# ---------------------------------------------------------------------------


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
        seq = [(ext[i - 1], ext[i], ext[i + 1], ext[i + 2])
               for i in range(1, len(ext) - 2)]
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


def shape_d(sh):
    pts = sh["pts"]
    return _catmull(pts, sh["closed"]) if sh["smooth"] else _polyline(pts, sh["closed"])


_NUM = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def write_svg(path, shapes, canvas=(200, 200), margin=15, stroke=2.3, title=""):
    """
    الحدود محسوبة من نقاط تحكّم بيزييه الفعلية (المنحنى محصور في غلافها المحدّب)،
    فلا يخرج أي جزء من الرسم عن الإطار.
    """
    W, H = canvas

    prepared = []          # (w, kind, payload)
    filled = []            # عناصر مُعبّأة (نقاط وأشكال مصمتة)
    xs, ys = [], []
    for sh in shapes:
        if sh["kind"] in ("circle", "dot"):
            cx, cy, r = sh["c"][0], sh["c"][1], sh["r"]
            if sh["kind"] == "dot":
                filled.append(("circle", sh))
            else:
                prepared.append((sh["w"], "circle", sh))
            xs += [cx - r, cx + r]
            ys += [cy - r, cy + r]
        else:
            d = shape_d(sh)
            if not d:
                continue
            if sh["kind"] == "fill":
                filled.append(("path", d))
            else:
                prepared.append((sh["w"], "path", d))
            nums = [float(v) for v in _NUM.findall(d)]
            if len(nums) % 2:
                nums = nums[:-1]
            xs += nums[0::2]
            ys += nums[1::2]

    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    bw, bh = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
    s = min((W - 2 * margin) / bw, (H - 2 * margin) / bh)
    tx = (W - bw * s) / 2 - x0 * s
    ty = (H - bh * s) / 2 - y0 * s

    groups = {}
    for wt, kind, payload in prepared:
        groups.setdefault(round(wt, 3), []).append((kind, payload))

    body = []
    for wt in sorted(groups, reverse=True):
        body.append(f'    <g stroke-width="{stroke * wt / s:.4f}">')
        for kind, payload in groups[wt]:
            if kind == "circle":
                body.append(f'      <circle cx="{fmt(payload["c"][0])}" '
                            f'cy="{fmt(payload["c"][1])}" r="{fmt(payload["r"])}"/>')
            else:
                body.append(f'      <path d="{payload}"/>')
        body.append("    </g>")

    if filled:
        body.append('    <g fill="#000000" stroke="none">')
        for kind, payload in filled:
            if kind == "circle":
                body.append(f'      <circle cx="{fmt(payload["c"][0])}" '
                            f'cy="{fmt(payload["c"][1])}" r="{fmt(payload["r"])}"/>')
            else:
                body.append(f'      <path d="{payload}"/>')
        body.append("    </g>")

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}">\n'
        f"  <title>{title}</title>\n"
        f'  <g transform="translate({fmt(tx)},{fmt(ty)}) scale({s:.5f})" '
        'fill="none" stroke="#000000" stroke-linecap="round" '
        'stroke-linejoin="round">\n'
        + "\n".join(body)
        + "\n  </g>\n</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")
