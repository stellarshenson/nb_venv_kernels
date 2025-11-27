# Release Notes

## Release 1.1.42

**Workspace Boundary Validation**
- Registration now validates path is within server workspace
- Prevents registering arbitrary system paths via CLI or API
- Global conda installations exempt (anaconda, miniconda, miniforge, mambaforge)
- Environments listed in `conda env list` also exempt

**Security Improvements**
- Only actual system conda installations bypass workspace check
- Random directories with `conda-meta` (e.g., in /tmp) no longer exempt
- Added `is_global_conda_environment()` function for proper validation

**Cache Coherence**
- API routes use server's kernel spec manager singleton
- Scan/register/unregister operations invalidate server cache immediately
- New kernels appear in kernel picker without page refresh

**JupyterLab Command Palette**
- Scan command accessible via Ctrl+Shift+C -> "Scan for Python Environments"
- Command registered under "Kernel" category
- UI tests for command registration and palette integration

**CI/CD**
- Fixed CI test to create venv in workspace instead of /tmp

## Release 1.1.18

**CI/CD and Testing**
- Added browser check step to GitHub Actions workflow
- Added Playwright integration tests for UI components
- Comprehensive tier 2 test suite: kernel discovery (venv, uv, conda), registry operations, Python API
- Fixed route tests for actual API endpoints
- Fixed HTTPClientError handling in tests
- Fixed cache invalidation in test suite

**Bug Fixes**
- Fixed `list_environments()` to show non-existent entries with `exists=False`
- Fixed `scan_directory()` return keys for consistency
- Fixed module-level imports for json/subprocess in registry

**Documentation**
- Added integration tests documentation (doc/INTEGRATION_TESTS.md)
- Added screenshots: CLI list command, Kernel menu, scan results modal
- Added PayPal donation badge

**UI Polish**
- Harmonized "no" indicator across CLI and modal (lowercase, red color)
- Modal headers and summary format aligned with CLI output
