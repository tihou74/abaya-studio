/* اختبار اللوحة على مقاس هاتف حقيقي وبلمسٍ حقيقي.

   لا يكفي تصغير النافذة: اللمس يختلف عن الفأرة في أمور تكسر الأدوات
   فعلاً — لا يوجد تحويم (hover) فلا تظهر دائرة الممحاة قبل اللمس،
   والمتصفّح يسرق السحب تمريراً للصفحة إن لم يُمنع، والمقابض الصغيرة
   لا تُصاب بالإصبع.

   شغّلي:  env -u NODE_OPTIONS node tools/audit_mobile.mjs [ملف]     */
import { launch } from "./cdp.mjs";

const FILE = process.argv[2] || "designer-single-file.html";
const URL = "file:///projects/sandbox/abaya-motifs/panel/" + FILE;
const SHOT = "/projects/sandbox/.kiro/artifacts/screenshots/";
const out = [];
const check = (name, pass, detail) => {
  out.push({ name, pass, detail });
  console.log(`${pass ? "✅" : "❌"} ${name}\n   ${detail}`);
};
const sleep = ms => new Promise(r => setTimeout(r, ms));

/* مقاسات شائعة: آيفون متوسّط، وأندرويد صغير، ولوحي */
const DEVICES = [
  { name: "iPhone 13/14", w: 390, h: 844, dpr: 3 },
  { name: "Android صغير", w: 360, h: 740, dpr: 2 },
  { name: "iPad", w: 820, h: 1180, dpr: 2 }
];

