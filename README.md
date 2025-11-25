# nb_uv_kernels

Jupyter server extension that discovers kernels from uv and venv Python environments. The equivalent of nb_conda_kernelss for non-conda workflows.

## Install

```bash
pip install nb_uv_kernels
```

## Usage

Register your environments after installing ipykernel in them:

```bash
nb_uv_kernels register /path/to/.venv
```

Registered environments appear automatically in JupyterLab's kernel selector. Manage registrations with:

```bash
nb_uv_kernels list                        # Show all registered environments
nb_uv_kernels unregister /path/to/.venv   # Remove from registry
```

## Implementation Details

The extension replaces Jupyter's default `KernelSpecManager` with `UvKernelSpecManager`. When JupyterLab requests available kernels, the manager reads `~/.uv/environments.txt` and scans each registered path for kernelspecs at `{path}/share/jupyter/kernels/*/kernel.json`. Results are cached for 60 seconds.

When a kernel is launched, the original argv from the kernelspec is wrapped with a runner script that activates the target environment before executing the kernel command. This ensures the kernel process runs with the correct Python interpreter and dependencies.

The registry file is a plain text list of absolute paths - one environment per line. This mirrors how conda tracks prefix environments in `~/.conda/environments.txt`.

## Configuration

Optional settings in `jupyter_server_config.py`:

```python
c.UvKernelSpecManager.uv_only = True                    # Hide system kernels
c.UvKernelSpecManager.env_filter = r"\.tox|\.nox"       # Exclude by pattern
c.UvKernelSpecManager.name_format = "{language} ({environment})"
```

## Uninstall

```bash
pip uninstall nb_uv_kernels
```
