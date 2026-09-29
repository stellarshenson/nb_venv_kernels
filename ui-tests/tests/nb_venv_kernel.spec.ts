import { expect, test } from '@jupyterlab/galata';

/**
 * Don't load JupyterLab webpage before running the tests.
 * This is required to ensure we capture all log messages.
 */
test.use({ autoGoto: false });

/**
 * Ready means the splash is gone and the shell is mounted. Galata's default
 * also waits for the Launcher to be the active tab, which never happens when
 * another extension opens its own tab at startup.
 */
test.use({
  waitForApplication: async ({ baseURL }, use) => {
    await use(async page => {
      await page.locator('#jupyterlab-splash').waitFor({ state: 'detached' });
      await page.locator('#main').waitFor();
    });
  }
});

test('should emit an activation console message', async ({ page }) => {
  const logs: string[] = [];

  page.on('console', message => {
    logs.push(message.text());
  });

  await page.goto();

  expect(
    logs.filter(s => s === 'JupyterLab extension nb_venv_kernels is activated!')
  ).toHaveLength(1);
});

test('scan command opens the scan results dialog', async ({ page }) => {
  await page.goto();

  // The command resolves only after its dialog is closed
  const scanned = page.evaluate(() =>
    (window as any).jupyterapp.commands.execute('nb_venv_kernels:scan')
  );

  const dialog = page.locator('.jp-Dialog');
  await expect(dialog.getByText('Environment Scan Results')).toBeVisible({
    timeout: 30000
  });

  await dialog.locator('.jp-mod-accept').click();
  await scanned;
});

test('should register refresh command', async ({ page }) => {
  await page.goto();

  const hasCommand = await page.evaluate(() =>
    (window as any).jupyterapp.commands.hasCommand('nb_venv_kernels:refresh')
  );

  expect(hasCommand).toBe(true);
});
