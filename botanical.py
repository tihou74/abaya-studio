#!/usr/bin/env python3
"""
رسم نباتي واقعي بالخط الرفيع: ورد وزنابق وأوراق مسنّنة.

لماذا ملف منفصل ومنهج مختلف:
  المجموعات السابقة وُلّدت بدوال متناظرة، وهذا ينجح في الأشكال الهندسية
  ويفشل في النبات الواقعي. الوردة الحقيقية بتلاتها متراكبة بترتيب حلزوني
  غير منتظم، وكل بتلة تُرسم **جزئياً** حيث تظهر فوق التي تحتها.
  فالبناء هنا بنقاط تحكّم محدّدة بقصد، لا بمعادلة تناظر.

القواعد المستخلصة من الفشل السابق:
  1. حافة البتلة قوس **مفتوح** لا شكل مغلق — هكذا تتراكب البتلات.
  2. لا تكشكش عالي التردّد: ثلاث موجات على قوس قصير تُنتج أشواكاً لا بتلة.
  3. تجويف خفيف في منتصف حافة البتلة — سمة بتلة الوردة الحقيقية.
  4. طرفا البتلة ينثنيان للداخل قليلاً (hook) فتبدو مطويّة لا مقوّسة.
"""

import math

from artlib import (TAU, W_FINE, W_MAIN, W_MID, CIRC, P, polar, ribbon,
                    taper_fn, tangent_of)

# سماكات هذا الأسلوب: رفيعة ومتقاربة
WO = 1.0        # المحيط
WI = 0.74       # حدود البتلات الداخلية
WV = 0.52       # العروق والأسدية


def _lin(n):
    return [i / (n - 1) for i in range(n)]


def arc_c(center, r, a0, a1, n=30, w=W_MAIN):
    return P([(center[0] + r * math.cos(a0 + (a1 - a0) * t),
               center[1] + r * math.sin(a0 + (a1 - a0) * t))
              for t in _lin(n)], smooth=True, w=w)


# ---------------------------------------------------------------------------
# الوردة
# ---------------------------------------------------------------------------


def rose_petal_edge(r_in, r_out, ang, spread, dip=0.14, hook=0.07,
                    wave=0.0, w=WI, n=38):
    """
    حافة بتلة وردة: قوس مفتوح من r_in إلى r_out ثم إلى r_in.

    dip  : تجويف خفيف في منتصف الحافة (سمة بتلة الوردة)
    hook : انثناء طرفَي البتلة للداخل فتبدو مطويّة
    wave : تمويج لطيف **موجة واحدة فقط** — أكثر من ذلك يُنتج أشواكاً
    """
    depth = r_out - r_in
    pts = []
    for u in _lin(n):
        a = ang + (u - 0.5) * 2 * spread
        k = math.sin(math.pi * u) ** 0.72          # 0 عند الطرفين، 1 في الوسط
        rr = r_in + depth * k
        # تجويف المنتصف
        rr -= depth * dip * math.exp(-((u - 0.5) / 0.17) ** 2)
        # انثناء الطرفين للداخل — بمدى واسع (σ=0.26) ومقدار صغير.
        # بـ σ=0.13 كان نصف القطر يتغيّر بحدّة على زاوية ضيّقة فينثني
        # المنحنى على نفسه وتظهر علامة × عند طرف كل بتلة.
        rr -= depth * hook * math.exp(-(u / 0.26) ** 2)
        rr -= depth * hook * math.exp(-((1 - u) / 0.26) ** 2)
        if wave:
            rr += depth * wave * math.sin(TAU * u) * k
        pts.append(polar(rr, a))
    return P(pts, smooth=True, w=w)


def rose_heart(R=1.0, rot=0.0):
    """
    قلب الوردة: لولب صغير + قوسان غير متمركزين يحيطانه.
    الأقواس غير المتمركزة هي ما يعطي الالتفاف الطبيعي؛
    الأقواس المتمركزة تُنتج حلقات آلية.
    """
    out = []
    pts = [polar(R * (0.05 + 0.16 * t), rot + 0.5 + TAU * 1.05 * t)
           for t in _lin(44)]
    out.append(P(pts, smooth=True, w=WI))
    out.append(arc_c((R * 0.03, R * 0.015), R * 0.26,
                     rot + math.radians(15), rot + math.radians(215),
                     n=26, w=WI))
    out.append(arc_c((-R * 0.025, R * 0.03), R * 0.36,
                     rot + math.radians(200), rot + math.radians(392),
                     n=26, w=WI))
    return out


