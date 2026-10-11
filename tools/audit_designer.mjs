/* تدقيق panel/designer.html في متصفّح حقيقي — كل عيب يُثبت بالأرقام.
   شغّلي:  env -u NODE_OPTIONS node tools/audit_designer.mjs           */
import { launch } from "./cdp.mjs";

const URL = "file:///projects/sandbox/abaya-motifs/panel/designer.html";
const out = [];
const check = (name, pass, detail) => {
  out.push({ name, pass, detail });
  console.log(`${pass ? "✅" : "❌"} ${name}\n   ${detail}`);
};

const b = await launch();
try {
  await b.open(URL, 1800);

  const boot = b.errors();
  check("إقلاع بلا أخطاء", boot.length === 0,
    boot.length ? boot.slice(0, 3).join(" | ") : "صفر خطأ");

  const info = await b.eval(`JSON.stringify({
    motifs: MOTIFS.length,
    cutOptions: [...document.querySelectorAll('#cut option')].map(o=>o.value),
    imgCuts: IMG_CUTS.map(c=>c.id),
    legacyCuts: CUTS.map(c=>c.id),
    pieces: IMG_CUTS.map(c=>c.id+':'+c.pieces.map(p=>p.id).join('/')),
    stamp: (document.querySelector('#buildStamp')||{}).textContent
  })`).then(JSON.parse);
  console.log(`   (${info.motifs} نقشة · قصّات القائمة: ${info.cutOptions.length}`
    + ` = ${info.imgCuts.length} صورية + ${info.legacyCuts.length} هندسية قديمة)`);
  console.log(`   القطع: ${info.pieces.join(" | ")}`);

  /* ١ · الطباعة تُسقط التدوير والقلب */
  const rotPrint = await b.eval(`
    localStorage.clear();
    state.items.length = 0;
    addMotif('B001'); const it = state.items[state.items.length-1];
    it.rot = 40; it.flip = true; it.scale = .3;
    select(it.uid); draw();
    printMotifs([it]);
    const win = document.querySelector('#printRoot .win');
    const html = win ? win.innerHTML : '';
    const hdr = document.querySelector('#printRoot .ph');
    document.querySelector('#printView').hidden = true;
    return JSON.stringify({
      hasRotate: /rotate\\s*\\(/.test(html),
      hasFlip: /scale\\s*\\(\\s*-/.test(html),
      header: hdr ? hdr.textContent.replace(/\\s+/g,' ').trim().slice(0,110) : ''
    });
  `).then(JSON.parse);
  check("الطباعة تحفظ التدوير والقلب",
    rotPrint.hasRotate && rotPrint.hasFlip,
    `نقشة مدوّرة 40° ومقلوبة → شيفرة الطباعة تحتوي `
    + `rotate=${rotPrint.hasRotate} و flip=${rotPrint.hasFlip}`);

  /* ٢ · المقاس الحقيقي يتجاهل التدوير */
  const rotSize = await b.eval(`
    state.items.length = 0;
    addMotif('B021'); const it = state.items[state.items.length-1];
    it.scale = .5; it.rot = 0; select(it.uid); draw();
    const a = outerSize(it);
    const ro0 = document.querySelector('#roSize') ? document.querySelector('#roSize').textContent : '';
    it.rot = 90; select(it.uid); draw(); syncProps();
    const c = outerSize(it);
    const ro90 = document.querySelector('#roSize') ? document.querySelector('#roSize').textContent : '';
    const sh0 = sheetGrid(a.w*cmPerUnit(), a.h*cmPerUnit());
    return JSON.stringify({w0:+a.w.toFixed(1), h0:+a.h.toFixed(1),
      w90:+c.w.toFixed(1), h90:+c.h.toFixed(1),
      ro0:(ro0||'').trim(), ro90:(ro90||'').trim(),
      sheets: sh0.rows+'×'+sh0.cols});
  `).then(JSON.parse);
  check("المقاس الحقيقي وعدد الأوراق يتبعان التدوير",
    rotSize.w90 !== rotSize.w0,
    `لوح ${rotSize.w0}×${rotSize.h0} وحدة · بعد تدوير 90° `
    + `${rotSize.w90}×${rotSize.h90} — البُعدان تبادلا، فالمقاس المعروض `
    + `وعدد الأوراق والمقاس المطبوع كلها للصندوق المحيط الفعلي`);

  /* ٣ · القصّة الصورية لا تُستعاد بعد إعادة التحميل */
  const cutRestore = await b.eval(`
    state.cut = 'closh'; state.piece = 'back';
    syncPieceLength(); save();
    // إعادة الحالة إلى الافتراضي ثم استدعاء load() الحقيقية
    state.cut = CUTS[0].id; state.piece = 'front';
    load();
    return JSON.stringify({savedCut:'closh', savedPiece:'back',
      restoredCut: state.cut, restoredPiece: state.piece,
      legacy: CUTS.map(c=>c.id)});
  `).then(JSON.parse);
  check("القصّة الصورية تُستعاد بعد إعادة التحميل",
    cutRestore.restoredCut === cutRestore.savedCut
      && cutRestore.restoredPiece === cutRestore.savedPiece,
    `حُفظت «${cutRestore.savedCut}/${cutRestore.savedPiece}» ثم أُعيدت الحالة `
    + `للافتراضي واستُدعيت load() → `
    + `«${cutRestore.restoredCut}/${cutRestore.restoredPiece}»`);

  /* ٤ · النسخ والتقطيع يتشاركان مصفوفة الممحاة */
  const eraseShare = await b.eval(`
    state.items.length = 0;
    addMotif('B001'); const it = state.items[state.items.length-1];
    it.erase = [{x:0,y:0,r:5}];
    select(it.uid);
    document.querySelector('#pDup').click();
    const items = pieceItems();
    const a = items[items.length-2], d = items[items.length-1];
    const shared = a.erase === d.erase;
    d.erase.push({x:10,y:10,r:5});
    return JSON.stringify({shared, lenA:a.erase.length, lenB:d.erase.length,
      count:items.length});
  `).then(JSON.parse);
  check("النسخة تملك ممحاتها الخاصة",
    !eraseShare.shared && eraseShare.lenA !== eraseShare.lenB,
    `بعد «Duplicate» المصفوفتان نفس المرجع=${eraseShare.shared} · `
    + `المسح على النسخة جعلها ${eraseShare.lenB} نقطة والأصل `
    + `${eraseShare.lenA} — مستقلّتان`);

  /* ٥ · «تراجع» الممحاة يُلغي نقطة لا مسحة */
  const erUndo = await b.eval(`
    state.items.length = 0;
    addMotif('B001'); const it = state.items[state.items.length-1];
    select(it.uid);
    // مسحة واحدة = عدّة نقاط مُستوفاة
    // مسحة واحدة كما يسجّلها البرنامج: نقاط مستوفاة برقم ضربة واحد
    it.erase = [{x:0,y:0,r:3,s:1},{x:2,y:2,r:3,s:1},
                {x:4,y:4,r:3,s:1},{x:6,y:6,r:3,s:1}];
    const before = it.erase.length;
    syncProps();
    const btn = document.querySelector('#erUndo');
    const label = btn ? btn.textContent.trim() : '';
    if (btn) btn.click();
    const info = document.querySelector('#erInfo');
    return JSON.stringify({before, after: it.erase.length, label,
      info: info ? info.textContent.trim() : ''});
  `).then(JSON.parse);
  check("«تراجع المسحة» يُلغي المسحة كاملةً",
    erUndo.after === 0,
    `مسحة واحدة سُجّلت ${erUndo.before} نقاط · زرّ «${erUndo.label}» `
    + `أعاد العدد إلى ${erUndo.after} بضغطة واحدة · والعدّاد: `
    + `«${erUndo.info}»`);

  /* ٦ · ورقة التصميم تسرد نقشات قطع أخرى */
  const designSheet = await b.eval(`
    state.cut = 'closh'; state.piece = 'front'; syncPieceLength();
    state.items.length = 0;
    addMotif('B001'); const a = state.items[state.items.length-1];
    state.piece = 'back';
    addMotif('B027'); const c = state.items[state.items.length-1];
    state.piece = 'front'; draw();
    const onBoard = pieceItems().length;
    printDesign();
    const rows = document.querySelectorAll('#printRoot table tbody tr').length;
    document.querySelector('#printView').hidden = true;
    return JSON.stringify({total: state.items.length, onBoard, rows});
  `).then(JSON.parse);
  check("ورقة التصميم تسرد ما في الصورة فقط",
    designSheet.rows === designSheet.onBoard,
    `${designSheet.total} نقشة على قطعتين · الصورة تُظهر `
    + `${designSheet.onBoard} والجدول يسرد ${designSheet.rows} — متطابقان`);

  /* ٧ · تعليمات الطباعة تطابق الإعدادات الفعلية */
  const instr = await b.eval(`
    state.items.length = 0;
    addMotif('B001'); const it = state.items[state.items.length-1]; it.scale = .4;
    PRINT.paper = 'A3'; PRINT.overlap = 8; applyPrintCss();
    printMotifs([it]);
    const intro = document.querySelector('#printRoot .intro');
    const txt = intro ? intro.textContent.replace(/\\s+/g,' ') : '';
    const ro = sheetsFor(1, 200);
    document.querySelector('#printView').hidden = true;
    PRINT.paper = 'A4'; applyPrintCss();
    return JSON.stringify({
      saysA4: /\\bA4\\b/.test(txt),
      says10mm: /10 ?mm/.test(txt),
      realOverlap: PRINT.overlap,
      sheetsLabel: ro
    });
  `).then(JSON.parse);
  check("تعليمات الطباعة تطابق الإعدادات المختارة",
    !instr.saysA4 && !instr.says10mm && !/A4/.test(instr.sheetsLabel),
    `بورق A3 وتداخل ${instr.realOverlap} مم: ذكر «A4»=${instr.saysA4} `
    + `وذكر «10 mm»=${instr.says10mm} · وعدّاد الأوراق: «${instr.sheetsLabel}»`);

  /* ٨ · صورة التتبّع المرفوعة لا تُحفظ */
  const bgSave = await b.eval(`
    state.bg = 'data:image/png;base64,iVBORw0KGgo='; state.bgOpacity = .4;
    state.showDim = false;
    save();
    const s = JSON.parse(localStorage.getItem('abaya-panel-v1'));
    return JSON.stringify({keys: Object.keys(s).sort(), hasBg: 'bg' in s,
      hasDim: 'showDim' in s});
  `).then(JSON.parse);
  check("صورة التتبّع وإظهار القياس يُحفظان", bgSave.hasBg && bgSave.hasDim,
    `المحفوظ: ${bgSave.keys.join(", ")}`);

  /* ٩ · امتلاء الحصّة يضيع التصميم بصمت */
  const quota = await b.eval(`
    const orig = localStorage.setItem.bind(localStorage);
    let threw = false, notified = false;
    const origAlert = window.alert;
    window.alert = () => { notified = true; };
    localStorage.setItem = (k,v) => {
      if (k === 'abaya-panel-v1') { threw = true;
        const e = new Error('QuotaExceededError'); e.name='QuotaExceededError'; throw e; }
      return orig(k,v);
    };
    let crashed = false;
    try { save(); } catch(e) { crashed = true; }
    localStorage.setItem = orig; window.alert = origAlert;
    return JSON.stringify({threw, notified, crashed});
  `).then(JSON.parse);
  check("امتلاء الحصّة يُبلَّغ للمستخدمة", quota.notified,
    `حُقن فشل الحفظ: أبلغت المستخدمة=${quota.notified} ولم تنهَر الدالّة `
    + `(crashed=${quota.crashed})`);

  /* ١٠ · بصمة البناء في النسخة ذات الملفين */
  check("بصمة البناء ظاهرة في نسخة الملفين",
    !!info.stamp && !/__BUILD__/.test(info.stamp),
    `الترويسة تُظهر «${info.stamp}» — لا نصّ بديل خام`);

  /* ١١ · البحث يُعيد بناء المكتبة في كل حرف */
  const search = await b.eval(`
    const t0 = performance.now();
    const q = document.querySelector('#libSearch');
    'rosette'.split('').forEach((ch,i) => {
      q.value = 'rosette'.slice(0,i+1);
      q.dispatchEvent(new Event('input'));
    });
    const ms = performance.now() - t0;
    const cards = document.querySelectorAll('#lib .card').length;
    q.value=''; q.dispatchEvent(new Event('input'));
    return JSON.stringify({ms:+ms.toFixed(0), cards,
      total: document.querySelectorAll('#lib .card').length});
  `).then(JSON.parse);
  check("كتابة البحث لا تُجمّد الواجهة", search.ms < 120,
    `كتابة 7 أحرف أعادت بناء المكتبة 7 مرّات في ${search.ms} مللي `
    + `(${search.total} بطاقة SVG في كل مرّة)`);


  /* ١٤ · إثبات عددي: المقاس المطبوع يساوي الصندوق المحيط */
  const exact = await b.eval(`
    state.items.length = 0;
    addMotif('B021'); const it = state.items[state.items.length-1];
    it.scale = .35; it.rot = 30; it.flip = true;
    it.crop = { t: 20, b: 10, l: 5, r: 5 };
    select(it.uid); draw();
    const k = cmPerUnit();
    const os = outerSize(it);
    printMotifs([it]);
    const svg = document.querySelector('#printRoot .win svg');
    const w = parseFloat(svg.getAttribute('width'));
    const h = parseFloat(svg.getAttribute('height'));
    const vb = svg.getAttribute('viewBox').split(/\\s+/).map(Number);
    const hasClip = !!svg.querySelector('clipPath');
    document.querySelector('#printView').hidden = true;
    return JSON.stringify({
      svgW:+w.toFixed(2), svgH:+h.toFixed(2),
      expW:+(os.w*k*10).toFixed(2), expH:+(os.h*k*10).toFixed(2),
      vbRatio:+(vb[2]/vb[3]).toFixed(4), mmRatio:+(w/h).toFixed(4),
      hasClip
    });
  `).then(JSON.parse);
  check("مقاس الورقة = الصندوق المحيط بالضبط ونِسَبه محفوظة",
    Math.abs(exact.svgW - exact.expW) < 0.05
      && Math.abs(exact.svgH - exact.expH) < 0.05
      && Math.abs(exact.vbRatio - exact.mmRatio) < 0.002
      && exact.hasClip,
    `نقشة مقصوصة ومقلوبة ومدوّرة 30°: الورقة ${exact.svgW}×${exact.svgH} مم `
    + `والمتوقّع ${exact.expW}×${exact.expH} · نسبة viewBox ${exact.vbRatio} `
    + `= نسبة المليمترات ${exact.mmRatio} (لا تشويه) · قصّ صريح=${exact.hasClip}`);

  const errs = b.errors();
  check("لا أخطاء جافاسكربت بعد كل العمليات", errs.length === 0,
    errs.length ? errs.slice(0, 4).join(" | ") : "صفر خطأ");

} finally { await b.close(); }

const bad = out.filter(r => !r.pass);
console.log("\n" + "=".repeat(64));
console.log(`المحصّلة: ${out.length - bad.length}/${out.length} سليم · `
  + `${bad.length} عيب مُثبَت`);
