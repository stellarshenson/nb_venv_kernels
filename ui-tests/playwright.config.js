/**
 * Configuration for Playwright using default from @jupyterlab/galata
 */
const path = require('path');
const baseConfig = require('@jupyterlab/galata/lib/playwright-config');

const PORT = process.env.JUPYTER_TEST_PORT || '8888';
const BASE_URL = `http://localhost:${PORT}`;

// The scan command writes the environment registries under HOME, so the test
// server gets a scratch HOME and workspace, recreated on every start.
const SCRATCH = path.join(__dirname, '.tmp');
const HOME = path.join(SCRATCH, 'home');
const ROOT = path.join(HOME, 'workspace');
const SWEEP = `node -e "const fs=require('fs');fs.rmSync('.tmp',{recursive:true,force:true});fs.mkdirSync('.tmp/home/workspace',{recursive:true})"`;

module.exports = {
  ...baseConfig,
  use: { ...baseConfig.use, baseURL: BASE_URL },
  webServer: {
    command: `${SWEEP} && jlpm start`,
    url: `${BASE_URL}/lab`,
    timeout: 120 * 1000,
    reuseExistingServer: false,
    env: {
      HOME,
      JUPYTER_DATA_DIR: path.join(HOME, '.local/share/jupyter'),
      JUPYTER_CONFIG_DIR: path.join(HOME, '.jupyter'),
      JUPYTER_SERVER_ROOT: ROOT,
      JUPYTERLAB_GALATA_ROOT_DIR: ROOT
    }
  }
};
