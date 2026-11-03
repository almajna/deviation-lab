import { expect, test } from '@playwright/test';

// The three VISUAL_SPEC usability flows, adapted to what the v0.2 data honestly supports.

test.describe('Market Arena', () => {
  test('opens on the synthetic label and an un-played replay', async ({ page }) => {
    await page.goto('./');
    await expect(page.getByRole('button', { name: /Data provenance: synthetic fixture, not a result/ })).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Two tasks');
    await expect(page.getByRole('slider', { name: 'Replay position' })).toHaveAttribute('aria-valuenow', '0');
    await expect(page.getByText('sealed', { exact: true })).toBeVisible();
  });

  test('step, seek and rewind are deterministic and deep-linkable', async ({ page }) => {
    // Reduced motion makes figures render their final value immediately, so text comparison is exact.
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('./');
    const step = page.getByRole('button', { name: 'Step forward' });
    for (let i = 0; i < 4; i++) await step.click();
    await expect(page).toHaveURL(/t=3/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Settlement');
    await expect(page.getByRole('heading', { level: 1 })).toContainText('+300');
    const settled = await page.locator('.stage').textContent();

    await page.getByRole('button', { name: 'Rewind to start' }).click();
    await expect(page).not.toHaveURL(/t=/);
    await page.goto('./#/arena?t=3');
    await expect(page.locator('.stage')).toHaveText(settled!);
    await page.getByRole('button', { name: 'Step back' }).click();
    await expect(page.getByText('sealed', { exact: true })).toBeVisible();
  });

  test('rapid key presses are never dropped', async ({ page }) => {
    await page.goto('./');
    await page.locator('body').focus();
    for (let i = 0; i < 5; i++) await page.keyboard.press('ArrowRight', { delay: 0 });
    await expect(page).toHaveURL(/t=4/);
    await page.keyboard.press('i');
    await page.keyboard.press('Escape');
    await page.keyboard.press('Home');
    await page.keyboard.press(' ');
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible();
  });

  test('keyboard controls play, step and inspect', async ({ page }) => {
    await page.goto('./');
    await page.locator('body').press('ArrowRight');
    await expect(page).toHaveURL(/t=0/);
    await page.locator('body').press('End');
    await expect(page).toHaveURL(/t=6/);
    await page.locator('body').press('i');
    const inspector = page.locator('aside.inspector');
    await expect(inspector).toContainText('utility_summary');
    await page.keyboard.press('Escape');
    await expect(inspector).toHaveAttribute('aria-hidden', 'true');
    await page.locator('body').press('Home');
    await page.locator('body').press(' ');
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible();
  });

  test('playback advances on its own and stops at the end', async ({ page }) => {
    await page.goto('./');
    await page.getByRole('button', { name: '2×' }).click();
    await page.getByRole('button', { name: 'Play' }).click();
    await expect(page).toHaveURL(/t=1/, { timeout: 6000 });
    await page.getByRole('button', { name: 'Pause' }).click();
    const url = page.url();
    await page.waitForTimeout(2000);
    expect(page.url()).toBe(url);
  });

  // Flow (c): inspect why a particular agent received resources.
  test('inspect why an agent received credits', async ({ page }) => {
    await page.goto('./#/arena?t=6');
    await page.getByRole('button', { name: /Account agent-1/ }).click();
    const inspector = page.getByRole('complementary', { name: 'Inspector' });
    await expect(inspector).toContainText('Synthetic economic agent');
    await expect(inspector).not.toContainText('initial balance');
    await expect(inspector).toContainText('+6 ← maker');
    await expect(inspector).toContainText('+6');
    await expect(inspector).toContainText('private signal are not part of the public replay');
    await inspector.getByRole('button', { name: 'Seek to event 5' }).click();
    await expect(page).toHaveURL(/t=5/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Maker pays agent-1');
  });

  test('every displayed figure opens its source event', async ({ page }) => {
    await page.goto('./#/arena?t=3');
    await page.getByRole('button', { name: /Realized spend 900. Inspect event 3/ }).click();
    const inspector = page.getByRole('complementary', { name: 'Inspector' });
    await expect(inspector).toContainText('Post-settlement. Revealed only after every decision was final');
    await expect(inspector.getByLabel('Event JSON')).toContainText('"realized_spend": 900');
  });

  test('rejects an invalid trace file with a reason', async ({ page }) => {
    await page.goto('./');
    await page.getByLabel('Load a v0.2 completed trace JSON file').setInputFiles({
      name: 'bad.json', mimeType: 'application/json',
      buffer: Buffer.from(JSON.stringify({ schema_version: '0.1', events: [] })),
    });
    await expect(page.getByRole('alert')).toContainText('bad.json was not loaded');
  });

  test('exports the trace JSON', async ({ page }) => {
    await page.goto('./');
    const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download trace JSON' }).click()]);
    expect(download.suggestedFilename()).toBe('SYNTHETIC-contract-conformance.seed-7.trace.json');
    const fs = await import('node:fs');
    const exported = JSON.parse(fs.readFileSync(await download.path(), 'utf8'));
    expect(exported).toEqual(JSON.parse(fs.readFileSync('fixtures/gate-a.synthetic.json', 'utf8')));
  });
});

// Flows (a) and (b): comparing policies and replaying an exploit are not supported by any approved trace.
test('Exploit Theater shows no fabricated attack', async ({ page }) => {
  await page.goto('./#/theater');
  await expect(page.getByRole('heading', { level: 1, name: 'Exploit Theater' })).toBeVisible();
  await expect(page.getByText('No attack traces exist')).toBeVisible();
  await expect(page.locator('main svg')).toHaveCount(0);
});

test('Mechanism Evolution shows empty axes only', async ({ page }) => {
  await page.goto('./#/evolution');
  await expect(page.getByText('No evaluation results exist')).toBeVisible();
  await expect(page.locator('.plot circle')).toHaveCount(0);
});

test('reduced motion disables movement', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce' });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:4173/#/arena?t=1');
  const d = await page.locator('.playhead').evaluate((el) => getComputedStyle(el).transitionDuration);
  expect(d).toBe('0s');
  await ctx.close();
});

