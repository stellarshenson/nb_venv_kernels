# Integration Tests

@nb_venv_kernels version: 1.1.31<br>
@created on: 2025-11-27

This document describes the test suite for nb_venv_kernels, covering kernel discovery, environment registry operations, and API functionality.

## Test Structure

Tests are organized in tiers based on complexity and external dependencies:

| Tier | File             | Description             | Dependencies    |
| ---- | ---------------- | ----------------------- | --------------- |
| 1    | test_routes.py   | REST API endpoint tests | jupyter_server  |
| 2    | test_manager.py  | Kernel discovery tests  | venv, ipykernel |
| 2    | test_registry.py | Registry operations     | venv            |
| 2    | test_api.py      | Python API tests        | venv, ipykernel |
| UI   | ui-tests/        | Playwright integration  | JupyterLab      |

## Running Tests

```bash
# Run all Python tests
pytest -vv nb_venv_kernels/tests/

# Run with coverage
pytest -vv --cov nb_venv_kernels nb_venv_kernels/tests/

# Run specific test file
pytest -vv nb_venv_kernels/tests/test_manager.py

# Run specific test class
pytest -vv nb_venv_kernels/tests/test_manager.py::TestVenvKernelDiscovery

# Run UI tests
cd ui-tests && jlpm playwright test
```

## Test Files

### test_routes.py - REST API Tests

Tests for Jupyter server REST endpoints.

| Test                         | Endpoint          | Description                             |
| ---------------------------- | ----------------- | --------------------------------------- |
| test_list_environments       | GET /environments | Returns list of registered environments |
| test_scan_environments       | POST /scan        | Scans directory with dry_run flag       |
| test_register_missing_path   | POST /register    | Returns 400 when path missing           |
| test_unregister_missing_path | POST /unregister  | Returns 400 when path missing           |

### test_manager.py - Kernel Discovery Tests

Tests for VEnvKernelSpecManager kernel discovery functionality.

**TestVenvKernelDiscovery**

- `test_venv_creation_and_registration` - Creates venv, installs ipykernel, verifies kernel discovery
- `test_venv_with_standard_name` - Tests .venv naming convention uses parent directory name
- `test_venv_kernel_spec_structure` - Verifies kernelspec has correct argv, env, and VIRTUAL_ENV

**TestUvKernelDiscovery** (skips if uv unavailable)

- `test_uv_environment_detection` - Verifies uv environments detected via pyvenv.cfg
- `test_uv_kernel_discovery` - Creates uv venv, installs ipykernel, verifies discovery

**TestCondaKernelDiscovery** (skips if conda unavailable or timing issues)

- `test_conda_base_discovery` - Verifies base conda environment discovery
- `test_conda_env_creation_and_discovery` - Creates conda env with ipykernel, verifies discovery (skips if conda indexing delayed)

**TestMixedEnvironments**

- `test_multiple_environments` - Creates and discovers multiple venvs simultaneously
- `test_environment_without_ipykernel` - Verifies environments without ipykernel are not discovered

**TestKernelSpecDetails**

- `test_kernel_metadata` - Verifies venv_env_path, venv_source in metadata
- `test_kernel_display_name` - Verifies display name format

### test_registry.py - Registry Operations Tests

Tests for environment registration and registry management.

**TestEnvironmentRegistration**

- `test_register_venv` - Registers venv, verifies in registry
- `test_unregister_venv` - Unregisters venv, verifies removed
- `test_register_invalid_path` - Raises ValueError for nonexistent path
- `test_register_non_venv_directory` - Raises ValueError for non-venv directory
- `test_double_registration` - Second registration returns False
- `test_unregister_nonexistent` - Unregistering non-registered returns False

**TestUvDetection** (skips if uv unavailable)

- `test_uv_detection_positive` - uv environments correctly detected
- `test_uv_detection_negative` - Regular venvs not detected as uv
- `test_uv_registered_in_uv_registry` - uv environments go to ~/.uv/environments.txt

**TestListEnvironments**

- `test_list_environments_structure` - Verifies return structure (name, type, exists, has_kernel, path)
- `test_list_environments_exists_flag` - Tests exists flag for present/deleted environments
- `test_list_environments_has_kernel_flag` - Tests has_kernel flag before/after ipykernel install

**TestDirectoryScanning**

- `test_scan_finds_venvs` - Scan discovers venv in nested directory
- `test_scan_depth_limit` - Scan respects max_depth parameter
- `test_scan_registers_environments` - Scan without dry_run registers found environments
- `test_scan_dry_run` - dry_run does not modify registry

**TestRegistryPaths**

- `test_venv_registry_path` - Verifies ~/.venv/environments.txt path
- `test_uv_registry_path` - Verifies ~/.uv/environments.txt path

### test_api.py - Python API Tests

Tests for VEnvKernelSpecManager public API methods.

**TestListEnvironmentsAPI**

- `test_list_environments_returns_list` - Returns list type
- `test_list_environments_entry_structure` - Entries have required fields

**TestScanEnvironmentsAPI**

- `test_scan_environments_returns_dict` - Returns dict with environments, summary, dry_run
- `test_scan_environments_summary_structure` - Summary has add, keep, remove counts
- `test_scan_environments_finds_venvs` - Discovers venvs in scanned directory
- `test_scan_environments_dry_run` - dry_run does not register
- `test_scan_environments_registers` - Without dry_run registers environments

**TestRegisterEnvironmentAPI**

- `test_register_environment_success` - Returns path, registered=True, error=None
- `test_register_environment_invalid_path` - Returns registered=False, error message
- `test_register_environment_double_registration` - Second registration returns False

**TestUnregisterEnvironmentAPI**

- `test_unregister_environment_success` - Returns path, unregistered=True
- `test_unregister_nonexistent` - Returns unregistered=False

**TestKernelSpecMethods**

- `test_find_kernel_specs` - Returns dict of kernel names to paths
- `test_get_kernel_spec_valid` - Returns KernelSpec with argv, display_name, language
- `test_get_all_specs` - Returns dict with spec key for each kernel

**TestCacheInvalidation**

- `test_register_invalidates_cache` - New kernel appears after registration
- `test_unregister_invalidates_cache` - Kernel disappears after unregistration

## UI Tests

Located in `ui-tests/tests/nb_venv_kernel.spec.ts`.

| Test                                      | Description                                |
| ----------------------------------------- | ------------------------------------------ |
| should emit an activation console message | Verifies extension logs activation message |

## Test Fixtures

Common fixtures used across test files:

| Fixture         | Description                                             |
| --------------- | ------------------------------------------------------- |
| temp_dir        | Creates temporary directory, cleans up after test       |
| manager         | Fresh VEnvKernelSpecManager instance with cleared cache |
| jp_fetch        | Jupyter server fetch function (from jupyter_server)     |
| uv_available    | Skips test if uv not installed                          |
| conda_available | Skips test if conda not available or times out          |

Helper function `invalidate_cache(manager)` clears the manager's kernel cache after `register_environment()` calls to ensure newly registered environments are discovered by `find_kernel_specs()`.

## Environment Requirements

Tests create real virtual environments and require:

- Python 3.8+
- venv module (standard library)
- ipykernel (installed in created venvs)
- Optional: uv for uv-specific tests
- Optional: conda for conda-specific tests

## CI Integration

Tests run in GitHub Actions workflow (build.yml):

```yaml
- name: Run Python tests
  run: pytest -vv -r ap --cov nb_venv_kernels nb_venv_kernels/tests/
```

Conda and uv tests automatically skip if the tools are not available in the CI environment.
