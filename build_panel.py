#!/usr/bin/env python3
"""
يجهّز بيانات النقشات للوحة التصميم.

لماذا تُضمَّن النقشات في ملف JavaScript بدل تحميلها من المجلدات:
  اللوحة تُفتح بالنقر المزدوج على الملف (file://)، وفي هذه الحالة يمنع
  المتصفح دالة fetch من قراءة الملفات المحلية (قيود CORS). أمّا وسم
  <script src="..."> فيعمل من file:// بلا مشاكل. فتصبح اللوحة ملفاً
  واحداً يُفتح بلا إنترنت وبلا تشغيل أي خادم.

ويُستبدل اللون الأسود بـ currentColor حتى يكفي تغيير خاصية color
في CSS لتلوين النقشة كاملةً (الخطوط والمساحات المصمتة معاً).

التشغيل:  python3 build_panel.py
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "panel"

SOURCES = [
    ("index_bands.json", "bands"),
    ("index_damask.json", "damask"),
]

RE_VIEWBOX = re.compile(r'viewBox="0 0 ([\d.]+) ([\d.]+)"')
RE_BODY = re.compile(r"<svg[^>]*>(.*)</svg>", re.S)
RE_TITLE = re.compile(r"<title>.*?</title>", re.S)


def extract(path: Path):
    text = path.read_text(encoding="utf-8")
    m = RE_VIEWBOX.search(text)
    if not m:
        raise ValueError(f"viewBox مفقود في {path.name}")
    w, h = float(m.group(1)), float(m.group(2))
    body = RE_BODY.search(text).group(1)
    body = RE_TITLE.sub("", body).strip()
    # لون واحد يتحكّم فيه CSS
    body = body.replace('stroke="#000000"', 'stroke="currentColor"')
    body = body.replace('fill="#000000"', 'fill="currentColor"')
    # تقليص المسافات الزائدة
    body = re.sub(r">\s+<", "><", body)
    return w, h, body


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items = []
    for index_file, folder in SOURCES:
        data = json.loads((ROOT / index_file).read_text(encoding="utf-8"))
        for d in data:
            p = ROOT / folder / d["file"]
            w, h, body = extract(p)
            items.append({
                "id": d["file"].split("_")[0],
                "file": d["file"],
                "name": d["title"],
                "fam": d["family"],
                "set": folder,
                "w": round(w, 1),
                "h": round(h, 1),
                "svg": body,
            })

    payload = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    js = ("/* بيانات النقشات — مُولّدة آلياً بـ build_panel.py. لا تُحرّر يدوياً. */\n"
          "window.MOTIFS = " + payload + ";\n")
    target = OUT / "motifs-data.js"
    target.write_text(js, encoding="utf-8")

    fams = {}
    for it in items:
        fams[it["fam"]] = fams.get(it["fam"], 0) + 1
    print(f"تم تجهيز {len(items)} نقشة في {target.relative_to(ROOT)}"
          f"  ({target.stat().st_size / 1024:.0f} ك.ب)")
    for f, c in fams.items():
        print(f"  - {f}: {c}")


if __name__ == "__main__":
    main()