ROSE_RINGS = (
    # (عدد البتلات, نصف القطر الداخلي, الخارجي, التمويج)
    (3, 0.30, 0.47, 0.0),
    (5, 0.42, 0.64, 0.0),
    (5, 0.60, 0.83, 0.02),
    (6, 0.78, 1.00, 0.03),
)


def rose_full(R=100.0, rot=0.0, rings=ROSE_RINGS):
    """وردة متفتّحة من الأعلى: قلب + حلقات بتلات متراكبة ومُزاحة."""
    out = rose_heart(R, rot)
    phase = rot
    for idx, (n, fi, fo, wv) in enumerate(rings):
        # عامل 1.0 بالضبط: البتلات المتجاورة تتلامس فتصنع ثنية V طبيعية.
        # بعامل 1.06 كانت تتراكب 6% فتتقاطع نهاياتها وتظهر علامة × عند
        # كل وصلة. والتراكب في الرسم الحقيقي يُخفيه الحجب، وهو غير متاح هنا.
        spread = (math.pi / n) * 1.0
        last = idx == len(rings) - 1
        for k in range(n):
            a = TAU * k / n + phase
            out.append(rose_petal_edge(R * fi, R * fo, a, spread,
                                       dip=0.13 + 0.03 * idx,
                                       hook=0.06,
                                       wave=wv,
                                       w=WO if last else WI,
                                       n=40))
        phase += math.pi / n
    return out


def rose_bud(H=76.0, rot=0.0):
    """
    برعم وردة: كأس بيضي + حافتا بتلتين ملفوفتان + خمس سبلات مدبّبة.
    السبلات تخرج من القاعدة وتنفرج للخارج.
    """
    W = H * 0.48
    out = []
    # الكأس
    out.append(ribbon(lambda t: (0.0, -H * t),
                      taper_fn(W * 0.5, 1.05, 0.80), n=70, w=WO))
    # حافتا بتلتين ملفوفتين، غير متقاطعتين: بخطّ واحد كان البرعم
    # يُقرأ كورقة مدبّقة لا كزهرة ملفوفة.
    out.append(P([(-W * 0.26, -H * 0.20), (-W * 0.02, -H * 0.50),
                  (W * 0.18, -H * 0.74), (W * 0.05, -H * 0.91)],
                 smooth=True, w=WI))
    out.append(P([(W * 0.30, -H * 0.30), (W * 0.30, -H * 0.56),
                  (W * 0.14, -H * 0.78)], smooth=True, w=WV))

    # الكأس (المحفظة) أسفل البرعم — إشارة قويّة على أنه زهرة لا ورقة
    out.append(P([(-W * 0.30, -H * 0.10), (-W * 0.34, -H * 0.02),
                  (-W * 0.24, H * 0.07), (0.0, H * 0.10),
                  (W * 0.24, H * 0.07), (W * 0.34, -H * 0.02),
                  (W * 0.30, -H * 0.10)], smooth=True, w=WO))
    # السبلات: أربع فقط، قصيرة (≈0.58·H) ومنفرجة ±40°.
    # بطول 1.0·H وانفراج ±52° كانت تطغى على الكأس فيبدو البرعم نجمة
    # من شفرات رقيقة لا برعماً. والسبلة الوسطى كانت تغطّي قمّة البرعم.
    # زوايا السبلات محسوبة لتبقى خارج الكأس:
    # الكأس أقصى نصف عرض له ≈ 0.18·H، وسبلة بزاوية 48° تبعد عن المحور
    # 0.215·H عند منتصفها، فتبقى خارجه. والزوج الداخلي السابق كان بزاوية
    # 18° فقط فكان يصعد *داخل* الكأس ويقطع مُحيطه.
    for deg, frac in ((-66, 0.40), (-40, 0.54), (40, 0.54), (66, 0.40)):
        ang = math.radians(deg)
        u = deg / 80.0
        ln = H * frac
        # قواعد السبلات موزّعة على قوس صغير لا من نقطة واحدة:
        # التلاقي في نقطة واحدة كان يصنع عقدة سوداء أسفل البرعم
        bx = u * W * 0.13
        by = -H * 0.03 * (1 - abs(u) * 0.5)

        def sep(t, ang=ang, ln=ln, bx=bx, by=by):
            bow = 0.16 * ln * (t ** 1.8)
            return (bx + math.sin(ang) * ln * t + bow * math.cos(ang),
                    by - math.cos(ang) * ln * t + bow * math.sin(ang))

        out.append(ribbon(sep, taper_fn(H * 0.050, 1.10, 1.35), n=46, w=WI))
    return out


