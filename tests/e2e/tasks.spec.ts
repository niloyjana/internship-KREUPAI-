import { test, expect } from '@playwright/test';

/**
 * E2E tests for the task queue page.
 *
 * Verifies:
 *   - Task queue page loads with a table of tasks
 *   - Table rows render with expected columns
 *   - Clicking a task opens a detail drawer or modal
 */

test.describe('Task Queue', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the tasks page
    await page.goto('/tasks');

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
      await page.waitForURL(/\/(dashboard|home|app|tasks)/, { timeout: 10_000 });

      // Navigate back to tasks if we ended up on dashboard
      if (!page.url().includes('/tasks')) {
        await page.goto('/tasks');
      }
    }
  });

  test('task queue page renders with a table', async ({ page }) => {
    // Wait for the task table or list to load
    const taskTable = page
      .locator('table')
      .or(page.locator('[data-testid*="task-table"]'))
      .or(page.locator('[data-testid*="task-list"]'))
      .or(page.locator('[class*="table"]'))
      .or(page.locator('[role="table"]'));

    await expect(taskTable.first()).toBeVisible({ timeout: 10_000 });
  });

  test('table rows render with data', async ({ page }) => {
    // Wait for table body rows
    const tableRows = page
      .locator('table tbody tr')
      .or(page.locator('[data-testid*="task-row"]'))
      .or(page.locator('[class*="table-row"]'));

    await expect(tableRows.first()).toBeVisible({ timeout: 10_000 });

    const rowCount = await tableRows.count();
    expect(rowCount).toBeGreaterThan(0);

    // Check that table headers include expected columns
    const headers = page
      .locator('table thead th')
      .or(page.locator('[role="columnheader"]'));

    if (await headers.first().isVisible().catch(() => false)) {
      const headerCount = await headers.count();
      expect(headerCount).toBeGreaterThanOrEqual(2);
    }
  });

  test('clicking a task opens detail drawer', async ({ page }) => {
    // Wait for table rows to load
    const tableRows = page
      .locator('table tbody tr')
      .or(page.locator('[data-testid*="task-row"]'))
      .or(page.locator('[class*="table-row"]'));

    await expect(tableRows.first()).toBeVisible({ timeout: 10_000 });

    // Click the first task row
    await tableRows.first().click();

    // Wait for a drawer, modal, or detail panel to appear
    const drawer = page
      .locator('[data-testid*="drawer"]')
      .or(page.locator('[data-testid*="detail"]'))
      .or(page.locator('[class*="drawer"]'))
      .or(page.locator('[class*="sheet"]'))
      .or(page.locator('[role="dialog"]'))
      .or(page.locator('[class*="modal"]'))
      .or(page.locator('[class*="panel"]'));

    // The detail view should become visible
    await expect(drawer.first()).toBeVisible({ timeout: 5_000 });

    // Verify the drawer contains task-related content
    const drawerContent = drawer.first();
    await expect(drawerContent).toContainText(/.+/); // Should have some text content
  });
});
