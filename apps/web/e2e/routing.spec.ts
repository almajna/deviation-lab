import { test, expect } from '@playwright/test';

test('selects real cases and steps through recorded requests', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Scientific verdict: INCONCLUSIVE.')).toBeVisible();
  await page.getByLabel('Execution').selectOption('1');
  await page.getByLabel('Seed').selectOption('23');
  await page.getByLabel('Condition').selectOption('inflated');
  await expect(page.getByRole('heading', {name: 'Request 1 of 24 — warmup'})).toBeVisible();
  await page.getByRole('button', {name: 'Next request'}).click();
  await expect(page.getByRole('heading', {name: 'Request 2 of 24 — warmup'})).toBeVisible();
  await page.getByLabel('Request', {exact: true}).fill('5');
  await expect(page.getByRole('heading', {name: 'Request 5 of 24 — measured'})).toBeVisible();
  await page.getByLabel('Seed').selectOption('7');
  await expect(page.getByRole('heading', {name: 'Request 1 of 24 — warmup'})).toBeVisible();
  await expect(page.getByText(/streaming control, honest and inflated routed 0 of 20/)).toBeVisible();
});
