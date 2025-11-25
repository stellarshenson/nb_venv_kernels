# -*- coding: utf-8 -*-
"""KernelSpecManager for venv/uv environments.

Combines system kernels, conda kernels (if nb_conda_kernels installed),
and venv/uv kernels from registered environments.
"""
import glob
import json
import os
import re
import time
from os.path import join, dirname, basename, abspath

from traitlets import Bool, Unicode
from jupyter_client.kernelspec import KernelSpecManager, KernelSpec, NoSuchKernel

# Try to import CondaKernelSpecManager for combined functionality
try:
    from nb_conda_kernels import CondaKernelSpecManager
    _HAS_CONDA = True
except ImportError:
    CondaKernelSpecManager = None
    _HAS_CONDA = False

from .registry import read_environments, is_uv_environment

CACHE_TIMEOUT = 60

RUNNER_COMMAND = ["python", "-m", "nb_venv_kernels.runner"]


class VEnvKernelSpecManager(KernelSpecManager):
    """A KernelSpecManager that discovers kernels from registered venv environments.

    Combines:
    - System kernels (from KernelSpecManager)
    - Conda kernels (from CondaKernelSpecManager if available)
    - Venv/uv kernels (from ~/.venv/environments.txt registry)
    """

    venv_only = Bool(
        False,
        config=True,
        help="Include only venv kernels, hide system and conda kernels."
    )

    env_filter = Unicode(
        None,
        config=True,
        allow_none=True,
        help="Regex pattern to exclude environments by path."
    )

    name_format = Unicode(
        "{language} [{source} env:{environment}]",
        config=True,
        help="Display name format. Available: {language}, {environment}, {kernel}, {display_name}, {source}"
    )

    def __init__(self, **kwargs):
        super(VEnvKernelSpecManager, self).__init__(**kwargs)

        self._venv_kernels_cache = None
        self._venv_kernels_cache_expiry = None

        # Create separate CondaKernelSpecManager instance for conda kernels
        self._conda_manager = None
        if _HAS_CONDA:
            self._conda_manager = CondaKernelSpecManager(**kwargs)

        if self.env_filter is not None:
            self._env_filter_regex = re.compile(self.env_filter)

        # Force initial scan
        _ = self._venv_kspecs

    @staticmethod
    def clean_kernel_name(kname):
        """Replace invalid characters in kernel name for Jupyter compatibility."""
        try:
            kname.encode("ascii")
        except UnicodeEncodeError:
            import unicodedata
            nfkd_form = unicodedata.normalize("NFKD", kname)
            kname = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        return re.sub(r"[^a-zA-Z0-9._\-]", "_", kname)

    def _all_envs(self):
        """Get all registered venv environments.

        Returns:
            Dict mapping environment names to paths.
        """
        all_envs = {}
        seen_names = {}

        for env_path in read_environments():
            # Apply filter if configured
            if self.env_filter and self._env_filter_regex.search(env_path):
                continue

            # Derive environment name from path
            # Use parent directory name if .venv, otherwise use directory name
            env_dir = basename(env_path)
            if env_dir == ".venv":
                env_name = basename(dirname(env_path))
            else:
                env_name = env_dir

            # Handle duplicates by appending counter
            if env_name in seen_names:
                seen_names[env_name] += 1
                env_name = f"{env_name}-{seen_names[env_name]}"
            else:
                seen_names[env_name] = 1

            all_envs[env_name] = env_path

        return all_envs

    def _all_venv_specs(self):
        """Find all kernel specs in registered venv environments.

        Returns:
            Dict mapping kernel names to kernel spec dicts.
        """
        all_specs = {}

        for env_name, env_path in self._all_envs().items():
            kspec_base = join(env_path, "share", "jupyter", "kernels")
            if not os.path.isdir(kspec_base):
                continue

            kspec_glob = glob.glob(join(kspec_base, "*", "kernel.json"))

            for spec_path in kspec_glob:
                try:
                    with open(spec_path, "rb") as fp:
                        data = fp.read()
                    spec = json.loads(data.decode("utf-8"))
                except Exception as err:
                    self.log.error(
                        "nb_venv_kernels | error loading %s:\n%s", spec_path, err
                    )
                    continue

                kernel_dir = dirname(spec_path)
                kernel_name = raw_kernel_name = basename(kernel_dir)

                # Normalize common kernel names
                if kernel_name in ("python2", "python3"):
                    kernel_name = "py"
                elif kernel_name == "ir":
                    kernel_name = "r"

                # Build unique kernel name
                kernel_name = f"venv-{env_name}-{kernel_name}"
                kernel_name = self.clean_kernel_name(kernel_name)

                # Detect environment source (uv vs venv)
                source = "uv" if is_uv_environment(env_path) else "venv"

                # Format display name
                display_prefix = spec["display_name"]
                if display_prefix.startswith("Python"):
                    display_prefix = "Python"

                display_name = self.name_format.format(
                    language=display_prefix,
                    environment=env_name,
                    kernel=raw_kernel_name,
                    display_name=spec["display_name"],
                    source=source,
                )

                # Mark if current environment
                is_current = env_path == os.sys.prefix
                if is_current:
                    display_name += " *"

                spec["display_name"] = display_name

                # Configure kernel to use venv's python directly with proper environment
                if not is_current:
                    # Replace python with venv's python path
                    venv_python = join(env_path, "bin", "python")
                    if os.path.exists(venv_python):
                        # Replace first argv element (python) with venv python
                        spec["argv"][0] = venv_python

                    # Set environment variables so !pip and subprocesses work
                    venv_bin = join(env_path, "bin")

                    # Build PATH: venv bin first, then rest of PATH
                    # Keep conda base bin for tools (pip, uv), skip only other conda env bins
                    path_parts = [venv_bin]
                    for p in os.environ.get("PATH", "").split(os.pathsep):
                        # Skip other conda environment paths (envs/*/bin)
                        if "/envs/" in p and "/bin" in p:
                            continue
                        if p and p not in path_parts:
                            path_parts.append(p)

                    spec["env"] = {
                        "VIRTUAL_ENV": env_path,
                        "PATH": os.pathsep.join(path_parts),
                        # Clear conda activation state but keep tools accessible
                        "CONDA_PREFIX": "",
                        "CONDA_DEFAULT_ENV": "",
                        "CONDA_PROMPT_MODIFIER": "",
                        "CONDA_SHLVL": "0",
                    }

                # Add metadata
                metadata = spec.get("metadata", {})
                metadata.update({
                    "venv_env_name": env_name,
                    "venv_env_path": env_path,
                    "venv_source": source,
                    "venv_language": display_prefix,
                    "venv_raw_kernel_name": raw_kernel_name,
                    "venv_is_currently_running": is_current,
                })
                spec["metadata"] = metadata

                spec["resource_dir"] = abspath(kernel_dir)
                all_specs[kernel_name] = spec

        return all_specs

    @property
    def _venv_kspecs(self):
        """Get (or refresh) the cache of venv kernels."""
        expiry = self._venv_kernels_cache_expiry
        if expiry is not None and expiry >= time.time():
            return self._venv_kernels_cache

        kspecs = {}
        for name, info in self._all_venv_specs().items():
            kspecs[name] = KernelSpec(**info)

        self._venv_kernels_cache_expiry = time.time() + CACHE_TIMEOUT
        self._venv_kernels_cache = kspecs

        return kspecs

    @property
    def _conda_kspecs(self):
        """Get conda kernels from the separate CondaKernelSpecManager instance."""
        if self._conda_manager is None:
            return {}
        return self._conda_manager._conda_kspecs

    def find_kernel_specs(self):
        """Returns a dict mapping kernel names to resource directories."""
        if self.venv_only:
            kspecs = {}
        else:
            kspecs = super(VEnvKernelSpecManager, self).find_kernel_specs()

        # Add venv kernels
        venv_kspecs = self._venv_kspecs
        spec_rev = {v: k for k, v in kspecs.items()}

        for name, spec in venv_kspecs.items():
            # Remove system kernel with same resource_dir
            dup = spec_rev.get(spec.resource_dir)
            if dup and dup != name:
                del kspecs[dup]
            kspecs[name] = spec.resource_dir

        # Add conda kernels, removing duplicate system kernels
        if _HAS_CONDA and not self.venv_only:
            conda_kspecs = self._conda_kspecs
            conda_resource_dirs = {spec.resource_dir for spec in conda_kspecs.values()}

            for sys_name in list(kspecs.keys()):
                if kspecs[sys_name] in conda_resource_dirs:
                    del kspecs[sys_name]

            for name, spec in conda_kspecs.items():
                if name not in kspecs:
                    kspecs[name] = spec.resource_dir

        # Apply whitelist if configured
        allow = getattr(self, "allowed_kernelspecs", None) or getattr(self, "whitelist", None)
        if allow:
            kspecs = {k: v for k, v in kspecs.items() if k in allow}

        return kspecs

    def get_kernel_spec(self, kernel_name):
        """Returns a KernelSpec instance for the given kernel_name."""
        # Check venv kernels first
        res = self._venv_kspecs.get(kernel_name)
        if res is not None:
            return res

        # Check conda kernels
        if _HAS_CONDA and not self.venv_only:
            res = self._conda_kspecs.get(kernel_name)
            if res is not None:
                return res

        # Fall back to system kernels
        if not self.venv_only:
            try:
                return super(VEnvKernelSpecManager, self).get_kernel_spec(kernel_name)
            except NoSuchKernel:
                pass

        raise NoSuchKernel(kernel_name)

    def get_all_specs(self):
        """Returns a dict mapping kernel names to resource_dir and spec."""
        res = {}
        for name, resource_dir in self.find_kernel_specs().items():
            try:
                spec = self.get_kernel_spec(name)
                res[name] = {
                    "resource_dir": resource_dir,
                    "spec": spec.to_dict()
                }
            except NoSuchKernel:
                self.log.warning("Error loading kernelspec %r", name, exc_info=True)
        return res
