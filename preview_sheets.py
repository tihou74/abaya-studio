#!/usr/bin/env python3
"""
مُحوّل SVG -> PNG بمكتبة Python القياسية فقط (بلا أي اعتماديات).
يُنتج "أوراق معاينة" مُجمّعة بأبعاد أقل من 2000 بكسل عمداً،
لتفادي حد الأبعاد في طلبات الصور المتعددة.

التشغيل:  python3 preview_sheets.py
"""

import json
import math
import re
import struct
import sys
import zlib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# المجموعة افتراضياً الأولى؛ ويمكن تمرير مجموعة أخرى:
#   python3 preview_sheets.py art index_art.json preview_art
_A = sys.argv[1:] if len(sys.argv) > 1 else []
SVG_DIR = ROOT / (_A[0] if len(_A) > 0 else "svg")
INDEX = ROOT / (_A[1] if len(_A) > 1 else "index.json")
OUT = ROOT / (_A[2] if len(_A) > 2 else "preview")
NS = "{http://www.w3.org/2000/svg}"

SS = 3            # معامل الإفراط في العيّنات (للتنعيم)
NUM = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")

# حدّ صلب لأبعاد أي PNG يُنتجه المشروع.
#
# طلبات الصور المتعدّدة تُرفض إذا تجاوز أي بُعد 2000 بكسل، والرفض يأتي
# *بعد* انتهاء العمل كله: الصورة تُرسم، ثم تُرفض قراءتها، فتضيع الجلسة
# بأكملها. حدث ذلك فعلاً عند معاينة تخطيط 4.0×12.0 إنش بدقّة 300 DPI
# (‏1200×3600 بكسل) — فالبُعد الطويل وحده كان 3600.
#
# لذلك الحدّ مفروض هنا، في `write_png`، وهي نقطة الاختناق التي يمرّ بها
# كل PNG في المشروع. الحارس في `zoom_preview.py` كان اختيارياً وموضعياً،
# فتجاوزه أول سكربت جديد لم يستعمله.
MAX_PX = 2000


def fit_rows(w, h, rows, limit=MAX_PX):
    """
    يُصغّر صورة رمادية (قائمة bytearray) لتدخل حدّ `limit` في كلّ بُعد.

    يُعيد (w, h, rows) كما هي إن كانت داخل الحدّ أصلاً، وإلا يُصغّرها
    بمتوسّط صندوقي بمعامل صحيح — فيبقى الخطّ الرفيع مرئياً بدل أن
    يتقطّع كما يحدث مع أخذ العيّنة الأقرب.
    """
    if max(w, h) <= limit:
        return w, h, rows
    factor = -(-max(w, h) // limit)          # ceil
    w2, h2 = max(1, w // factor), max(1, h // factor)
    inv = 1.0 / (factor * factor)
    out = []
    for y in range(h2):
        row = bytearray(w2)
        src = rows[y * factor:y * factor + factor]
        for x in range(w2):
            x0 = x * factor
            tot = 0
            for r in src:
                tot += sum(r[x0:x0 + factor])
            row[x] = min(255, int(tot * inv))
        out.append(row)
    return w2, h2, out


# --------------------------------------------------------------------------
# كاتب PNG (رمادي 8-بت)
# --------------------------------------------------------------------------


def write_png(path, w, h, rows, limit=MAX_PX):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    if max(w, h) > limit:
        ow, oh = w, h
        w, h, rows = fit_rows(w, h, rows, limit)
        print(f"   ! {path.name}: {ow}x{oh} يتجاوز {limit} بكسل "
              f"— صُغِّرت إلى {w}x{h} لتكون قابلة للقراءة")

    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6))
           + chunk(b"IEND", b""))
    path.write_bytes(png)
    return w, h


# --------------------------------------------------------------------------
# قراءة SVG وتحويله إلى قطع خطية
# --------------------------------------------------------------------------


def flatten_cubic(p0, c1, c2, p3):
    span = (math.dist(p0, c1) + math.dist(c1, c2) + math.dist(c2, p3))
    n = max(3, min(28, int(span / 2.5)))
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        x = (u ** 3 * p0[0] + 3 * u * u * t * c1[0]
             + 3 * u * t * t * c2[0] + t ** 3 * p3[0])
        y = (u ** 3 * p0[1] + 3 * u * u * t * c1[1]
             + 3 * u * t * t * c2[1] + t ** 3 * p3[1])
        out.append((x, y))
    return out


