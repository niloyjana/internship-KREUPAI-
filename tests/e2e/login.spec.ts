import { test, expect } from '@playwright/test';

/**
 * E2E tests for the login flow.
 *
 * Verifies:
 *   - Login page renders correctly
 *   - Successful login redirects to dashboard
 *   - Invalid credentials show an error message
 *   - Empty form shows validation errors
 */

test.describe('Login Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
  });

  test('login page renders with form elements', async ({ page }) => {
    // Verify the login page loaded
    await expect(page).toHaveURL(/\/login/);

    // Check for email and password fields
    const emailInput = page.getByLabel(/email/i).or(page.locator('input[type="email"]'));
    const passwordInput = page.getByLabel(/password/i).or(page.locator('input[type="password"]'));
    const submitButton = page.getByRole('button', { name: /sign in|log in|login/i });

    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(submitButton).toBeVisible();
  });

  test('successful login redirects to dashboard', async ({ page }) => {
    // Fill in valid credentials
    const emailInput = page.getByLabel(/email/i).or(page.locator('input[type="email"]'));
    const passwordInput = page.getByLabel(/password/i).or(page.locator('input[type="password"]'));
    const submitButton = page.getByRole('button', { name: /sign in|log in|login/i });

    await emailInput.fill('admin@demo.kreupai.com');
    await passwordInput.fill('demo-password');

    // Also fill tenant/workspace if visible
    const tenantInput = page.getByLabel(/tenant|workspace|organization/i);
    if (await tenantInput.isVisible().catch(() => false)) {
      await tenantInput.fill('demo');
    }

    await submitButton.click();

    // Wait for navigation to dashboard
    await page.waitForURL(/\/(dashboard|home|app)/, { timeout: 10_000 });

    // Verify we landed on the dashboard
    await expect(page).toHaveURL(/\/(dashboard|home|app)/);
  });

  test('invalid credentials show error message', async ({ page }) => {
    const emailInput = page.getByLabel(/email/i).or(page.locator('input[type="email"]'));
    const passwordInput = page.getByLabel(/password/i).or(page.locator('input[type="password"]'));
    const submitButton = page.getByRole('button', { name: /sign in|log in|login/i });

    await emailInput.fill('wrong@example.com');
    await passwordInput.fill('wrong-password');
    await submitButton.click();

    // Expect an error message to appear
    const errorMessage = page
      .getByText(/invalid|incorrect|unauthorized|failed/i)
      .or(page.locator('[role="alert"]'));

    await expect(errorMessage).toBeVisible({ timeout: 5_000 });
  });

  test('empty form shows validation errors', async ({ page }) => {
    const submitButton = page.getByRole('button', { name: /sign in|log in|login/i });

    // Click submit without filling any fields
    await submitButton.click();

    // Expect validation messages for required fields
    const validationMessage = page
      .getByText(/required|enter.*email|enter.*password/i)
      .or(page.locator(':invalid'));

    // At least one validation indicator should appear
    const validationCount = await validationMessage.count();
    expect(validationCount).toBeGreaterThan(0);
  });
});
