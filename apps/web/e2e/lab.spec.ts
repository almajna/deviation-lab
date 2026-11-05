import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';

// Browser tests. "R<n>" = regressions for the first PR #17 review; "B<n>" = the remaining blockers
// listed for the redesign (docs/REVIEW.md maps each to its fix).

const TRACE = JSON.parse(fs.readFileSync('fixtures/gate-a.synthetic.json', 'utf8'));
const EVENTS = TRACE.events as any[];
const N = EVENTS.length; // 7 events; cursor N is the closing frame
const slider = (p: Page) => p.getByRole('slider', { name: 'Scene' });
const dialog = (p: Page) => p.getByRole('dialog');
const file = (name: string, body: unknown) => ({ name, mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(body)) });
const loader = (p: Page) => p.getByLabel('Load a v0.2 completed trace JSON file');
/** Trace selection, download and load live in the Data panel. */
const openData = async (p: Page) => {
  await p.getByRole('button', { name: 'Data: every figure and its source' }).click();
  await expect(p.getByRole('dialog')).toBeVisible();
};
const closeDialog = async (p: Page) => {
  await p.keyboard.press('Escape');
  await expect(p.getByRole('dialog')).toHaveCount(0);
};
const at = (t: number) => (t < 0 ? './' : `./#/arena?t=${t}`);

test.describe('replay', () => {
  test('opens on the title card with the synthetic label', async ({ page }) => {
    await page.goto('./');
    await expect(page).toHaveTitle('LLM Prediction Markets');
    await expect(page.getByRole('heading', { level: 1 })).toHaveText('LLM Prediction Markets');
    await expect(page.getByText('An interactive laboratory for the economics of AI compute.')).toBeVisible();
    await expect(page.getByRole('button', { name: /Data provenance: synthetic fixture, not a result/ })).toBeVisible();
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '1');
  });

  test('step, seek and deep links are deterministic', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('./');
    for (let i = 0; i < 4; i++) await page.getByRole('button', { name: 'Next scene' }).click();
    await expect(page).toHaveURL(/t=3/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('+300');
    await page.waitForTimeout(50);
    // An empty style attribute left by React after a style is cleared renders identically.
    const html = async () => (await page.locator('.scene').innerHTML()).replace(/ style=""/g, '');
    const settled = await html();
    await page.goto('./');
    await page.goto(at(3));
    await page.waitForTimeout(50);
    expect(await html()).toBe(settled);
    await page.getByRole('button', { name: 'Previous scene' }).click();
    await expect(page.getByText('real costs sealed until settlement')).toBeVisible();
  });

  test('keyboard: arrows, Home/End, Space and I', async ({ page }) => {
    await page.goto('./');
    await page.locator('body').press('ArrowRight');
    await expect(page).toHaveURL(/t=0/);
    await page.locator('body').press('End');
    await expect(page).toHaveURL(new RegExp(`t=${N}`));
    await page.locator('body').press('ArrowLeft');
    await page.locator('body').press('i');
    await expect(dialog(page)).toContainText('utility_summary');
    await page.keyboard.press('Escape');
    await expect(dialog(page)).toHaveCount(0);
    await page.locator('body').press('Home');
    await page.locator('body').press(' ');
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible();
  });

  test('rapid key presses are never dropped', async ({ page }) => {
    await page.goto('./');
    await page.locator('body').focus();
    for (let i = 0; i < 5; i++) await page.keyboard.press('ArrowRight');
    await expect(page).toHaveURL(/t=4/);
    await page.keyboard.press('i');
    await page.keyboard.press('Escape');
    await page.keyboard.press('Home');
    await page.keyboard.press(' ');
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible();
  });

  test('keyboard steps land instantly: no animation in the diagram', async ({ page }) => {
    await page.goto(at(3));
    await page.locator('body').press('ArrowRight');
    await expect(page).toHaveURL(/t=4/);
    for (const sel of ['.scene .account-node', '.narration h1']) {
      expect(await page.locator(sel).first().evaluate((el) => getComputedStyle(el).animationName), sel).toBe('none');
    }
  });

  test('inspect why an agent received credits', async ({ page }) => {
    await page.goto(at(N - 1));
    await page.getByRole('button', { name: /^Account agent-1/ }).click();
    await expect(dialog(page)).toContainText('Synthetic economic agent');
    await expect(dialog(page)).toContainText('+6 ← maker');
    await expect(dialog(page)).not.toContainText('initial balance');
    await dialog(page).getByRole('button', { name: 'Seek to event 6' }).click();
    await expect(page).toHaveURL(/t=5/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('The maker pays 6 credits to agent');
  });

  test('rejects an invalid trace file with a reason', async ({ page }) => {
    await page.goto('./');
    await openData(page);
    await loader(page).setInputFiles(file('bad.json', { schema_version: '0.1', events: [] }));
    await expect(page.getByRole('alert')).toContainText('bad.json was not loaded');
  });

  test('exports the exact trace', async ({ page }) => {
    await page.goto('./');
    await openData(page);
    const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download complete trace' }).click()]);
    expect(JSON.parse(fs.readFileSync(await download.path(), 'utf8'))).toEqual(TRACE);
  });
});

