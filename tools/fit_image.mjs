/* تصغير أي صورة إلى ما دون حدّ 2000 بكسل، وتحويلها إلى PNG.

   لماذا بالمتصفّح؟ لأن check_png.py --fix يدعم الرمادي 8-بت غير
   المتداخل فقط، وصور القصّات الواردة ملوّنة (RGBA) وبعضها JPEG.
   وPillow غير مثبّت ولا إنترنت لتثبيته. وChromium موجود ويفكّ
   كل الصيغ ويُعيد التحجيم بترشيح عالي الجودة.

   الحدّ مفروض هنا بلا استثناء، ويُتحقّق من الأبعاد *الناتجة* بعد
   الكتابة لا قبلها — فقراءة صورة فوق 2000 بكسل تُرفض بعد انتهاء
   العمل كلّه، فتضيع الجلسة.

   الاستخدام:
     node tools/fit_image.mjs <مدخل> <مخرَج> [الحدّ]
*/
import { launch } from "./cdp.mjs";
import { readFileSync, writeFileSync, existsSync, statSync } from "node:fs";
import { extname, resolve } from "node:path";

const [inPath, outPath, maxArg] = process.argv.slice(2);
const MAX = Number(maxArg || 2000);

if (!inPath || !outPath) {
  console.error("الاستخدام: node tools/fit_image.mjs <مدخل> <مخرَج> [الحدّ]");
  process.exit(2);
}
if (!existsSync(inPath)) {
  console.error("الملف غير موجود: " + inPath);
  process.exit(2);
}

const MIME = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif" };
const ext = extname(inPath).toLowerCase();
const mime = MIME[ext];
if (!mime) { console.error("صيغة غير مدعومة: " + ext); process.exit(2); }

const dataUrl = `data:${mime};base64,`
  + readFileSync(inPath).toString("base64");

const b = await launch({ width: 600, height: 400 });
try {
  await b.open("about:blank", 200);

  const res = await b.eval(`
    const src = ${JSON.stringify(dataUrl)};
    const MAX = ${MAX};
    const img = new Image();
    await new Promise((ok, no) => {
      img.onload = ok;
      img.onerror = () => no(new Error("تعذّر فكّ الصورة"));
      img.src = src;
    });
    const w0 = img.naturalWidth, h0 = img.naturalHeight;
    const s = Math.min(1, MAX / Math.max(w0, h0));
    const w = Math.max(1, Math.floor(w0 * s));
    const h = Math.max(1, Math.floor(h0 * s));

    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    const ctx = cv.getContext("2d");
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(img, 0, 0, w, h);

    // هل للصورة شفافية فعلية؟ يُفيد في معرفة أن التحديد مفرّغ
    const px = ctx.getImageData(0, 0, w, h).data;
    let transparent = 0;
    for (let i = 3; i < px.length; i += 4) if (px[i] < 250) transparent++;

    return JSON.stringify({
      w0, h0, w, h, scale: +s.toFixed(5),
      transparentPct: +(transparent / (w * h) * 100).toFixed(1),
      png: cv.toDataURL("image/png").split(",")[1]
    });
  `).then(JSON.parse);

  writeFileSync(outPath, Buffer.from(res.png, "base64"));

  // التحقّق من الأبعاد المكتوبة فعلاً — لا من المحسوبة
  const buf = readFileSync(outPath);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  if (w > MAX || h > MAX) {
    console.error(`فشل: المكتوب ${w}×${h} ما زال يتجاوز ${MAX}`);
    process.exit(1);
  }

  const kb = (statSync(outPath).size / 1024).toFixed(0);
  console.log(`${inPath}  ${res.w0}×${res.h0}`
    + (res.scale < 1 ? `  →  ${w}×${h} (×${res.scale})` : `  (بلا تصغير)`));
  console.log(`كُتب: ${outPath}  ${kb} ك.ب  ·`
    + ` شفافية: ${res.transparentPct}%  ·  داخل حدّ ${MAX} ✓`);
} finally {
  await b.close();
}
