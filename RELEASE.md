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