test.describe('controls', () => {
  test.use({ reducedMotion: 'reduce' });

  test('bounds and disabled states', async ({ page }) => {
    await page.goto('./');
    await expect(page.getByRole('button', { name: 'Previous scene' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Inspect the current event' })).toBeDisabled();
    await page.goto(at(N));
    await expect(page.getByRole('button', { name: 'Next scene' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Replay from start' })).toBeVisible();
  });

  test('speed control changes dwell time', async ({ page }) => {
    await page.goto('./');
    await page.getByRole('button', { name: /^Speed 1×, change to 2×/ }).click();
    await expect(page.getByRole('button', { name: /^Speed 2×/ })).toBeVisible();
    const t0 = Date.now();
    await page.getByRole('button', { name: 'Play' }).click();
    await expect(page).toHaveURL(/t=1/, { timeout: 5000 });
    expect(Date.now() - t0).toBeLessThan(3500);
  });

  test('play runs to the closing frame and stops; Replay restarts', async ({ page }) => {
    await page.clock.install();
    await page.goto('./');
    await page.getByRole('button', { name: 'Play' }).click();
    await page.clock.runFor(90_000);
    await expect(page).toHaveURL(new RegExp(`t=${N}`));
    await page.getByRole('button', { name: 'Replay from start' }).click();
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible();
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '1');
  });

  test('scrubber click and drag seek to whole scenes; the player never moves', async ({ page }) => {
    await page.goto('./');
    const box = (await slider(page).boundingBox())!;
    const x = (pos: number) => box.x + box.width * (pos / (N + 1));
    await page.mouse.click(x(5), box.y + box.height / 2);
    await expect(page).toHaveURL(/t=4/);
    await page.mouse.move(x(1), box.y + 5);
    await page.mouse.down();
    await page.mouse.move(x(3), box.y + 5, { steps: 6 });
    await page.mouse.up();
    await expect(page).toHaveURL(/t=2/);
    for (const t of [-1, 3, N]) {
      await page.goto(at(t));
      expect((await slider(page).boundingBox())!.y, `t=${t}`).toBeCloseTo(box.y, 0);
    }
  });

  test('slider keys, Data, Inspect, nav and provenance', async ({ page }) => {
    await page.goto('./');
    await slider(page).focus();
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '3');
    await page.getByRole('button', { name: 'Data: every figure and its source' }).click();
    await expect(dialog(page)).toHaveAccessibleName('Data');
    await expect(dialog(page)).toContainText('reserved 200 on a');
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: 'Inspect the current event' }).click();
    await expect(dialog(page)).toHaveAccessibleName('Event 2');
    await page.keyboard.press('Escape');
    await page.getByRole('button', { name: /Data provenance/ }).click();
    await expect(dialog(page)).toContainText('apps/web/fixtures/gate-a.synthetic.json');
    await page.getByRole('button', { name: 'Close inspector' }).click();
    for (const v of ['Theater', 'Evolution', 'Replay']) {
      await page.getByRole('link', { name: new RegExp(v) }).first().click();
      await expect(page).toHaveURL(new RegExp(v === 'Replay' ? '#/arena' : `#/${v.toLowerCase()}`));
    }
  });

  test('a valid loaded trace replaces the replay and stays labelled', async ({ page }) => {
    await page.goto('./');
    await openData(page);
    await loader(page).setInputFiles({ name: 'mine.json', mimeType: 'application/json', buffer: fs.readFileSync('fixtures/gate-a.synthetic.json') });
    await expect(page.getByRole('combobox', { name: 'Select trace' })).toHaveValue('file:mine.json');
    await closeDialog(page);
    await expect(page.getByRole('button', { name: /Data provenance: loaded file/ })).toBeVisible();
  });

  test('copy JSON and seek from the inspector', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
    await page.goto(at(4));
    await page.getByRole('button', { name: 'Source: event 5' }).click();
    await dialog(page).getByRole('button', { name: 'Copy JSON' }).click();
    await expect(dialog(page).getByRole('button', { name: /Copied|Copy unavailable/ })).toBeVisible();
    await dialog(page).getByRole('button', { name: 'Seek here' }).click();
    await expect(page).toHaveURL(/t=4/);
  });
});

// ── Every number in the diagram is a recorded value or derived from recorded values ─
test('every number in the diagram comes from the events (or the labelled budget annotation)', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  for (let t = -1; t <= N; t++) {
    await page.goto(at(t));
    const known = EVENTS.slice(0, Math.max(0, Math.min(t, N - 1) + 1));
    const allowed = new Set<string>(['600', '0']);
    const add = (v: number) => allowed.add(String(Math.abs(v)));
    let reserved = 0;
    for (const e of known) {
      JSON.stringify(e.payload, (_k, v) => (typeof v === 'number' && add(v), v));
      if (e.type === 'reservation') add((reserved += e.payload.reserved_cost));
      if (e.type === 'realized_cost_report') for (const c of e.payload.selected_costs) add(c.realized_cost - known.find((r) => r.type === 'reservation' && r.payload.task_id === c.task_id).payload.reserved_cost);
    }
    const net = new Map<string, number>();
    for (const e of known.filter((e) => e.type === 'ledger_transfer')) {
      net.set(e.payload.payer, (net.get(e.payload.payer) ?? 0) - e.payload.amount);
      net.set(e.payload.payee, (net.get(e.payload.payee) ?? 0) + e.payload.amount);
    }
    net.forEach(add);
    const texts = (await page.locator('.scene text').evaluateAll((els) => els.map((e) => e.textContent ?? ''))).map((s) => s.replace(/(eval|agent)-\d+/g, ''));
    for (const tok of texts.join(' ').match(/\d+(?:\.\d+)?/g) ?? []) {
      const v = String(Math.abs(Number(tok)));
      expect(allowed.has(v), `position ${t + 2}: "${tok}" is not established by known events`).toBe(true);
    }
  }
});

