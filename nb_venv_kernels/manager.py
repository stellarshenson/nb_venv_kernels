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

from traitlets import Bool, Unicode, Integer
from jupyter_client.kernelspec import KernelSpecManager, KernelSpec, NoSuchKernel

# Try to import CondaKernelSpecManager for combined functionality
try:
    from nb_conda_kernels import CondaKernelSpecManager
    _HAS_CONDA = True
except ImportError:
    CondaKernelSpecManager = None
    _HAS_CONDA = False

from .registry import (
    read_environments,
    read_environments_with_names,
    is_uv_environment,
    list_environments as _list_environments,
    scan_directory,
    register_environment,
    unregister_environment,
    _check_has_kernel,
    get_conda_environments,
)

CACHE_TIMEOUT = 60

RUNNER_COMMAND = ["python", "-m", "nb_venv_kernels.runner"]


def get_workspace_root():
    """Get the workspace/server root directory.

    Reads from Jupyter server config or environment variables:
    1. JUPYTER_SERVER_ROOT environment variable
    2. ServerApp.root_dir from jupyter_server_config
    3. JUPYTERHUB_ROOT_DIR environment variable
    4. Falls back to current working directory
    """
    # Check environment variable first
    for var in ['JUPYTER_SERVER_ROOT', 'JUPYTERHUB_ROOT_DIR']:
        root = os.environ.get(var)
        if root and os.path.isdir(root):
            return os.path.abspath(root)

    # Try to read from Jupyter server config
    try:
        from jupyter_core.paths import jupyter_config_dir
        import json as json_module

        config_dir = jupyter_config_dir()
        config_file = os.path.join(config_dir, "jupyter_server_config.json")
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                config = json_module.load(f)
            root_dir = config.get("ServerApp", {}).get("root_dir")
            if root_dir and os.path.isdir(root_dir):
                return os.path.abspath(root_dir)
    except Exception:
        pass

    return os.getcwd()


def path_relative_to_workspace(path: str, workspace: str = None) -> str:
    """Convert absolute path to path relative to workspace.

    Args:
        path: Absolute path to convert
        workspace: Workspace root (auto-detected if None)

    Returns:
        Relative path string, or absolute path if outside workspace
    """
    if workspace is None:
        workspace = get_workspace_root()

    try:
        abs_path = os.path.abspath(path)
        abs_workspace = os.path.abspath(workspace)
        if abs_path.startswith(abs_workspace + os.sep) or abs_path == abs_workspace:
            return os.path.relpath(abs_path, abs_workspace)
    except ValueError:
        pass
    return path