# ---------------------------------------------------------------------------
# أوراق الورد: مسنّنة ومركّبة
# ---------------------------------------------------------------------------


def _saw(t, teeth):
    return 4 * abs(t * teeth - math.floor(t * teeth + 0.5)) - 1


def rose_leaflet(L=54.0, Wd=14.0, bend=3.0, teeth=22, amp=0.055,
                 veins=4, w=WO):
    """
    وُرَيقة ورد: حافة مسنّنة + عِرق أوسط + عروق جانبية منحنية.

    التسنين: 22 سنّاً بعمق 5.5% — وبـ 11 سنّاً وعمق 11% كانت الأسنان
    مثلثات كبيرة تجعل الورقة تشبه نصل منشار أو شجرة صنوبر.
    والعرض: نصف عرض 0.26·L (كامل ≈ نصف الطول)؛ وبـ 0.35·L كانت معيّنة عريضة.
    """
    base = taper_fn(Wd, 0.80, 1.05)

    def axis(t):
        return (bend * math.sin(math.pi * t), -L * t)

    def half(t):
        g = amp * math.sin(math.pi * t) ** 0.45
        return base(t) * (1 + g * _saw(t, teeth))

    out = [ribbon(axis, half, n=120, w=w)]
    out.append(P([axis(0.03 + 0.93 * i / 16) for i in range(17)],
                 smooth=True, w=WV))
    for k in range(1, veins + 1):
        t = 0.14 + 0.66 * k / (veins + 1)
        te = min(0.94, t + 0.15)
        bx, by = axis(t)
        ex, ey = axis(te)
        e = 1e-3
        p0, p1 = axis(max(0, te - e)), axis(min(1, te + e))
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        m = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / m, dx / m
        he = base(te) * 0.78
        mx, my = axis((t + te) / 2)
        for side in (1, -1):
            # عرق منحنٍ بثلاث نقاط — الخط المستقيم يبدو هندسياً لا نباتياً
            out.append(P([(bx, by),
                          (mx + side * nx * he * 0.45,
                           my + side * ny * he * 0.45),
                          (ex + side * nx * he, ey + side * ny * he)],
                         smooth=True, w=WV))
    return out


def rose_leaf(L=96.0, size=1.0, leaflets=5, w=WO):
    """ورقة ورد مركّبة: زوجان من الوُرَيقات + وُرَيقة طرفية."""
    out = [P([(0, 0), (0, -L * 0.5), (0, -L)], smooth=True, w=WI)]
    pairs = (leaflets - 1) // 2
    for k in range(pairs):
        t = 0.30 + 0.40 * k / max(1, pairs - 1) if pairs > 1 else 0.42
        py = -L * t
        for side in (1, -1):
            for s in rose_leaflet(52 * size, 13.5 * size, bend=side * 2.5,
                                  w=w):
                out.append(_rot_shift(s, side * math.radians(58), (0, py)))
    for s in rose_leaflet(58 * size, 15 * size, w=w):
        out.append(_rot_shift(s, 0.0, (0, -L)))
    return out


def _rot_shift(shape, ang, at):
    ca, sa = math.cos(ang), math.sin(ang)
    s = dict(shape)
    if shape["kind"] in ("path", "fill"):
        s["pts"] = [(at[0] + x * ca - y * sa, at[1] + x * sa + y * ca)
                    for x, y in shape["pts"]]
    else:
        x, y = shape["c"]
        s["c"] = (at[0] + x * ca - y * sa, at[1] + x * sa + y * ca)
    return s


# ---------------------------------------------------------------------------
# الزنبق
# ---------------------------------------------------------------------------