def parse_d(d):
    """يدعم M / L / C / Z المطلقة فقط (وهو ما يُنتجه المولّد)."""
    polys = []
    cur = []
    start = None
    pos = None
    i = 0
    tokens = re.findall(r"[MLCZ]|-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", d)
    while i < len(tokens):
        t = tokens[i]
        if t == "M":
            if len(cur) > 1:
                polys.append(cur)
            pos = (float(tokens[i + 1]), float(tokens[i + 2]))
            start = pos
            cur = [pos]
            i += 3
        elif t == "L":
            pos = (float(tokens[i + 1]), float(tokens[i + 2]))
            cur.append(pos)
            i += 3
        elif t == "C":
            c1 = (float(tokens[i + 1]), float(tokens[i + 2]))
            c2 = (float(tokens[i + 3]), float(tokens[i + 4]))
            p3 = (float(tokens[i + 5]), float(tokens[i + 6]))
            cur.extend(flatten_cubic(pos, c1, c2, p3))
            pos = p3
            i += 7
        elif t == "Z":
            if start:
                cur.append(start)
            polys.append(cur)
            cur = [start] if start else []
            i += 1
        else:
            i += 1
    if len(cur) > 1:
        polys.append(cur)
    return polys


def load_svg(path):
    """
    يُرجع (قائمة (مسار, سماكة), عرض, ارتفاع).
    يدعم المجموعتين: سماكة واحدة على المجموعة الرئيسية (المجموعة الأولى)،
    أو مجموعات متداخلة بسماكات مختلفة (المجموعة الفنّية).
    """
    root = ET.parse(path).getroot()
    vw, vh = [float(v) for v in root.get("viewBox").split()[2:]]
    g = root.find(f"{NS}g")
    tr = g.get("transform", "")
    m = re.search(r"translate\(([-\d.eE+]+),([-\d.eE+]+)\)", tr)
    tx, ty = (float(m.group(1)), float(m.group(2))) if m else (0.0, 0.0)
    m = re.search(r"scale\(([-\d.eE+]+)\)", tr)
    s = float(m.group(1)) if m else 1.0
    root_sw = float(g.get("stroke-width", 1) or 1)

    out = []

    def emit(el, sw, filled=False):
        tag = el.tag.replace(NS, "")
        if tag == "path":
            for poly in parse_d(el.get("d", "")):
                pts = [(x * s + tx, y * s + ty) for x, y in poly]
                out.append((pts, sw * s, filled))
        elif tag == "circle":
            cx, cy, r = (float(el.get("cx")), float(el.get("cy")),
                         float(el.get("r")))
            cx, cy, r = cx * s + tx, cy * s + ty, r * s
            ring = [(cx + r * math.cos(math.tau * k / 64),
                     cy + r * math.sin(math.tau * k / 64)) for k in range(65)]
            if filled:
                # نقطة مُعبّأة: تُرسم كقرص مصمت بسماكة تساوي قطرها
                out.append(([(cx, cy), (cx + 0.01, cy)], r * 2, False))
            else:
                out.append((ring, sw * s, False))

    for child in g:
        if child.tag.replace(NS, "") == "g":
            sub_sw = float(child.get("stroke-width", root_sw) or root_sw)
            is_filled = (child.get("fill") or "none") != "none"
            for el in child.iter():
                emit(el, sub_sw, is_filled)
        else:
            emit(child, root_sw)
    return out, vw, vh


