// Review captures of the real page: real motion, real scroll, true device widths.
//   node scripts/capture.mjs            (dev server must be running on 127.0.0.1:5173)
// Drives the locally installed Chrome through puppeteer-core, so nothing is downloaded.
import { mkdirSync, writeFileSync } from "node:fs";
import puppeteer from "puppeteer-core";

const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
const URL = "http://127.0.0.1:5173/";
const OUT = "../.impeccable/review";
const SECTIONS = ["top", "question", "voices", "method", "results", "words", "stability", "limits", "build", "contact"];

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function capture(browser, name, viewport, reducedMotion = false) {
  const page = await browser.newPage();
  await page.setViewport(viewport);
  // Set the preference explicitly: this machine's OS has animations off, which would otherwise
  // make every capture the reduced-motion fallback.
  await page.emulateMediaFeatures([
    { name: "prefers-reduced-motion", value: reducedMotion ? "reduce" : "no-preference" },
  ]);
  await page.goto(URL, { waitUntil: "networkidle0" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForSelector("canvas", { timeout: 20000 });
  await sleep(3500); // hero word reveal + first field frames

  const info = await page.evaluate(() => ({
    satoshi: document.fonts.check("16px Satoshi"),
    clash: document.fonts.check("500 16px 'Clash Display'"),
    overflowX: document.documentElement.scrollWidth > window.innerWidth,
    docW: document.documentElement.scrollWidth,
    vw: window.innerWidth,
  }));
  console.log(name, JSON.stringify(info));

  for (const id of SECTIONS) {
    // Scroll the way a visitor does, then let the entrance settle.
    await page.evaluate((sid) => {
      const el = document.getElementById(sid);
      window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 64, behavior: "instant" });
    }, id);
    await sleep(1600);
    if (id === "question") {
      // Mid-progress: place the paragraph so roughly half its words have been reached.
      await page.evaluate(() => {
        const p = document.querySelector("#question p");
        const r = p.getBoundingClientRect();
        window.scrollTo({ top: r.top + window.scrollY - window.innerHeight * 0.42, behavior: "instant" });
      });
      await sleep(900);
    }
    await page.screenshot({ path: `${OUT}/${name}-${id}.png` });
  }

  // Full page, as viewport-tall segments that scripts/stitch.py joins. A single fullPage
  // screenshot wraps at 8192 device px in the software renderer and repeats the top of the
  // page. The fixed nav is hidden after the first segment so it appears once.
  const total = await page.evaluate(() => document.documentElement.scrollHeight);
  const step = viewport.height;
  // Pre-pass: walk the page in half-viewport steps so every enter-on-scroll animation has
  // played. Otherwise a card can still be mid-entrance at a segment boundary.
  for (let y = 0; y < total; y += step / 2) {
    await page.evaluate((top) => window.scrollTo({ top, behavior: "instant" }), y);
    await sleep(350);
  }
  await sleep(1200);
  const tops = [];
  for (let y = 0; y < total; y += step) tops.push(Math.min(y, total - step));
  for (const [i, y] of tops.entries()) {
    await page.evaluate(
      (top, hideNav) => {
        window.scrollTo({ top, behavior: "instant" });
        document.querySelector("header").style.visibility = hideNav ? "hidden" : "visible";
      },
      y,
      i > 0,
    );
    await sleep(900);
    await page.screenshot({ path: `${OUT}/seg/${name}-${String(i).padStart(3, "0")}.png` });
  }
  writeFileSync(`${OUT}/seg/${name}.json`, JSON.stringify({ tops, total, step, scale: viewport.deviceScaleFactor }));
  await page.close();
}

mkdirSync(`${OUT}/seg`, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: "new",
  args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
});
await capture(browser, "desktop", { width: 1440, height: 900, deviceScaleFactor: 1 });
await capture(browser, "mobile", { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await capture(browser, "reduced", { width: 1440, height: 900, deviceScaleFactor: 1 }, true);

// Footer in its complete state (`?demo` fills obviously fake author details): repository
// button, contact form, then the form's focus and error states.
async function captureFooter(name, viewport) {
  const page = await browser.newPage();
  await page.setViewport(viewport);
  await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "no-preference" }]);
  await page.goto(`${URL}?demo`, { waitUntil: "networkidle0" });
  await page.evaluate(() => document.fonts.ready);
  await sleep(2500);
  const toForm = () =>
    page.evaluate(() => {
      const f = document.querySelector("#contact form");
      window.scrollTo({ top: f.getBoundingClientRect().top + window.scrollY - 140, behavior: "instant" });
    });
  await page.evaluate(() => document.getElementById("contact").scrollIntoView({ behavior: "instant" }));
  await sleep(1800);
  await page.screenshot({ path: `${OUT}/${name}-contact-demo.png` });
  await toForm();
  await sleep(600);
  await page.focus("#message");
  await sleep(300);
  await page.screenshot({ path: `${OUT}/${name}-contact-demo-focus.png` });
  await page.click('#contact button[type="submit"]');
  await sleep(500);
  await page.screenshot({ path: `${OUT}/${name}-contact-demo-error.png` });
  await page.close();
}
// Phone section menu, open.
{
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  await page.emulateMediaFeatures([{ name: "prefers-reduced-motion", value: "no-preference" }]);
  await page.goto(URL, { waitUntil: "networkidle0" });
  await page.evaluate(() => document.fonts.ready);
  await sleep(3000);
  await page.click('header button[aria-controls="mobile-sections"]');
  await sleep(500);
  await page.screenshot({ path: `${OUT}/mobile-menu-open.png` });
  await page.close();
}
await captureFooter("desktop", { width: 1440, height: 900, deviceScaleFactor: 1 });
await captureFooter("mobile", { width: 390, height: 844, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
await browser.close();
