// Lists elements wider than a 390px phone viewport (the cause of mobile zoom-out).
import puppeteer from "puppeteer-core";
const browser = await puppeteer.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe", headless: "new" });
const page = await browser.newPage();
await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await page.goto("http://127.0.0.1:5173/?capture", { waitUntil: "networkidle0" });
const out = await page.evaluate(() => {
  const res = [];
  for (const el of document.querySelectorAll("body *")) {
    if (el.closest(".rail") && !el.classList.contains("rail")) continue;
    if (el.closest(".marquee") && !el.classList.contains("marquee")) continue;
    const r = el.getBoundingClientRect();
    if (r.width > 392 || r.right > 392) {
      res.push(`${el.tagName.toLowerCase()}.${String(el.className).slice(0, 60)} w=${Math.round(r.width)} right=${Math.round(r.right)} sec=${el.closest("section,footer,header")?.id}`);
    }
  }
  return { vw: window.innerWidth, docW: document.documentElement.scrollWidth, res: res.slice(0, 25) };
});
console.log(JSON.stringify(out, null, 1));
await browser.close();