// ── R2: no future information anywhere, at any position ───────────────────
test.describe('R2 knowledge boundary', () => {
  test.use({ reducedMotion: 'reduce' });

  const tokensOf = (e: any) => {
    const t = new Set<string>();
    const walk = (v: any) => {
      if (typeof v === 'number' && Number.isInteger(v) && Math.abs(v) >= 10) t.add(String(v));
      else if (typeof v === 'string' && /[_\-\d]/.test(v) && /[a-z]/.test(v)) t.add(v);
      else if (v && typeof v === 'object') for (const [k, x] of Object.entries(v)) { if (!Array.isArray(v) && /\d/.test(k)) t.add(k); walk(x); }
    };
    walk(e.payload);
    return t;
  };
  const future = (k: number) => {
    const known = new Set<string>(['600', 'eval-1', 'eval-2', 'nano_synthetic_units', 'expected_preference_proxy']);
    let reserved = 0;
    for (let i = 0; i <= k; i++) {
      tokensOf(EVENTS[i]).forEach((x) => known.add(x));
      if (EVENTS[i].type === 'reservation') known.add(String((reserved += EVENTS[i].payload.reserved_cost)));
    }
    const f = new Set<string>();
    for (let i = k + 1; i < N; i++) tokensOf(EVENTS[i]).forEach((x) => !known.has(x) && f.add(x));
    return [...f];
  };
  // What a person can perceive: text, accessible names and titles (not SVG geometry or styles).
  const scan = (p: Page) =>
    p.evaluate(() => {
      const roots = [document.querySelector('main')!, document.querySelector('.player')!];
      const out: string[] = [];
      for (const r of roots) {
        out.push(r.textContent ?? '');
        r.querySelectorAll('[aria-label], [title], [aria-valuetext]').forEach((el) => out.push(el.getAttribute('aria-label') ?? '', el.getAttribute('title') ?? '', el.getAttribute('aria-valuetext') ?? ''));
      }
      return out.join(' | ');
    });

  for (const k of [-1, 0, 1, 2, 3, 4, 5]) {
    test(`position ${k + 2}: page, player and every inspector contain nothing from later events`, async ({ page }) => {
      await page.goto(at(k));
      const fut = future(k);
      if (k < N - 2) expect(fut.length).toBeGreaterThan(0);
      const html = await scan(page);
      for (const tok of fut) expect(html, `"${tok}" leaked at position ${k + 2}`).not.toMatch(new RegExp(`(^|[^\\w.-])${tok.replace(/[-_]/g, '\\$&')}([^\\w-]|$)`));
      const names: Array<string | RegExp> = ['Data: every figure and its source', ...(k >= 0 ? [`Source: event ${k + 1}`] : [])];
      for (const a of await page.getByRole('button', { name: /^Account / }).all()) names.push((await a.getAttribute('aria-label'))!);
      for (const name of names) {
        await page.getByRole('button', { name, exact: true }).first().click();
        const text = await dialog(page).innerText();
        for (const tok of fut) expect(text, `"${tok}" leaked in an inspector at ${k + 2}`).not.toContain(tok);
        for (let s = k + 1; s < N; s++) expect(text).not.toContain(`event ${s + 1}`);
        await page.keyboard.press('Escape');
        await expect(dialog(page)).toHaveCount(0);
      }
    });
  }

  test('R2: at event 5 the agent inspector shows the fee only', async ({ page }) => {
    await page.goto(at(4));
    await page.getByRole('button', { name: /^Account agent-1/ }).click();
    await expect(dialog(page)).toContainText('−2 → fee_sink');
    await expect(dialog(page)).not.toContainText('maker');
    await expect(dialog(page)).not.toContainText('+6');
    await expect(dialog(page)).toContainText('Utility is reported at the end of settlement');
  });

  test('R2: before settlement no account, overrun or excess is drawn', async ({ page }) => {
    await page.goto(at(2));
    await expect(page.getByRole('button', { name: /^Account / })).toHaveCount(0);
    await expect(page.locator('.scene .account-node, .scene .excess, .scene .block-delta')).toHaveCount(0);
    expect(await page.locator('.scene rect.over').evaluateAll((els) => els.filter((e) => !/scaleX\(0\)/.test((e as SVGElement).style.transform)).length)).toBe(0);
  });
});

