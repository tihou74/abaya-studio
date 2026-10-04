#!/usr/bin/env python3
"""
بناء صفحات طباعة A4 جاهزة من ملفات SVG.

يُنتج:
  print/catalog.html  — فهرس للاختيار (20 رسمة في الصفحة)
  print/trace.html    — مقاس الرسم على الورق (4 في الصفحة، ~88 مم)

التشغيل:  python3 build_print.py
ثم افتح الملف في المتصفح واطبع (Ctrl+P) بمقاس A4 وبدون "تحجيم لملاءمة الصفحة".
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "print"

CSS = """
@page { size: A4 portrait; margin: 10mm; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Noto Sans Arabic", "Segoe UI", Tahoma, sans-serif;
       direction: rtl; color: #111; background: #f4f4f4; }
.page { width: 190mm; min-height: 277mm; margin: 0 auto 6mm; padding: 0;
        background: #fff; page-break-after: always; break-after: page;
        display: flex; flex-direction: column; }
.page:last-child { page-break-after: auto; break-after: auto; }
.head { display: flex; justify-content: space-between; align-items: baseline;
        border-bottom: 0.4mm solid #111; padding-bottom: 2mm; margin-bottom: 4mm;
        font-size: 3.4mm; }
.head b { font-size: 4.2mm; }
.grid { display: grid; gap: 3mm; }
.cell { display: flex; flex-direction: column; align-items: center;
        page-break-inside: avoid; break-inside: avoid; }
.cell img { display: block; width: 100%; height: auto; }
.cap { font-size: 2.6mm; color: #444; margin-top: 1mm; text-align: center;
       line-height: 1.3; }
.cap b { color: #000; }
.foot { margin-top: auto; padding-top: 3mm; border-top: 0.3mm solid #bbb;
        font-size: 2.6mm; color: #666; display: flex; justify-content: space-between; }
.note { background: #fff; width: 190mm; margin: 0 auto 6mm; padding: 8mm;
        font-size: 3.4mm; line-height: 1.8; page-break-after: always;
        break-after: page; }
.note h1 { font-size: 6mm; margin: 0 0 4mm; }
.note li { margin-bottom: 2mm; }
@media print { body { background: #fff; } .page { margin: 0; box-shadow: none; } }
@media screen { .page, .note { box-shadow: 0 1mm 4mm rgba(0,0,0,.15); } }
"""


def page(items, cols, title, pageno, total_pages, img_w_mm=None):
    cells = []
    for it in items:
        cells.append(
            f'<div class="cell"><img src="../svg/{it["file"]}" alt="{it["num"]}">'
            f'<div class="cap"><b>{it["num"]:03d}</b> — {it["title"]}</div></div>'
        )
    style = f"grid-template-columns: repeat({cols}, 1fr);"
    return (
        f'<section class="page">'
        f'<div class="head"><b>{title}</b>'
        f'<span>صفحة {pageno} من {total_pages}</span></div>'
        f'<div class="grid" style="{style}">' + "".join(cells) + "</div>"
        f'<div class="foot"><span>رسومات أطراف العباية — تحديد فقط</span>'
        f'<span>SVG متجهي قابل للتكبير</span></div>'
        f"</section>"
    )


def chunk(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def build(name, square_per_page, square_cols, wide_per_page, heading, intro_html):
    data = json.loads((ROOT / "index.json").read_text(encoding="utf-8"))
    squares = [d for d in data if not d["wide"]]
    wides = [d for d in data if d["wide"]]

    sq_pages = chunk(squares, square_per_page)
    wd_pages = chunk(wides, wide_per_page)
    total = len(sq_pages) + len(wd_pages)

    body = [intro_html]
    n = 0
    for grp in sq_pages:
        n += 1
        body.append(page(grp, square_cols, f"{heading} — وحدات ومربعات", n, total))
    for grp in wd_pages:
        n += 1
        body.append(page(grp, 1, f"{heading} — أشرطة الأطراف", n, total))

    html = (
        f'<!DOCTYPE html>\n<html lang="ar" dir="rtl">\n<head>\n'
        f'<meta charset="utf-8">\n<title>{heading}</title>\n'
        f"<style>{CSS}</style>\n</head>\n<body>\n" + "\n".join(body) + "\n</body>\n</html>\n"
    )
    (OUT / name).write_text(html, encoding="utf-8")
    return total


INTRO_CATALOG = """
<div class="note">
<h1>فهرس رسومات أطراف العباية — 200 رسمة</h1>
<p>هذه صفحات <b>للاختيار</b>. كل رسمة تحديد خارجي فقط (بلا تلوين) بصيغة SVG متجهية،
فتُكبّر أو تُصغّر لأي مقاس بلا فقدان في الجودة.</p>
<ul>
<li><b>للطباعة بمقاس الرسم الحقيقي:</b> افتح <code>trace.html</code> واطبع بمقاس A4
مع تعطيل خيار «تحجيم لملاءمة الصفحة» (اجعل المقياس 100%).</li>
<li><b>لمقاس مخصّص:</b> افتح أي ملف من مجلد <code>svg/</code> في أي برنامج متجهي
(Illustrator / Inkscape / Affinity) وحدّد العرض بالمليمتر الذي تريده.</li>
<li><b>للنقل على العباية:</b> اطبع، ثم انقل الخطوط بورق كربون للأقمشة
أو بقلم مُعلّم يزول بالماء، ثم ارسم فوقها.</li>
<li>أشرطة الأطراف قابلة للتكرار بطول الطرف بوضع نسخ متتالية بنفس الارتفاع.</li>
</ul>
</div>
"""

INTRO_TRACE = """
<div class="note">
<h1>صفحات النقل — مقاس الرسم على الورق</h1>
<p>اطبع هذه الصفحات بمقاس <b>A4</b> و<b>مقياس 100%</b>
(عطّل «Fit to page» / «تحجيم لملاءمة الصفحة»)، وإلا تغيّر المقاس الفعلي.</p>
<ul>
<li>الوحدات المربعة بعرض ≈ <b>88 مم</b> للرسمة.</li>
<li>أشرطة الأطراف بعرض ≈ <b>190 مم</b> (عرض الصفحة كاملاً).</li>
<li>تريد مقاساً أكبر أو أصغر؟ استخدم ملف SVG مباشرة — فهو متجهي وغير محدود المقاس.</li>
</ul>
</div>
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a = build("catalog.html", 20, 4, 5, "فهرس الرسومات", INTRO_CATALOG)
    b = build("trace.html", 4, 2, 2, "صفحات النقل", INTRO_TRACE)
    print(f"print/catalog.html — {a} صفحة")
    print(f"print/trace.html   — {b} صفحة")


if __name__ == "__main__":
    main()
