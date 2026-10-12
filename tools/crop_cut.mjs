/* قصّ صورة القصّة على حدود العباية بالضبط.

   لماذا هذا إلزامي: معامل القياس يُشتقّ من فرض أن ارتفاع الصورة =
   الطول الحقيقي للعباية. فأي هامش أبيض — أو تسمية مكتوبة أسفل
   الرسمة — يُخطئ كل مقاس بنفس النسبة. صورة «بليزر عباية» الواردة
   كانت 1152×2048 والرسمة تشغل نحو 65% من الطول فقط، والباقي هوامش
   ونصّ: أي خطأ 35% في كل مقاس لو استُعملت كما هي.

   الطريقة: تُحسب كثافة الحبر في كل صفٍّ من البكسلات، فتظهر الرسمة
   شريطاً متّصلاً من الصفوف المُحبَّرة، ويفصلها عن التسمية فراغ
   أبيض. فيُختار أطول شريط (الرسمة) ويُستبعد ما سواه، ثم يُحسب
   الصندوق المحيط أفقياً داخل ذلك الشريط.

   وهذا أدقّ من الصندوق المحيط للصورة كلها، الذي يشمل التسمية.

   الاستخدام:
     node tools/crop_cut.mjs <مدخل> <مخرَج> [--pad=0] [--max=2000]
                             [--band=N] [--thr=235] [--dry]
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
const DRY = args.includes("--dry");
const [inPath, outPath] = pos;
const PAD = flag("pad", 0);        // بكسلات هامش مقصودة (0 = حدود تماماً)
const MAX = flag("max", 2000);
const MIN_GAP = flag("band", 12);  // فراغ بهذا العدد من الصفوف يفصل شريطين
const THR = flag("thr", 235);      // ما دون هذه الإضاءة يُعدّ حبراً

if (!inPath || (!outPath && !DRY)) {
  console.error("الاستخدام: node tools/crop_cut.mjs <مدخل> <مخرَج> "
    + "[--pad=0] [--max=2000] [--band=12] [--thr=235] [--dry]");
  process.exit(2);
}
if (!existsSync(inPath)) { console.error("غير موجود: " + inPath); process.exit(2); }

const MIME = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
               ".webp": "image/webp", ".gif": "image/gif" };
const mime = MIME[extname(inPath).toLowerCase()];
if (!mime) { console.error("صيغة غير مدعومة"); process.exit(2); }

const dataUrl = `data:${mime};base64,` + readFileSync(inPath).toString("base64");

const b = await launch({ width: 600, height: 400 });
try {
  await b.open("about:blank", 200);
  const r = await b.eval(`
    const src = ${JSON.stringify(dataUrl)};
    const THR = ${THR}, MIN_GAP = ${MIN_GAP}, PAD = ${PAD}, MAX = ${MAX};
    const img = new Image();
    await new Promise((ok, no) => {
      img.onload = ok;
      img.onerror = () => no(new Error("تعذّر فكّ الصورة"));
      img.src = src;
    });
    const W = img.naturalWidth, H = img.naturalHeight;
    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const ctx = cv.getContext("2d");
    // خلفية بيضاء: الصور الشفّافة يجب أن تُقاس على أبيض لا على أسود
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, W, H);
    ctx.drawImage(img, 0, 0);
    const px = ctx.getImageData(0, 0, W, H).data;

    const ink = (x, y) => {
      const i = (y * W + x) * 4;
      const a = px[i + 3];
      if (a < 24) return false;                       // شفاف = ورق
      const l = 0.299 * px[i] + 0.587 * px[i+1] + 0.114 * px[i+2];
      return l < THR;
    };

    // كثافة الحبر لكل صفّ
    const rows = new Array(H).fill(0);
    for (let y = 0; y < H; y++) {
      let c = 0;
      for (let x = 0; x < W; x++) if (ink(x, y)) c++;
      rows[y] = c;
    }
    // الأشرطة: مقاطع متّصلة من الصفوف المُحبَّرة يفصلها فراغ ≥ MIN_GAP
    const bands = [];
    let y = 0;
    while (y < H) {
      if (rows[y] === 0) { y++; continue; }
      let s = y, e = y, gap = 0;
      while (e + 1 < H) {
        if (rows[e + 1] > 0) { e++; gap = 0; }
        else if (gap < MIN_GAP) { e++; gap++; }
        else break;
      }
      // قصّ الفراغ المُلتقط في الذيل
      let ee = e;
      while (ee > s && rows[ee] === 0) ee--;
      bands.push({ top: s, bottom: ee, h: ee - s + 1,
                   ink: rows.slice(s, ee + 1).reduce((a, v) => a + v, 0) });
      y = e + 1;
    }
    if (!bands.length) throw new Error("لا حبر في الصورة");

    // الرسمة = أطول شريط. التسمية شريط قصير أسفله.
    const main = bands.reduce((a, c) => (c.h > a.h ? c : a), bands[0]);

    // الصندوق المحيط أفقياً داخل الشريط المختار
    let x0 = W, x1 = -1;
    for (let yy = main.top; yy <= main.bottom; yy++) {
      for (let x = 0; x < W; x++) {
        if (ink(x, yy)) { if (x < x0) x0 = x; if (x > x1) x1 = x; }
      }
    }
    let cx0 = Math.max(0, x0 - PAD), cx1 = Math.min(W - 1, x1 + PAD);
    let cy0 = Math.max(0, main.top - PAD), cy1 = Math.min(H - 1, main.bottom + PAD);
    const cw = cx1 - cx0 + 1, ch = cy1 - cy0 + 1;

    // التصغير إن تجاوز الحدّ — على القصّ لا على الأصل
    const s = Math.min(1, MAX / Math.max(cw, ch));
    const ow = Math.max(1, Math.round(cw * s)), oh = Math.max(1, Math.round(ch * s));
    const out = document.createElement("canvas");
    out.width = ow; out.height = oh;
    const octx = out.getContext("2d");
    octx.fillStyle = "#fff"; octx.fillRect(0, 0, ow, oh);
    octx.imageSmoothingEnabled = true;
    octx.imageSmoothingQuality = "high";
    octx.drawImage(cv, cx0, cy0, cw, ch, 0, 0, ow, oh);

    return JSON.stringify({
      W, H,
      bands: bands.map(x => ({ top: x.top, bottom: x.bottom, h: x.h })),
      chosen: { top: main.top, bottom: main.bottom },
      box: { x: cx0, y: cy0, w: cw, h: ch },
      out: { w: ow, h: oh, scale: +s.toFixed(5) },
      wastedTop: cy0,
      wastedBottom: H - 1 - cy1,
      png: out.toDataURL("image/png").split(",")[1]
    });
  `).then(JSON.parse);

  console.log(`المصدر: ${inPath}  ${r.W}×${r.H}`);
  console.log(`أشرطة الحبر المكتشفة: ${r.bands.length}`);
  r.bands.forEach((x, i) => {
    const pick = (x.top === r.chosen.top && x.bottom === r.chosen.bottom)
      ? "  ← الرسمة" : "  (مُستبعد — تسمية أو زخرفة)";
    console.log(`  ${i + 1}) الصفوف ${x.top}–${x.bottom}  ارتفاع ${x.h}${pick}`);
  });
  console.log(`الصندوق: x=${r.box.x} y=${r.box.y} `
    + `${r.box.w}×${r.box.h}`);
  console.log(`أُسقط من الأعلى ${r.wastedTop} بكسل ومن الأسفل `
    + `${r.wastedBottom} بكسل`);
  const errPct = ((r.H - r.box.h) / r.H * 100).toFixed(1);
  console.log(`خطأ الطول لو استُعملت بلا قصّ: ${errPct}%`);

  if (DRY) { console.log("(--dry: لم يُكتب شيء)"); }
  else {
    writeFileSync(outPath, Buffer.from(r.png, "base64"));
    const buf = readFileSync(outPath);
    const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);
    if (w > MAX || h > MAX) {
      console.error(`فشل: المكتوب ${w}×${h} يتجاوز ${MAX}`);
      process.exit(1);
    }
    console.log(`كُتب: ${outPath}  ${w}×${h}  `
      + `${(statSync(outPath).size / 1024).toFixed(0)} ك.ب  ·  `
      + `داخل حدّ ${MAX} ✓`);
    console.log(`النسبة عرض/طول = ${(w / h).toFixed(4)}`);
  }
} finally { await b.close(); }