test('no private signal or hidden outcome ships in the public bundle', async ({ page, request }) => {
  await page.goto('./');
  const srcs = await page.locator('script[src]').evaluateAll((els) => els.map((e) => (e as HTMLScriptElement).src));
  const css = await page.locator('link[rel=stylesheet]').evaluateAll((els) => els.map((e) => (e as HTMLLinkElement).href));
  const all = [await page.content(), ...(await Promise.all([...srcs, ...css].map(async (u) => (await request.get(u)).text())))].join('\n');
  for (const k of ['private_signal', 'owner_agent_id', 'available_credits', 'training_rows', 'model_reservations', 'fit_group_ids', 'Synthetic training']) expect(all, k).not.toContain(k);
  expect(all).not.toMatch(/"?a"?\s*:\s*0?\.5\s*,\s*"?b"?\s*:\s*0?\.7/);
});

// ── R3/R4 + B3/B4: imported accounting must reconcile; bad imports are recoverable ─
test.describe('imports', () => {
  const cfg = { schema_version: '0.2', cost_unit: 'nano_synthetic_units', reservation_budget: 600, agent_accounts: ['agent-1'], maker_account: 'maker', fee_sink_account: 'fee_sink', initial_balances: { 'agent-1': 20, fee_sink: 0, maker: 50 }, exogenous_history_actors: ['seed-history'] };
  const pack = { trace: TRACE, run_config: cfg };
  const ledger = { schema_version: '0.2', unit: 'virtual_credit', initial_balances: { 'agent-1': 20, fee_sink: 0, maker: 50 }, final_balances: { 'agent-1': 24, fee_sink: 2, maker: 44 }, transfers: EVENTS.filter((e) => e.type === 'ledger_transfer').map((e) => e.payload), agent_utilities: EVENTS[N - 1].payload, maker_account: 'maker', maker_initial_subsidy: 50, maker_cash_pnl: -6, maker_realized_loss: 6 };
  const withReport = (patch: object) => ({ ...TRACE, events: EVENTS.map((e, i) => (i === 3 ? { ...e, payload: { ...e.payload, ...patch } } : e)) });

  const cases: Array<[string, unknown, RegExp]> = [
    ['contradictory final balance', { ...pack, ledger: { ...ledger, final_balances: { ...ledger.final_balances, maker: 45 } } }, /final balance for maker is 45, transfers imply 44/],
    ['missing utility summary', { ...TRACE, events: EVENTS.slice(0, -1) }, /no utility_summary/],
    ['duplicate utility summary', { ...TRACE, events: [...EVENTS, { ...EVENTS[N - 1], seq: N }] }, /after the utility summary/],
    ['invalid settlement actor', { ...TRACE, events: EVENTS.map((e, i) => (i === 3 ? { ...e, actor: 'allocator' } : e)) }, /must be recorded by "system"/],
    ['impossible budget excess (B3)', withReport({ realized_budget_excess: 450 }), /budget excess 450 is impossible/],
    ['malformed run_config', { ...pack, run_config: { ...cfg, initial_balances: { 'agent-1': 'twenty' } } }, /run_config\.initial_balances\.agent-1/],
    ['malformed decision_tasks', { ...pack, decision_tasks: [{}] }, /decision_tasks\[0\]/],
    ['private fields in the file', { ...pack, information: {} }, /fields outside a public replay bundle \(information\)/],
  ];
  for (const [name, body, msg] of cases) {
    test(`rejects ${name} with a recoverable error`, async ({ page }) => {
      await page.goto('./');
      await openData(page);
      await loader(page).setInputFiles(file('x.json', body));
      await expect(page.getByRole('alert')).toContainText(msg);
      await expect(page.getByRole('combobox', { name: 'Select trace' })).toHaveValue('fixture:gate-a');
      await closeDialog(page);
      await page.getByRole('button', { name: 'Next scene' }).click();
      await expect(page).toHaveURL(/t=0/);
    });
  }

  test('B4: a bundle with reordered keys is accepted (validation ignores key order)', async ({ page }) => {
    const reorder = (v: any): any => (Array.isArray(v) ? v.map(reorder) : v && typeof v === 'object' ? Object.fromEntries(Object.keys(v).reverse().map((k) => [k, reorder(v[k])])) : v);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('./');
    await openData(page);
    await loader(page).setInputFiles(file('reordered.json', reorder({ ...pack, ledger })));
    await expect(page.getByRole('alert')).toHaveCount(0);
    await closeDialog(page);
    await page.locator('body').press('End');
    await expect(page.getByRole('button', { name: /^Account maker: change −6 credits/ })).toContainText('balance 44');
  });

  test('B3: a bare trace (no budget) makes no budget claim anywhere', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('./');
    await openData(page);
    await loader(page).setInputFiles({ name: 'bare.json', mimeType: 'application/json', buffer: fs.readFileSync('fixtures/gate-a.synthetic.json') });
    await closeDialog(page);
    for (let k = 0; k <= N + 1; k++) {
      const more = page.getByRole('button', { name: 'More detail' });
      if (await more.count()) await more.click();
      const text = await page.locator('main').innerText();
      expect(text, `scene ${k + 1}`).not.toMatch(/budget/i);
      await page.locator('body').press('ArrowRight');
    }
  });
});

