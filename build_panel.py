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

    build_single_file(payload)


# ---------------------------------------------------------------------------
# نسخة الملف الواحد — للجوال
# ---------------------------------------------------------------------------

PANEL_SRC = "designer.html"
PANEL_ONE = "designer-single-file.html"
DATA_TAG = '<script src="motifs-data.js"></script>'


def inline_cut_images(html: str) -> str:
    """يستبدل src: "cuts/x.png" بـ data URL."""
    import base64
    import re as _re

    def rep(m):
        rel = m.group(1)
        f = OUT / rel
        if not f.exists():
            raise FileNotFoundError(f"صورة قصّة مفقودة: {rel}")
        b64 = base64.b64encode(f.read_bytes()).decode()
        kind = "png" if f.suffix.lower() == ".png" else "jpeg"
        print(f"   دُمجت {rel} ({f.stat().st_size / 1024:.0f} ك.ب)")
        return f'src: "data:image/{kind};base64,{b64}"'

    out, n = _re.subn(r'src:\s*"(cuts/[^"]+)"', rep, html)
    if not n:
        print("   ! لم تُوجد صور قصّات للدمج")
    return out


def build_single_file(payload: str):
    """
    يدمج البيانات داخل الصفحة فتصير ملفاً واحداً مستقلاً.

    لماذا؟ النسخة العادية ملفان يجب أن يكونا بجوار بعضهما
    (`لوحة-فاطمة.html` و `motifs-data.js`). وهذا يفشل كثيراً على
    الجوال: تطبيقات الملفات تفتح الـ HTML في عارض معزول لا يُحمّل
    الملف المجاور، فتظهر رسالة «لم يتم تحميل ملف النقشات» — وعلى
    آيفون خاصةً. أما الملف الواحد فيُفتح ويُرسَل عبر واتساب بلا مشاكل.
    """
    src = OUT / PANEL_SRC
    html = src.read_text(encoding="utf-8")
    if DATA_TAG not in html:
        raise ValueError(f"وسم البيانات غير موجود في {PANEL_SRC}")

    # </script> داخل نصّ السكربت يُنهي الوسم مبكّراً فتتلف الصفحة،
    # ولا يظهر ذلك إلا عند الفتح. ويُتفادى بتقسيم التسلسل.
    safe = payload.replace("</", "<\\/")

    # صور القصّات تُدمَج كـ data URL، وإلا ظهرت القطع فارغة في
    # نسخة الملف الواحد لأن المسار النسبي (cuts/...) لا يوجد بجوارها.
    html = inline_cut_images(html)

    inline = ("<script>\n"
              "/* بيانات النقشات مدموجة — مُولّدة آلياً بـ build_panel.py */\n"
              "window.MOTIFS = " + safe + ";\n"
              "</script>")
    out = OUT / PANEL_ONE
    out.write_text(html.replace(DATA_TAG, inline, 1), encoding="utf-8")
    print(f"ونسخة ملف واحد للجوال: {out.relative_to(ROOT)}"
          f"  ({out.stat().st_size / 1024 / 1024:.1f} م.ب)")


if __name__ == "__main__":
    main()
