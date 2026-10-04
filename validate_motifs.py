#!/usr/bin/env python3
"""
تدقيق برمجي لملفات SVG — بديل المراجعة البصرية لـ 200 صورة.
يفحص: صحة XML، وجود viewBox، أن الرسم "تحديد فقط" (fill=none + stroke)،
وأن الهندسة بالكامل داخل حدود الإطار، وعدم وجود إحداثيات تالفة (NaN/inf).

التشغيل:  python3 validate_motifs.py
"""

import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# افتراضياً المجموعة الأولى؛ ولفحص المجموعة الثانية:
#   python3 validate_motifs.py art index_art.json 78
_A = sys.argv[1:]
SVG_DIR = ROOT / (_A[0] if len(_A) > 0 else "svg")
INDEX = ROOT / (_A[1] if len(_A) > 1 else "index.json")
NS = "{http://www.w3.org/2000/svg}"
EXPECTED = int(_A[2]) if len(_A) > 2 else 200
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def parse_transform(t):
    tx = ty = 0.0
    s = 1.0
    m = re.search(r"translate\(\s*(-?[\d.eE+-]+)\s*,\s*(-?[\d.eE+-]+)\s*\)", t or "")
    if m:
        tx, ty = float(m.group(1)), float(m.group(2))
    m = re.search(r"scale\(\s*(-?[\d.eE+-]+)\s*\)", t or "")
    if m:
        s = float(m.group(1))
    return tx, ty, s


def path_points(d):
    """كل أزواج الإحداثيات في مسار مُطلق (M/C/L/Z فقط — وهو ما يُنتجه المولّد)."""
    nums = [float(x) for x in NUM_RE.findall(d)]
    if len(nums) % 2:
        nums = nums[:-1]
    return list(zip(nums[0::2], nums[1::2]))


