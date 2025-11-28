import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { IMainMenu } from '@jupyterlab/mainmenu';
import { ICommandPalette } from '@jupyterlab/apputils';
import { Dialog, showDialog } from '@jupyterlab/apputils';
import { URLExt } from '@jupyterlab/coreutils';
import { ServerConnection, KernelSpec } from '@jupyterlab/services';
import { Widget } from '@lumino/widgets';

/**
 * Module-level reference to kernel spec manager for refreshing after scan
 */
let kernelSpecManager: KernelSpec.IManager | null = null;

interface IScanEnvironment {
  action: string;
  name: string;
  type: string;
  exists: boolean;
  has_kernel: boolean;
  path: string;
}

interface IScanResult {
  environments: IScanEnvironment[];
  summary: {
    add: number;
    update: number;
    keep: number;
    remove: number;
  };
  dry_run: boolean;
  workspace_root: string;
}

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
 * Sort environments to match CLI order: action -> type -> name
 */
function sortEnvironments(
  environments: IScanEnvironment[]
): IScanEnvironment[] {
  const actionOrder: Record<string, number> = {
    add: 0,
    update: 1,
    keep: 2,
    remove: 3
  };
  const typeOrder: Record<string, number> = { conda: 0, uv: 1, venv: 2 };

  return [...environments].sort((a, b) => {
    // Sort by action first
    const actionDiff =
      (actionOrder[a.action] ?? 3) - (actionOrder[b.action] ?? 3);
    if (actionDiff !== 0) {
      return actionDiff;
    }

    // Then by type
    const typeDiff = (typeOrder[a.type] ?? 3) - (typeOrder[b.type] ?? 3);
    if (typeDiff !== 0) {
      return typeDiff;
    }

    // Then by name alphabetically
    return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
  });
}

/**
 * Build HTML content for scan results
 */
function buildResultsContent(result: IScanResult): string {
  // Build intro message
  const total = result.environments.length;
  const added = result.summary.add;
  const updated = result.summary.update || 0;
  const kept = result.summary.keep;
  const removed = result.summary.remove;

  let intro: string;
  if (total === 0) {
    intro = '<p>No environments found.</p>';
  } else {
    const parts = [];
    if (added > 0) {
      parts.push(`${added} new`);
    }
    if (updated > 0) {
      parts.push(`${updated} updated`);
    }
    if (kept > 0) {
      parts.push(`${kept} kept`);
    }
    if (removed > 0) {
      parts.push(`${removed} missing`);
    }
    intro = `<p>Found ${total} environment${total !== 1 ? 's' : ''}: ${parts.join(', ')}.</p>`;
  }

  if (result.environments.length === 0) {
    return intro;
  }

  // Sort environments to match CLI order
  const sortedEnvs = sortEnvironments(result.environments);

  const rows = sortedEnvs
    .map(env => {
      const existsText = env.exists
        ? 'yes'
        : '<span class="nb-venv-no">no</span>';
      const kernelText = env.has_kernel
        ? 'yes'
        : '<span class="nb-venv-no">no</span>';
      const actionClass = `nb-venv-action-${env.action}`;

      return `<tr>
      <td class="${actionClass}">${env.action}</td>
      <td>${env.name}</td>
      <td>${env.type}</td>
      <td>${existsText}</td>
      <td>${kernelText}</td>
      <td class="path-col">${env.path}</td>
    </tr>`;
    })
    .join('');

  const summaryParts = [];
  // Use past tense since scan has completed
  if (result.summary.add > 0) {
    summaryParts.push(`${result.summary.add} added`);
  }
  if (updated > 0) {
    summaryParts.push(`${updated} updated`);
  }
  if (result.summary.keep > 0) {
    summaryParts.push(`${result.summary.keep} kept`);
  }
  if (result.summary.remove > 0) {
    summaryParts.push(`${result.summary.remove} removed`);
  }

  // Check if any environments are missing a kernel
  const missingKernel = result.environments.some(
    e => e.exists && !e.has_kernel
  );
  const kernelNote = missingKernel
    ? '<p style="margin-top: 8px; font-size: 0.9em; color: var(--jp-ui-font-color2);"><em>Install ipykernel in environments without kernel to use them in JupyterLab.</em></p>'
    : '';

  return `
    <style>
      .nb-venv-table { border-collapse: collapse; width: 100%; margin-top: 8px; font-size: var(--jp-ui-font-size1); }
      .nb-venv-table th, .nb-venv-table td { text-align: left; padding: 1px 6px; white-space: nowrap; vertical-align: baseline; }
      .nb-venv-table thead tr { border-bottom: 1px solid var(--jp-border-color1); }
      .nb-venv-table tbody tr { line-height: 1.2; }
      .nb-venv-table .path-col { font-family: var(--jp-code-font-family); font-size: var(--jp-code-font-size); white-space: normal; }
      .nb-venv-action-add { color: #22c55e; font-weight: 500; }
      .nb-venv-action-update { color: #06b6d4; font-weight: 500; }
      .nb-venv-action-keep { color: #3b82f6; }
      .nb-venv-action-remove { color: #f97316; }
      .nb-venv-no { color: #ef4444; }
    </style>
    ${intro}
    <table class="nb-venv-table">
      <thead>
        <tr>
          <th>action</th>
          <th>name</th>
          <th>type</th>
          <th>exists</th>
          <th>kernel</th>
          <th>path (relative to workspace)</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
    <p style="margin-top: 8px; color: var(--jp-ui-font-color2);"><strong>Summary:</strong> ${summaryParts.join(', ')}</p>
    ${kernelNote}
  `;
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
 * Execute the scan command - scans workspace for Python environments
 */
async function executeScanCommand(): Promise<void> {
  const loadingDialog = showLoadingDialog();

  try {
    const result = await scanEnvironments();
    loadingDialog.dispose();
    await showScanResults(result);

    // Refresh kernel specs so new kernels appear immediately in kernel picker
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
  optional: [IMainMenu, ICommandPalette],
  activate: (
    app: JupyterFrontEnd,
    mainMenu: IMainMenu | null,
    palette: ICommandPalette | null
  ) => {
    console.log('JupyterLab extension nb_venv_kernels is activated!');

    // Capture kernel spec manager for refreshing after scan
    kernelSpecManager = app.serviceManager.kernelspecs;

    // Register scan command
    app.commands.addCommand(SCAN_COMMAND, {
      label: 'Scan for Python Environments',
      caption: 'Scan workspace for venv/uv/conda environments',
      execute: executeScanCommand
    });

    // Add to Kernel menu
    if (mainMenu) {
      mainMenu.kernelMenu.addGroup([{ command: SCAN_COMMAND }], 100);
    }

    // Add to command palette
    if (palette) {
      palette.addItem({
        command: SCAN_COMMAND,
        category: 'Kernel'
      });
    }
  }
};

export default plugin;