// ── R5 + B1/B2/B6: modal semantics, contained focus, skip link, discoverability ─
test.describe('accessibility', () => {
  for (const reduced of [false, true]) {
    test(`R5/B1: inspector modal focus and Escape${reduced ? ' (reduced motion)' : ''}`, async ({ page }) => {
      if (reduced) await page.emulateMedia({ reducedMotion: 'reduce' });
      await page.goto(at(3));
      const trigger = page.getByRole('button', { name: 'Source: event 4' });
      await trigger.click();
      const d = dialog(page);
      await expect(d).toHaveAttribute('aria-modal', 'true');
      await expect(d).toHaveAccessibleName('Event 4');
      await expect(page.getByRole('button', { name: 'Close inspector' })).toBeFocused();
      await expect(page.locator('main')).toHaveAttribute('inert', '');
      for (let i = 0; i < 12; i++) {
        await page.keyboard.press(i % 3 ? 'Tab' : 'Shift+Tab');
        expect(await d.evaluate((el) => el.contains(document.activeElement))).toBe(true);
      }
      await page.keyboard.press('Escape');
      await expect(d).toHaveCount(0);
      await expect(page.locator('main')).not.toHaveAttribute('inert', '');
      await expect(trigger).toBeFocused();
      // Escape also works when focus has left the dialog.
      await trigger.click();
      await expect(d).toBeVisible();
      await page.evaluate(() => (document.activeElement as HTMLElement)?.blur());
      await page.keyboard.press('Escape');
      await expect(d).toHaveCount(0);
    });
  }

  test('B2: skip link is visible, keeps the view and replay position, and moves focus', async ({ page }) => {
    await page.goto(at(3));
    await page.keyboard.press('Tab');
    const link = page.getByRole('link', { name: 'Skip to content' });
    await expect(link).toBeFocused();
    expect((await link.boundingBox())!.y).toBeGreaterThanOrEqual(0);
    await page.keyboard.press('Enter');
    await expect(page.locator('main')).toBeFocused();
    await expect(page).toHaveURL(/#\/arena\?t=3$/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('+300');
  });

  test('B6: diagram parts are discoverable: labelled, focusable buttons with a visible hint', async ({ page }) => {
    await page.goto(at(3));
    await expect(page.getByText('Select any part of the diagram to see the record behind it.')).toBeVisible();
    const hits = page.locator('.scene .hit');
    expect(await hits.count()).toBeGreaterThan(4);
    for (const h of await hits.all()) {
      await expect(h).toHaveAttribute('role', 'button');
      await expect(h).toHaveAttribute('tabindex', '0');
      expect(await h.getAttribute('aria-label')).toMatch(/Inspect$/);
      expect(await h.evaluate((el) => getComputedStyle(el).cursor)).toBe('pointer');
    }
    await hits.first().focus();
    await page.keyboard.press('Enter');
    await expect(dialog(page)).toBeVisible();
  });
});

test('R6: the server under test serves the build produced for this run', async ({ request }) => {
  const html = await (await request.get('./')).text();
  const asset = /assets\/(index-[\w-]+\.js)/.exec(html)![1];
  expect(fs.existsSync(`dist/assets/${asset}`)).toBe(true);
});

test('R7: reduced motion removes movement from the player, diagram and drawer', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce', viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:4317/#/arena?t=3');
  for (const sel of ['.pbtn', '.pbtn.play', '.scrubber .knob', '.scrubber .fill', '.scene .block-body rect', '.scene .node', '.inspector']) {
    expect(await page.locator(sel).first().evaluate((el) => getComputedStyle(el).transitionProperty), sel).not.toMatch(/transform|left|width|all/);
  }
  expect(await page.locator('.scene .link[data-selected="true"]').first().evaluate((el) => getComputedStyle(el).animationName)).toBe('none');
  const btn = page.getByRole('button', { name: 'Previous scene' });
  const b = (await btn.boundingBox())!;
  await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2);
  await page.mouse.down();
  expect(await btn.evaluate((el) => getComputedStyle(el).transform)).toBe('none');
  await page.mouse.up();
  await ctx.close();
});