# --------------------------------------------------------------------------
# الرسم على شبكة بكسلات
# --------------------------------------------------------------------------


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.buf = bytearray(b"\xff" * (w * h))

    def dot(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.buf[y * self.w + x] = 0

    def disc(self, cx, cy, r):
        ri = int(math.ceil(r))
        for dy in range(-ri, ri + 1):
            for dx in range(-ri, ri + 1):
                if dx * dx + dy * dy <= r * r:
                    self.dot(cx + dx, cy + dy)

    def thick_line(self, p0, p1, r):
        x0, y0 = p0
        x1, y1 = p1
        n = max(1, int(max(abs(x1 - x0), abs(y1 - y0))) + 1)
        for i in range(n + 1):
            t = i / n
            self.disc(int(round(x0 + (x1 - x0) * t)),
                      int(round(y0 + (y1 - y0) * t)), r)

    def fill_poly(self, pts):
        """
        تعبئة مضلّع بالمسح السطري وقاعدة **nonzero** — وهي القاعدة
        الافتراضية في SVG.

        استخدام الزوجي-الفردي هنا كان خطأً يُظهر فراغات بيضاء عند تقاطع
        الشكل مع نفسه (كالحلزون الملفوف)، مع أن الملف نفسه يُرسم مصمتاً
        في أي عارض SVG. أي أن المعاينة كانت تكذب على الناظر.
        """
        if len(pts) < 3:
            return
        ys = [p[1] for p in pts]
        y_lo = max(0, int(math.floor(min(ys))))
        y_hi = min(self.h - 1, int(math.ceil(max(ys))))
        n = len(pts)
        for y in range(y_lo, y_hi + 1):
            yc = y + 0.5
            xs = []
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                if y1 <= yc < y2:
                    xs.append((x1 + (yc - y1) / (y2 - y1) * (x2 - x1), 1))
                elif y2 <= yc < y1:
                    xs.append((x1 + (yc - y1) / (y2 - y1) * (x2 - x1), -1))
            if not xs:
                continue
            xs.sort()
            row = y * self.w
            wind = 0
            for idx in range(len(xs) - 1):
                wind += xs[idx][1]
                if wind == 0:
                    continue
                xa = max(0, int(math.ceil(xs[idx][0] - 0.5)))
                xb = min(self.w - 1, int(math.floor(xs[idx + 1][0] - 0.5)))
                for x in range(xa, xb + 1):
                    self.buf[row + x] = 0

    def downsample(self, factor):
        w2, h2 = self.w // factor, self.h // factor
        rows = []
        inv = 1.0 / (factor * factor)
        for y in range(h2):
            row = bytearray(w2)
            for x in range(w2):
                tot = 0
                for dy in range(factor):
                    base = (y * factor + dy) * self.w + x * factor
                    tot += sum(self.buf[base:base + factor])
                row[x] = int(tot * inv)
            rows.append(row)
        return w2, h2, rows


def render_cell(canvas, polys, vw, vh, ox, oy, cw, ch):
    """يرسم رسمة واحدة داخل خلية (ox,oy,cw,ch) بإحداثيات الـ supersample."""
    k = min(cw / vw, ch / vh)
    dx = ox + (cw - vw * k) / 2
    dy = oy + (ch - vh * k) / 2
    for poly, sw, filled in polys:
        mapped = [(px * k + dx, py * k + dy) for px, py in poly]
        if filled:
            canvas.fill_poly(mapped)
            continue
        r = max(0.8, sw * k / 2)
        for a, b in zip(mapped, mapped[1:]):
            canvas.thick_line(a, b, r)


def frame(canvas, ox, oy, cw, ch):
    for x in range(int(cw)):
        canvas.dot(int(ox + x), int(oy))
        canvas.dot(int(ox + x), int(oy + ch - 1))
    for y in range(int(ch)):
        canvas.dot(int(ox), int(oy + y))
        canvas.dot(int(ox + cw - 1), int(oy + y))


def build_sheet(files, cols, cell_w, cell_h, out_path, draw_frames=True):
    rows_n = math.ceil(len(files) / cols)
    W, H = cols * cell_w, rows_n * cell_h
    cv = Canvas(W * SS, H * SS)
    for idx, f in enumerate(files):
        r, c = divmod(idx, cols)
        polys, vw, vh = load_svg(SVG_DIR / f)
        ox, oy = c * cell_w * SS, r * cell_h * SS
        pad = 5 * SS
        if draw_frames:
            frame(cv, ox + 1, oy + 1, cell_w * SS - 2, cell_h * SS - 2)
        render_cell(cv, polys, vw, vh,
                    ox + pad, oy + pad, cell_w * SS - 2 * pad, cell_h * SS - 2 * pad)
    w2, h2, rows = cv.downsample(SS)
    # الأبعاد المُعادة هي ما كُتب فعلاً — `write_png` قد يُصغّر أكثر
    # إن تجاوز المقاس حدّ MAX_PX.
    return write_png(out_path, w2, h2, rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    talls = [d["file"] for d in data if d.get("tall")]
    squares = [d["file"] for d in data if not d["wide"] and not d.get("tall")]
    wides = [d["file"] for d in data if d["wide"]]

    made = []

    # الأشرطة الرأسية تُعرض في صف واحد بخلايا طويلة
    per = 8
    for n, i in enumerate(range(0, len(talls), per), start=1):
        grp = talls[i:i + per]
        p = OUT / f"sheet_tall_{n}.png"
        w, h = build_sheet(grp, len(grp), 145, 640, p)
        made.append((p.name, w, h, len(grp)))
        print(f"{p.name}  {w}x{h}")

    # في المجموعة الرأسية تكون "wide" ألواحاً طويلة لا أشرطة أفقية
    if talls:
        per = 4
        for n, i in enumerate(range(0, len(wides), per), start=1):
            grp = wides[i:i + per]
            p = OUT / f"sheet_panel_{n}.png"
            w, h = build_sheet(grp, len(grp), 290, 640, p)
            made.append((p.name, w, h, len(grp)))
            print(f"{p.name}  {w}x{h}")
        wides = []
    # المجموعات الصغيرة تُعرض بخلايا أكبر لتُرى التفاصيل،
    # مع البقاء دائماً تحت 2000 بكسل في كل بُعد.
    if len(squares) <= 90:
        cols, cell, per = 4, 280, 16
    else:
        cols, cell, per = 6, 200, 48
    for n, i in enumerate(range(0, len(squares), per), start=1):
        p = OUT / f"sheet_units_{n}.png"
        w, h = build_sheet(squares[i:i + per], cols, cell, cell, p)
        made.append((p.name, w, h, len(squares[i:i + per])))
        print(f"{p.name}  {w}x{h}")

    per = 14            # عمودان × 7 صفوف
    for n, i in enumerate(range(0, len(wides), per), start=1):
        p = OUT / f"sheet_borders_{n}.png"
        w, h = build_sheet(wides[i:i + per], 2, 600, 170, p)
        made.append((p.name, w, h, len(wides[i:i + per])))
        print(f"{p.name}  {w}x{h}")

    bad = [m for m in made if m[1] > 2000 or m[2] > 2000]
    print(f"\n{len(made)} ورقة معاينة | تجاوزت 2000 بكسل: {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
