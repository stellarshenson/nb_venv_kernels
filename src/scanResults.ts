/**
 * Scan results dialog content - pure rendering, no JupyterLab dependencies.
 */

export interface IScanEnvironment {
  action: string;
  name: string;
  type: string;
  exists: boolean;
  has_kernel: boolean;
  path: string;
}

export interface IScanResult {
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

const HTML_ESCAPES: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
};

/**
 * Escape text for insertion into HTML. Environment names and paths come from
 * folder names on disk, so they must never be parsed as markup.
 */
export function escapeHtml(text: string): string {
  return String(text).replace(/[&<>"']/g, c => HTML_ESCAPES[c]);
}

/**
 * Sort environments to match CLI order: action -> type -> name
 */
export function sortEnvironments(
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
export function buildResultsContent(result: IScanResult): string {
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
      const action = escapeHtml(env.action);

      return `<tr>
      <td class="nb-venv-action-${action}">${action}</td>
      <td>${escapeHtml(env.name)}</td>
      <td>${escapeHtml(env.type)}</td>
      <td>${existsText}</td>
      <td>${kernelText}</td>
      <td class="path-col">${escapeHtml(env.path)}</td>
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