test('no horizontal overflow', async ({ page }) => {
  for (const v of ['arena?t=6', 'theater', 'evolution']) {
    await page.goto(`./#/${v}`);
    const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(over, v).toBeLessThanOrEqual(0);
  }
});

// ── Independent verification of every control ─────────────────────────────
test.describe('controls', () => {
  test.use({ reducedMotion: 'reduce' });
  const slider = (p: import('@playwright/test').Page) => p.getByRole('slider', { name: 'Replay position' });

  test('rewind, step back/forward bounds and disabled states', async ({ page }) => {
    await page.goto('./');
    await expect(page.getByRole('button', { name: 'Rewind to start' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Step back' })).toBeDisabled();
    await page.goto('./#/arena?t=6');
    await expect(page.getByRole('button', { name: 'Step forward' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Replay from start' })).toBeVisible();
    await page.getByRole('button', { name: 'Rewind to start' }).click();
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '0');
  });

  test('speed buttons are exclusive and change dwell time', async ({ page }) => {
    await page.goto('./');
    for (const s of ['0.5×', '2×', '1×']) {
      await page.getByRole('button', { name: s, exact: true }).click();
      await expect(page.getByRole('button', { name: s, exact: true })).toHaveAttribute('aria-pressed', 'true');
      await expect(page.locator('.speed[aria-pressed="true"]')).toHaveCount(1);
    }
    await page.getByRole('button', { name: '2×', exact: true }).click();
    const t0 = Date.now();
    await page.getByRole('button', { name: 'Play' }).click();
    await expect(page).toHaveURL(/t=1/, { timeout: 5000 });
    expect(Date.now() - t0).toBeLessThan(3500); // 1× would need ≥ 3.6 s to reach event 1
  });

  test('play runs to the end and stops; Replay restarts', async ({ page }) => {
    await page.clock.install();
    await page.goto('./');
    await page.getByRole('button', { name: 'Play' }).click();
    await page.clock.runFor(60_000);
    await expect(page).toHaveURL(/t=6/);
    await expect(page.getByRole('button', { name: 'Replay from start' })).toBeVisible();
    await page.getByRole('button', { name: 'Replay from start' }).click();
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible();
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '0');
  });

  test('timeline click and drag seek to whole events', async ({ page }) => {
    await page.goto('./');
    await slider(page).scrollIntoViewIfNeeded();
    const box = (await slider(page).boundingBox())!;
    await page.mouse.click(box.x + box.width * (4.5 / 7), box.y + box.height / 2);
    await expect(page).toHaveURL(/t=4/);
    // Controls must not move while the replay changes (handoff: stable during playback).
    expect((await slider(page).boundingBox())!.y).toBeCloseTo(box.y, 0);
    await page.mouse.move(box.x + box.width * (0.5 / 7), box.y + 5);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * (2.4 / 7), box.y + 5, { steps: 6 });
    await page.mouse.up();
    await expect(page).toHaveURL(/t=2/);
  });

  test('slider arrow keys, nav links, provenance and trace selector', async ({ page }) => {
    await page.goto('./');
    await slider(page).focus();
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '2');
    await page.getByRole('button', { name: /Data provenance/ }).click();
    const insp = page.locator('aside.inspector');
    await expect(insp).toContainText('gate-a');
    await expect(insp).toContainText('Fixture annotation');
    await page.getByRole('button', { name: 'Close inspector' }).click();
    await expect(page.getByRole('button', { name: /Data provenance/ })).toBeFocused();
    await expect(page.getByRole('combobox', { name: 'Select trace' })).toHaveValue('fixture:gate-a');
    await page.getByRole('link', { name: /Theater/ }).click();
    await expect(page).toHaveURL(/#\/theater/);
    await page.getByRole('link', { name: /Evolution/ }).click();
    await expect(page).toHaveURL(/#\/evolution/);
    await page.getByRole('link', { name: /Arena/ }).first().click();
    await expect(page).toHaveURL(/#\/arena/);
  });

  test('loading a valid trace file switches the replay and keeps it labelled', async ({ page }) => {
    const fs = await import('node:fs');
    await page.goto('./');
    await page.getByLabel('Load a v0.2 completed trace JSON file').setInputFiles({
      name: 'mine.json', mimeType: 'application/json', buffer: fs.readFileSync('fixtures/gate-a.synthetic.json'),
    });
    await expect(page.getByRole('combobox', { name: 'Select trace' })).toHaveValue('file:mine.json');
    await expect(page.getByRole('button', { name: /Data provenance: loaded file/ })).toBeVisible();
    await expect(page.getByText('No run configuration loaded; budget unknown.')).toBeVisible();
  });

  test('copy JSON and seek from the inspector', async ({ page, context, browserName }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
    await page.goto('./#/arena?t=4');
    await page.getByRole('button', { name: 'View source event 4' }).click();
    const insp = page.locator('aside.inspector');
    await insp.getByRole('button', { name: 'Copy JSON' }).click();
    await expect(insp.getByRole('button', { name: /Copied|Copy unavailable/ })).toBeVisible();
    await insp.getByRole('button', { name: 'Seek here' }).click();
    await expect(page).toHaveURL(/t=4/);
    expect(browserName).toBe('chromium');
  });
});

// ── Every displayed number comes from its referenced event ───────────────
test('stage figures equal the values in their source events', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  const fs = await import('node:fs');
  const trace = JSON.parse(fs.readFileSync('fixtures/gate-a.synthetic.json', 'utf8'));
  const ev = trace.events;
  await page.goto('./#/arena?t=6');
  const label = async (re: RegExp) => (await page.getByRole('button', { name: re }).getAttribute('aria-label'))!;

  // Every clickable figure names its event; that event must contain the figure.
  const figures = page.locator('.stage button.value-btn');
  const n = await figures.count();
  expect(n).toBeGreaterThan(5);
  for (let i = 0; i < n; i++) {
    const aria = (await figures.nth(i).getAttribute('aria-label'))!;
    const seq = Number(/Inspect event (\d+)/.exec(aria)![1]);
    const shown = (await figures.nth(i).innerText()).replace(/[+−,]/g, '').trim();
    const payload = JSON.stringify(ev[seq].payload);
    const value = Number(shown);
    const derived = ev[seq].type === 'realized_cost_report'
      ? ev[seq].payload.selected_costs.map((c: any) => c.realized_cost - ev.find((e: any) => e.type === 'reservation' && e.payload.task_id === c.task_id).payload.reserved_cost).map(Math.abs)
      : [];
    expect(payload.includes(String(value)) || payload.includes(shown) || derived.includes(value), `${aria} shows ${shown}`).toBe(true);
  }
  expect(await label(/Realized spend/)).toContain('event 3');
  // Ledger deltas equal the sum of that account's transfers.
  const net = (id: string) => ev.filter((e: any) => e.type === 'ledger_transfer').reduce((s: number, e: any) => s + (e.payload.payee === id ? e.payload.amount : e.payload.payer === id ? -e.payload.amount : 0), 0);
  for (const id of ['agent-1', 'fee_sink', 'maker']) {
    const v = net(id);
    await expect(page.getByRole('button', { name: new RegExp(`Account ${id}: change ${v > 0 ? '\\+' : v < 0 ? '−' : ''}${Math.abs(v)} credits`) })).toBeVisible();
  }
});

// ── Knowledge boundary and private data ───────────────────────────────────
test('nothing post-settlement is rendered before settlement', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('./#/arena?t=2');
  const text = await page.locator('main').innerText();
  for (const v of ['900', '700', '+500', 'over budget', '+6', '−6']) expect(text, v).not.toContain(v);
  await expect(page.getByText('revealed at event 6')).toBeVisible();
});

test('no private signal or hidden outcome ships in the public bundle or DOM', async ({ page, request }) => {
  await page.goto('./#/arena?t=6');
  const srcs = await page.locator('script[src]').evaluateAll((els) => els.map((e) => (e as HTMLScriptElement).src));
  const css = await page.locator('link[rel=stylesheet]').evaluateAll((els) => els.map((e) => (e as HTMLLinkElement).href));
  const bodies = [await page.content(), ...(await Promise.all([...srcs, ...css].map(async (u) => (await request.get(u)).text())))];
  const all = bodies.join('\n');
  // Keys that exist only in the pack's private information set and training rows (never in app code).
  for (const k of ['private_signal', 'owner_agent_id', 'available_credits', 'training_rows', 'model_reservations', 'fit_group_ids', 'Synthetic training']) {
    expect(all, k).not.toContain(k);
  }
  // agent-1's private signal values {a: 0.5, b: 0.7}, in JSON or minified form.
  expect(all).not.toMatch(/"?a"?\s*:\s*0?\.5\s*,\s*"?b"?\s*:\s*0?\.7/);
  // Balances are not in the public trace and must not be displayed.
  const text = await page.locator('main').innerText();
  for (const v of ['20', '24', '44', '50']) expect(text.split(/\s+/), v).not.toContain(v);
});
