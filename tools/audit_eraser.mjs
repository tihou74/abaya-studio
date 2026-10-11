/* اختبار الممحاة الجديدة بتحريك مؤشّر حقيقي عبر CDP — لا بمحاكاة
   أحداث جافاسكربت، فالمحاكاة قد تنجح حيث يفشل الاستخدام الفعلي.
   شغّلي:  env -u NODE_OPTIONS node tools/audit_eraser.mjs            */
import { launch } from "./cdp.mjs";

const URL = "file:///projects/sandbox/abaya-motifs/panel/designer.html";
const out = [];
const check = (name, pass, detail) => {
  out.push({ name, pass, detail });
  console.log(`${pass ? "✅" : "❌"} ${name}\n   ${detail}`);
};
const sleep = ms => new Promise(r => setTimeout(r, ms));

const b = await launch({ width: 1500, height: 940 });
try {
  await b.open(URL, 1800);
  await b.setSize(1500, 940);
  await sleep(400);

  /* تصميم ابتدائي: نقشة واحدة كبيرة في منتصف العباية */
  const geo = await b.eval(`
    localStorage.clear();
    state.items.length = 0; state.showDim = false;
    addMotif('B021');
    const it = state.items[0];
    it.x = 0; it.y = 500; it.scale = .6; it.rot = 0;
    select(it.uid); draw();
    // موضع مركز النقشة على الشاشة بالبكسل
    const g = board.querySelector('[data-stack="'+it.uid+'"]');
    const r = g.getBoundingClientRect();
    return JSON.stringify({uid: it.uid,
      cx: Math.round(r.left + r.width/2), cy: Math.round(r.top + r.height/2),
      w: Math.round(r.width), h: Math.round(r.height)});
  `).then(JSON.parse);
  console.log(`   (النقشة على الشاشة ${geo.w}×${geo.h} بكسل، مركزها `
    + `${geo.cx},${geo.cy})`);

  /* ---- ١ · دائرة الفرشاة تظهر وتتبع المؤشّر ---- */
  await b.eval(`setEraseMode(true); return 1;`);
  await b.mouseMove(geo.cx, geo.cy);
  await sleep(150);
  const ring1 = await b.eval(`
    const c = board.querySelector('.er-brush-ring');
    return JSON.stringify(c ? {r:+(+c.getAttribute('r')).toFixed(1),
      cx:+(+c.getAttribute('cx')).toFixed(1), cy:+(+c.getAttribute('cy')).toFixed(1),
      cursor: getComputedStyle(board).cursor} : null);
  `).then(JSON.parse);
  await b.mouseMove(geo.cx + 40, geo.cy + 25);
  await sleep(150);
  const ring2 = await b.eval(`
    const c = board.querySelector('.er-brush-ring');
    return JSON.stringify(c ? {cx:+(+c.getAttribute('cx')).toFixed(1),
      cy:+(+c.getAttribute('cy')).toFixed(1)} : null);
  `).then(JSON.parse);
  check("دائرة الفرشاة تظهر وتتبع المؤشّر",
    !!ring1 && !!ring2 && (ring2.cx !== ring1.cx) && ring1.r > 0
      && ring1.cursor === "none",
    `الدائرة نصف قطرها ${ring1 && ring1.r} وحدة · انتقلت من `
    + `(${ring1 && ring1.cx},${ring1 && ring1.cy}) إلى `
    + `(${ring2 && ring2.cx},${ring2 && ring2.cy}) مع المؤشّر · `
    + `ومؤشّر النظام مخفيّ (cursor:${ring1 && ring1.cursor}) فلا يُربك`);

  /* ---- ٢ · مقاس الفرشاة يُرى فوراً عند تغييره ---- */
  const sizes = await b.eval(`
    const rr = () => +(+board.querySelector('.er-brush-ring')
      .getAttribute('r')).toFixed(2);
    const a = rr();
    document.querySelector('#erS1').click();   // دقيقة 0.1
    const small = rr();
    document.querySelector('#erS4').click();   // مسح واسع 1.2
    const big = rr();
    setBrush(.25);
    return JSON.stringify({a, small, big, ratio:+(big/small).toFixed(2)});
  `).then(JSON.parse);
  check("أزرار المقاس تُغيّر الدائرة فوراً",
    sizes.big > sizes.small * 5,
    `«دقيقة 0.1″» → نصف قطر ${sizes.small} · «مسح 1.2″» → ${sizes.big} `
    + `(أكبر ${sizes.ratio} مرّة) — الفرق مرئي قبل أي ضغطة`);

  /* ---- ٣ · المسح بسحب حقيقي على نقشة *غير محدّدة* ---- */
  const erased = await b.eval(`
    // إلغاء التحديد كي يُختبر أن المسح لا يشترط تحديداً مسبقاً
    state.sel = null; draw(); syncProps();
    return JSON.stringify({sel: state.sel,
      before: (state.items[0].erase||[]).length});
  `).then(JSON.parse);
  await b.drag(geo.cx - 30, geo.cy - 60, geo.cx + 30, geo.cy + 60, 14);
  await sleep(250);
  const after = await b.eval(`
    const it = state.items[0];
    return JSON.stringify({dots: (it.erase||[]).length,
      strokes: strokeCount(it), sel: state.sel,
      ghost: board.querySelectorAll('.er-ghost circle').length,
      moved: it.x !== 0 || it.y !== 500});
  `).then(JSON.parse);
  check("السحب يمحو نقشةً لم تُحدَّد مسبقاً ولا يُحرّكها",
    after.dots > 1 && after.strokes === 1 && !after.moved && after.ghost > 0,
    `قبل السحب التحديد=${erased.sel} والمسح=${erased.before} نقطة · `
    + `بعده ${after.dots} نقطة في ${after.strokes} مسحة واحدة، `
    + `والنقشة لم تنزح (moved=${after.moved}) · `
    + `وأثر المسح معروض بـ${after.ghost} دائرة`);

  /* ---- ٤ · التراجع يُلغي المسحة كاملةً بضغطة ---- */
  const undo = await b.eval(`
    const it = state.items[0];
    select(it.uid);
    const before = (it.erase||[]).length;
    document.querySelector('#erUndo').click();
    return JSON.stringify({before, after: (it.erase||[]).length});
  `).then(JSON.parse);
  check("«Undo last stroke» يُلغي المسحة كاملةً",
    undo.before > 1 && undo.after === 0,
    `${undo.before} نقطة (مسحة واحدة) → ${undo.after} بضغطة واحدة`);

  /* ---- ٥ · فرشاة الإرجاع تُعيد ما مُسح ---- */
  await b.drag(geo.cx - 30, geo.cy - 60, geo.cx + 30, geo.cy + 60, 14);
  await sleep(200);
  const midCount = await b.eval(`
    return JSON.stringify({dots:(state.items[0].erase||[]).length});`)
    .then(JSON.parse);
  await b.eval(`
    select(state.items[0].uid);
    document.querySelector('#erRest').click();   // فرشاة الإرجاع
    setBrush(.6);
    return 1;`);
  await b.drag(geo.cx - 30, geo.cy - 60, geo.cx + 30, geo.cy + 60, 14);
  await sleep(250);
  const restored = await b.eval(`
    const ring = board.querySelector('.er-brush-ring');
    return JSON.stringify({dots:(state.items[0].erase||[]).length,
      greenRing: ring ? ring.getAttribute('class').includes('restore') : false,
      banner: (document.querySelector('#erBanner')||{}).textContent || ''});
  `).then(JSON.parse);
  check("فرشاة الإرجاع تُعيد ما مُسح وتتميّز بلونها",
    restored.dots < midCount.dots && restored.greenRing,
    `المسح ${midCount.dots} نقطة → بعد المرور بفرشاة الإرجاع `
    + `${restored.dots} · والدائرة تحوّلت لحالة الإرجاع `
    + `(${restored.greenRing}) · الشريط: «${restored.banner.slice(0, 60)}»`);

  /* ---- ٦ · الاختصارات ---- */
  const keys = await b.eval(`
    select(state.items[0].uid);
    document.querySelector('#erRest').click();   // إطفاء الإرجاع
    const r0 = erBrushIn;
    return JSON.stringify({r0:+r0.toFixed(3), mode: eraseMode});
  `).then(JSON.parse);
  await b.key("]");
  await b.key("]");
  await sleep(100);
  const bigger = await b.eval(`JSON.stringify({r:+erBrushIn.toFixed(3)})`)
    .then(JSON.parse);
  await b.key("Escape");
  await sleep(150);
  const offNow = await b.eval(`JSON.stringify({
    mode: eraseMode, cursor: getComputedStyle(board).cursor,
    ring: !!board.querySelector('.er-brush-ring'),
    banner: document.querySelector('#erBanner').hidden })`).then(JSON.parse);
  await b.key("e");
  await sleep(150);
  const onAgain = await b.eval(`JSON.stringify({mode: eraseMode})`)
    .then(JSON.parse);
  check("الاختصارات: ] للتكبير · Esc للخروج · E للتشغيل",
    bigger.r > keys.r0 && offNow.mode === false && offNow.ring === false
      && offNow.banner === true && onAgain.mode === true,
    `[ ] غيّرت المقاس ${keys.r0}″ → ${bigger.r}″ · Esc أطفأت الممحاة `
    + `(mode=${offNow.mode}, الدائرة=${offNow.ring}, الشريط مخفي=`
    + `${offNow.banner}) · E أعادت التشغيل (${onAgain.mode})`);

  /* ---- ٧ · الممسوح يُطبع ممسوحاً ---- */
  await b.eval(`setEraseMode(false); return 1;`);
  await b.drag(geo.cx - 20, geo.cy - 40, geo.cx + 20, geo.cy + 40, 10)
    .catch(() => {});
  const printed = await b.eval(`
    const it = state.items[0];
    setEraseMode(true);
    return 1;`);
  await b.drag(geo.cx - 25, geo.cy - 50, geo.cx + 25, geo.cy + 50, 12);
  await sleep(250);
  const pr = await b.eval(`
    setEraseMode(false);
    const it = state.items[0];
    printMotifs([it]);
    const svg = document.querySelector('#printRoot .win svg');
    const html = svg ? svg.outerHTML : '';
    const n = (html.match(/<circle/g) || []).length;
    const hasMask = /mask=/.test(html);
    document.querySelector('#printView').hidden = true;
    return JSON.stringify({dots:(it.erase||[]).length, maskCircles:n, hasMask});
  `).then(JSON.parse);
  check("الممسوح يُطبع ممسوحاً",
    pr.hasMask && pr.maskCircles >= pr.dots && pr.dots > 0,
    `${pr.dots} نقطة مسح → شيفرة الطباعة فيها قناع (${pr.hasMask}) `
    + `و${pr.maskCircles} دائرة — فالمطبوع يطابق المعروض`);

  /* ---- ٨ · المسح يبقى في موضعه بعد التحجيم والتدوير ---- */
  const stable = await b.eval(`
    const it = state.items[0];
    const snap = JSON.stringify(it.erase);
    it.scale *= 1.8; it.rot = 42; draw();
    const same = JSON.stringify(it.erase) === snap;
    it.scale /= 1.8; it.rot = 0; draw();
    return JSON.stringify({same, dots:(it.erase||[]).length});
  `).then(JSON.parse);
  check("المسح يثبت في موضعه بعد التكبير والتدوير",
    stable.same,
    `بعد تكبير ×1.8 وتدوير 42° بقيت نقاط المسح كما هي `
    + `(${stable.dots} نقطة) — فهي مُسجَّلة بإحداثيات النقشة لا اللوح`);

  const errs = b.errors();
  check("لا أخطاء جافاسكربت", errs.length === 0,
    errs.length ? errs.slice(0, 4).join(" | ") : "صفر خطأ");

  /* لقطة للممحاة وهي تعمل */
  await b.eval(`
    const it = state.items[0];
    setBrush(.45); setEraseMode(true); select(it.uid);
    return 1;`);
  await b.mouseMove(geo.cx + 15, geo.cy - 20);
  await sleep(300);
  await b.shot("/projects/sandbox/.kiro/artifacts/screenshots/eraser.png",
    1500, 940);
  console.log("\nلقطة: .kiro/artifacts/screenshots/eraser.png");

} finally { await b.close(); }

const bad = out.filter(r => !r.pass);
console.log("\n" + "=".repeat(64));
console.log(`المحصّلة: ${out.length - bad.length}/${out.length} سليم`
  + (bad.length ? ` · ${bad.length} فاشل` : " · صفر فاشل"));
