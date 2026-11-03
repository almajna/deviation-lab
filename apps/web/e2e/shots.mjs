// Review screenshots: BASE=http://127.0.0.1:<port>/ node e2e/shots.mjs <dir>
// Captures every scene at desktop (1440), phone (390) and narrow phone (320), first viewport,
// plus the Data panel, an account inspector and the two unavailable views.
import { chromium } from '@playwright/test';
const out = process.argv[2] ?? 'shots';
const base = process.env.BASE ?? 'http://127.0.0.1:4173/';
const scenes = [['01-setup', ''], ['02-forecast', '#/arena?t=0'], ['03-reserve', '#/arena?t=1'], ['04-reserve', '#/arena?t=2'], ['05-settle', '#/arena?t=3'], ['06-fee', '#/arena?t=4'], ['07-payout', '#/arena?t=5'], ['08-utility', '#/arena?t=6'], ['09-conclusion', '#/arena?t=7']];
const browser = await chromium.launch();
for (const [vw, vh, tag, dpr] of [[1440, 900, 'desktop', 1], [390, 844, 'mobile', 2], [320, 640, 'narrow', 2]]) {
  const page = await browser.newPage({ viewport: { width: vw, height: vh }, deviceScaleFactor: dpr, reducedMotion: 'reduce' });
  for (const [name, hash] of scenes) {
    await page.goto(base + hash);
    await page.waitForTimeout(400);
    await page.screenshot({ path: `${out}/${tag}-${name}.png` });
  }
  if (tag !== 'narrow') {
    await page.goto(base + '#/arena?t=6');
    await page.getByRole('button', { name: 'Data: every figure and its source' }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${out}/${tag}-data-panel.png` });
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: /^Account agent-1/ }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${out}/${tag}-inspector.png` });
    for (const v of ['theater', 'evolution']) {
      await page.goto(base + '#/' + v);
      await page.waitForTimeout(300);
      await page.screenshot({ path: `${out}/${tag}-${v}.png`, fullPage: true });
    }
  }
  await page.close();
}
await browser.close();
