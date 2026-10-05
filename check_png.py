#!/usr/bin/env python3
"""
تحقّق من أبعاد ملفات PNG قبل قراءتها، وصغّر ما يتجاوز الحدّ.

لماذا؟ لأن قراءة صورة يتجاوز أحد أبعادها 2000 بكسل تُرفض، والرفض يأتي
بعد انتهاء العمل كله — فتضيع الجلسة. هذه الأداة تكشف المشكلة قبل وقوعها.

التشغيل:
  python3 check_png.py                      # يفحص كل PNG في المشروع
  python3 check_png.py preview_zoom         # يفحص مجلداً
  python3 check_png.py a.png b.png          # يفحص ملفات محدّدة
  python3 check_png.py --fix [هدف ...]      # يُصغّر المتجاوز في مكانه

رمز الخروج: 0 إذا كان الكل آمناً للقراءة، 1 إذا وُجد متجاوز (بدون --fix).
"""

import struct
import sys
import zlib
from pathlib import Path

import preview_sheets as PS

ROOT = Path(__file__).resolve().parent
LIMIT = PS.MAX_PX


def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("ليس ملف PNG")
    w, h = struct.unpack(">II", head[16:24])
    return w, h


def read_gray(path):
    """يقرأ PNG رمادي 8-بت غير متداخل — وهي الصيغة التي يُنتجها المشروع."""
    data = path.read_bytes()
    pos, idat = 8, b""
    w = h = depth = color = interlace = None
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
        pos += 12 + ln
    if (depth, color, interlace) != (8, 0, 0):
        raise ValueError(f"يُدعم الرمادي 8-بت غير المتداخل فقط "
                         f"(depth={depth} color={color} interlace={interlace})")

    raw = zlib.decompress(idat)
    stride = w + 1
    rows, prev = [], bytearray(w)
    for y in range(h):
        ft = raw[y * stride]
        line = bytearray(raw[y * stride + 1:y * stride + 1 + w])
        if ft == 1:
            for x in range(1, w):
                line[x] = (line[x] + line[x - 1]) & 0xFF
        elif ft == 2:
            for x in range(w):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif ft == 3:
            for x in range(w):
                left = line[x - 1] if x else 0
                line[x] = (line[x] + ((left + prev[x]) >> 1)) & 0xFF
        elif ft == 4:
            for x in range(w):
                a = line[x - 1] if x else 0
                b = prev[x]
                c = prev[x - 1] if x else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
        elif ft != 0:
            raise ValueError(f"مُرشِّح غير معروف: {ft}")
        rows.append(line)
        prev = line
    return w, h, rows


def targets(args):
    if not args:
        return sorted(ROOT.glob("**/*.png"))
    out = []
    for a in args:
        p = (ROOT / a) if not Path(a).is_absolute() else Path(a)
        if p.is_dir():
            out += sorted(p.glob("**/*.png"))
        elif p.exists():
            out.append(p)
        else:
            print(f"!! غير موجود: {a}")
    return out


def main():
    args = [a for a in sys.argv[1:] if a != "--fix"]
    fix = "--fix" in sys.argv[1:]

    files = targets(args)
    if not files:
        print("لا توجد ملفات PNG.")
        return 0

    over = []
    for p in files:
        rel = p.relative_to(ROOT) if ROOT in p.parents else p
        try:
            w, h = png_size(p)
        except Exception as e:
            print(f"!! {rel}: {e}")
            continue
        if max(w, h) > LIMIT:
            over.append((p, rel, w, h))
            print(f"!! {rel}  {w}x{h}  يتجاوز {LIMIT} بكسل — لا تقرأها")
        else:
            print(f"ok {rel}  {w}x{h}")

    if not over:
        print(f"\n{len(files)} ملفاً | الكل داخل حدّ {LIMIT} بكسل — آمنة للقراءة")
        return 0

    if not fix:
        print(f"\n{len(over)} من {len(files)} يتجاوز {LIMIT} بكسل. "
              f"شغّل: python3 check_png.py --fix")
        return 1

    print()
    for p, rel, w, h in over:
        try:
            ww, hh, rows = read_gray(p)
            nw, nh, nrows = PS.fit_rows(ww, hh, rows, LIMIT)
            PS.write_png(p, nw, nh, nrows)
            print(f"-> {rel}  {w}x{h}  صار  {nw}x{nh}")
        except Exception as e:
            print(f"!! {rel}: فشل التصغير — {e}")
            return 1
    print(f"\nصُغِّر {len(over)} ملفاً — الكل آمن للقراءة الآن")
    return 0


if __name__ == "__main__":
    sys.exit(main())
