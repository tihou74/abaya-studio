/* اختبار بنية القصّات: البناء الآلي للقطع، ومعامل كل وجه،
   والمعايرة، ورفض القصّة الناقصة.
   شغّلي:  env -u NODE_OPTIONS node tools/audit_cuts.mjs [ملف]       */
import { launch } from "./cdp.mjs";

const FILE = process.argv[2] || "designer.html";
const URL = "file:///projects/sandbox/abaya-motifs/panel/" + FILE;
const out = [];
const check = (name, pass, detail) => {
  out.push({ name, pass, detail });
  console.log(`${pass ? "✅" : "❌"} ${name}\n   ${detail}`);
};
const sleep = ms => new Promise(r => setTimeout(r, ms));

const b = await launch({ width: 1500, height: 940 });
try {
  await b.open(URL, 1900);
  await b.setSize(1500, 940);
  await sleep(300);
  console.log(`   (${FILE})`);

  const boot = b.errors();
  check("إقلاع بلا أخطاء", boot.length === 0,
    boot.length ? boot.slice(0, 3).join(" | ") : "صفر خطأ");

  /* ١ · القطع تُبنى آلياً من الأوجه */
  const built = await b.eval(`JSON.stringify({
    srcCount: window.ABAYA_CUTS.length,
    builtCount: IMG_CUTS.length,
    problems: CUT_PROBLEMS.length,
    closh: IMG_CUTS.find(c=>c.id==='closh').pieces.map(p=>p.id),
    thoub: IMG_CUTS.find(c=>c.id==='thoub').pieces.map(p=>p.id),
    srcHasPieces: 'pieces' in window.ABAYA_CUTS[0]
  })`).then(JSON.parse);
  check("القطع مشتقّة آلياً لا مكتوبة في البيانات",
    !built.srcHasPieces && built.builtCount === built.srcCount
      && built.closh.includes("sketchB") && !built.thoub.includes("sketchB")
      && built.closh.length === 6 && built.thoub.length === 5,
    `بيانات القصّة لا تحتوي pieces (${built.srcHasPieces}) · `
    + `الكلوش له وجهان فبُنيت له ${built.closh.length} قطعة `
    + `[${built.closh.join(", ")}] · والثوب وجه واحد فـ`
    + `${built.thoub.length} قطعة بلا sketchB — بلا تكرار يدوي`);

  /* ٢ · معامل القياس لكل وجه على حدة */
  const ppi = await b.eval(`
    const c = IMG_CUTS.find(x=>x.id==='closh');
    const f = facePPI(c,'front'), bk = facePPI(c,'back');
    const t = facePPI(IMG_CUTS.find(x=>x.id==='thoub'),'front');
    return JSON.stringify({
      front:+f.toFixed(4), back:+bk.toFixed(4), thoub:+t.toFixed(4),
      expFront:+(1026/58).toFixed(4), expBack:+(1018/58).toFixed(4),
      differ: f !== bk, hasLiteral: false
    });
  `).then(JSON.parse);
  check("معامل القياس يُحسب لكل وجه من ارتفاع صورته",
    Math.abs(ppi.front - ppi.expFront) < 1e-3
      && Math.abs(ppi.back - ppi.expBack) < 1e-3 && ppi.differ,
    `الأمامي ${ppi.front} (= 1026÷58) والخلفي ${ppi.back} (= 1018÷58) — `
    + `مختلفان كما يجب لأن ارتفاعي الصورتين مختلفان · والثوب `
    + `${ppi.thoub} — لا رقم مكتوب باليد`);

  /* ٣ · القصّة الناقصة تُرفض برسالة واضحة */
  const bad = await b.eval(`
    const probe = [
      { id:"no-front", name:"X", measures:{length:58,chest:24,shoulder:15,hem:50},
        faces:{ back:{src:"cuts/x.png",w:10,h:10} } },
      { id:"too-big", name:"Y", measures:{length:58,chest:24,shoulder:15,hem:50},
        faces:{ front:{src:"cuts/y.png",w:2400,h:3000} } },
      { id:"no-dims", name:"Z", measures:{length:58,chest:24,shoulder:15,hem:50},
        faces:{ front:{src:"cuts/z.png"} } },
      { id:"no-len",  name:"W", measures:{chest:24,shoulder:15,hem:50},
        faces:{ front:{src:"cuts/w.png",w:10,h:10} } },
      { id:"bad id",  name:"V", measures:{length:58,chest:24,shoulder:15,hem:50},
        faces:{ front:{src:"cuts/v.png",w:10,h:10} } }
    ];
    return JSON.stringify(probe.map(c => ({ id:c.id, errs: validateCut(c) })));
  `).then(JSON.parse);
  const txt = JSON.stringify(bad);
  check("القصّة الناقصة تُرفض بسبب مُسمّى",
    bad.every(r => r.errs.length > 0)
      && /size reference/.test(txt) && /2000px limit/.test(txt)
      && /check_png/.test(txt) && /not positive/.test(txt)
      && /latin, no spaces/.test(txt),
    bad.map(r => `${r.id}: ${r.errs[0]}`).join("\n   "));

  /* ٤ · المعايرة تُصحّح معامل وجه واحد فقط */
  const cal = await b.eval(`
    localStorage.clear();
    state.cut = 'closh'; state.piece = 'sketchF';
    syncPieceLength(); renderPieces();
    const c = imgCut();
    const beforeFront = facePPI(c,'front'), beforeBack = facePPI(c,'back');
    const beforeH = pieceInches().hIn;
    // البرنامج قاس 58″ والحقيقة 60″ → الوجه يجب أن يكبر بنسبة 60/58
    const okApply = applyCalibration(58, 60);
    const afterFront = facePPI(c,'front'), afterBack = facePPI(c,'back');
    const afterH = pieceInches().hIn;
    return JSON.stringify({
      okApply, face: calibratableFace(),
      beforeH:+beforeH.toFixed(3), afterH:+afterH.toFixed(3),
      ratio:+(afterH/beforeH).toFixed(4), expected:+(60/58).toFixed(4),
      backUnchanged: Math.abs(beforeBack-afterBack) < 1e-9,
      calibVal:+(c.calib.front).toFixed(5)
    });
  `).then(JSON.parse);
  check("المعايرة تُصحّح الوجه المعروض وحده",
    cal.okApply && Math.abs(cal.ratio - cal.expected) < 1e-3
      && cal.backUnchanged,
    `الوجه «${cal.face}»: ${cal.beforeH}″ → ${cal.afterH}″ `
    + `(النسبة ${cal.ratio} = المتوقّع ${cal.expected}) · `
    + `والوجه الخلفي لم يتأثّر (${cal.backUnchanged}) · `
    + `المعامل المحفوظ ${cal.calibVal}`);

  /* ٥ · المعايرة تُحفظ وتُستعاد */
  const persist = await b.eval(`
    save();
    const raw = JSON.parse(localStorage.getItem('abaya-panel-v1'));
    const row = (raw.circ||[]).find(r=>r.id==='closh');
    const c = imgCut();
    const saved = row && row.calib ? row.calib.front : null;
    // إعادة إلى الأصل ثم استعادة
    c.calib = {};
    load();
    return JSON.stringify({saved: saved!=null ? +saved.toFixed(5) : null,
      restored: c.calib.front!=null ? +c.calib.front.toFixed(5) : null});
  `).then(JSON.parse);
  check("المعايرة تُحفظ وتُستعاد",
    persist.saved != null && persist.restored === persist.saved,
    `المحفوظ ${persist.saved} والمستعاد ${persist.restored}`);

  /* ٦ · الإرجاع يُلغي المعايرة */
  const reset = await b.eval(`
    resetCalibration();
    const c = imgCut();
    return JSON.stringify({calib: c.calib.front == null,
      h:+pieceInches().hIn.toFixed(2)});
  `).then(JSON.parse);
  check("إرجاع المعايرة يعيد المعامل الأصلي",
    reset.calib && Math.abs(reset.h - 58) < 0.01,
    `حُذف المعامل (${reset.calib}) والوجه عاد ${reset.h}″ = الطول المُعطى`);

  /* ٧ · المعايرة لا تظهر على القطع المحسوبة من المقاسات */
  const scope = await b.eval(`
    const r = {};
    ['front','flat','sleeve','sketchF'].forEach(pid => {
      state.piece = pid; renderPieces();
      r[pid] = calibratableFace();
    });
    state.piece = 'front'; renderPieces();
    return JSON.stringify(r);
  `).then(JSON.parse);
  check("المعايرة محصورة برسوم المرجع",
    scope.front === null && scope.flat === null && scope.sleeve === null
      && scope.sketchF === "front",
    `الجسم=${scope.front} · المفروشة=${scope.flat} · الكُمّ=${scope.sleeve} `
    + `· الرسم=${scope.sketchF} — فالقطع المحسوبة من المقاسات لا تُعاير`);

  /* ٨ · صور القصّات محمَّلة فعلاً (المسار أو data URL) */
  const imgs = await b.eval(`
    state.cut='closh'; state.piece='sketchF'; syncPieceLength(); draw();
    await new Promise(r=>setTimeout(r,500));
    const im = board.querySelector('image');
    const href = im ? (im.getAttribute('href')||'') : '';
    return JSON.stringify({
      found: !!im,
      kind: href.startsWith('data:') ? 'data-url' : (href ? 'path' : 'none'),
      w: im ? +im.getAttribute('width') : 0
    });
  `).then(JSON.parse);
  check("صورة الوجه تُعرض على اللوح",
    imgs.found && imgs.kind !== "none" && imgs.w > 0,
    `نوع المصدر: ${imgs.kind} · عرض العنصر ${imgs.w} وحدة`);

  /* ٩ · كل القصّات تمرّ بكل قطعها بلا خطأ */
  const sweep = await b.eval(`
    const log = [];
    for (const c of IMG_CUTS) {
      for (const pc of c.pieces) {
        state.cut = c.id; state.piece = pc.id;
        syncPieceLength(); renderPieces(); draw(); syncProps(); renderList();
        const pi = pieceInches();
        log.push(c.id+'/'+pc.id+'='+pi.wIn.toFixed(1)+'x'+pi.hIn.toFixed(1));
      }
    }
    const expected = IMG_CUTS.reduce((a,c)=>a+c.pieces.length,0);
    return JSON.stringify({n: log.length, expected, log});
  `).then(JSON.parse);
  const errs2 = b.errors();
  check("كل القصّات بكل قطعها تُعرض بلا خطأ",
    errs2.length === 0 && sweep.n === sweep.expected && sweep.n > 0,
    `${sweep.n}/${sweep.expected} قطعة: ${sweep.log.join(" · ")}`);


  /* ١٠ · اتفاقية الشفافية: الخلفية شفّافة والجسم مُعتِم */
  const alpha = await b.eval(`
    const out = [];
    for (const c of IMG_CUTS) {
      for (const fk of Object.keys(c.faces)) {
        const f = c.faces[fk];
        const img = new Image();
        img.src = f.src;
        await new Promise(ok => { img.onload = ok; img.onerror = ok; });
        if (!img.naturalWidth) { out.push({id:c.id+'/'+fk, load:false}); continue; }
        const W = img.naturalWidth, H = img.naturalHeight;
        const cv = document.createElement('canvas');
        cv.width = W; cv.height = H;
        const ctx = cv.getContext('2d');
        ctx.drawImage(img, 0, 0);
        const px = ctx.getImageData(0,0,W,H).data;
        const A = (x,y) => px[((y*W+x)*4)+3];
        let trans = 0;
        for (let i=3;i<px.length;i+=4) if (px[i] < 24) trans++;
        out.push({ id: c.id+'/'+fk, load: true,
          corner: A(1,1), center: A(Math.floor(W/2), Math.floor(H*0.55)),
          transPct: +(trans/(W*H)*100).toFixed(1) });
      }
    }
    return JSON.stringify(out);
  `).then(JSON.parse);
  const alphaOk = alpha.every(a => a.load && a.corner < 24 && a.center > 200
    && a.transPct > 3 && a.transPct < 80);
  check("صور القصّات: خلفية شفّافة وجسم مُعتِم",
    alphaOk,
    alpha.map(a => a.load
      ? `${a.id}: زاوية=${a.corner} مركز=${a.center} شفاف=${a.transPct}%`
      : `${a.id}: لم تُحمَّل`).join("\n   "));

} finally { await b.close(); }

const bad2 = out.filter(r => !r.pass);
console.log("\n" + "=".repeat(64));
console.log(`المحصّلة: ${out.length - bad2.length}/${out.length} سليم`
  + (bad2.length ? ` · ${bad2.length} فاشل` : " · صفر فاشل"));