def check(path):
    errs = []
    warns = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [f"XML غير صالح: {exc}"], []

    root = tree.getroot()
    vb = root.get("viewBox")
    if not vb:
        errs.append("viewBox مفقود — الرسم غير قابل للتكبير بشكل سليم")
        return errs, warns
    vx, vy, vw, vh = [float(v) for v in vb.split()]

    g = root.find(f"{NS}g")
    if g is None:
        errs.append("مجموعة <g> الرئيسية مفقودة")
        return errs, warns

    if g.get("fill") != "none":
        errs.append(f'fill يجب أن يكون "none" (القيمة: {g.get("fill")!r}) — المطلوب تحديد فقط')
    stroke = g.get("stroke")
    if not stroke or stroke == "none":
        errs.append(f"stroke مفقود (القيمة: {stroke!r})")

    tx, ty, s = parse_transform(g.get("transform"))
    if s <= 0:
        errs.append(f"مقياس غير صالح: {s}")
        return errs, warns

    # هل يحتوي الملف مجموعة مُعبّأة؟ (الزخرفة المصمتة قد تكون بلا أي خط)
    has_fill_group = any(
        sub.tag.replace(NS, "") == "g"
        and (sub.get("fill") or "none") != "none"
        for sub in g)

    # السماكات: إمّا واحدة على المجموعة الرئيسية، أو عدة مجموعات متداخلة
    widths = []
    if g.get("stroke-width"):
        widths.append(float(g.get("stroke-width")))
    for sub in g:
        if sub.tag.replace(NS, "") == "g" and sub.get("stroke-width"):
            widths.append(float(sub.get("stroke-width")))

    if widths:
        eff_max = max(w * s for w in widths)
        eff_min = min(w * s for w in widths)
        if not (0.5 <= eff_min and eff_max <= 3.5):
            warns.append(f"سماكة الخط الفعلية {eff_min:.2f}–{eff_max:.2f} "
                         f"خارج المدى المعتاد 0.5–3.5")
        eff = eff_max
    elif has_fill_group:
        # رسمة مصمتة بالكامل: لا تحتاج سماكة خط، والحدود بلا هامش خط
        eff = 0.0
    else:
        errs.append("لا سماكة خط ولا مجموعة مُعبّأة — الملف بلا محتوى مرئي")
        eff = 0.0

    xs, ys = [], []
    count = 0
    for el in g.iter():
        tag = el.tag.replace(NS, "")
        if tag == "path":
            d = el.get("d", "")
            if not d.strip():
                errs.append("مسار بقيمة d فارغة")
                continue
            if re.search(r"[mclsqtahvz]", d):
                warns.append("المسار يستخدم أوامر نسبية (صغيرة) — غير متوقع")
            pts = path_points(d)
            if not pts:
                errs.append("مسار بلا إحداثيات")
                continue
            for x, y in pts:
                if not (math.isfinite(x) and math.isfinite(y)):
                    errs.append("إحداثيات تالفة (NaN/inf)")
                xs.append(x)
                ys.append(y)
            count += 1
        elif tag == "circle":
            cx, cy, r = (float(el.get("cx", 0)), float(el.get("cy", 0)),
                         float(el.get("r", 0)))
            if r <= 0:
                errs.append("دائرة بنصف قطر غير موجب")
            xs += [cx - r, cx + r]
            ys += [cy - r, cy + r]
            count += 1

    if count == 0:
        errs.append("الملف لا يحتوي أي عنصر رسم")
        return errs, warns

    # الحدود بعد تطبيق الـ transform، مع احتساب نصف سماكة الخط
    pad = eff / 2
    x0, x1 = min(xs) * s + tx - pad, max(xs) * s + tx + pad
    y0, y1 = min(ys) * s + ty - pad, max(ys) * s + ty + pad
    tol = 1.0
    if x0 < vx - tol or y0 < vy - tol or x1 > vx + vw + tol or y1 > vy + vh + tol:
        errs.append(f"الرسم يخرج عن الإطار: "
                    f"[{x0:.1f},{y0:.1f},{x1:.1f},{y1:.1f}] خارج [0,0,{vw},{vh}]")

    # التحقق من أن الرسم يملأ الإطار بشكل معقول (ليس نقطة صغيرة في الوسط)
    fill_ratio = max((x1 - x0) / vw, (y1 - y0) / vh)
    if fill_ratio < 0.55:
        warns.append(f"الرسم صغير نسبياً داخل الإطار (نسبة {fill_ratio:.2f})")

    return errs, warns


def main():
    files = sorted(SVG_DIR.glob("*.svg"))
    print(f"فحص {len(files)} ملف في {SVG_DIR}\n")

    bad = 0
    warn_count = 0
    if len(files) != EXPECTED:
        print(f"!! العدد {len(files)} لا يساوي المطلوب {EXPECTED}")
        bad += 1

    # الرقم التسلسلي = أول مجموعة أرقام في اسم الملف (يدعم "001_" و "A001_")
    nums = [m.group(0) for m in (re.match(r"[A-Za-z]*(\d+)", f.name) for f in files)
            if m]
    if len(nums) != len(files):
        print("!! توجد ملفات بلا رقم تسلسلي في الاسم")
        bad += 1
    elif len(set(nums)) != len(nums):
        print("!! توجد أرقام مكرّرة في أسماء الملفات")
        bad += 1

    for f in files:
        errs, warns = check(f)
        if errs:
            bad += 1
            print(f"[خطأ]  {f.name}")
            for e in errs:
                print(f"        - {e}")
        for w in warns:
            warn_count += 1
            print(f"[تنبيه] {f.name}: {w}")

    idx = INDEX
    if idx.exists():
        data = json.loads(idx.read_text(encoding="utf-8"))
        missing = [d["file"] for d in data if not (SVG_DIR / d["file"]).exists()]
        if missing:
            bad += 1
            print(f"!! ملفات مذكورة في index.json وغير موجودة: {missing[:5]}")
        print(f"\nindex.json: {len(data)} مدخلة")

    print(f"\nالنتيجة: {len(files) - bad} سليم / {len(files)} | "
          f"أخطاء: {bad} | تنبيهات: {warn_count}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
