import { test, expect } from '@playwright/test';

test.describe('RoadSoS SOS Flow', () => {
  test.use({ baseURL: 'http://localhost:3000' });

  test('SOS flow from home page to dispatch - English', async ({ page }) => {
    // Navigate to home
    await page.goto('/');

    // Verify home page loads
    await expect(page).toHaveTitle(/RoadSoS/);
    await expect(page.locator('text=SOS')).toBeVisible();

    // Click/Type SOS button
    const [response] = await Promise.all([
      page.waitForResponse((resp) => resp.url().includes('/v1/incident/initiate')),
      page.click('button:has-text("SOS")'),
    ]);

    // Verify initiate response
    const respBody = await response.json();
    expect(respBody.incident_id).toBeTruthy();
    expect(respBody.first_question).toBeTruthy();

    // Wait for triage page
    await page.waitForURL('**/incident/**');

    // Answer 3-5 triage questions
    const firstQuestion = await page.locator('text=/Are you the victim|Are you helping/');
    expect(firstQuestion).toBeVisible();

    // Click "I am the victim" or equivalent
    await page.getByText(/victim|I am the victim/).click();

    // Continue answering
    await page.getByText(/No|unconscious|not responding/).first().click();
    await page.getByText(/No|not breathing/).first().click();

    // Verify we reach a completion state or dispatch screen
    await expect(page.locator('text=/severity|RED|YELLOW|GREEN|dispatch/i')).toBeVisible({ timeout: 10000 });
  });

  test('Triage chat component renders', async ({ page }) => {
    await page.goto('/');
    await page.click('button:has-text("SOS")');
    await page.waitForURL('**/incident/**');
    await expect(page.locator('[data-testid="triage-chat"]')).toBeVisible();
  });

  test('Admin dashboard loads with stats', async ({ page }) => {
    await page.goto('/admin');
    await expect(page.locator('text=Admin Dashboard')).toBeVisible();
    await expect(page.locator('text=Total Incidents')).toBeVisible();
  });

  test('AR page loads with camera start button', async ({ page }) => {
    await page.goto('/ar');
    await expect(page.locator('text=Start Camera')).toBeVisible();
    // Camera may not be available in test env - that's OK
    await page.click('button:has-text("Start Camera")');
  });
});