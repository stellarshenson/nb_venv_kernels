/**
 * Unit tests for the scan results dialog content
 */

import { JupyterFrontEnd } from '@jupyterlab/application';
import { CommandRegistry } from '@lumino/commands';

import plugin from '../index';

// apputils pulls in ESM-only UI packages; activation touches none of it
jest.mock('@jupyterlab/apputils', () => ({
  Dialog: {},
  showDialog: jest.fn()
}));
import {
  IScanEnvironment,
  IScanResult,
  buildResultsContent,
  sortEnvironments
} from '../scanResults';

function env(overrides: Partial<IScanEnvironment>): IScanEnvironment {
  return {
    action: 'add',
    name: 'project',
    type: 'venv',
    exists: true,
    has_kernel: true,
    path: 'project/.venv',
    ...overrides
  };
}

function result(environments: IScanEnvironment[]): IScanResult {
  return {
    environments,
    summary: { add: environments.length, update: 0, keep: 0, remove: 0 },
    dry_run: false,
    workspace_root: '/workspace'
  };
}

describe('buildResultsContent', () => {
  it('shows an environment name holding markup as text', () => {
    const html = buildResultsContent(
      result([env({ name: '<img src=x onerror=alert(1)>' })])
    );
    const node = document.createElement('div');
    node.innerHTML = html;

    expect(node.querySelector('img')).toBeNull();
    expect(node.textContent).toContain('<img src=x onerror=alert(1)>');
  });

  it('shows a path, type and action holding markup as text', () => {
    const html = buildResultsContent(
      result([
        env({
          action: '"><b>a</b>',
          type: '<i>t</i>',
          path: 'x/<script>p</script>/.venv'
        })
      ])
    );
    const node = document.createElement('div');
    node.innerHTML = html;

    expect(node.querySelector('tbody b, tbody i, tbody script')).toBeNull();
    expect(node.textContent).toContain('x/<script>p</script>/.venv');
  });
});

describe('sortEnvironments', () => {
  it('orders rows by action, then type, then name', () => {
    const sorted = sortEnvironments([
      env({ action: 'keep', type: 'venv', name: 'b' }),
      env({ action: 'add', type: 'venv', name: 'z' }),
      env({ action: 'keep', type: 'conda', name: 'c' }),
      env({ action: 'add', type: 'uv', name: 'a' }),
      env({ action: 'keep', type: 'venv', name: 'A' })
    ]);

    expect(sorted.map(e => `${e.action}/${e.type}/${e.name}`)).toEqual([
      'add/uv/a',
      'add/venv/z',
      'keep/conda/c',
      'keep/venv/A',
      'keep/venv/b'
    ]);
  });
});

describe('plugin wiring', () => {
  it('adds no Kernel-menu item and no command palette entry of its own', () => {
    // The companion extension owns those entries; without the menu or palette
    // token the plugin has no handle to add either
    const tokens = [...(plugin.requires ?? []), ...(plugin.optional ?? [])];
    expect(tokens.filter(t => /mainmenu|commandpalette/i.test(t.name))).toEqual(
      []
    );
  });

  it('registers exactly the scan and refresh commands', () => {
    const commands = new CommandRegistry();
    const app = {
      commands,
      serviceManager: { kernelspecs: {} }
    } as unknown as JupyterFrontEnd;

    void plugin.activate(app);

    expect(commands.listCommands().sort()).toEqual([
      'nb_venv_kernels:refresh',
      'nb_venv_kernels:scan'
    ]);
  });
});