def is_path_within_workspace(path: str, workspace: str = None) -> bool:
    """Check if path is within the workspace.

    Args:
        path: Path to check
        workspace: Workspace root (auto-detected if None)

    Returns:
        True if path is within workspace
    """
    if workspace is None:
        workspace = get_workspace_root()

    try:
        abs_path = os.path.abspath(path)
        abs_workspace = os.path.abspath(workspace)
        return abs_path.startswith(abs_workspace + os.sep) or abs_path == abs_workspace
    except ValueError:
        return False


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

    scan_depth = Integer(
        10,
        config=True,
        help="Default directory depth for 'nb_venv_kernels scan' command."
    )

    require_kernelspec = Bool(
        False,
        config=True,
        help="If True, only register environments with ipykernel installed. "
             "Environments without kernelspec are ignored during scan."
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

        for env_path, custom_name in read_environments_with_names():
            # Apply filter if configured
            if self.env_filter and self._env_filter_regex.search(env_path):
                continue

            # Use custom name if available, otherwise derive from path
            if custom_name:
                env_name = custom_name
            else:
                # Use parent directory name if .venv, otherwise use directory name
                env_dir = basename(env_path)
                if env_dir == ".venv":
                    env_name = basename(dirname(env_path))
                else:
                    env_name = env_dir

            # Handle duplicates by appending _1, _2, etc.
            if env_name in seen_names:
                suffix = seen_names[env_name]
                while f"{env_name}_{suffix}" in seen_names:
                    suffix += 1
                seen_names[f"{env_name}_{suffix}"] = 1
                seen_names[env_name] = suffix + 1
                env_name = f"{env_name}_{suffix}"
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

    def _get_kernel_sort_key(self, kernel_name):
        """Return sort key for kernel ordering.

        Priority order:
        0 - Current environment (marked with *)
        1 - Conda kernels
        2 - UV kernels
        3 - Venv kernels
        4 - System kernels
        """
        # Check if current environment (venv/uv)
        venv_spec = self._venv_kspecs.get(kernel_name)
        if venv_spec:
            metadata = getattr(venv_spec, 'metadata', {}) or {}
            if metadata.get('venv_is_currently_running'):
                return (0, kernel_name)
            source = metadata.get('venv_source', 'venv')
            if source == 'uv':
                return (2, kernel_name)
            return (3, kernel_name)

        # Check if conda kernel
        if _HAS_CONDA and not self.venv_only:
            if kernel_name in self._conda_kspecs:
                # Check if current conda env
                conda_spec = self._conda_kspecs[kernel_name]
                display_name = getattr(conda_spec, 'display_name', '')
                if display_name.endswith(' *'):
                    return (0, kernel_name)
                return (1, kernel_name)

        # System kernel
        return (4, kernel_name)

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

        # Sort kernels: current first, then conda, uv, venv, system
        sorted_names = sorted(kspecs.keys(), key=self._get_kernel_sort_key)
        return {name: kspecs[name] for name in sorted_names}

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

    # --- API methods for programmatic access ---

    def _resolve_name_conflicts(self, environments, update_action_on_change=False):
        """Add suffixes to duplicate names to make them unique.

        Args:
            environments: List of dicts with 'name' key
            update_action_on_change: If True and env has 'action' key, change action to 'update'
                                     when name is modified due to conflict

        Returns:
            Same list with 'name' values made unique via _1, _2, _3 suffixes
        """
        seen_names = {}
        for env in environments:
            name = env["name"]
            if name in seen_names:
                # Find next available suffix
                suffix = seen_names[name]
                while f"{name}_{suffix}" in seen_names:
                    suffix += 1
                env["name"] = f"{name}_{suffix}"
                seen_names[f"{name}_{suffix}"] = 1
                seen_names[name] = suffix + 1
                # Mark as update if requested and action exists
                if update_action_on_change and "action" in env and env["action"] == "keep":
                    env["action"] = "update"
            else:
                seen_names[name] = 1
        return environments

    def list_environments(self):
        """List all registered environments with their status.

        Returns:
            List of dicts with keys: name, type, exists, has_kernel, path, custom_name
        """
        envs = _list_environments()

        # Add display name
        result = []
        for env in envs:
            env_type = env.get("type", "venv")
            path = env["path"]
            custom_name = env.get("custom_name")

            # Use custom name if provided, otherwise derive from path
            if custom_name:
                name = custom_name
            else:
                env_dir = basename(path)
                if env_dir in (".venv", "venv", ".env", "env"):
                    name = basename(dirname(path))
                elif env_type == "conda" and env_dir.lower() in (
                    "conda", "anaconda", "anaconda3", "miniconda", "miniconda3",
                    "miniforge", "miniforge3", "mambaforge", "mambaforge3"
                ):
                    name = "base"
                else:
                    name = env_dir

            # Determine type display
            if env_type == "conda":
                if basename(path).lower() in (
                    "conda", "anaconda", "anaconda3", "miniconda", "miniconda3",
                    "miniforge", "miniforge3", "mambaforge", "mambaforge3"
                ):
                    type_display = "conda"
                else:
                    type_display = "conda (local)"
            else:
                type_display = env_type

            result.append({
                "name": name,
                "type": type_display,
                "exists": env["exists"],
                "has_kernel": env["has_kernel"],
                "path": path,
                "custom_name": custom_name,
            })

        return self._resolve_name_conflicts(result)

    def scan_environments(self, path=".", max_depth=None, dry_run=False):
        """Scan directory for environments and register them.

        If require_kernelspec config is True, only environments with ipykernel
        installed are registered. Environments without kernelspec are reported
        with action='ignore'. If False (default), all valid environments are registered.

        Args:
            path: Directory to scan (default: current directory)
            max_depth: Maximum depth to recurse (default: from config)
            dry_run: If True, only report without making changes

        Returns:
            Dict with keys: environments (list), summary (dict), dry_run (bool)
        """
        if max_depth is None:
            max_depth = self.scan_depth

        path = abspath(path)
        result = scan_directory(
            path, max_depth=max_depth, dry_run=dry_run,
            require_kernelspec=self.require_kernelspec
        )

        # Build lookup of custom names from registry
        registry_envs = _list_environments()
        custom_names = {env["path"]: env.get("custom_name") for env in registry_envs}

        def get_env_info(env_path, env_type, action, exists=None, custom_name=None):
            """Build environment info dict with exists and has_kernel."""
            # Trust exists parameter if provided (environment was just found)
            if exists is None:
                exists = os.path.isdir(env_path)
            kernel_path = join(env_path, "share", "jupyter", "kernels")
            has_kernel = _check_has_kernel(kernel_path) if exists else False
            return {
                "action": action,
                "name": self._get_env_display_name(env_path, env_type, custom_name),
                "type": env_type,
                "exists": exists,
                "has_kernel": has_kernel,
                "path": env_path,
            }

        # Build environment list with actions
        environments = []
        seen_paths = set()

        # Environments found during scan - they exist (we just found them)
        for env_path in result["registered"]:
            env_type = "uv" if is_uv_environment(env_path) else "venv"
            environments.append(get_env_info(env_path, env_type, "add", exists=True))
            seen_paths.add(env_path)

        # Environments that were actually updated (name changed)
        for env_path in result.get("updated", []):
            env_type = "uv" if is_uv_environment(env_path) else "venv"
            custom_name = custom_names.get(env_path)
            environments.append(get_env_info(env_path, env_type, "update", exists=True, custom_name=custom_name))
            seen_paths.add(env_path)

        # Environments already registered (no change)
        for env_path in result["skipped"]:
            env_type = "uv" if is_uv_environment(env_path) else "venv"
            custom_name = custom_names.get(env_path)
            environments.append(get_env_info(env_path, env_type, "keep", exists=True, custom_name=custom_name))
            seen_paths.add(env_path)

        for env_path in result["conda_found"]:
            environments.append(get_env_info(env_path, "conda", "keep", exists=True))
            seen_paths.add(env_path)

        # Add global conda environments not in scan path
        global_conda_count = 0
        for env_path in get_conda_environments():
            if env_path not in seen_paths:
                environments.append(get_env_info(env_path, "conda", "keep"))
                global_conda_count += 1

        # Environments being removed from registry (don't exist or lost kernelspec)
        removed_paths = set()
        for item in result["not_available"]:
            removed_paths.add(item["path"])

        # Environments without kernelspec (ipykernel not installed)
        # Exclude paths that are being removed - they show as 'remove', not 'ignore'
        for env_path in result.get("ignore", []):
            if env_path in removed_paths:
                continue  # Will be shown as 'remove' instead
            env_type = "uv" if is_uv_environment(env_path) else "venv"
            environments.append({
                "action": "ignore",
                "name": self._get_env_display_name(env_path, env_type),
                "type": env_type,
                "exists": True,
                "has_kernel": False,
                "path": env_path,
            })
            seen_paths.add(env_path)

        for item in result["not_available"]:
            custom_name = item.get("custom_name")
            environments.append({
                "action": "remove",
                "name": self._get_env_display_name(item["path"], item["type"], custom_name),
                "type": item["type"],
                "exists": False,
                "has_kernel": False,
                "path": item["path"],
            })

        # Invalidate cache after scan (if not dry run)
        if not dry_run:
            self._venv_kernels_cache = None
            self._venv_kernels_cache_expiry = None

        # Resolve name conflicts before returning (mark changed names as "update")
        environments = self._resolve_name_conflicts(environments, update_action_on_change=True)

        # Calculate counts from actual actions (after name conflict resolution)
        summary = {"add": 0, "update": 0, "keep": 0, "ignore": 0, "remove": 0}
        for env in environments:
            action = env.get("action", "keep")
            if action in summary:
                summary[action] += 1

        return {
            "environments": environments,
            "summary": summary,
            "dry_run": dry_run,
        }

    def register_environment(self, path, name=None):
        """Register an environment for kernel discovery.

        Args:
            path: Path to the environment directory
            name: Optional custom display name (ignored for conda environments)

        Returns:
            Dict with keys: path, registered (bool), updated (bool), name (str or None), error (str or None)
        """
        path = abspath(path)
        try:
            registered, updated = register_environment(
                path, name=name, require_kernelspec=self.require_kernelspec
            )
            # Invalidate cache
            self._venv_kernels_cache = None
            self._venv_kernels_cache_expiry = None
            return {"path": path, "registered": registered, "updated": updated, "name": name, "error": None}
        except ValueError as e:
            return {"path": path, "registered": False, "updated": False, "name": name, "error": str(e)}

    def unregister_environment(self, path):
        """Remove an environment from kernel discovery.

        Args:
            path: Path to the environment directory

        Returns:
            Dict with keys: path, unregistered (bool)
        """
        path = abspath(path)
        unregistered = unregister_environment(path)
        if unregistered:
            # Invalidate cache
            self._venv_kernels_cache = None
            self._venv_kernels_cache_expiry = None
        return {"path": path, "unregistered": unregistered}

    def _get_env_display_name(self, env_path, env_type, custom_name=None):
        """Get display name for an environment."""
        # Use custom name if provided
        if custom_name:
            return custom_name

        env_dir = basename(env_path)

        if env_type in ("venv", "uv"):
            if env_dir in (".venv", "venv", ".env", "env", ".virtualenv", "virtualenv"):
                return basename(dirname(env_path))
            return env_dir

        if env_type == "conda":
            if env_dir.lower() in (
                "conda", "anaconda", "anaconda3", "miniconda", "miniconda3",
                "miniforge", "miniforge3", "mambaforge", "mambaforge3"
            ):
                return "base"
            return env_dir

        return env_dir
