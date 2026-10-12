/* تفريغ خلفية رسمة القصّة: الخارج يصير شفّافاً وجسم العباية مُعتِماً.

   لماذا: اللوحة تُعبّئ لون العباية داخل الرسمة باستخدام **قناة
   الشفافية** للصورة. فصور الكلوش والثوب خلفيّتها شفّافة (alpha=0 في
   الزوايا) وجسمها مُعتِم، فيظهر اللون داخل الشكل وحده. وصورة
   وردت بخلفية بيضاء مُعتِمة تُعبَّأ كاملةً، فتظهر مستطيلاً داكناً
   لا عباية — وهو ما حدث فعلاً مع «بليزر عباية».

   الطريقة: تعبئة انتشارية من حدود الصورة عبر بكسلات «الورق»
   (الفاتحة)، فكل ما تبلغه التعبئة هو الخارج ويصير شفّافاً. وما لم
   تبلغه — داخل العباية وخطوطها — يبقى مُعتِماً.

   والصورة تُحاط بهامش أبيض قبل التعبئة: القصّ على حدود الرسمة يجعلها
   تلامس الحواف الأربع، فالانطلاق من الحدّ يبدأ فوق الخطّ نفسه
   فتفشل التعبئة.

   وحذارِ التسرّب: لو كان في محيط الرسمة فُرجة بكسل واحد، تسرّبت
   التعبئة إلى الداخل فأُفرغت العباية كلها. فتُطبع نسبة الخارج دائماً
   ويُنبَّه إذا كانت غير معقولة.

   الاستخدام:
     node tools/silhouette.mjs <مدخل> <مخرَج> [--thr=235] [--pad=6]
                               [--max=2000]
*/
import { launch } from "./cdp.mjs";
import { readFileSync, writeFileSync, existsSync, statSync } from "node:fs";
import { extname } from "node:path";

const args = process.argv.slice(2);
const pos = args.filter(a => !a.startsWith("--"));
const flag = (n, d) => {
  const f = args.find(a => a.startsWith("--" + n + "="));
  return f ? Number(f.split("=")[1]) : d;
};
const [inPath, outPath] = pos;
const THR = flag("thr", 235);
const PAD = flag("pad", 6);
const MAX = flag("max", 2000);

if (!inPath || !outPath) {
  console.error("الاستخدام: node tools/silhouette.mjs <مدخل> <مخرَج> "
    + "[--thr=235] [--pad=6] [--max=2000]");
  process.exit(2);
}
if (!existsSync(inPath)) { console.error("غير موجود: " + inPath); process.exit(2); }
const MIME = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg" };
const mime = MIME[extname(inPath).toLowerCase()];
if (!mime) { console.error("صيغة غير مدعومة"); process.exit(2); }
const dataUrl = `data:${mime};base64,` + readFileSync(inPath).toString("base64");

