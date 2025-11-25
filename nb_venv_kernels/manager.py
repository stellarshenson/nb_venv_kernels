# -*- coding: utf-8 -*-
"""KernelSpecManager for uv/venv environments.

Extends CondaKernelSpecManager (if available) or KernelSpecManager to discover
kernels from registered uv/venv environments alongside conda environments.
"""
import glob
import json
import os
import re
import time
from os.path import join, dirname, basename, abspath

from traitlets import Bool, Unicode, validate
from jupyter_client.kernelspec import KernelSpecManager, KernelSpec, NoSuchKernel

# Try to import CondaKernelSpecManager for combined functionality
try:
    from nb_conda_kernels import CondaKernelSpecManager
    _BASE_MANAGER = CondaKernelSpecManager
    _HAS_CONDA = True
except ImportError:
    _BASE_MANAGER = KernelSpecManager
    _HAS_CONDA = False

from .registry import read_environments

CACHE_TIMEOUT = 60

RUNNER_COMMAND = ["python", "-m", "nb_venv_kernels.runner"]


class UvKernelSpecManager(_BASE_MANAGER):
    """A KernelSpecManager that discovers kernels from registered uv/venv environments."""

    uv_only = Bool(
        False,
        config=True,
        help="Include only uv/venv kernels, hide system kernels."
    )

    env_filter = Unicode(
        None,
        config=True,
        allow_none=True,
        help="Regex pattern to exclude environments by path."
    )

    name_format = Unicode(
        "{language} [venv: {environment}]",
        config=True,
        help="Display name format. Available: {language}, {environment}, {kernel}, {display_name}"
    )

    def __init__(self, **kwargs):
        super(UvKernelSpecManager, self).__init__(**kwargs)

        self._uv_kernels_cache = None
        self._uv_kernels_cache_expiry = None

        if self.env_filter is not None:
            self._env_filter_regex = re.compile(self.env_filter)

        self.log.info("nb_venv_kernels | UvKernelSpecManager initialized")
        self.log.info("nb_venv_kernels | Base class: %s (conda support: %s)", _BASE_MANAGER.__name__, _HAS_CONDA)
        self.log.info("nb_venv_kernels | uv_only=%s, env_filter=%s", self.uv_only, self.env_filter)
        self.log.info("nb_venv_kernels | name_format=%s", self.name_format)

        # Force initial scan and log results
        kspecs = self._uv_kspecs
        self.log.info("nb_venv_kernels | Found %s uv/venv kernels", len(kspecs))
        for name in kspecs:
            self.log.info("nb_venv_kernels |   - %s", name)

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
        """Get all registered environments.

        Returns:
            Dict mapping environment names to paths.
        """
        all_envs = {}
        seen_names = {}

        registered = read_environments()
        self.log.debug("nb_venv_kernels | _all_envs: registry returned %s environments", len(registered))

        for env_path in registered:
            self.log.debug("nb_venv_kernels | _all_envs: processing %s", env_path)

            # Apply filter if configured
            if self.env_filter and self._env_filter_regex.search(env_path):
                self.log.debug("nb_venv_kernels | _all_envs: filtered out by env_filter")
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
            self.log.debug("nb_venv_kernels | _all_envs: added %s -> %s", env_name, env_path)

        self.log.debug("nb_venv_kernels | _all_envs: returning %s environments", len(all_envs))
        return all_envs

    def _all_specs(self):
        """Find all kernel specs in registered environments.

        Returns:
            Dict mapping kernel names to kernel spec dicts.
        """
        all_specs = {}
        all_envs = self._all_envs()

        self.log.debug("nb_venv_kernels | _all_specs: scanning %s environments", len(all_envs))

        for env_name, env_path in all_envs.items():
            kspec_base = join(env_path, "share", "jupyter", "kernels")
            self.log.debug("nb_venv_kernels | _all_specs: scanning %s", kspec_base)

            if not os.path.isdir(kspec_base):
                self.log.debug("nb_venv_kernels | _all_specs: directory does not exist, skipping")
                continue

            kspec_glob = glob.glob(join(kspec_base, "*", "kernel.json"))
            self.log.debug("nb_venv_kernels | _all_specs: found %s kernel.json files", len(kspec_glob))

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
                kernel_name = f"uv-{env_name}-{kernel_name}"
                kernel_name = self.clean_kernel_name(kernel_name)

                # Format display name
                display_prefix = spec["display_name"]
                if display_prefix.startswith("Python"):
                    display_prefix = "Python"

                display_name = self.name_format.format(
                    language=display_prefix,
                    environment=env_name,
                    kernel=raw_kernel_name,
                    display_name=spec["display_name"],
                )

                # Mark if current environment
                is_current = env_path == os.sys.prefix
                if is_current:
                    display_name += " *"

                spec["display_name"] = display_name

                # Prepend runner command for non-current environments
                if not is_current:
                    spec["argv"] = RUNNER_COMMAND + [env_path] + spec["argv"]

                # Add metadata
                metadata = spec.get("metadata", {})
                metadata.update({
                    "uv_env_name": env_name,
                    "uv_env_path": env_path,
                    "uv_language": display_prefix,
                    "uv_raw_kernel_name": raw_kernel_name,
                    "uv_is_currently_running": is_current,
                })
                spec["metadata"] = metadata

                spec["resource_dir"] = abspath(kernel_dir)
                all_specs[kernel_name] = spec
                self.log.debug("nb_venv_kernels | _all_specs: added kernel %s", kernel_name)

        self.log.debug("nb_venv_kernels | _all_specs: returning %s kernels", len(all_specs))
        return all_specs

    @property
    def _uv_kspecs(self):
        """Get (or refresh) the cache of uv kernels."""
        expiry = self._uv_kernels_cache_expiry
        if expiry is not None and expiry >= time.time():
            return self._uv_kernels_cache

        kspecs = {}
        for name, info in self._all_specs().items():
            kspecs[name] = KernelSpec(**info)

        self._uv_kernels_cache_expiry = time.time() + CACHE_TIMEOUT
        self._uv_kernels_cache = kspecs

        return kspecs

    def find_kernel_specs(self):
        """Returns a dict mapping kernel names to resource directories."""
        self.log.debug("nb_venv_kernels | find_kernel_specs called")

        if self.uv_only:
            kspecs = {}
            self.log.debug("nb_venv_kernels | uv_only=True, starting with empty kspecs")
        else:
            kspecs = super(UvKernelSpecManager, self).find_kernel_specs()
            self.log.debug("nb_venv_kernels | parent find_kernel_specs returned %s kernels", len(kspecs))

        # Add uv kernels, resolving duplicates in favor of uv
        uv_kspecs = self._uv_kspecs
        self.log.debug("nb_venv_kernels | adding %s uv kernels", len(uv_kspecs))

        spec_rev = {v: k for k, v in kspecs.items()}
        for name, spec in uv_kspecs.items():
            kspecs[name] = spec.resource_dir
            dup = spec_rev.get(kspecs[name])
            if dup:
                self.log.debug("nb_venv_kernels | removing duplicate %s in favor of %s", dup, name)
                del kspecs[dup]

        # Apply whitelist if configured
        allow = getattr(self, "allowed_kernelspecs", None) or getattr(self, "whitelist", None)
        if allow:
            kspecs = {k: v for k, v in kspecs.items() if k in allow}

        self.log.debug("nb_venv_kernels | find_kernel_specs returning %s kernels: %s", len(kspecs), list(kspecs.keys()))
        return kspecs

    def get_kernel_spec(self, kernel_name):
        """Returns a KernelSpec instance for the given kernel_name."""
        res = self._uv_kspecs.get(kernel_name)
        if res is None and not self.uv_only:
            res = super(UvKernelSpecManager, self).get_kernel_spec(kernel_name)
        if res is None:
            raise NoSuchKernel(kernel_name)
        return res

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
