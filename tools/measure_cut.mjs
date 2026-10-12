/* قياس عرض الرسمة عند ارتفاعات مفتاحية، لمطابقتها بالمقاسات المعطاة.

   لماذا: المقاس المعطى قد يكون محيطاً أو مفروشاً، والفرق ضعف ويقلب
   كل القياسات. والرسمة نفسها شاهد مستقلّ: إن قيل إن الذيل 42 إنشاً
   وأظهرت الرسمة 24 إنشاً، فـ42 محيط لا مفروش. وهذا ما صحّح قراءة
   الكلوش والثوب سابقاً.

   تفترض أن ارتفاع الصورة = الطول المُعطى (أي أنها مقصوصة على حدود
   العباية). وتُخرج العرض بالإنش عند نسب من الأعلى.

   الاستخدام:
     node tools/measure_cut.mjs <صورة> <الطول بالإنش>
*/
import { launch } from "./cdp.mjs";
import { readFileSync, existsSync } from "node:fs";
import { extname } from "node:path";

const [inPath, lenArg] = process.argv.slice(2);
const LEN = Number(lenArg);
if (!inPath || !(LEN > 0)) {
  console.error("الاستخدام: node tools/measure_cut.mjs <صورة> <الطول بالإنش>");
  process.exit(2);
}
if (!existsSync(inPath)) { console.error("غير موجود: " + inPath); process.exit(2); }
const MIME = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg" };
const mime = MIME[extname(inPath).toLowerCase()];
const dataUrl = `data:${mime};base64,` + readFileSync(inPath).toString("base64");

const b = await launch({ width: 600, height: 400 });
try {
  await b.open("about:blank", 200);
  const r = await b.eval(`
    const img = new Image();
    await new Promise((ok, no) => { img.onload = ok;
      img.onerror = () => no(new Error("decode")); img.src = ${JSON.stringify(dataUrl)}; });
    const W = img.naturalWidth, H = img.naturalHeight;
    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const c = cv.getContext("2d");
    c.fillStyle = "#fff"; c.fillRect(0, 0, W, H);
    c.drawImage(img, 0, 0);
    const px = c.getImageData(0, 0, W, H).data;
    const ink = (x, y) => {
      const i = (y * W + x) * 4;
      if (px[i + 3] < 24) return false;
      return (0.299*px[i] + 0.587*px[i+1] + 0.114*px[i+2]) < 235;
    };
    // عرض الحبر في صفّ: من أوّل بكسل مُحبَّر إلى آخره
    const rowSpan = y => {
      let a = -1, z = -1;
      for (let x = 0; x < W; x++) if (ink(x, y)) { if (a < 0) a = x; z = x; }
      return a < 0 ? 0 : z - a + 1;
    };
    const spans = [];
    for (let y = 0; y < H; y++) spans.push(rowSpan(y));
    let widest = 0, widestY = 0;
    spans.forEach((v, y) => { if (v > widest) { widest = v; widestY = y; } });
    const at = p => {
      const y = Math.min(H - 1, Math.max(0, Math.round(p / 100 * (H - 1))));
      return { pct: p, y, px: spans[y] };
    };
    return JSON.stringify({
      W, H,
      marks: [2, 4, 6, 8, 12, 17, 25, 50, 75, 90, 97, 100].map(at),
      widest: { px: widest, y: widestY, pct: +(widestY / (H - 1) * 100).toFixed(1) }
    });
  `).then(JSON.parse);

  const ppi = r.H / LEN;
  const inch = p => p / ppi;
  console.log(`الصورة ${r.W}×${r.H} بكسل · الطول المُعطى ${LEN}″`);
  console.log(`معامل القياس = ${r.H}÷${LEN} = ${ppi.toFixed(3)} بكسل/إنش`);
  console.log(`عرض الصورة كاملاً = ${inch(r.W).toFixed(2)}″\n`);
  console.log("النسبة من الأعلى │ العرض بالبكسل │ العرض بالإنش │ لو كان محيطاً");
  console.log("─".repeat(66));
  r.marks.forEach(m => {
    const i = inch(m.px);
    console.log(`${String(m.pct).padStart(10)}% │ ${String(m.px).padStart(13)}`
      + ` │ ${i.toFixed(2).padStart(12)}″ │ ${(i * 2).toFixed(2).padStart(10)}″`);
  });
  console.log("─".repeat(66));
  console.log(`أوسع نقطة: ${r.widest.px} بكسل = `
    + `${inch(r.widest.px).toFixed(2)}″ عند ${r.widest.pct}% من الأعلى`);
} finally { await b.close(); }
