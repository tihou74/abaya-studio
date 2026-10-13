/* اختبار مكتبة التصاميم: الحفظ، والفتح، والبقاء بعد إعادة التحميل،
   والنسخة الاحتياطية.

   أهمّ اختبار هنا هو **إعادة تحميل الصفحة فعلياً** بعد الحفظ، لا
   قراءة localStorage مباشرةً — فالمطلوب أن تجد المستخدمة عبايتها
   بعد أن تُغلق البرنامج وتعود إليه.

   شغّلي:  env -u NODE_OPTIONS node tools/audit_designs.mjs [ملف]    */
import { launch } from "./cdp.mjs";

const FILE = process.argv[2] || "designer.html";
const URL = "file:///projects/sandbox/abaya-motifs/panel/" + FILE;
const out = [];
const check = (name, pass, detail) => {
  out.push({ name, pass, detail });
  console.log(`${pass ? "✅" : "❌"} ${name}\n   ${detail}`);
};
const sleep = ms => new Promise(r => setTimeout(r, ms));

const b = await launch({ width: 1400, height: 900 });
try {
  await b.open(URL, 1900);
  console.log(`   (${FILE})\n`);
  // النوافذ المنبثقة تُعطَّل: prompt/confirm تُجمّد الصفحة في الاختبار
  const stub = `
    window.__asked = [];
    window.prompt = (q, d) => { window.__asked.push(['prompt', q]);
      return window.__promptWith !== undefined ? window.__promptWith : d; };
    window.confirm = q => { window.__asked.push(['confirm', q]);
      return window.__confirmWith !== false; };
    window.alert = m => { window.__asked.push(['alert', m]); };
    return 1;`;
  await b.eval(stub);

  const boot = b.errors();
  check("إقلاع بلا أخطاء", boot.length === 0,
    boot.length ? boot.slice(0, 3).join(" | ") : "صفر خطأ");

  /* ١ · حفظ عبايتين مختلفتين */
  const saved = await b.eval(`
    localStorage.clear();
    designs = { seq: 1, list: [] }; curDesignId = null;
    // العباية الأولى: بليزر بنقشتين
    state.cut='blazer'; state.piece='front'; syncPieceLength();
    state.items.length=0; state.abayaColor='#1c1c22';
    addMotif('B001'); state.items[0].x=-50; state.items[0].y=600;
    addMotif('B027'); state.items[1].x=0; state.items[1].y=250;
    const e1 = saveDesignAs('My blazer');
    // العباية الثانية: كلوش بنقشة واحدة
    curDesignId = null;
    state.cut='closh'; state.piece='front'; syncPieceLength();
    state.items.length=0; state.abayaColor='#5b4b3f';
    addMotif('D001'); state.items[0].x=30; state.items[0].y=500;
    const e2 = saveDesignAs('Closh gold');
    return JSON.stringify({n: designs.list.length,
      names: designs.list.map(d=>d.name),
      cuts: designs.list.map(d=>d.data.cut),
      counts: designs.list.map(d=>d.data.items.length),
      cur: curDesignId, e1: !!e1, e2: !!e2});
  `).then(JSON.parse);
  check("حفظ عبايتين مستقلّتين",
    saved.n === 2 && saved.names.includes("My blazer")
      && saved.names.includes("Closh gold")
      && saved.cuts.includes("blazer") && saved.cuts.includes("closh"),
    `${saved.n} عباية: ${saved.names.join(" · ")} · `
    + `القصّات ${saved.cuts.join(",")} · عدد النقشات ${saved.counts.join(",")}`);

  /* ٢ · البقاء بعد إعادة تحميل الصفحة فعلياً */
  await b.open(URL, 1900);
  await b.eval(stub);
  const afterReload = await b.eval(`JSON.stringify({
    n: designs.list.length,
    names: designs.list.map(d=>d.name),
    counts: designs.list.map(d=>d.data.items.length),
    badge: document.getElementById('designCount').textContent
  })`).then(JSON.parse);
  check("العبايات تبقى بعد إغلاق البرنامج وإعادة فتحه",
    afterReload.n === 2 && afterReload.names.includes("My blazer"),
    `بعد إعادة التحميل: ${afterReload.n} عباية `
    + `[${afterReload.names.join(" · ")}] · والعدّاد يُظهر `
    + `«${afterReload.badge}»`);

  /* ٣ · فتح عباية يُعيد كل شيء */
  const opened = await b.eval(`
    const target = designs.list.find(d => d.name === 'My blazer');
    window.__confirmWith = false;      // لا حفظ للعمل الحالي
    openDesign(target.id);
    return JSON.stringify({
      cut: state.cut, piece: state.piece, color: state.abayaColor,
      items: state.items.length,
      mids: state.items.map(i=>i.mid),
      pos: state.items.map(i=>[i.x,i.y]),
      cur: curDesignId === target.id,
      label: document.getElementById('curDesign').textContent,
      onBoard: board.querySelectorAll('.motif-wrap').length
    });
  `).then(JSON.parse);
  check("فتح عباية يُعيد القصّة والألوان والنقشات ومواضعها",
    opened.cut === "blazer" && opened.items === 2
      && opened.color === "#1c1c22" && opened.cur
      && JSON.stringify(opened.pos) === JSON.stringify([[-50,600],[0,250]]),
    `القصّة ${opened.cut}/${opened.piece} · اللون ${opened.color} · `
    + `${opened.items} نقشة [${opened.mids.join(",")}] عند `
    + `${JSON.stringify(opened.pos)} · على اللوح ${opened.onBoard} · `
    + `الترويسة: «${opened.label}»`);

  /* ٤ · التعديل يُحدَّث آلياً بلا زرّ */
  const autoUpd = await b.eval(`
    const id = curDesignId;
    const before = designs.list.find(d=>d.id===id).data.items.length;
    addMotif('B013');
    state.items[state.items.length-1].x = 90;
    save();
    await new Promise(r=>setTimeout(r,120));
    const stored = JSON.parse(localStorage.getItem('abaya-designs-v1'));
    const e = stored.list.find(d=>d.id===id);
    return JSON.stringify({before, after: e.data.items.length,
      lastX: e.data.items[e.data.items.length-1].x});
  `).then(JSON.parse);
  check("التعديل على عباية مفتوحة يُحفظ آلياً",
    autoUpd.after === autoUpd.before + 1 && autoUpd.lastX === 90,
    `كانت ${autoUpd.before} نقشة وصارت ${autoUpd.after} في المخزن، `
    + `وآخر نقشة عند x=${autoUpd.lastX} — بلا ضغط أي زرّ`);

  /* ٥ · «جديد» لا يمحو عملاً غير محفوظ */
  const newGuard = await b.eval(`
    curDesignId = null;
    state.items.length = 0;
    addMotif('B005');
    const n0 = designs.list.length;
    window.__asked = [];
    window.__confirmWith = true;            // نعم، احفظ أوّلاً
    window.__promptWith = 'Rescued abaya';
    document.getElementById('btnReset').click();
    return JSON.stringify({before: n0, after: designs.list.length,
      names: designs.list.map(d=>d.name),
      items: state.items.length,
      asked: window.__asked.map(a=>a[0])});
  `).then(JSON.parse);
  check("«جديد» يعرض حفظ العمل غير المحفوظ قبل محوه",
    newGuard.after === newGuard.before + 1
      && newGuard.names.includes("Rescued abaya")
      && newGuard.items === 0,
    `كانت ${newGuard.before} عباية فصارت ${newGuard.after} `
    + `وفيها «Rescued abaya» · واللوح فُرِّغ (${newGuard.items} نقشة) · `
    + `الأسئلة: ${newGuard.asked.join(",")}`);

  /* ٦ · تسمية ونسخ وحذف */
  const crud = await b.eval(`
    const t = designs.list.find(d=>d.name==='Closh gold');
    window.__promptWith = 'Closh renamed';
    renameDesign(t.id);
    const renamed = designs.list.find(d=>d.id===t.id).name;
    duplicateDesign(t.id);
    const copies = designs.list.filter(d=>d.name.indexOf('Closh renamed')===0);
    window.__confirmWith = true;
    const victim = copies.find(d=>d.name.indexOf('(copy)')>0);
    deleteDesign(victim.id);
    return JSON.stringify({renamed,
      copyMade: copies.length === 2,
      afterDelete: designs.list.filter(d=>d.name.indexOf('(copy)')>0).length,
      total: designs.list.length});
  `).then(JSON.parse);
  check("تسمية ونسخ وحذف العبايات",
    crud.renamed === "Closh renamed" && crud.copyMade
      && crud.afterDelete === 0,
    `أُعيدت التسمية إلى «${crud.renamed}» · النسخة أُنشئت `
    + `(${crud.copyMade}) ثم حُذفت (المتبقّي ${crud.afterDelete}) · `
    + `المجموع ${crud.total}`);

  /* ٧ · النسخة الاحتياطية ذهاباً وعودةً */
  const backup = await b.eval(`
    const text = JSON.stringify({ app:'abaya-designer', kind:'designs',
      version:1, designs: designs });
    const n0 = designs.list.length;
    importDesigns(text);                     // تُضاف ولا تُستبدل
    return JSON.stringify({before:n0, after: designs.list.length,
      doubled: designs.list.length === n0*2});
  `).then(JSON.parse);
  check("استعادة النسخة الاحتياطية تُضيف ولا تمحو",
    backup.doubled,
    `كانت ${backup.before} عباية فصارت ${backup.after} بعد الاستعادة — `
    + `أُضيفت كلها ولم يُستبدل شيء`);

  /* ٨ · الواجهة: البطاقات والمصغّرات */
  const ui = await b.eval(`
    openDesigns();
    await new Promise(r=>setTimeout(r,400));
    const cards = document.querySelectorAll('.dv-card').length;
    const thumbs = document.querySelectorAll('.dv-thumb svg').length;
    const motifsInThumbs = document.querySelectorAll('.dv-thumb svg .motif-wrap').length;
    const vis = !document.getElementById('designsView').hidden;
    closeDesigns();
    return JSON.stringify({cards, thumbs, motifsInThumbs, vis,
      listed: designs.list.length});
  `).then(JSON.parse);
  check("نافذة «عباياتي» تعرض بطاقةً ومصغّرةً لكل عباية",
    ui.vis && ui.cards === ui.listed && ui.thumbs > 0
      && ui.motifsInThumbs > 0,
    `${ui.cards} بطاقة لـ${ui.listed} عباية · ${ui.thumbs} مصغّرة `
    + `فيها ${ui.motifsInThumbs} نقشة مرسومة`);

  /* ٩ · المصغّرة لا تُفسد حالة العمل */
  const noSide = await b.eval(`
    state.cut='blazer'; state.piece='sketchF'; syncPieceLength();
    state.items.length=0; addMotif('B021');
    const snap = JSON.stringify({cut:state.cut, piece:state.piece,
      len:state.lenCm, n:state.items.length, sel:state.sel,
      color:state.abayaColor});
    designs.list.forEach(d => designThumb(d.data));
    const after = JSON.stringify({cut:state.cut, piece:state.piece,
      len:state.lenCm, n:state.items.length, sel:state.sel,
      color:state.abayaColor});
    return JSON.stringify({same: snap === after, snap, after});
  `).then(JSON.parse);
  check("رسم المصغّرات لا يُغيّر ما تعملين عليه",
    noSide.same,
    noSide.same ? `الحالة قبل الرسم وبعده متطابقة: ${noSide.snap}`
      : `اختلفت!\n   قبل: ${noSide.snap}\n   بعد: ${noSide.after}`);

  /* ١٠ · امتلاء الحصّة يُبلَّغ ولا يُفقد بصمت */
  const quota = await b.eval(`
    const orig = localStorage.setItem.bind(localStorage);
    window.__asked = [];
    localStorage.setItem = (k, v) => {
      if (k === 'abaya-designs-v1') {
        const e = new Error('Quota'); e.name = 'QuotaExceededError'; throw e;
      }
      return orig(k, v);
    };
    const ok = persistDesigns();
    localStorage.setItem = orig;
    return JSON.stringify({ok, warn: (document.getElementById('dvWarn')||{}).textContent || '',
      alerted: window.__asked.some(a=>a[0]==='alert')});
  `).then(JSON.parse);
  check("امتلاء الحصّة يُبلَّغ بوضوح", quota.alerted && !quota.ok,
    `أرجعت الدالّة ${quota.ok} وأبلغت المستخدمة (${quota.alerted}) · `
    + `التنبيه: «${String(quota.warn).slice(0, 70)}»`);

  const errs = b.errors();
  check("لا أخطاء جافاسكربت", errs.length === 0,
    errs.length ? errs.slice(0, 4).join(" | ") : "صفر خطأ");

} finally { await b.close(); }

const bad = out.filter(r => !r.pass);
console.log("\n" + "=".repeat(64));
console.log(`المحصّلة: ${out.length - bad.length}/${out.length} سليم`
  + (bad.length ? ` · ${bad.length} فاشل` : " · صفر فاشل"));
