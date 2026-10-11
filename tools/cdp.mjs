/* سائق Chrome DevTools Protocol بلا أي اعتماديات خارجية.
   الصندوق بلا إنترنت فلا يمكن تثبيت playwright، لكن Node 22 يملك
   WebSocket مدمجاً وChromium موجود في /opt/playwright — فهذا يكفي
   لتشغيل اللوحة في متصفّح حقيقي وتنفيذ شيفرة داخلها.

   الاستخدام:
     const b = await launch();
     await b.open('file:///path/page.html');
     const v = await b.eval('document.title');
     await b.shot('/tmp/x.png', 1200, 900);
     await b.close();
*/
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME = process.env.CHROME
  || "/opt/playwright/chromium-1232/chrome-linux64/chrome";

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function fetchJSON(url, tries = 60) {
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(url);
      if (r.ok) return await r.json();
    } catch { /* المتصفّح لم يرفع المنفذ بعد */ }
    await sleep(250);
  }
  throw new Error("لم يستجب المتصفّح على منفذ التنقيح: " + url);
}

export async function launch({ width = 1440, height = 980 } = {}) {
  const port = 9222 + Math.floor(Math.random() * 2000);
  const profile = mkdtempSync(join(tmpdir(), "cdp-"));
  const proc = spawn(CHROME, [
    "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
    "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
    "--disable-extensions", "--allow-file-access-from-files",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    `--window-size=${width},${height}`,
    "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  const stderr = [];
  proc.stderr.on("data", d => stderr.push(String(d)));

  const info = await fetchJSON(`http://127.0.0.1:${port}/json/version`);
  const ws = new WebSocket(info.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.onopen = res;
    ws.onerror = () => rej(new Error("فشل الاتصال بالمتصفّح\n" + stderr.join("")));
  });

  let seq = 0;
  const pending = new Map();
  const events = [];
  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { res, rej } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
    } else if (msg.method) {
      events.push(msg);
    }
  };

  // جلسة على الصفحة نفسها لا على المتصفّح
  const targets = await send("Target.getTargets");
  const page = targets.targetInfos.find(t => t.type === "page");
  const { sessionId } = await send("Target.attachToTarget",
    { targetId: page.targetId, flatten: true });

  function send(method, params = {}, sid) {
    const id = ++seq;
    return new Promise((res, rej) => {
      pending.set(id, { res, rej });
      ws.send(JSON.stringify({ id, method, params, sessionId: sid }));
      setTimeout(() => {
        if (pending.has(id)) { pending.delete(id); rej(new Error("مهلة: " + method)); }
      }, 60000);
    });
  }
  const cmd = (m, p) => send(m, p, sessionId);

  await cmd("Page.enable");
  await cmd("Runtime.enable");
  await cmd("Log.enable");

  const api = {
    events,
    /** أخطاء الصفحة ورسائل console.error منذ آخر فتح */
    errors() {
      return events
        .filter(e => e.method === "Log.entryAdded"
          && ["error", "warning"].includes(e.params.entry.level))
        .map(e => `[${e.params.entry.level}] ${e.params.entry.text}`
          + (e.params.entry.url ? ` @ ${e.params.entry.url}` : ""));
    },
    async open(url, waitMs = 900) {
      events.length = 0;
      await cmd("Page.navigate", { url });
      // انتظار اكتمال التحميل ثم مهلة قصيرة لتشغيل سكربتات التهيئة
      const t0 = Date.now();
      while (Date.now() - t0 < 20000) {
        const r = await cmd("Runtime.evaluate",
          { expression: "document.readyState", returnByValue: true });
        if (r.result.value === "complete") break;
        await sleep(120);
      }
      await sleep(waitMs);
    },
    /** تنفيذ تعبير وإرجاع قيمته (يدعم await) */
    async eval(expr) {
      const r = await cmd("Runtime.evaluate", {
        expression: `(async()=>{${expr.includes("return") ? expr : "return (" + expr + ")"}})()`,
        awaitPromise: true, returnByValue: true,
      });
      if (r.exceptionDetails) {
        throw new Error("خطأ داخل الصفحة: "
          + (r.exceptionDetails.exception?.description
            || r.exceptionDetails.text));
      }
      return r.result.value;
    },
    /* ===== إدخال حقيقي =====
       تُرسَل الأحداث عبر Input.dispatch* فيُولّدها المتصفّح بنفسه،
       فتمرّ بكل مسار المعالجة الحقيقي (pointer events، التقاط
       المؤشّر، getScreenCTM). أمّا dispatchEvent من جافاسكربت فيصنع
       حدثاً اصطناعياً قد ينجح حيث يفشل الاستخدام الفعلي — وهو ما
       يجعل الاختبار يكذب. */
    async mouseMove(x, y, buttons = 0) {
      await cmd("Input.dispatchMouseEvent", {
        type: "mouseMoved", x, y, buttons,
        button: buttons ? "left" : "none",
        pointerType: "mouse",
      });
    },
    async mouseDown(x, y) {
      await cmd("Input.dispatchMouseEvent", {
        type: "mousePressed", x, y, button: "left", buttons: 1,
        clickCount: 1, pointerType: "mouse",
      });
    },
    async mouseUp(x, y) {
      await cmd("Input.dispatchMouseEvent", {
        type: "mouseReleased", x, y, button: "left", buttons: 0,
        clickCount: 1, pointerType: "mouse",
      });
    },
    /** سحب بخطوات وسطية — الخطوة الواحدة لا تُحاكي السحب الحقيقي */
    async drag(x1, y1, x2, y2, steps = 10) {
      await api.mouseMove(x1, y1);
      await api.mouseDown(x1, y1);
      for (let i = 1; i <= steps; i++) {
        const t = i / steps;
        await api.mouseMove(x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, 1);
        await sleep(16);
      }
      await api.mouseUp(x2, y2);
      await sleep(40);
    },
    async key(k, modifiers = 0) {
      const special = {
        Escape: { code: "Escape", vk: 27 },
        Enter: { code: "Enter", vk: 13, text: "\r" },
        Delete: { code: "Delete", vk: 46 },
        Alt: { code: "AltLeft", vk: 18 },
        ArrowUp: { code: "ArrowUp", vk: 38 },
        ArrowDown: { code: "ArrowDown", vk: 40 },
        ArrowLeft: { code: "ArrowLeft", vk: 37 },
        ArrowRight: { code: "ArrowRight", vk: 39 },
      };
      const sp = special[k];
      const base = sp
        ? { key: k, code: sp.code, windowsVirtualKeyCode: sp.vk,
            nativeVirtualKeyCode: sp.vk, text: sp.text }
        : { key: k, code: "Key" + k.toUpperCase(), text: k,
            windowsVirtualKeyCode: k.toUpperCase().charCodeAt(0),
            nativeVirtualKeyCode: k.toUpperCase().charCodeAt(0) };
      await cmd("Input.dispatchKeyEvent",
        Object.assign({ type: sp && !sp.text ? "rawKeyDown" : "keyDown",
          modifiers }, base));
      await cmd("Input.dispatchKeyEvent",
        Object.assign({ type: "keyUp", modifiers }, base));
      await sleep(40);
    },
    async setSize(w, h) {
      await cmd("Emulation.setDeviceMetricsOverride",
        { width: w, height: h, deviceScaleFactor: 1, mobile: false });
    },
    /** لقطة شاشة — تحرس حدّ 2000 بكسل في كل بُعد */
    async shot(path, w = 1440, h = 980) {
      if (w > 2000 || h > 2000) {
        throw new Error(`لقطة ${w}×${h} تتجاوز حدّ 2000 بكسل — `
          + `الصور الأكبر تُرفض في طلبات الصور المتعدّدة. صغّري المقاس.`);
      }
      await api.setSize(w, h);
      await sleep(250);
      const r = await cmd("Page.captureScreenshot", { format: "png" });
      writeFileSync(path, Buffer.from(r.data, "base64"));
      return path;
    },
    /** لقطة لمنطقة محدّدة بتكبير — للتدقيق في التفاصيل.
        المتصفّح يقتطع ويُكبّر بنفسه فلا حاجة لمكتبة صور (وPillow
        غير مثبّت ولا إنترنت لتثبيته). والحدّ 2000 بكسل محروس على
        الأبعاد *الناتجة* بعد التكبير. */
    async shotClip(path, { x, y, width, height, scale = 1 }) {
      const outW = Math.round(width * scale), outH = Math.round(height * scale);
      if (outW > 2000 || outH > 2000) {
        throw new Error(`اللقطة الناتجة ${outW}×${outH} تتجاوز حدّ 2000 بكسل `
          + `— صغّري المنطقة أو التكبير (الأقصى هنا `
          + `${(2000 / Math.max(width, height)).toFixed(2)}×)`);
      }
      const r = await cmd("Page.captureScreenshot", {
        format: "png",
        clip: { x, y, width, height, scale },
        captureBeyondViewport: false,
      });
      writeFileSync(path, Buffer.from(r.data, "base64"));
      return { path, width: outW, height: outH };
    },
    async close() {
      try { ws.close(); } catch {}
      proc.kill("SIGKILL");
      try { rmSync(profile, { recursive: true, force: true }); } catch {}
    },
  };
  return api;
}
