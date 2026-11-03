import { expect, test, type Page } from '@playwright/test';
import fs from 'node:fs';

// Browser tests. Names prefixed "R<n>" are regressions for the PR #17 review findings
// (docs/REVIEW.md maps each finding to its fix and test).

const TRACE = JSON.parse(fs.readFileSync('fixtures/gate-a.synthetic.json', 'utf8'));
const EVENTS = TRACE.events as any[];
const N = EVENTS.length; // 7 events; cursor N is the closing frame
const slider = (p: Page) => p.getByRole('slider', { name: 'Replay position' });
const dialog = (p: Page) => p.getByRole('dialog');
const file = (name: string, body: unknown) => ({ name, mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(body)) });
const loader = (p: Page) => p.getByLabel('Load a v0.2 completed trace JSON file');

test.describe('Market Arena', () => {
  test('opens on the synthetic label and an un-played replay', async ({ page }) => {
    await page.goto('./');
    await expect(page.getByRole('button', { name: /Data provenance: synthetic fixture, not a result/ })).toBeVisible();
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Two tasks');
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '0');
    await expect(page.getByText('sealed', { exact: true }).first()).toBeVisible();
  });

  test('step, seek and rewind are deterministic and deep-linkable', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('./');
    const step = page.getByRole('button', { name: 'Step forward' });
    for (let i = 0; i < 4; i++) await step.click();
    await expect(page).toHaveURL(/t=3/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('+300');
    const settled = await page.locator('.stage').textContent();
    await page.getByRole('button', { name: 'Rewind to start' }).click();
    await expect(page).not.toHaveURL(/t=/);
    await page.goto('./#/arena?t=3');
    await expect(page.locator('.stage')).toHaveText(settled!);
    await page.getByRole('button', { name: 'Step back' }).click();
    await expect(page.getByText('sealed', { exact: true }).first()).toBeVisible();
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

  test('keyboard steps land instantly: no entrance animation', async ({ page }) => {
    await page.goto('./#/arena?t=3');
    await page.locator('body').press('ArrowRight');
    await expect(page).toHaveURL(/t=4/);
    for (const sel of ['.account', '.seg.grow', '.narration h1']) {
      expect(await page.locator(sel).first().evaluate((el) => getComputedStyle(el).animationName), sel).toBe('none');
    }
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

  test('inspect why an agent received credits', async ({ page }) => {
    await page.goto(`./#/arena?t=${N - 1}`);
    await page.getByRole('button', { name: /Account agent-1/ }).click();
    await expect(dialog(page)).toContainText('Synthetic economic agent');
    await expect(dialog(page)).toContainText('+6 ← maker');
    await expect(dialog(page)).not.toContainText('initial balance');
    await expect(dialog(page)).toContainText('private signal are not part of the public replay');
    await dialog(page).getByRole('button', { name: 'Seek to event 6' }).click();
    await expect(page).toHaveURL(/t=5/);
    await expect(page.getByRole('heading', { level: 1 })).toContainText('Maker pays agent-1');
  });

  test('rejects an invalid trace file with a reason', async ({ page }) => {
    await page.goto('./');
    await loader(page).setInputFiles(file('bad.json', { schema_version: '0.1', events: [] }));
    await expect(page.getByRole('alert')).toContainText('bad.json was not loaded');
  });

  test('exports the exact trace', async ({ page }) => {
    await page.goto('./');
    const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download complete trace' }).click()]);
    expect(download.suggestedFilename()).toBe('SYNTHETIC-contract-conformance.seed-7.trace.json');
    expect(JSON.parse(fs.readFileSync(await download.path(), 'utf8'))).toEqual(TRACE);
  });
});

test.describe('controls', () => {
  test.use({ reducedMotion: 'reduce' });

  test('rewind, step bounds and disabled states', async ({ page }) => {
    await page.goto('./');
    await expect(page.getByRole('button', { name: 'Rewind to start' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Step back' })).toBeDisabled();
    await page.goto(`./#/arena?t=${N}`);
    await expect(page.getByRole('button', { name: 'Step forward' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Replay from start' })).toBeVisible();
    await page.getByRole('button', { name: 'Rewind to start' }).click();
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '0');
  });

  test('speed control changes dwell time', async ({ page, isMobile }) => {
    await page.goto('./');
    if (isMobile) {
      await page.getByRole('button', { name: /^Speed 1×, change to 2×/ }).click();
      await expect(page.getByRole('button', { name: /^Speed 2×/ })).toBeVisible();
    } else {
      for (const s of ['0.5×', '2×']) {
        await page.getByRole('button', { name: s, exact: true }).click();
        await expect(page.locator('.speed[aria-pressed="true"]')).toHaveText(s);
      }
    }
    const t0 = Date.now();
    await page.getByRole('button', { name: 'Play' }).click();
    await expect(page).toHaveURL(/t=1/, { timeout: 5000 });
    expect(Date.now() - t0).toBeLessThan(3500); // 1× needs ≥ 3.6 s to reach event 2
  });

  test('play runs to the closing frame and stops; Replay restarts', async ({ page }) => {
    await page.clock.install();
    await page.goto('./');
    await page.getByRole('button', { name: 'Play' }).click();
    await page.clock.runFor(90_000);
    await expect(page).toHaveURL(new RegExp(`t=${N}`));
    await expect(page.getByRole('button', { name: 'Replay from start' })).toBeVisible();
    await page.getByRole('button', { name: 'Replay from start' }).click();
    await expect(page.getByRole('button', { name: 'Pause' })).toBeVisible();
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '0');
  });

  test('timeline click and drag seek to whole frames; controls never move', async ({ page }) => {
    await page.goto('./');
    const box = (await slider(page).boundingBox())!;
    const at = (i: number) => box.x + box.width * ((i + 0.5) / (N + 1));
    await page.mouse.click(at(4), box.y + box.height / 2);
    await expect(page).toHaveURL(/t=4/);
    expect((await slider(page).boundingBox())!.y).toBeCloseTo(box.y, 0);
    await page.mouse.move(at(0), box.y + 5);
    await page.mouse.down();
    await page.mouse.move(at(2), box.y + 5, { steps: 6 });
    await page.mouse.up();
    await expect(page).toHaveURL(/t=2/);
    for (const t of [0, 3, N]) {
      await page.goto(`./#/arena?t=${t}`);
      expect((await slider(page).boundingBox())!.y, `t=${t}`).toBeCloseTo(box.y, 0);
    }
  });

  test('slider keys, nav links, provenance and trace selector', async ({ page }) => {
    await page.goto('./');
    await slider(page).focus();
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await expect(slider(page)).toHaveAttribute('aria-valuenow', '2');
    await page.getByRole('button', { name: /Data provenance/ }).click();
    await expect(dialog(page)).toContainText('apps/web/fixtures/gate-a.synthetic.json');
    await expect(dialog(page)).toContainText('Fixture annotation');
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

  test('a valid loaded trace replaces the replay and stays labelled', async ({ page }) => {
    await page.goto('./');
    await loader(page).setInputFiles({ name: 'mine.json', mimeType: 'application/json', buffer: fs.readFileSync('fixtures/gate-a.synthetic.json') });
    await expect(page.getByRole('combobox', { name: 'Select trace' })).toHaveValue('file:mine.json');
    await expect(page.getByRole('button', { name: /Data provenance: loaded file/ })).toBeVisible();
    await page.goto(`./#/arena?t=3&trace=${encodeURIComponent('file:mine.json')}`);
    await expect(page.getByText('budget unknown', { exact: false })).toHaveCount(0); // reload drops loaded files
  });

  test('copy JSON and seek from the inspector', async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']).catch(() => {});
    await page.goto('./#/arena?t=4');
    await page.getByRole('button', { name: 'View source event 5' }).click();
    await dialog(page).getByRole('button', { name: 'Copy JSON' }).click();
    await expect(dialog(page).getByRole('button', { name: /Copied|Copy unavailable/ })).toBeVisible();
    await dialog(page).getByRole('button', { name: 'Seek here' }).click();
    await expect(page).toHaveURL(/t=4/);
  });
});

test('every displayed figure equals a value in its source event', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`./#/arena?t=${N}`);
  const figures = page.locator('.stage button.value-btn');
  const count = await figures.count();
  expect(count).toBeGreaterThan(5);
  for (let i = 0; i < count; i++) {
    const aria = (await figures.nth(i).getAttribute('aria-label'))!;
    const seq = Number(/Inspect event (\d+)/.exec(aria)![1]) - 1;
    const values: number[] = [];
    JSON.stringify(EVENTS[seq].payload, (_k, v) => (typeof v === 'number' && values.push(v), v));
    const derived = EVENTS[seq].type === 'realized_cost_report'
      ? EVENTS[seq].payload.selected_costs.map((c: any) => Math.abs(c.realized_cost - EVENTS.find((e: any) => e.type === 'reservation' && e.payload.task_id === c.task_id).payload.reserved_cost))
      : [];
    for (const shown of (await figures.nth(i).innerText()).split(/\s+/).filter((x) => /\d/.test(x))) {
      const v = Number(shown.replace(/[+,]/g, '').replace('−', '-'));
      expect(values.some((x) => Math.abs(x) === Math.abs(v)) || derived.includes(Math.abs(v)), `${aria} shows ${shown}`).toBe(true);
    }
  }
  const net = (id: string) => EVENTS.filter((e) => e.type === 'ledger_transfer').reduce((s, e) => s + (e.payload.payee === id ? e.payload.amount : e.payload.payer === id ? -e.payload.amount : 0), 0);
  for (const id of ['agent-1', 'fee_sink', 'maker']) {
    const v = net(id);
    await expect(page.getByRole('button', { name: new RegExp(`Account ${id}: change ${v > 0 ? '\\+' : v < 0 ? '−' : ''}${Math.abs(v)} credits`) })).toBeVisible();
  }
});

// ── R2: no future information anywhere, at any position ───────────────────
test.describe('R2 knowledge boundary', () => {
  test.use({ reducedMotion: 'reduce' });

  // Tokens that first appear in event k's payload: multi-digit figures and identifiers
  // (strings with "_", "-" or digits, such as agent-1, fee_sink, action_fee, reward-1).
  const tokensOf = (e: any) => {
    const t = new Set<string>();
    const walk = (v: any) => {
      if (typeof v === 'number' && Number.isInteger(v) && Math.abs(v) >= 10) t.add(String(v));
      else if (typeof v === 'string' && /[_\-\d]/.test(v) && /[a-z]/.test(v)) t.add(v);
      else if (v && typeof v === 'object') {
        for (const [k, x] of Object.entries(v)) {
          if (!Array.isArray(v) && /\d/.test(k)) t.add(k); // account names used as keys (utility_summary)
          walk(x);
        }
      }
    };
    walk(e.payload);
    return t;
  };
  const before = (k: number) => {
    const known = new Set<string>(['600', 'eval-1', 'eval-2', 'nano_synthetic_units', 'expected_preference_proxy']);
    let reserved = 0;
    for (let i = 0; i <= k; i++) {
      tokensOf(EVENTS[i]).forEach((x) => known.add(x));
      if (EVENTS[i].type === 'reservation') known.add(String((reserved += EVENTS[i].payload.reserved_cost))); // running total is displayed
    }
    const future = new Set<string>();
    for (let i = k + 1; i < N; i++) tokensOf(EVENTS[i]).forEach((x) => !known.has(x) && future.add(x));
    return [...future];
  };
  // Axis ticks are scale labels, not data; strip them (and static legends) before scanning.
  const scan = (p: Page) =>
    p.evaluate(() => {
      const pick = (sel: string) => {
        const el = document.querySelector(sel)!.cloneNode(true) as HTMLElement;
        el.querySelectorAll('.axis, .legend, .boundary, .budget-line').forEach((x) => x.remove());
        return el.innerHTML;
      };
      return pick('main') + pick('.timeline');
    });

  for (const k of [-1, 0, 1, 2, 3, 4, 5]) {
    test(`position ${k + 1}: page and inspectors contain nothing from later events`, async ({ page }) => {
      await page.goto(k < 0 ? './' : `./#/arena?t=${k}`);
      const future = before(k);
      const html = await scan(page);
      if (k < N - 2) expect(future.length, 'test must have something to look for').toBeGreaterThan(0);
      for (const tok of future) expect(html, `"${tok}" leaked at position ${k + 1}`).not.toMatch(new RegExp(`(^|[^\\w.-])${tok.replace(/[-_]/g, '\\$&')}([^\\w-]|$)`));
      // Every inspector reachable at this position shows only the past.
      const accounts = page.getByRole('button', { name: /^Account / });
      for (let i = 0; i < (await accounts.count()); i++) {
        await accounts.nth(i).click();
        const text = await dialog(page).innerText();
        for (const tok of future) expect(text, `"${tok}" leaked in an account inspector at ${k + 1}`).not.toContain(tok);
        for (let s = k + 1; s < N; s++) expect(text).not.toContain(`event ${s + 1}`);
        await page.keyboard.press('Escape');
      }
      if (k >= 0) {
        await page.getByRole('button', { name: `View source event ${k + 1}` }).click();
        const text = await dialog(page).innerText();
        for (const tok of future) expect(text).not.toContain(tok);
        await page.keyboard.press('Escape');
      }
    });
  }

  test('R2: at event 5 the agent inspector shows the fee only, no payout, cash total or utility', async ({ page }) => {
    await page.goto('./#/arena?t=4');
    await page.getByRole('button', { name: /Account agent-1/ }).click();
    await expect(dialog(page)).toContainText('−2 → fee_sink');
    await expect(dialog(page)).toContainText('net so far');
    await expect(dialog(page)).not.toContainText('maker');
    await expect(dialog(page)).not.toContainText('+6');
    await expect(dialog(page)).not.toContainText('utility +');
    await expect(dialog(page)).toContainText('Utility is reported at the end of settlement');
  });

  test('R2: before settlement no account, transfer or utility is rendered at all', async ({ page }) => {
    await page.goto('./#/arena?t=2');
    await expect(page.getByRole('button', { name: /^Account / })).toHaveCount(0);
    await expect(page.getByText('No credits move until settlement.')).toBeVisible();
    await expect(page.locator('.frame[data-tone]')).toHaveCount(0);
    await expect(page.locator('.seg.over, .seg.dim, .bar-note')).toHaveCount(0);
  });

  test('R2: an inspector cannot show an event beyond the current position', async ({ page }) => {
    await page.goto('./#/arena?t=6');
    await page.getByRole('button', { name: /Utility/i }).first().click().catch(() => {});
    await page.keyboard.press('Escape');
    await page.goto('./#/arena?t=1');
    // Seek back with the inspector open: content re-derives from the new position.
    await page.getByRole('button', { name: 'View source event 2' }).click();
    await expect(dialog(page)).toContainText('reservation');
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

// ── R3/R4: imported accounting must reconcile; bad imports are recoverable ─
test.describe('R3/R4 imports', () => {
  const pack = { trace: TRACE, run_config: { schema_version: '0.2', cost_unit: 'nano_synthetic_units', reservation_budget: 600, agent_accounts: ['agent-1'], maker_account: 'maker', fee_sink_account: 'fee_sink', initial_balances: { 'agent-1': 20, fee_sink: 0, maker: 50 }, exogenous_history_actors: ['seed-history'] } };
  const ledger = { schema_version: '0.2', unit: 'virtual_credit', initial_balances: { 'agent-1': 20, fee_sink: 0, maker: 50 }, final_balances: { 'agent-1': 24, fee_sink: 2, maker: 44 }, transfers: EVENTS.filter((e) => e.type === 'ledger_transfer').map((e) => e.payload), agent_utilities: EVENTS[N - 1].payload, maker_account: 'maker', maker_initial_subsidy: 50, maker_cash_pnl: -6, maker_realized_loss: 6 };

  const cases: Array<[string, unknown, RegExp]> = [
    ['contradictory final balance', { ...pack, ledger: { ...ledger, final_balances: { ...ledger.final_balances, maker: 45 } } }, /final balance for maker is 45, transfers imply 44/],
    ['missing utility summary', { ...TRACE, events: EVENTS.slice(0, -1) }, /no utility_summary/],
    ['duplicate utility summary', { ...TRACE, events: [...EVENTS, { ...EVENTS[N - 1], seq: N }] }, /after the utility summary/],
    ['invalid settlement actor', { ...TRACE, events: EVENTS.map((e, i) => (i === 3 ? { ...e, actor: 'allocator' } : e)) }, /must be recorded by "system"/],
    ['post-summary transfer', { ...TRACE, events: [...EVENTS, { ...EVENTS[4], seq: N, payload: { ...EVENTS[4].payload, transfer_id: 'late' } }] }, /after the utility summary/],
    ['malformed run_config', { ...pack, run_config: { ...pack.run_config, initial_balances: { 'agent-1': 'twenty' } } }, /run_config\.initial_balances\.agent-1/],
    ['malformed decision_tasks', { ...pack, decision_tasks: [{}] }, /decision_tasks\[0\]/],
    ['ledger without run_config', { trace: TRACE, ledger }, /requires the trusted run_config/],
    ['private fields in the file', { ...pack, information: {} }, /fields outside a public replay bundle \(information\)/],
  ];
  for (const [name, body, msg] of cases) {
    test(`rejects ${name} with a recoverable error`, async ({ page }) => {
      await page.goto('./');
      await loader(page).setInputFiles(file('x.json', body));
      await expect(page.getByRole('alert')).toContainText(msg);
      // The app is intact and still plays the bundled fixture.
      await page.getByRole('button', { name: 'Step forward' }).click();
      await expect(page).toHaveURL(/t=0/);
      await expect(page.getByRole('combobox', { name: 'Select trace' })).toHaveValue('fixture:gate-a');
    });
  }

  test('a fully reconciled bundle shows balances and its ledger checks out', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('./');
    await loader(page).setInputFiles(file('full.json', { ...pack, ledger }));
    await expect(page.getByRole('alert')).toHaveCount(0);
    await page.getByRole('button', { name: 'Step forward' }).click();
    await page.locator('body').press('End');
    await expect(page.getByRole('button', { name: /Account maker: change −6 credits/ })).toContainText('44');
    await expect(page.getByRole('button', { name: /Account agent-1: change \+4 credits/ })).toContainText('24');
  });
});

// ── R5: modal semantics, contained focus, skip link ─────────────────────────
test.describe('R5 accessibility', () => {
  test('inspector is a labelled modal with contained focus and inert background', async ({ page }) => {
    await page.goto('./#/arena?t=3');
    const trigger = page.getByRole('button', { name: 'View source event 4' });
    await trigger.click();
    const d = dialog(page);
    await expect(d).toHaveAttribute('aria-modal', 'true');
    await expect(d).toHaveAccessibleName('Event 4');
    await expect(page.locator('main')).toHaveAttribute('inert', '');
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press(i % 3 ? 'Tab' : 'Shift+Tab');
      expect(await d.evaluate((el) => el.contains(document.activeElement))).toBe(true);
    }
    await page.keyboard.press('Escape');
    await expect(d).toHaveCount(0);
    await expect(page.locator('main')).not.toHaveAttribute('inert', '');
    await expect(trigger).toBeFocused();
  });

  test('scrim click closes the modal', async ({ page }) => {
    await page.goto('./#/arena?t=3');
    await page.getByRole('button', { name: 'View source event 4' }).click();
    await page.locator('.scrim').click({ position: { x: 5, y: 5 } });
    await expect(dialog(page)).toHaveCount(0);
  });

  test('skip link is visible when focused and moves focus to the content', async ({ page }) => {
    await page.goto('./');
    await page.keyboard.press('Tab');
    const link = page.getByRole('link', { name: 'Skip to content' });
    await expect(link).toBeFocused();
    const box = (await link.boundingBox())!;
    expect(box.y).toBeGreaterThanOrEqual(0);
    expect(box.height).toBeGreaterThan(20);
    expect(await link.evaluate((el) => getComputedStyle(el).color)).not.toBe(await link.evaluate((el) => getComputedStyle(el).backgroundColor));
    await page.keyboard.press('Enter');
    await expect(page.locator('main')).toBeFocused();
  });
});

// ── R6: tests run against this build only ─────────────────────────────────
test('R6: the server under test serves the build produced for this run', async ({ request }) => {
  const html = await (await request.get('./')).text();
  const asset = /assets\/(index-[\w-]+\.js)/.exec(html)![1];
  expect(fs.existsSync(`dist/assets/${asset}`)).toBe(true);
  expect(html).toContain('<title>DEVIATION</title>');
});

// ── R7: reduced motion removes all movement, including the transport ──────
test('R7: reduced motion removes movement from transport, playhead, bars and drawer', async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: 'reduce', viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto('http://127.0.0.1:4317/#/arena?t=3');
  const prop = (sel: string) => page.locator(sel).first().evaluate((el) => getComputedStyle(el).transitionProperty);
  for (const sel of ['.tbtn', '.tbtn.primary', '.playhead', '.seg', '.frame', '.inspector', '.track > i']) {
    expect(await prop(sel), sel).not.toMatch(/transform|left|width|all/);
  }
  const btn = page.getByRole('button', { name: 'Step back' });
  const box = (await btn.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  expect(await btn.evaluate((el) => getComputedStyle(el).transform)).toBe('none');
  await page.mouse.up();
  expect(await page.locator('.seg').first().evaluate((el) => getComputedStyle(el).animationName)).toBe('none');
  await ctx.close();
});

// ── Mobile composition ────────────────────────────────────────────────────
test.describe('mobile', () => {
  test.skip(({ isMobile }) => !isMobile, 'phone layout');

  test('narration, the current diagram and the player share the first screen', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    const vh = page.viewportSize()!.height;
    for (const [t, row] of [[3, 'budget'], [5, 'ledger'], [0, 'tasks']] as const) {
      await page.goto(`./#/arena?t=${t}`);
      const dock = (await page.locator('.timeline').boundingBox())!;
      const target = row === 'tasks' ? page.locator('[data-row="tasks"] .model').first() : row === 'budget' ? page.locator('.bar-row').last() : page.locator('.account').first();
      const b = (await target.boundingBox())!;
      expect(b.y + b.height, `${row} at t=${t}`).toBeLessThanOrEqual(dock.y);
      expect(dock.y + dock.height).toBeLessThanOrEqual(vh + 1);
      await expect(page.getByRole('heading', { level: 1 })).toBeInViewport();
    }
  });

  test('player is compact and touch targets are at least 44px', async ({ page }) => {
    await page.goto('./#/arena?t=2');
    expect((await page.locator('.timeline').boundingBox())!.height).toBeLessThanOrEqual(130);
    for (const name of ['Play', 'Rewind to start', 'Step back', 'Step forward']) {
      const b = (await page.getByRole('button', { name }).boundingBox())!;
      expect(b.height, name).toBeGreaterThanOrEqual(44);
      expect(b.width, name).toBeGreaterThanOrEqual(44);
    }
  });

  test('labels are readable (≥ 12px)', async ({ page }) => {
    await page.goto('./#/arena?t=3');
    for (const sel of ['.colhead span', '.axis .ticks span', '.caption small', '.bar-row > span:first-child', '.model .name']) {
      const px = await page.locator(sel).first().evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
      expect(px, sel).toBeGreaterThanOrEqual(12);
    }
  });
});

test('ledger draws one arrow per known transfer, labelled with its amount', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('./#/arena?t=4');
  await expect(page.locator('.flows g')).toHaveCount(1);
  await expect(page.locator('.flows g.live text')).toHaveText('2');
  await page.goto('./#/arena?t=5');
  await expect(page.locator('.flows g')).toHaveCount(2);
  await expect(page.locator('.flows g.live text')).toHaveText('6');
  await expect(page.locator('.flows g.past path')).toHaveAttribute('marker-end', 'url(#arrow-past)');
});

test('visually hidden labels stay hidden (no stray "Trace" text)', async ({ page }) => {
  await page.goto('./');
  const box = await page.locator('.tracebar .sr-only').first().boundingBox();
  expect(box!.width).toBeLessThanOrEqual(1);
  await expect(page.getByRole('combobox', { name: 'Select trace' })).toBeVisible();
});

test('ledger arc labels do not touch another arc', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('./#/arena?t=5');
  const overlap = await page.evaluate(() => {
    const labels = [...document.querySelectorAll('.flows text')] as SVGTextElement[];
    const paths = [...document.querySelectorAll('.flows path')] as SVGPathElement[];
    let hits = 0;
    labels.forEach((t, i) => {
      const b = t.getBBox();
      paths.forEach((p, j) => {
        if (j === i) return;
        for (let s = 0; s <= 1; s += 0.01) {
          const pt = p.getPointAtLength(p.getTotalLength() * s);
          if (pt.x >= b.x && pt.x <= b.x + b.width && pt.y >= b.y && pt.y <= b.y + b.height) { hits++; break; }
        }
      });
    });
    return hits;
  });
  expect(overlap).toBe(0);
});

test('reserved and realized are separate columns; the change is labelled', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('./#/arena?t=3');
  const row = page.locator('[aria-label="Task eval-1"] .model[data-chosen="true"]');
  await expect(row.locator('.cost').first()).toHaveText('200');
  await expect(row.locator('.realized')).toHaveText('700+500 over');
  await expect(row.locator('.realized small')).toHaveClass(/loss/);
  await expect(page.locator('[aria-label^="Task eval-2"] .model[data-chosen="true"] .realized')).toHaveText('200100 under');
  await expect(page.getByRole('button', { name: 'Realized 700, 500 over the reservation. Inspect event 4' })).toBeVisible();
});

test('closing frame states only what the events establish', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(`./#/arena?t=${N}`);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Within budget on paper. +300 over once costs were known.');
  const items = page.locator('.findings li');
  await expect(items).toHaveText([
    'Reserved 500 of a 600 budget before any cost was revealed.',
    'eval-1 ran +500 over its reservation; eval-2 came in 100 under.',
    'Credits moved: agent-1 +4, fee_sink +2, maker −6. They sum to zero: nothing was created or burned.',
    'Agent-1 ends with utility +6 from cash +4.',
  ]);
  await expect(page.getByText('not a mechanism result')).toBeVisible();
});

test('unavailable views are short and draw no data', async ({ page }) => {
  for (const v of ['theater', 'evolution']) {
    await page.goto(`./#/${v}`);
    await expect(page.locator('.requires')).toBeVisible();
    await expect(page.locator('main circle, main rect, main path')).toHaveCount(0);
    const words = (await page.locator('main').innerText()).split(/\s+/).length;
    expect(words, v).toBeLessThan(90);
  }
});

test('no horizontal overflow', async ({ page }) => {
  for (const v of [`arena?t=${N}`, 'arena?t=3', 'theater', 'evolution']) {
    await page.goto(`./#/${v}`);
    const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(over, v).toBeLessThanOrEqual(0);
  }
});
