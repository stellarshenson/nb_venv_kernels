# nb_venv_kernels

Jupyter server extension that discovers kernels from uv and venv Python environments. Works standalone or alongside nb_conda_kernels for combined conda + venv kernel discovery.

## Install

```bash
pip install nb_venv_kernels
nb_venv_kernels config enable
```

The `config enable` command updates Jupyter configuration to use `UvKernelSpecManager`. This is required when nb_conda_kernels is installed, otherwise its manager takes precedence.

## Usage

Register environments after installing ipykernel:

```bash
nb_venv_kernels register /path/to/.venv
nb_venv_kernels list
nb_venv_kernels unregister /path/to/.venv
```

Manage Jupyter configuration:

```bash
nb_venv_kernels config enable     # Enable UvKernelSpecManager
nb_venv_kernels config disable    # Disable UvKernelSpecManager
nb_venv_kernels config show       # Show current config status
```

Registered environments with ipykernel appear in JupyterLab's kernel selector.

## How It Works

- Reads registry from `~/.uv/environments.txt`
- Scans `{path}/share/jupyter/kernels/*/kernel.json` for each registered environment
- Wraps kernel argv with runner script that activates the venv before launch
- Caches results for 60 seconds
- Inherits from `CondaKernelSpecManager` if available, otherwise `KernelSpecManager`

## Configuration

Optional settings in `jupyter_server_config.py`:

```python
c.UvKernelSpecManager.uv_only = True                    # Hide system kernels
c.UvKernelSpecManager.env_filter = r"\.tox|\.nox"       # Exclude by pattern
c.UvKernelSpecManager.name_format = "{language} ({environment})"
```

## Uninstall

```bash
nb_venv_kernels config disable
pip uninstall nb_venv_kernels
```
