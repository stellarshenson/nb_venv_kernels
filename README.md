# nb_venv_kernels

Composite Jupyter kernel spec manager that discovers kernels from conda, venv and uv Python environments. Combines functionality of nb_conda_kernels with venv/uv environment discovery.

![UV and Conda virtual environments co-exist and are properly discovered](.resources/screenshot.png)

## Install

```bash
pip install nb_venv_kernels
```

The extension installs itself as the default kernel spec manager via `jupyter_config.json`. If nb_conda_kernels is installed, nb_venv_kernels takes precedence and includes all conda kernel discovery functionality.

## Usage

Register environments after installing ipykernel:

```bash
nb_venv_kernels register /path/to/.venv
nb_venv_kernels list
nb_venv_kernels unregister /path/to/.venv
```

Manage Jupyter configuration:

```bash
nb_venv_kernels config enable     # Enable VEnvKernelSpecManager
nb_venv_kernels config disable    # Disable VEnvKernelSpecManager
nb_venv_kernels config show       # Show current config status
```

Registered environments with ipykernel appear in JupyterLab's kernel selector.

## How It Works

- **venv environments**: Registry at `~/.venv/environments.txt`
- **uv environments**: Registry at `~/.uv/environments.txt`, auto-detected via `pyvenv.cfg`
- **conda environments**: Discovers via `CondaKernelSpecManager` if nb_conda_kernels is installed
- Scans `{path}/share/jupyter/kernels/*/kernel.json` for each registered environment
- Configures kernel to use venv's python directly with `VIRTUAL_ENV` and `PATH` environment variables
- Caches results for 60 seconds
- `config enable` backs up existing config, `config disable` restores from backup

## Configuration

Optional settings in `jupyter_server_config.py`:

```python
c.VEnvKernelSpecManager.venv_only = True                      # Hide system/conda kernels
c.VEnvKernelSpecManager.env_filter = r"\.tox|\.nox"           # Exclude by pattern
c.VEnvKernelSpecManager.name_format = "{language} [{source} env:{environment}]"  # Default format
```

**Display name variables**: `{language}`, `{environment}`, `{source}` (uv/venv), `{kernel}`, `{display_name}`

## Uninstall

```bash
pip uninstall nb_venv_kernels
```

After uninstall, nb_conda_kernels (if installed) will resume handling kernel discovery.
