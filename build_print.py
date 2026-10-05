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
       direction: ltr; color: #111; background: #f4f4f4; }
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
            f'<span>Page {pageno} of {total}</span></div>'
            f'<div class="grid" style="grid-template-columns: repeat({cols},1fr)">'
            f'{cells}</div>'
            f'<div class="foot"><span>{sub}</span>'
            f'<span>Scalable vector SVG</span></div></section>')


def strip_page(items, heading, pageno, total, svg_dir, height_mm=235):
    cells = "".join(
        f'<div class="cell" style="flex:1;min-width:0">'
        f'<img src="../{svg_dir}/{it["file"]}" '
        f'style="height:{height_mm}mm;width:auto;margin:0 auto;display:block">'
        f'<div class="cap"><b>{it["num"]:03d}</b> — {it["title"]}</div></div>'
        for it in items)
    return (f'<section class="page">'
            f'<div class="head"><b>{heading}</b>'
            f'<span>Page {pageno} of {total}</span></div>'
            f'<div style="display:flex;gap:6mm;justify-content:center;'
            f'align-items:flex-start">{cells}</div>'
            f'<div class="foot"><span>Vertical band ≈ {height_mm} mm tall</span>'
            f'<span>Vector SVG</span></div></section>')


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
        body.append(strip_page(grp, f"{heading} — panels", n, total, svg_dir,
                               height_mm=230))
    for grp in up:
        n += 1
        body.append(grid_page(grp, units_cols, f"{heading} — single motifs",
                              "Motifs to place freely", n, total, svg_dir))

    html = (f'<!DOCTYPE html>\n<html lang="en" dir="ltr">\n<head>\n'
            f'<meta charset="utf-8">\n<title>{heading}</title>\n'
            f"<style>{CSS}</style>\n</head>\n<body>\n"
            + "\n".join(body) + "\n</body>\n</html>\n")
    (OUT / name).write_text(html, encoding="utf-8")
    return total


INTRO_BANDS = """
<div class="note">
<h1>Vertical edge bands — embroidery patterns</h1>
<p>A vertical format for the front edge of an abaya, with filled black dots,
leaves hatched with lines (satin stitch), hanging strands and ornate
rosettes.</p>
<ul>
<li>Print at <b>A4</b> and <b>100%</b> scale — turn off "fit to page",
or the real size on paper will change.</li>
<li>Each band is ≈ <b>235 mm</b> tall. For a longer edge, print several
copies and join them end to end — the pattern is designed to continue.</li>
<li><b>Black dots</b> are stitched as French knots or beads.</li>
<li><b>Lines inside leaves</b> are satin stitch, and show needle direction.</li>
<li>Rosettes and clusters are single motifs to place as you like.</li>
</ul>
</div>
"""

INTRO_DAMASK = """
<div class="note">
<h1>Solid ornament, classic borders & pendants</h1>
<p>Solid floral sprigs with graded stroke weight and a scroll at the base,
symmetrical classic borders (damask, arabesque, Greek key, spiral meander),
and pendant panels.</p>
<ul>
<li>Print at <b>A4</b> and <b>100%</b> scale.</li>
<li><b>Sprigs and borders</b> suit the front edge and sleeves — ≈ 235 mm tall.</li>
<li><b>Pendant panels</b> suit a full area: shoulder, back, or the width of
the edge.</li>
<li>The ornament is <b>solid</b>: stitch it as a filled area (satin), cut it
from fabric and applique it, or use it as a stencil for fabric printing.</li>
<li>Want <b>outline only</b>, with no fill? See the note in `README.md` —
a one-line change in the generator.</li>
</ul>
</div>
"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.html"):
        old.unlink()
    a = build("bands.html", "Vertical edge bands", INTRO_BANDS,
              "index_bands.json", "bands", units_cols=4, units_per_page=12)
    b = build("damask.html", "Solid & classic ornament", INTRO_DAMASK,
              "index_damask.json", "damask", units_cols=4, units_per_page=8)
    print(f"print/bands.html  — {a} pages")
    print(f"print/damask.html — {b} pages")


if __name__ == "__main__":
    main()
