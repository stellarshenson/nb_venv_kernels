# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

## 1.2.9

### Configurable Scan Exclusions

- Added `scan_config.json` for configurable directory and path exclusions
- Scan now excludes uv cache directories (`@cache`, `archive-v0`, `environments-v*`)
- Cleanup removes cache paths from registry automatically
- Exclude patterns loaded from `nb_venv_kernels/scan_config.json`

## 1.2.8

### Consistent Sort Order

- Fixed inconsistent sort order between `list` and `scan` commands
- Both now use manager's conflict-resolved name for sorting

## 1.2.7

### Scan Shows Update for Sanitized Names

- Scan now shows "update" action when duplicate names are sanitized in registry
- Added `sanitize_registry_names()` function to registry API
- Added tests for sanitization update visibility in scan results

## 1.2.6

### Registry Sanitization

- Registry now auto-fixes duplicate custom names in-place when reading
- Duplicate names detected from manual edits or older versions get `_1`, `_2` suffixes
- Registry is the single source of truth for unique names

### Thread/Multiprocess Safety

- All registry operations now use file locking via `filelock` package
- Cross-platform support (Linux, macOS, Windows)
- Single global lock at `~/.venv/registry.lock` prevents race conditions
- Added `filelock` as package dependency

### CLI Improvements

- `scan` command now defaults to workspace root when `--path` not specified
- Path must be provided with `--path` flag (no longer positional argument)
- CLI list command now uses manager's conflict-resolved names

## 1.2.4

### Kernel Display Names

- Kernel display names in JupyterLab now use custom names from registry
- Previously kernels showed path-derived names even when custom name was registered
- Added `read_environments_with_names()` function to registry API
- Added test for kernel display names with custom names

## 1.2.2

### Name Conflict Resolution

- Duplicate environment names now get `_1`, `_2`, `_3` suffixes automatically
- Applies to both `list` and `scan` commands
- Name changes from conflict resolution show as "update" action in scan output

### Update Action Fix

- "update" action now only shows when an actual change was made
- Previously showed "update" for any environment with custom name
- Now correctly shows "keep" for unchanged environments with custom names

### Bug Fixes

- Fixed `unregister_environment` failing to remove entries with custom names
- Registry entries with tab-separated custom names are now properly parsed during unregister

### Testing

- Added comprehensive test suite for name conflict resolution
- Tests cover: no duplicates, duplicates, mixed, action updates, field preservation
- Added test for unregistering environments with custom names

## 1.1.45

### Custom Environment Names

- Added `-n/--name` option to `register` command for custom display names
- Registry format extended with tab-separated names (backward compatible)
- Custom names used in kernel selector display (venv/uv only, ignored for conda)

### UI Improvements

- Increased name column width from 25 to 30 characters
- Changed remove action color to darker orange for better visibility

### Frontend Kernel Refresh

- JupyterLab extension now calls `refreshSpecs()` after scan completes
- New kernels appear immediately in kernel picker without page refresh

## 1.1.42

### Workspace Boundary Validation

- Registration now validates path is within server workspace
- Prevents registering arbitrary system paths
- Global conda installations exempt (anaconda, miniconda, miniforge, etc.)
- Environments listed in `conda env list` also exempt

### Security

- Only actual system conda installations bypass workspace check
- Random directories with `conda-meta` in /tmp no longer exempt
- Added `is_global_conda_environment()` function for proper validation

### CI/CD

- Fixed CI test to create venv in workspace instead of /tmp

## 1.1.35

### Cache Coherence

- API routes now use server's kernel spec manager singleton when available
- Scan/register/unregister operations invalidate server cache immediately
- New kernels appear in kernel picker without page refresh

## 1.1.33

### JupyterLab Command Palette

- Added scan command to JupyterLab command palette under "Kernel" category
- Refactored menu command to use proper command registration pattern
- Command accessible via Ctrl+Shift+C -> "Scan for Python Environments"

### Testing

- Added UI tests for scan command registration and command palette integration
- Tests verify command is registered in app.commands
- Tests verify command appears in command palette search results

## 1.1.20

### CLI/API Harmonization

- Consistent sorting across CLI and JupyterLab modal: action (add/keep/remove), then type (conda/uv/venv), then name
- Added `sortEnvironments()` function in frontend to match CLI sort order

### Documentation

- Added "Scan Output Ordering" section to NB_VENV_KERNELS_MECHANICS.md
- Added API architecture diagram to README

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
  - Skips common non-environment directories (node_modules, **pycache**, .git, etc.)

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