const b = await launch({ width: 420, height: 900 });
try {
  await b.open(URL, 2000);
  console.log(`   (${FILE})\n`);
  const boot = b.errors();
  check("إقلاع بلا أخطاء", boot.length === 0,
    boot.length ? boot.slice(0, 3).join(" | ") : "صفر خطأ");

  /* ---- التخطيط على كل مقاس ---- */
  for (const d of DEVICES) {
    await b.touchMode(d.w, d.h, d.dpr);
    await sleep(500);
    const r = await b.eval(`
      window.dispatchEvent(new Event('resize'));
      await new Promise(r=>setTimeout(r,250));
      const doc = document.documentElement;
      const bd = document.getElementById('board').getBoundingClientRect();
      const sides = [...document.querySelectorAll('.side')].map(s => {
        const q = s.getBoundingClientRect();
        return { w: Math.round(q.width), h: Math.round(q.height) };
      });
      // هل يوجد تمرير أفقي؟ وهو أسوأ عيب على الجوال
      const hScroll = doc.scrollWidth - doc.clientWidth;
      // أصغر هدف لمس بين الأزرار الظاهرة
      let minTap = 1e9, worst = '';
      document.querySelectorAll('button, select, input, .chip, .card')
        .forEach(el => {
          const q = el.getBoundingClientRect();
          if (q.width < 1 || q.height < 1) return;
          const m = Math.min(q.width, q.height);
          if (m < minTap) { minTap = m; worst = (el.id || el.className || el.tagName); }
        });
      return JSON.stringify({
        vw: doc.clientWidth, vh: doc.clientHeight,
        hScroll, boardW: Math.round(bd.width), boardH: Math.round(bd.height),
        sides, minTap: Math.round(minTap), worst: String(worst).slice(0, 28)
      });
    `).then(JSON.parse);
    check(`التخطيط — ${d.name} (${d.w}×${d.h})`,
      r.hScroll <= 1 && r.boardW > 0 && r.boardW <= r.vw + 1,
      `النافذة ${r.vw}×${r.vh} · اللوح ${r.boardW}×${r.boardH} · `
      + `تمرير أفقي ${r.hScroll}px · أصغر هدف لمس ${r.minTap}px `
      + `(${r.worst})`);
    await b.shot(SHOT + `mobile-${d.w}.png`,
      Math.min(d.w, 2000), Math.min(d.h, 2000));
  }

  /* ---- اللمس: إضافة نقشة وسحبها بالإصبع ---- */
  await b.touchMode(390, 844, 3);
  await sleep(400);
  const setup = await b.eval(`
    localStorage.clear();
    state.cut='blazer'; state.piece='front'; syncPieceLength();
    state.items.length=0; renderPieces(); draw(); renderList();
    // بطاقة من المكتبة
    const card = document.querySelector('#lib .card');
    card.scrollIntoView({block:'center'});
    await new Promise(r=>setTimeout(r,250));
    const q = card.getBoundingClientRect();
    return JSON.stringify({x:Math.round(q.left+q.width/2),
      y:Math.round(q.top+q.height/2), w:Math.round(q.width)});
  `).then(JSON.parse);

  await b.tap(setup.x, setup.y);
  await sleep(500);
  const added = await b.eval(`JSON.stringify({n: state.items.length,
    sel: state.sel != null})`).then(JSON.parse);
  check("لمس بطاقة المكتبة يُضيف النقشة",
    added.n === 1 && added.sel,
    `عدد النقشات بعد اللمس = ${added.n} · ومحدّدة = ${added.sel}`);

  const pos = await b.eval(`
    const it = state.items[0];
    it.x = 0; it.y = 500; it.scale = .4; select(it.uid); draw();
    document.getElementById('stage').scrollIntoView({block:'center'});
    await new Promise(r=>setTimeout(r,300));
    const g = board.querySelector('[data-stack="'+it.uid+'"]');
    const q = g.getBoundingClientRect();
    return JSON.stringify({x:Math.round(q.left+q.width/2),
      y:Math.round(q.top+q.height/2), x0:it.x, y0:it.y,
      scrollY: window.scrollY});
  `).then(JSON.parse);

  await b.touchDrag(pos.x, pos.y, pos.x + 40, pos.y - 60, 12);
  await sleep(300);
  const moved = await b.eval(`
    const it = state.items[0];
    return JSON.stringify({x:it.x, y:it.y, x0:${pos.x0}, y0:${pos.y0},
      scrollY: window.scrollY, scrolled: window.scrollY !== ${pos.scrollY}});
  `).then(JSON.parse);
  check("سحب النقشة بالإصبع يُحرّكها ولا يُمرّر الصفحة",
    (moved.x !== moved.x0 || moved.y !== moved.y0) && !moved.scrolled,
    `من (${moved.x0}, ${moved.y0}) إلى (${moved.x}, ${moved.y}) · `
    + `والصفحة لم تنزلق (${!moved.scrolled})`);

  /* ---- الممحاة باللمس: لا تحويم، فهل تظهر الدائرة؟ ---- */
  const er = await b.eval(`
    const it = state.items[0];
    select(it.uid); setBrush(.5); setEraseMode(true);
    renderPieces(); syncProps();
    const g = board.querySelector('[data-stack="'+it.uid+'"]');
    const q = g.getBoundingClientRect();
    return JSON.stringify({
      ringBefore: !!board.querySelector('.er-brush-ring'),
      x:Math.round(q.left+q.width/2), y:Math.round(q.top+q.height/2),
      h:Math.round(q.height)});
  `).then(JSON.parse);
  await b.touchDrag(er.x, er.y - er.h * 0.2, er.x, er.y + er.h * 0.2, 14);
  await sleep(300);
  const erAfter = await b.eval(`
    const it = state.items[0];
    return JSON.stringify({dots:(it.erase||[]).length,
      strokes: strokeCount(it),
      ringNow: !!board.querySelector('.er-brush-ring')});
  `).then(JSON.parse);
  check("الممحاة تمحو باللمس",
    erAfter.dots > 1 && erAfter.strokes === 1,
    `${erAfter.dots} نقطة في ${erAfter.strokes} مسحة · `
    + `الدائرة قبل اللمس: ${er.ringBefore} (لا تحويم على اللمس) · `
    + `بعده: ${erAfter.ringNow}`);
  await b.shot(SHOT + "mobile-eraser.png", 390, 844);

  /* ---- الطباعة تعمل على الجوال ---- */
  const pr = await b.eval(`
    setEraseMode(false);
    printMotifs(state.items);
    const n = document.querySelectorAll('#printRoot .pg').length;
    const vis = !document.getElementById('printView').hidden;
    const bar = document.querySelector('.pv-bar');
    const bw = bar ? Math.round(bar.getBoundingClientRect().width) : 0;
    const overflow = document.documentElement.scrollWidth
      - document.documentElement.clientWidth;
    return JSON.stringify({sheets:n, vis, barW:bw, overflow,
      vw: document.documentElement.clientWidth});
  `).then(JSON.parse);
  check("معاينة الطباعة تظهر على مقاس الهاتف",
    pr.vis && pr.sheets >= 1,
    `${pr.sheets} ورقة · شريط الأدوات ${pr.barW}px في نافذة ${pr.vw}px · `
    + `زيادة أفقية ${pr.overflow}px`);
  await b.shot(SHOT + "mobile-print.png", 390, 844);

  const errs = b.errors();
  check("لا أخطاء جافاسكربت", errs.length === 0,
    errs.length ? errs.slice(0, 4).join(" | ") : "صفر خطأ");

} finally { await b.close(); }

const bad = out.filter(r => !r.pass);
console.log("\n" + "=".repeat(64));
console.log(`المحصّلة: ${out.length - bad.length}/${out.length} سليم`
  + (bad.length ? ` · ${bad.length} فاشل` : " · صفر فاشل"));
console.log(`اللقطات: ${SHOT}mobile-*.png`);
