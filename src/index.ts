import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { requestAPI } from './request';

/**
 * Initialization data for the nb_uv_kernels extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'nb_uv_kernels:plugin',
  description: 'Jupyterlab extension to detect notebook kernels similarly to how nb_conda_kernel does',
  autoStart: true,
  activate: (app: JupyterFrontEnd) => {
    console.log('JupyterLab extension nb_uv_kernels is activated!');

    requestAPI<any>('hello')
      .then(data => {
        console.log(data);
      })
      .catch(reason => {
        console.error(
          `The nb_uv_kernels server extension appears to be missing.\n${reason}`
        );
      });
  }
};

export default plugin;