const b = await launch({ width: 600, height: 400 });
try {
  await b.open("about:blank", 200);
  const r = await b.eval(`
    const THR = ${THR}, PAD = ${PAD}, MAX = ${MAX};
    const img = new Image();
    await new Promise((ok, no) => { img.onload = ok;
      img.onerror = () => no(new Error("decode"));
      img.src = ${JSON.stringify(dataUrl)}; });
    const W0 = img.naturalWidth, H0 = img.naturalHeight;
    const W = W0 + PAD * 2, H = H0 + PAD * 2;

    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const c = cv.getContext("2d");
    c.fillStyle = "#fff"; c.fillRect(0, 0, W, H);
    c.drawImage(img, PAD, PAD);
    const id = c.getImageData(0, 0, W, H);
    const px = id.data;

    const isPaper = i => {
      if (px[i + 3] < 24) return true;              // شفاف أصلاً = ورق
      const l = 0.299*px[i] + 0.587*px[i+1] + 0.114*px[i+2];
      return l >= THR;
    };

    // تعبئة انتشارية من كل بكسلات الحدّ — بطابور صريح لا باستدعاء
    // متداخل، فالصور الكبيرة تُفجّر مكدّس الاستدعاء
    const seen = new Uint8Array(W * H);
    const qx = new Int32Array(W * H), qy = new Int32Array(W * H);
    let qh = 0, qt = 0;
    const push = (x, y) => {
      if (x < 0 || y < 0 || x >= W || y >= H) return;
      const k = y * W + x;
      if (seen[k]) return;
      if (!isPaper(k * 4)) return;
      seen[k] = 1; qx[qt] = x; qy[qt] = y; qt++;
    };
    for (let x = 0; x < W; x++) { push(x, 0); push(x, H - 1); }
    for (let y = 0; y < H; y++) { push(0, y); push(W - 1, y); }
    while (qh < qt) {
      const x = qx[qh], y = qy[qh]; qh++;
      push(x + 1, y); push(x - 1, y); push(x, y + 1); push(x, y - 1);
    }

    // الخارج شفّاف، والباقي مُعتِم
    let outside = 0;
    for (let k = 0; k < W * H; k++) {
      if (seen[k]) { px[k * 4 + 3] = 0; outside++; }
      else { px[k * 4 + 3] = 255; }
    }
    c.putImageData(id, 0, 0);

    // إزالة الهامش ثم التصغير إن لزم
    const cw = W0, ch = H0;
    const s = Math.min(1, MAX / Math.max(cw, ch));
    const ow = Math.max(1, Math.round(cw * s)), oh = Math.max(1, Math.round(ch * s));
    const out = document.createElement("canvas");
    out.width = ow; out.height = oh;
    const o = out.getContext("2d");
    o.imageSmoothingEnabled = true; o.imageSmoothingQuality = "high";
    o.drawImage(cv, PAD, PAD, cw, ch, 0, 0, ow, oh);

    // قياس النتيجة على القصّ النهائي
    const fin = o.getImageData(0, 0, ow, oh).data;
    let t = 0;
    for (let i = 3; i < fin.length; i += 4) if (fin[i] < 24) t++;
    const cornerA = fin[3];
    const ci = ((Math.floor(oh * 0.55)) * ow + Math.floor(ow / 2)) * 4;

    return JSON.stringify({
      W0, H0, ow, oh, scale: +s.toFixed(5),
      outsidePctPadded: +(outside / (W * H) * 100).toFixed(1),
      transPct: +(t / (ow * oh) * 100).toFixed(1),
      cornerAlpha: cornerA, centerAlpha: fin[ci + 3],
      png: out.toDataURL("image/png").split(",")[1]
    });
  `).then(JSON.parse);

  writeFileSync(outPath, Buffer.from(r.png, "base64"));
  const buf = readFileSync(outPath);
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
  if (w > MAX || h > MAX) {
    console.error(`فشل: المكتوب ${w}×${h} يتجاوز ${MAX}`);
    process.exit(1);
  }

  console.log(`${inPath}  ${r.W0}×${r.H0}  →  ${outPath}  ${w}×${h}`);
  console.log(`الخارج الشفّاف: ${r.transPct}%  ·  `
    + `الزاوية alpha=${r.cornerAlpha}  ·  المركز alpha=${r.centerAlpha}`);
  console.log(`الحجم ${(statSync(outPath).size / 1024).toFixed(0)} ك.ب  ·  `
    + `داخل حدّ ${MAX} ✓`);

  const ok = r.cornerAlpha < 24 && r.centerAlpha > 200
    && r.transPct > 3 && r.transPct < 80;
  if (!ok) {
    console.error(`\n⚠ النتيجة غير معقولة:`);
    if (r.cornerAlpha >= 24) console.error("  الزاوية ليست شفّافة — فشلت التعبئة");
    if (r.centerAlpha <= 200) {
      console.error("  مركز العباية شفّاف — **تسرّبت** التعبئة إلى الداخل،"
        + " أي أن محيط الرسمة فيه فُرجة. جرّبي --thr أقلّ (مثل 215).");
    }
    if (r.transPct >= 80) console.error("  الشفاف أكثر من 80% — تسرّب شبه كامل");
    if (r.transPct <= 3) console.error("  الشفاف أقلّ من 3% — لم تُفرَّغ الخلفية");
    process.exit(1);
  }
  console.log("\n✓ الاتفاقية مطابقة لصور الكلوش والثوب:"
    + " خلفية شفّافة وجسم مُعتِم");
} finally { await b.close(); }
