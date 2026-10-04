#!/usr/bin/env python3
"""
بناء صفحات طباعة A4 للمجموعتين.

يُنتج:
  print/bands.html   — أشرطة الأطراف الرأسية (نقوش تطريز)
  print/damask.html  — الزخرفة المصمتة والأشرطة الكلاسيكية والمتدلّيات

التشغيل:  python3 build_print.py
ثم افتح الملف في المتصفح واطبع (Ctrl+P) بمقاس A4 ومقياس 100%
وبدون «تحجيم لملاءمة الصفحة».
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
.grid { display: grid; gap: 4mm; }
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


def chunk(seq, n):
    return [seq[i:i + n] for i in range(0, len(seq), n)]


def grid_page(items, cols, heading, sub, pageno, total, svg_dir):
    cells = "".join(
        f'<div class="cell"><img src="../{svg_dir}/{it["file"]}" '
        f'alt="{it["num"]}">'
        f'<div class="cap"><b>{it["num"]:03d}</b> — {it["title"]}</div></div>'
        for it in items)
    return (f'<section class="page">'
            f'<div class="head"><b>{heading}</b>'
            f'<span>صفحة {pageno} من {total}</span></div>'
            f'<div class="grid" style="grid-template-columns: repeat({cols},1fr)">'
            f'{cells}</div>'
            f'<div class="foot"><span>{sub}</span>'
            f'<span>SVG متجهي قابل للتكبير</span></div></section>')


def strip_page(items, heading, pageno, total, svg_dir, height_mm=235):
    cells = "".join(
        f'<div class="cell" style="flex:1;min-width:0">'
        f'<img src="../{svg_dir}/{it["file"]}" '
        f'style="height:{height_mm}mm;width:auto;margin:0 auto;display:block">'
        f'<div class="cap"><b>{it["num"]:03d}</b> — {it["title"]}</div></div>'
        for it in items)
    return (f'<section class="page">'
            f'<div class="head"><b>{heading}</b>'
            f'<span>صفحة {pageno} من {total}</span></div>'
            f'<div style="display:flex;gap:6mm;justify-content:center;'
            f'align-items:flex-start">{cells}</div>'
            f'<div class="foot"><span>شريط رأسي بطول ≈ {height_mm} مم</span>'
            f'<span>SVG متجهي</span></div></section>')


def build(name, heading, intro, index_file, svg_dir,
          talls_per_page=2, wides_per_page=2, units_cols=3, units_per_page=9):
    data = json.loads((ROOT / index_file).read_text(encoding="utf-8"))
    talls = [d for d in data if d.get("tall")]
    wides = [d for d in data if d.get("wide")]
    units = [d for d in data if not d.get("tall") and not d.get("wide")]

    tp = chunk(talls, talls_per_page)
    wp = chunk(wides, wides_per_page)
    up = chunk(units, units_per_page)
    total = len(tp) + len(wp) + len(up)

    body = [intro]
    n = 0
    for grp in tp:
        n += 1
        body.append(strip_page(grp, heading, n, total, svg_dir))
    for grp in wp:
        n += 1
        body.append(strip_page(grp, f"{heading} — ألواح", n, total, svg_dir,
                               height_mm=230))
    for grp in up:
        n += 1
        body.append(grid_page(grp, units_cols, f"{heading} — عناصر منفردة",
                              "عناصر تُوزَّع بحرّية", n, total, svg_dir))

    html = (f'<!DOCTYPE html>\n<html lang="ar" dir="rtl">\n<head>\n'
            f'<meta charset="utf-8">\n<title>{heading}</title>\n'
            f"<style>{CSS}</style>\n</head>\n<body>\n"
            + "\n".join(body) + "\n</body>\n</html>\n")
    (OUT / name).write_text(html, encoding="utf-8")
    return total


INTRO_BANDS = """
<div class="note">
<h1>أشرطة أطراف رأسية — نقوش تطريز</h1>
<p>صيغة رأسية تناسب طرف العباية الأمامي، بنقاط مُعبّأة سوداء،
وأوراق محشوّة بخطوط (تطريز ساتان)، وسلاسل معلّقة، ووريدات مزخرفة.</p>
<ul>
<li>اطبع بمقاس <b>A4</b> ومقياس <b>100%</b> — عطّل «تحجيم لملاءمة الصفحة»،
وإلا تغيّر المقاس الفعلي على الورق.</li>
<li>الشريط الواحد بطول ≈ <b>235 مم</b>. لطرف أطول اطبع عدة نسخ وصِلها
طرفاً بطرف — النمط مُصمَّم ليتّصل.</li>
<li><b>النقاط السوداء</b> تُطرَّز عُقَداً فرنسية (French knots) أو خرزاً.</li>
<li><b>الخطوط داخل الأوراق</b> تُطرَّز ساتان، وهي دليل اتجاه الإبرة.</li>
<li>الوريدات والعناقيد عناصر منفردة تُوزَّع كما تشاء.</li>
</ul>
</div>
"""

INTRO_DAMASK = """
<div class="note">
<h1>زخرفة مصمتة وأشرطة كلاسيكية ومتدلّيات</h1>
<p>فروع زهرية مصمتة بتدرّج سماكة وحلزون في أسفلها، وأشرطة كلاسيكية
متناظرة (داماسك، أرابيسك، مفتاح يوناني، فرط لولبي)، وألواح متدلّيات.</p>
<ul>
<li>اطبع بمقاس <b>A4</b> ومقياس <b>100%</b>.</li>
<li><b>الفروع والأشرطة</b> للطرف الأمامي والأكمام — بطول ≈ 235 مم.</li>
<li><b>ألواح المتدلّيات</b> لمساحة كاملة: الكتف أو الظهر أو عرض الطرف.</li>
<li>الزخرفة <b>مصمتة</b>: تُطرَّز مساحةً ممتلئة (ساتان) أو تُقص قماشاً
وتُخاط (أبليك)، أو تُستخدم كاستنسل للطباعة على القماش.</li>
<li>تريدها <b>تحديداً فقط</b> بلا تعبئة؟ انظر الملاحظة في الدليل
(`README.md`) — تعديل سطر واحد في المولّد.</li>
</ul>
</div>
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.html"):
        old.unlink()
    a = build("bands.html", "أشرطة أطراف رأسية", INTRO_BANDS,
              "index_bands.json", "bands", units_cols=4, units_per_page=12)
    b = build("damask.html", "زخرفة مصمتة وكلاسيكية", INTRO_DAMASK,
              "index_damask.json", "damask", units_cols=4, units_per_page=8)
    print(f"print/bands.html  — {a} صفحة")
    print(f"print/damask.html — {b} صفحة")


if __name__ == "__main__":
    main()