def lily_petal(L=100.0, Wd=17.0, bend=6.0, recurve=0.12, wave=0.04,
               w=WO, veins=True):
    """
    بتلة زنبق: رمحية مدبّقة، منعكفة الطرف قليلاً، بعِرق أوسط ظاهر.

    ملاحظات على الأبعاد (Wd هو *نصف* العرض):
      - نصف عرض 0.34·L كان يُنتج وتداً حادّاً لا بتلة؛ النسبة الطبيعية
        لبتلة الزنبق ≈ 0.17·L (أي عرض كامل ثلث الطول).
      - الانعكاف القوي (0.30) مع انحناء جانبي كبير كان يشوّه المُحيط؛
        يُشترط أن يبقى نصف العرض أصغر بكثير من نصف قطر انحناء المحور،
        وإلا انثنت الحافة الداخلية على نفسها.
    """
    def axis(t):
        return (bend * math.sin(math.pi * t) + recurve * L * t ** 3 * 0.20,
                -L * t)

    base = taper_fn(Wd, 0.85, 1.02)

    def half(t):
        return base(t) * (1 + wave * math.sin(TAU * t) * math.sin(math.pi * t))

    out = [ribbon(axis, half, n=110, w=w)]
    if veins:
        out.append(P([axis(0.03 + 0.93 * i / 16) for i in range(17)],
                     smooth=True, w=WV))
        for off in (-0.45, 0.45):
            pts = []
            for i in range(15):
                t = 0.10 + 0.80 * i / 14
                ax, ay = axis(t)
                e = 1e-3
                p0, p1 = axis(max(0, t - e)), axis(min(1, t + e))
                dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                m = math.hypot(dx, dy) or 1.0
                nx, ny = -dy / m, dx / m
                h = base(t) * off
                pts.append((ax + nx * h, ay + ny * h))
            out.append(P(pts, smooth=True, w=WV))
    return out


def lily_flower(R=100.0, rot=0.0, petals=6, stamens=6):
    """
    زنبق: ست بتلات عريضة موزّعة بانتظام + أسدية واضحة بمآبر مستطيلة.

    تصحيحات على المحاولة الأولى:
      - البتلة كانت بعرض 0.26·R فتبدو ورقة؛ الزنبق بتلاته عريضة (0.34·R).
      - البتلات الداخلية كانت مُزاحة في نصف القطر فتختفي خلف الخارجية.
      - الأسدية كانت طويلة فتبدو شوائب وسط البتلات؛ طولها الآن 0.46·R
        والمئبر مستطيل واضح عند الطرف.
    """
    out = []
    for k in range(petals):
        a = TAU * k / petals + rot
        # انحناء بالإشارة نفسها لكل البتلات: تبادل الإشارة كان يجعل
        # نصف البتلات معكوس الشكل فتبدو الزهرة غير متّسقة
        for s in lily_petal(R, R * 0.22, bend=R * 0.055,
                            recurve=0.12, wave=0.04, w=WO):
            out.append(_rot_shift(s, a, polar(R * 0.11, a - math.pi / 2)))

    # الأسدية في الفراغات بين البتلات.
    # البتلة الموضوعة بزاوية a تتّجه نحو (a − 90°)، فمركز الفراغ بينها
    # وبين تاليتها عند (a − 90° + 30°) = (a − 60°).
    # استخدام (a + 30°) كان يجعل كل سداة تنطبق على بتلة تماماً فتختفي.
    for k in range(stamens):
        a = TAU * k / petals + rot - math.pi / 3
        r_tip = R * 0.62          # يتجاوز أعرض موضع في البتلة فيظهر المئبر
        base = polar(R * 0.05, a)
        mid = polar(R * 0.26, a + 0.13)
        tip = polar(r_tip, a + 0.05)
        out.append(P([base, mid, tip], smooth=True, w=WV))
        th = math.atan2(tip[1] - mid[1], tip[0] - mid[0])
        anther = ribbon(lambda t: (0.0, -R * 0.115 * t),
                        taper_fn(R * 0.032, 1.05, 1.05), n=24, w=WI)
        out.append(_rot_shift(anther, th + math.pi / 2, tip))

    # المدقّة
    out.append(CIRC((0, 0), R * 0.055, w=WI))
    out.append(P([(0, 0), polar(R * 0.30, rot + math.radians(100))],
                 smooth=False, w=WV))
    return out


def lily_leaf(L=110.0, Wd=20.0, bend=8.0, w=WO, veins=5):
    """ورقة زنبق: رمحية طويلة بعِرق أوسط وعروق موازية."""
    base = taper_fn(Wd, 0.95, 1.10)

    def axis(t):
        return (bend * math.sin(math.pi * t), -L * t)

    out = [ribbon(axis, base, n=100, w=w)]
    out.append(P([axis(0.03 + 0.93 * i / 16) for i in range(17)],
                 smooth=True, w=WV))
    for off in (-0.52, 0.52, -0.26, 0.26):
        pts = []
        for i in range(14):
            t = 0.08 + 0.84 * i / 13
            ax, ay = axis(t)
            e = 1e-3
            p0, p1 = axis(max(0, t - e)), axis(min(1, t + e))
            dx, dy = p1[0] - p0[0], p1[1] - p0[1]
            m = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / m, dx / m
            h = base(t) * off
            pts.append((ax + nx * h, ay + ny * h))
        out.append(P(pts, smooth=True, w=WV))
    return out
