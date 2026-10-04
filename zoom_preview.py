#!/usr/bin/env python3
"""
معاينة مُكبّرة لملفات محدّدة — للحكم على التفاصيل.

الحكم على صور مصغّرة عرضها 145 بكسل لرسمة مقاسها 200×700 لا يكشف العيوب:
التفاصيل تضيع تماماً. هذه الأداة ترسم ملفات قليلة بمقاس كبير
مع البقاء تحت 2000 بكسل في كل بُعد.

التشغيل:
  python3 zoom_preview.py <مجلد> <عرض_الخلية> <ارتفاع_الخلية> <ملف> [ملف ...]
مثال:
  python3 zoom_preview.py damask 500 1600 D001_vine_01.svg D004_vine_04.svg
"""

import sys
from pathlib import Path

import preview_sheets as PS

ROOT = Path(__file__).resolve().parent


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return 1
    src = ROOT / sys.argv[1]
    cw, ch = int(sys.argv[2]), int(sys.argv[3])
    files = sys.argv[4:]

    PS.SVG_DIR = src
    out_dir = ROOT / "preview_zoom"
    out_dir.mkdir(parents=True, exist_ok=True)

    cols = len(files)
    if cols * cw > 2000 or ch > 2000:
        print(f"!! الأبعاد {cols * cw}x{ch} تتجاوز 2000 بكسل — قلّل العدد أو المقاس")
        return 1

    out = out_dir / f"zoom_{src.name}_{'_'.join(f[:4] for f in files)}.png"
    w, h = PS.build_sheet(files, cols, cw, ch, out)
    print(f"{out.relative_to(ROOT)}  {w}x{h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
