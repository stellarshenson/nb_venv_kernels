import { expect, test } from '@jupyterlab/galata';

/**
 * Don't load JupyterLab webpage before running the tests.
 * This is required to ensure we capture all log messages.
 */
test.use({ autoGoto: false });

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

test('should register scan command', async ({ page }) => {
  await page.goto();

  // Check that the scan command is registered
  const hasCommand = await page.evaluate(() => {
    const app = (window as any).jupyterapp;
    return app?.commands?.hasCommand('nb_venv_kernels:scan') ?? false;
  });

  expect(hasCommand).toBe(true);
});
