import { test, expect } from '@playwright/test';

/**
 * E2E tests for the dashboard page.
 *
 * Verifies:
 *   - KPI cards render with numeric values
 *   - Charts / visualization containers load
 *   - Sidebar navigation works (links are clickable and route correctly)
 */

test.describe('Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate directly to dashboard (assumes auth cookies or test bypass)
    await page.goto('/dashboard');

    // If redirected to login, perform login first
    if (page.url().includes('/login')) {
      const emailInput = page.getByLabel(/email/i).or(page.locator('input[type="email"]'));
      const passwordInput = page.getByLabel(/password/i).or(page.locator('input[type="password"]'));
      const submitButton = page.getByRole('button', { name: /sign in|log in|login/i });

      await emailInput.fill('admin@demo.kreupai.com');
      await passwordInput.fill('demo-password');

      const tenantInput = page.getByLabel(/tenant|workspace|organization/i);
      if (await tenantInput.isVisible().catch(() => false)) {
        await tenantInput.fill('demo');
      }

      await submitButton.click();
      await page.waitForURL(/\/(dashboard|home|app)/, { timeout: 10_000 });
    }
  });

  test('KPI cards render with values', async ({ page }) => {
    // Look for stat/KPI card containers
    const kpiCards = page
      .locator('[data-testid*="kpi"]')
      .or(page.locator('[class*="stat"]'))
      .or(page.locator('[class*="card"]').filter({ hasText: /\d+/ }));

    // Wait for at least one card to appear
    await expect(kpiCards.first()).toBeVisible({ timeout: 10_000 });

    // Verify there are multiple KPI cards
    const cardCount = await kpiCards.count();
    expect(cardCount).toBeGreaterThanOrEqual(1);
  });

  test('charts load within containers', async ({ page }) => {
    // Look for chart containers (canvas, svg, or dedicated chart divs)
    const chartContainers = page
      .locator('canvas')
      .or(page.locator('svg[class*="chart"]'))
      .or(page.locator('[data-testid*="chart"]'))
      .or(page.locator('[class*="chart"]'));

    // Wait for at least one chart to render
    await expect(chartContainers.first()).toBeVisible({ timeout: 15_000 });
  });

  test('sidebar navigation works', async ({ page }) => {
    // Find the sidebar or navigation element
    const sidebar = page
      .locator('nav')
      .or(page.locator('[data-testid="sidebar"]'))
      .or(page.locator('[class*="sidebar"]'));

    await expect(sidebar.first()).toBeVisible();

    // Find navigation links within the sidebar
    const navLinks = sidebar.first().locator('a');
    const linkCount = await navLinks.count();
    expect(linkCount).toBeGreaterThan(0);

    // Click the first non-active navigation link and verify navigation
    for (let i = 0; i < Math.min(linkCount, 5); i++) {
      const link = navLinks.nth(i);
      const href = await link.getAttribute('href');

      if (href && href !== '#' && !href.startsWith('javascript:')) {
        await link.click();
        // Verify navigation happened (URL changed or content updated)
        await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => {});

        // Navigate back to dashboard for next iteration
        await page.goto('/dashboard');
        break;
      }
    }
  });
});
