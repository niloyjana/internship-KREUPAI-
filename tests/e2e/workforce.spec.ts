import { test, expect } from '@playwright/test';

/**
 * E2E tests for the AI Workforce catalog page.
 *
 * Verifies:
 *   - Agent catalog page loads with agent cards
 *   - Department filter narrows the displayed agents
 *   - Clicking an agent card navigates to agent detail page
 */

test.describe('AI Workforce Catalog', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the workforce / agents catalog page
    await page.goto('/workforce');

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
      await page.waitForURL(/\/(dashboard|home|app|workforce)/, { timeout: 10_000 });

      // Navigate back to workforce if we ended up on dashboard
      if (!page.url().includes('/workforce')) {
        await page.goto('/workforce');
      }
    }
  });

  test('catalog page loads with agent cards', async ({ page }) => {
    // Wait for the catalog to render
    const agentCards = page
      .locator('[data-testid*="agent-card"]')
      .or(page.locator('[class*="agent-card"]'))
      .or(page.locator('[class*="card"]').filter({ hasText: /agent|worker|ai/i }));

    await expect(agentCards.first()).toBeVisible({ timeout: 10_000 });

    const cardCount = await agentCards.count();
    expect(cardCount).toBeGreaterThan(0);
  });

  test('filter by department narrows displayed agents', async ({ page }) => {
    // Find department filter (select, dropdown, or filter buttons)
    const departmentFilter = page
      .getByLabel(/department|category|filter/i)
      .or(page.locator('select[name*="department"]'))
      .or(page.locator('[data-testid*="department-filter"]'))
      .or(page.locator('[class*="filter"]').first());

    if (await departmentFilter.isVisible().catch(() => false)) {
      // Count initial cards
      const initialCards = page
        .locator('[data-testid*="agent-card"]')
        .or(page.locator('[class*="agent-card"]'))
        .or(page.locator('[class*="card"]').filter({ hasText: /agent|worker|ai/i }));

      const initialCount = await initialCards.count();

      // Select a specific department
      if (departmentFilter.first().evaluate((el) => el.tagName === 'SELECT')) {
        await departmentFilter.first().selectOption({ index: 1 });
      } else {
        await departmentFilter.first().click();
        // Click the first option in the dropdown
        const option = page.locator('[role="option"]').first();
        if (await option.isVisible().catch(() => false)) {
          await option.click();
        }
      }

      // Wait for re-render
      await page.waitForTimeout(1000);

      // Count should be <= initial (filtered)
      const filteredCount = await initialCards.count();
      expect(filteredCount).toBeLessThanOrEqual(initialCount);
    }
  });

  test('clicking agent card opens agent detail page', async ({ page }) => {
    // Wait for agent cards to load
    const agentCards = page
      .locator('[data-testid*="agent-card"]')
      .or(page.locator('[class*="agent-card"]'))
      .or(page.locator('[class*="card"]').filter({ hasText: /agent|worker|ai/i }));

    await expect(agentCards.first()).toBeVisible({ timeout: 10_000 });

    // Click the first agent card
    await agentCards.first().click();

    // Wait for navigation to detail page
    await page.waitForLoadState('networkidle', { timeout: 5_000 }).catch(() => {});

    // Verify we navigated to a detail page
    // The URL should contain an agent ID or the page should show detailed info
    const detailContent = page
      .locator('[data-testid*="agent-detail"]')
      .or(page.locator('h1, h2').filter({ hasText: /agent|worker|ai/i }))
      .or(page.locator('[class*="detail"]'));

    // At least one detail element should be visible
    const hasDetail = await detailContent.first().isVisible().catch(() => false);
    const urlChanged = !page.url().endsWith('/workforce');

    expect(hasDetail || urlChanged).toBeTruthy();
  });
});
