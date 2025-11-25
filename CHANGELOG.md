# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

## 1.0.4

- Add screenshot to README showing kernel selector with UV and conda environments
- Fix package.json URLs (homepage, bugs, repository) for npm publishing
- Fix jupyter-releaser check-npm validation

## 1.0.3

- Install jupyter_config.json directly to override nb_conda_kernels settings
- Add notebook-config.d for NotebookApp nbserver_extensions
- Add server-config.d for ServerApp jpserver_extensions
- Extension auto-enables as default kernel spec manager on pip install

## 1.0.2

- Remove server extension API dependency from labextension
- Simplify frontend to log activation only (no API calls)
- Delete unused request.ts

## 1.0.1

- Add auto-configuration via jupyter_server_config.d
- Update README install instructions

## 1.0.0

- Initial stable release
- VEnvKernelSpecManager discovers kernels from conda, venv, and uv environments
- Composition-based integration with CondaKernelSpecManager
- Direct venv python execution with VIRTUAL_ENV and PATH environment variables
- Config backup/restore functionality in CLI
- Registry at ~/.venv/environments.txt
- Display name format: `{language} [{source} env:{environment}]`

<!-- <END NEW CHANGELOG ENTRY> -->

## 0.9.x - Development

### Core Implementation

- Implement VEnvKernelSpecManager (originally UvKernelSpecManager)
- Create registry.py for environment registration at ~/.venv/environments.txt
- Create runner.py for venv activation (later replaced with direct python execution)
- Create manager.py with kernel discovery logic
- Create cli.py with register/unregister/list/config commands

### Kernel Discovery

- Scan `{path}/share/jupyter/kernels/*/kernel.json` for each registered environment
- Detect uv-created environments via pyvenv.cfg
- Cache kernel specs for 60 seconds
- Combine system + venv + conda kernels without duplicates

### Configuration

- Auto-detect Jupyter config location (JUPYTER_CONFIG_DIR, CONDA_PREFIX, standard paths)
- `config enable` - enable VEnvKernelSpecManager with backup
- `config disable` - restore from backup or remove settings
- `config show` - display current configuration status

### CI/CD

- Streamline GitHub workflows based on jupyterlab extension standards
- Consolidated build.yml with Python tests and CLI verification

### Bug Fixes

- Fix inheritance conflicts with CondaKernelSpecManager using composition
- Fix kernel invocation to use venv python directly instead of runner script
- Fix PATH handling to keep conda bin for pip/uv tools
- Clear CONDA_PREFIX to avoid activation confusion
- Remove duplicate system kernels when conda provides same resource
