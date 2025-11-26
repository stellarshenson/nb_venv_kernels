# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

## 1.1.20

### CLI/API Harmonization

- Unified sorting across CLI and JupyterLab modal: action (add/keep/remove), then type (conda/uv/venv), then name alphabetically
- Added `sortEnvironments()` function in frontend to match CLI sort order
- Both interfaces now display identical scan results ordering

### Documentation

- Added "Scan Output Ordering" section to NB_VENV_KERNELS_MECHANICS.md
- Documented three-tier sort criteria with priority table

## 1.1.18

### CI/CD and Testing

- Added browser check step to GitHub Actions workflow
- Added Playwright integration tests for UI components
- Comprehensive tier 2 test suite: kernel discovery (venv, uv, conda), registry operations, Python API
- Fixed route tests for actual API endpoints
- Fixed HTTPClientError handling in tests
- Fixed cache invalidation in test suite

### Bug Fixes

- Fixed `list_environments()` to show non-existent entries with `exists=False`
- Fixed `scan_directory()` return keys for consistency
- Fixed module-level imports for json/subprocess in registry

### Documentation

- Added integration tests documentation (doc/INTEGRATION_TESTS.md)
- Added screenshots: CLI list command, Kernel menu, scan results modal
- Added PayPal donation badge

### UI Polish

- Harmonized "no" indicator across CLI and modal (lowercase, red color)
- Modal headers and summary format aligned with CLI output

## 1.1.0

### New Features

- **Scan command**: `nb_venv_kernels scan` finds venv/uv environments in directory trees
  - Animated spinner during scanning
  - Configurable depth via `--depth` or `c.VEnvKernelSpecManager.scan_depth` (default: 7)
  - Automatically cleans up non-existent environments from registries
  - Skips common non-environment directories (node_modules, __pycache__, .git, etc.)

- **Enhanced list command**: Shows all environment types (conda, uv, venv)
  - Columns: NAME, TYPE, EXISTS, KERNEL, PATH
  - TYPE shows `conda (global)`, `conda (local)`, `uv`, `venv`
  - Sorted by type (conda global first) then by name
  - Names derived from project directories

- **Registry cleanup**: Both `scan` and `register` commands remove non-existent environments

### Configuration

- Added `c.VEnvKernelSpecManager.scan_depth = 7` setting for default scan depth

### Documentation

- Updated mermaid diagram to show CLI scan/register populating registries
- Added "Listing Environments" section to README with example output

## 1.0.8

- Separate registries: `~/.venv/environments.txt` for venv, `~/.uv/environments.txt` for uv
- Auto-detect uv environments via `pyvenv.cfg` on register
- Kernel ordering: current environment first, then conda, uv, venv, system (alphabetical within groups)
- Add standard badges to README (GitHub Actions, npm, PyPI, downloads, JupyterLab 4)
- Add Features section to README
- Add link to nb_conda_kernels in README
- Improve README description

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
