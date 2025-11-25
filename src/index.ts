import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

/**
 * Initialization data for the nb_venv_kernels extension.
 *
 * This extension provides VEnvKernelSpecManager which discovers kernels
 * from conda, venv, and uv environments. No frontend functionality needed -
 * the kernel discovery happens server-side via KernelSpecManager.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'nb_venv_kernels:plugin',
  description: 'Discovers Jupyter kernels from conda, venv, and uv environments',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    console.log('nb_venv_kernels: VEnvKernelSpecManager active');
  }
};

export default plugin;
