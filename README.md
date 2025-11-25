# nb_venv_kernels

Composite Jupyter kernel spec manager that discovers kernels from conda, venv and uv Python environments. Combines functionality of nb_conda_kernels with venv/uv environment discovery.

## Install

```bash
pip install nb_venv_kernels
nb_venv_kernels config enable
```

The `config enable` command updates Jupyter configuration to use `VEnvKernelSpecManager`. This is required when nb_conda_kernels is installed, otherwise its manager takes precedence.

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

- Reads venv registry from `~/.venv/environments.txt`
- Scans `{path}/share/jupyter/kernels/*/kernel.json` for each registered environment
- Wraps kernel argv with runner script that activates the venv before launch
- Caches results for 60 seconds
- Combines with `CondaKernelSpecManager` if available for unified conda + venv discovery

## Configuration

Optional settings in `jupyter_server_config.py`:

```python
c.VEnvKernelSpecManager.venv_only = True                      # Hide system/conda kernels
c.VEnvKernelSpecManager.env_filter = r"\.tox|\.nox"           # Exclude by pattern
c.VEnvKernelSpecManager.name_format = "{language} [{source}: {environment}]"  # Default format
```

**Display name variables**: `{language}`, `{environment}`, `{source}` (uv/venv), `{kernel}`, `{display_name}`

## Uninstall

```bash
nb_venv_kernels config disable
pip uninstall nb_venv_kernels
```
