// Screenshot capture for design review: node e2e/shots.mjs <outdir>
import { chromium } from '@playwright/test';
const out = process.argv[2] ?? 'shots';
const base = process.env.BASE ?? 'http://127.0.0.1:4173/';
const arena = [['arena-open', ''], ['arena-t1', '#/arena?t=1'], ['arena-t3', '#/arena?t=3'], ['arena-t6', '#/arena?t=6'], ['arena-end', '#/arena?t=7']];
// First-viewport captures cover the Arena frames; full-page captures also cover the other views.
const views = process.env.FULL === '0' ? arena : [...arena, ['theater', '#/theater'], ['evolution', '#/evolution']];
const browser = await chromium.launch();
for (const [vw, vh, tag] of [[1440, 900, 'desktop'], [390, 844, 'mobile']]) {
  const page = await browser.newPage({ viewport: { width: vw, height: vh }, deviceScaleFactor: tag === 'mobile' ? 2 : 1, reducedMotion: 'reduce' });
  for (const [name, hash] of views) {
    await page.goto(base + hash);
    await page.waitForTimeout(500);
    if (process.env.FULL !== '0') {
      // Grow the viewport to the page height so the fixed player renders at the true bottom.
      const h = await page.evaluate(() => document.documentElement.scrollHeight);
      await page.setViewportSize({ width: vw, height: Math.max(vh, h) });
      await page.waitForTimeout(150);
      await page.screenshot({ path: `${out}/${tag}-${name}.png` });
      await page.setViewportSize({ width: vw, height: vh });
    } else {
      await page.screenshot({ path: `${out}/${tag}-${name}.png` });
    }
  }
  if (process.env.FULL === '0') { await page.close(); continue; }
  await page.goto(base + '#/arena?t=6');
  await page.getByRole('button', { name: /Account agent-1/ }).click();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${out}/${tag}-inspector.png` });
  await page.close();
}
await browser.close();