// ── B5: no overlapping or clipped labels, nothing clipped, 320 px to desktop ─
for (const width of [320, 390, 1440]) {
  test(`B5: no overlapping or clipped labels and no overflow at ${width}px`, async ({ browser }) => {
    const ctx = await browser.newContext({ viewport: { width, height: width < 700 ? 720 : 900 }, reducedMotion: 'reduce' });
    const page = await ctx.newPage();
    for (let t = -1; t <= N; t++) {
      await page.goto(`http://127.0.0.1:4317/#/arena${t < 0 ? '' : `?t=${t}`}`);
      await page.waitForTimeout(60);
      const problems = await page.evaluate(() => {
        const svg = document.querySelector('.scene') as SVGSVGElement;
        const frame = svg.getBoundingClientRect();
        const boxes = [...svg.querySelectorAll('text')]
          .map((el) => ({ r: el.getBoundingClientRect(), t: el.textContent }))
          .filter(({ r }) => r.width > 0 && r.top >= frame.top + 28 && r.bottom <= frame.bottom); // fully inside the camera, below the top fade
        const out: string[] = [];
        for (const { r, t } of boxes) if (r.left < frame.left - 1 || r.right > frame.right + 1) out.push(`clipped: ${t}`);
        for (let i = 0; i < boxes.length; i++)
          for (let j = i + 1; j < boxes.length; j++) {
            const a = boxes[i].r, b = boxes[j].r;
            if (a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1) out.push(`overlap: "${boxes[i].t}" × "${boxes[j].t}"`);
          }
        const over = document.documentElement.scrollWidth - document.documentElement.clientWidth;
        if (over > 0) out.push(`page overflow ${over}px`);
        for (const b of document.querySelectorAll('.player button')) {
          const r = b.getBoundingClientRect();
          if (r.right > window.innerWidth + 0.5 || r.left < -0.5) out.push(`player control clipped: ${b.getAttribute('aria-label')}`);
        }
        return out;
      });
      expect(problems, `${width}px, scene ${t + 2}`).toEqual([]);
    }
    await ctx.close();
  });
}

