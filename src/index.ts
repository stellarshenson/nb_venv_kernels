import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { Dialog, showDialog } from '@jupyterlab/apputils';
import { URLExt } from '@jupyterlab/coreutils';
import { ServerConnection, KernelSpec } from '@jupyterlab/services';
import { Widget } from '@lumino/widgets';

import { IScanResult, buildResultsContent } from './scanResults';

/**
 * Module-level reference to kernel spec manager for refreshing after scan
 */
let kernelSpecManager: KernelSpec.IManager | null = null;

/**
 * Call the scan API endpoint
 */
async function scanEnvironments(): Promise<IScanResult> {
  const settings = ServerConnection.makeSettings();
  const requestUrl = URLExt.join(settings.baseUrl, 'nb-venv-kernels', 'scan');

  const response = await ServerConnection.makeRequest(
    requestUrl,
    {
      method: 'POST',
      body: JSON.stringify({})
    },
    settings
  );

  if (!response.ok) {
    throw new Error(`Scan failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Show loading dialog with spinner
 */
function showLoadingDialog(): Dialog<unknown> {
  const content = document.createElement('div');
  content.style.display = 'flex';
  content.style.alignItems = 'center';
  content.style.gap = '12px';
  content.style.padding = '8px 0';
  content.innerHTML = `
    <div style="
      width: 24px;
      height: 24px;
      border: 3px solid var(--jp-border-color2);
      border-top-color: var(--jp-brand-color1);
      border-radius: 50%;
      animation: nb-venv-spin 1s linear infinite;
    "></div>
    <span>Scanning for Python environments...</span>
    <style>
      @keyframes nb-venv-spin {
        to { transform: rotate(360deg); }
      }
    </style>
  `;

  const body = new Widget({ node: content });

  const dialog = new Dialog({
    title: 'Scanning',
    body,
    buttons: []
  });

  dialog.launch();
  return dialog;
}

/**
 * Show scan results in a dialog
 */
async function showScanResults(result: IScanResult): Promise<void> {
  const content = document.createElement('div');
  content.style.minWidth = '500px';
  content.style.maxHeight = '400px';
  content.style.overflow = 'auto';
  content.innerHTML = buildResultsContent(result);

  const body = new Widget({ node: content });

  await showDialog({
    title: 'Environment Scan Results',
    body,
    buttons: [Dialog.okButton()]
  });
}

/**
 * Command ID for scanning environments
 */
const SCAN_COMMAND = 'nb_venv_kernels:scan';

/**
 * Command ID for refreshing kernel specs
 */
const REFRESH_COMMAND = 'nb_venv_kernels:refresh';

/**
 * Invalidate server-side kernel spec cache
 */
async function invalidateServerCache(): Promise<void> {
  const settings = ServerConnection.makeSettings();
  const requestUrl = URLExt.join(
    settings.baseUrl,
    'nb-venv-kernels',
    'refresh'
  );

  try {
    await ServerConnection.makeRequest(
      requestUrl,
      { method: 'POST' },
      settings
    );
  } catch (error) {
    console.warn('Failed to invalidate server cache:', error);
  }
}

/**
 * Execute the refresh command - refreshes kernel specs immediately
 */
async function executeRefreshCommand(): Promise<void> {
  // First invalidate server cache so it rebuilds from registries
  await invalidateServerCache();

  // Then refresh frontend kernel specs
  if (kernelSpecManager) {
    await kernelSpecManager.refreshSpecs();
    console.log('Kernel specs refreshed');
  }
}

/**
 * Execute the scan command - scans workspace for Python environments
 */
async function executeScanCommand(): Promise<void> {
  const loadingDialog = showLoadingDialog();

  try {
    const result = await scanEnvironments();
    loadingDialog.dispose();
    await showScanResults(result);

    // Invalidate backend cache and refresh kernel specs
    await invalidateServerCache();
    if (kernelSpecManager) {
      await kernelSpecManager.refreshSpecs();
    }
  } catch (error) {
    loadingDialog.dispose();
    console.error('Scan failed:', error);
    await showDialog({
      title: 'Scan Failed',
      body: `Failed to scan environments: ${error}`,
      buttons: [Dialog.okButton()]
    });
  }
}

/**
 * Initialization data for the nb_venv_kernels extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'nb_venv_kernels:plugin',
  description:
    'Discovers Jupyter kernels from conda, venv, and uv environments',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    console.log('JupyterLab extension nb_venv_kernels is activated!');

    // Capture kernel spec manager for refreshing after scan
    kernelSpecManager = app.serviceManager.kernelspecs;

    // Register the scan command. Its execute renders the scan results modal.
    // It is triggered by the app-launcher applet and the companion
    // jupyterlab_nb_venv_kernels_ui_extension. This extension deliberately adds
    // no Kernel-menu or Command-Palette entry of its own - those menu items and
    // launcher cards belong to the companion and the applet.
    app.commands.addCommand(SCAN_COMMAND, {
      label: 'Scan for Virtual Environments',
      caption: 'Scan workspace for venv/uv/conda environments',
      execute: executeScanCommand
    });

    // Register the refresh command, invoked programmatically by the companion
    // UI extension after registry changes. Also headless - no menu/palette.
    app.commands.addCommand(REFRESH_COMMAND, {
      label: 'Refresh Kernel List',
      caption: 'Refresh available kernels (use after CLI changes)',
      execute: executeRefreshCommand
    });
  }
};

export default plugin;
