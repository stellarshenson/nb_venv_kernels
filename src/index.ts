import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { IMainMenu } from '@jupyterlab/mainmenu';
import { Dialog, showDialog } from '@jupyterlab/apputils';
import { URLExt } from '@jupyterlab/coreutils';
import { ServerConnection } from '@jupyterlab/services';
import { Widget } from '@lumino/widgets';

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
    keep: number;
    remove: number;
  };
  dry_run: boolean;
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
 * Build HTML content for scan results
 */
function buildResultsContent(result: IScanResult): string {
  // Build intro message
  const total = result.environments.length;
  const existing = result.environments.filter(e => e.exists).length;
  const missing = result.summary.remove;

  let intro: string;
  if (total === 0) {
    intro = '<p>No Python environments were found in the workspace.</p>';
  } else if (missing > 0) {
    intro = `<p>Found ${existing} environment${existing !== 1 ? 's' : ''}, ${missing} missing will be removed.</p>`;
  } else {
    intro = `<p>Found ${total} Python environment${total !== 1 ? 's' : ''}.</p>`;
  }

  if (result.environments.length === 0) {
    return intro;
  }

  const rows = result.environments
    .map(env => {
      let actionStyle = '';
      if (env.action === 'add') {
        actionStyle = 'color: #22c55e; font-weight: 500;';
      } else if (env.action === 'keep') {
        actionStyle = 'color: #3b82f6;';
      } else if (env.action === 'remove') {
        actionStyle = 'color: #f97316;';
      }

      const existsText = env.exists ? 'yes' : '<span style="color: #ef4444;">no</span>';
      const kernelText = env.has_kernel ? 'yes' : '<span style="color: #ef4444;">no</span>';

      return `<tr>
      <td style="${actionStyle} padding: 4px 8px;">${env.action}</td>
      <td style="padding: 4px 8px;">${env.name}</td>
      <td style="padding: 4px 8px;">${env.type}</td>
      <td style="padding: 4px 8px;">${existsText}</td>
      <td style="padding: 4px 8px;">${kernelText}</td>
      <td style="padding: 4px 8px; font-family: var(--jp-code-font-family); font-size: 0.9em;">${env.path}</td>
    </tr>`;
    })
    .join('');

  const summaryParts = [];
  if (result.summary.add > 0) {
    summaryParts.push(`${result.summary.add} added`);
  }
  if (result.summary.keep > 0) {
    summaryParts.push(`${result.summary.keep} kept`);
  }
  if (result.summary.remove > 0) {
    summaryParts.push(`${result.summary.remove} removed`);
  }

  // Check if any environments are missing a kernel
  const missingKernel = result.environments.some(e => e.exists && !e.has_kernel);
  const kernelNote = missingKernel
    ? '<p style="margin-top: 8px; font-size: 0.9em; color: var(--jp-ui-font-color2);"><em>Install ipykernel in environments without kernel to use them in JupyterLab.</em></p>'
    : '';

  return `
    ${intro}
    <table style="border-collapse: collapse; width: 100%; margin-top: 8px;">
      <thead>
        <tr style="border-bottom: 1px solid var(--jp-border-color1);">
          <th style="text-align: left; padding: 4px 8px;">Action</th>
          <th style="text-align: left; padding: 4px 8px;">Name</th>
          <th style="text-align: left; padding: 4px 8px;">Type</th>
          <th style="text-align: left; padding: 4px 8px;">Exists</th>
          <th style="text-align: left; padding: 4px 8px;">Kernel</th>
          <th style="text-align: left; padding: 4px 8px;">Path</th>
        </tr>
      </thead>
      <tbody>
        ${rows}
      </tbody>
    </table>
    <p style="margin-top: 12px; color: var(--jp-ui-font-color2);"><strong>Summary:</strong> ${summaryParts.join(', ')}</p>
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
 * Initialization data for the nb_venv_kernels extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'nb_venv_kernels:plugin',
  description: 'Discovers Jupyter kernels from conda, venv, and uv environments',
  autoStart: true,
  optional: [IMainMenu],
  activate: (app: JupyterFrontEnd, mainMenu: IMainMenu | null) => {
    console.log('nb_venv_kernels: VEnvKernelSpecManager active');

    // Add command to scan environments
    const commandId = 'nb_venv_kernels:scan';
    app.commands.addCommand(commandId, {
      label: 'Scan for Python Environments',
      caption: 'Scan workspace for venv/uv/conda environments',
      execute: async () => {
        // Show loading spinner
        const loadingDialog = showLoadingDialog();

        try {
          const result = await scanEnvironments();
          loadingDialog.dispose();
          await showScanResults(result);
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
    });

    // Add to Kernel menu if available
    if (mainMenu) {
      mainMenu.kernelMenu.addGroup([{ command: commandId }], 100);
    }
  }
};

export default plugin;
