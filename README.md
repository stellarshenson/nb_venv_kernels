# nb_venv_kernels

[![GitHub Actions](https://github.com/stellarshenson/nb_venv_kernels/actions/workflows/build.yml/badge.svg)](https://github.com/stellarshenson/nb_venv_kernels/actions/workflows/build.yml)
[![npm version](https://img.shields.io/npm/v/nb_venv_kernels.svg)](https://www.npmjs.com/package/nb_venv_kernels)
[![PyPI version](https://img.shields.io/pypi/v/nb_venv_kernels.svg)](https://pypi.org/project/nb_venv_kernels/)
[![Total PyPI downloads](https://static.pepy.tech/badge/nb_venv_kernels)](https://pepy.tech/project/nb_venv_kernels)
[![JupyterLab 4](https://img.shields.io/badge/JupyterLab-4-orange.svg)](https://jupyterlab.readthedocs.io/en/stable/)
[![Brought To You By KOLOMOLO](https://img.shields.io/badge/Brought%20To%20You%20By-KOLOMOLO-00ffff?style=flat)](https://kolomolo.com)

Use Python virtual environments as Jupyter kernels. Discovers and registers kernels from venv, uv, and conda environments in JupyterLab's kernel selector.

![UV and Conda virtual environments co-exist and are properly discovered](.resources/screenshot.png)

## Features

- **Unified kernel discovery** - conda, venv, and uv environments in one kernel selector
- **Auto-detection** - distinguishes uv from venv via `pyvenv.cfg`
- **Smart ordering** - current environment first, then conda, uv, venv, system
- **Drop-in replacement** - replaces nb_conda_kernels while preserving all conda functionality
- **CLI management** - register, unregister, and list environments
- **Zero config** - auto-enables on install, works immediately

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

## Environment Registries

Environments are registered in separate files based on their source:

- **venv**: `~/.venv/environments.txt`
- **uv**: `~/.uv/environments.txt`
- **conda**: `~/.conda/environments.txt` + global environments from `conda env list`

The `register` command auto-detects uv environments via `pyvenv.cfg` and writes to the appropriate registry.

## How It Works

- Scans `{path}/share/jupyter/kernels/*/kernel.json` for each registered environment
- Configures kernel to use venv's python directly with `VIRTUAL_ENV` and `PATH` environment variables
- Kernel order: current environment first, then conda, uv, venv, system
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