test.describe('mobile', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone layout');

  test('narration, the relevant diagram and the player share the first screen', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    for (const [t, sel] of [[1, '.scene .block'], [3, '.scene .excess'], [5, '.scene .account-node']] as const) {
      await page.goto(at(t));
      await page.waitForTimeout(50);
      const player = (await page.locator('.player').boundingBox())!;
      const b = (await page.locator(sel).first().boundingBox())!;
      expect(b.y + b.height, `${sel} at t=${t}`).toBeLessThanOrEqual(player.y);
      await expect(page.getByRole('heading', { level: 1 })).toBeInViewport();
    }
  });

  test('touch targets are at least 44px', async ({ page }) => {
    await page.goto(at(2));
    for (const name of ['Play', 'Previous scene', 'Next scene', 'Inspect the current event', 'Data: every figure and its source', /^Speed/]) {
      const b = (await page.getByRole('button', { name }).boundingBox())!;
      expect(b.height, String(name)).toBeGreaterThanOrEqual(44);
      expect(b.width, String(name)).toBeGreaterThanOrEqual(44);
    }
  });

  test('diagram labels render at a readable size (≥ 12px on screen)', async ({ page }) => {
    await page.goto(at(3));
    for (const sel of ['.scene .label', '.scene .block-label', '.scene .budget-mark text', '.scene .caption-label']) {
      const px = await page.locator(sel).first().evaluate((el) => (el as SVGTextElement).getBoundingClientRect().height);
      expect(px, sel).toBeGreaterThanOrEqual(12);
    }
  });
});

test('reserved and realized read clearly on the block', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(at(3));
  await expect(page.locator('.scene .block-label')).toHaveText(['eval-1 700', 'eval-2 200']);
  await expect(page.locator('.scene .block-delta')).toHaveText(['reserved 200 · +500', 'reserved 300 · 100 unused']);
  // Red marks only the over-budget region; per-task differences are neutral.
  await expect(page.locator('.scene .block-delta.loss, .scene .block-delta.gain')).toHaveCount(0);
  await expect(page.locator('.scene .excess-fill')).toHaveCount(1);
  await expect(page.locator('.scene .reserved-outline')).toHaveCount(2);
  await expect(page.getByRole('button', { name: 'eval-1: reserved 200, realized 700, 500 over. Inspect' })).toBeVisible();
});

test('closing frame states only what the events establish', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(at(N));
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Reserved 500. Used 900.');
  await expect(page.locator('.findings li')).toHaveText([
    'The plan fit the 600 budget (fixture annotation); the real costs ran +300 over it.',
    'eval\u20111 used 500 more than reserved; eval\u20112 used 100 less.',
    'Credits moved: agent\u20111 +4, fee_sink +2, maker −6. They sum to zero: nothing was created or burned.',
    'Agent\u20111 ends with utility +6 from cash +4.',
  ]);
});

test('unavailable views are short and draw no data', async ({ page }) => {
  for (const v of ['theater', 'evolution']) {
    await page.goto(`./#/${v}`);
    await expect(page.locator('.requires')).toBeVisible();
    await expect(page.locator('main circle, main rect, main path')).toHaveCount(0);
    expect((await page.locator('main').innerText()).split(/\s+/).length, v).toBeLessThan(90);
  }
});
