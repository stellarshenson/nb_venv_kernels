# -*- coding: utf-8 -*-
"""Registry for venv/uv environments.

Manages two registry files:
- ~/.venv/environments.txt for venv environments
- ~/.uv/environments.txt for uv environments
"""
import json
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict


def get_venv_registry_path() -> Path:
    """Return path to venv environments registry file."""
    return Path.home() / ".venv" / "environments.txt"


def get_uv_registry_path() -> Path:
    """Return path to uv environments registry file."""
    return Path.home() / ".uv" / "environments.txt"


def get_registry_path(source: str = "venv") -> Path:
    """Return path to environments registry file.

    Args:
        source: "venv" or "uv"
    """
    if source == "uv":
        return get_uv_registry_path()
    return get_venv_registry_path()


def ensure_registry_dir(source: str = "venv") -> None:
    """Create registry directory if it doesn't exist."""
    registry_path = get_registry_path(source)
    registry_path.parent.mkdir(parents=True, exist_ok=True)


def is_uv_environment(env_path: str) -> bool:
    """Check if environment was created by uv.

    uv creates pyvenv.cfg with 'uv = <version>' line.
    """
    pyvenv_cfg = os.path.join(env_path, "pyvenv.cfg")
    if os.path.exists(pyvenv_cfg):
        try:
            with open(pyvenv_cfg, "r") as f:
                for line in f:
                    if line.strip().startswith("uv ="):
                        return True
        except IOError:
            pass
    return False


def _read_registry_file(registry_path: Path, include_missing: bool = False,
                        include_names: bool = False) -> List:
    """Read environments from a single registry file.

    Registry format supports optional custom names (tab-separated):
        /path/to/env
        /path/to/env\tcustom-name

    Args:
        registry_path: Path to the registry file
        include_missing: If True, include paths that don't exist on disk
        include_names: If True, return list of (path, name) tuples instead of just paths

    Returns:
        List of paths (str) or list of (path, name) tuples if include_names=True
    """
    if not registry_path.exists():
        return []

    environments = []
    with open(registry_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Parse tab-separated format: path[\tname]
                parts = line.split('\t', 1)
                env_path = os.path.abspath(os.path.expanduser(parts[0]))
                custom_name = parts[1] if len(parts) > 1 else None

                if include_missing or os.path.isdir(env_path):
                    if include_names:
                        environments.append((env_path, custom_name))
                    else:
                        environments.append(env_path)

    return environments


def read_environments() -> List[str]:
    """Read all registered environment paths from both registries.

    Returns:
        List of absolute paths to registered environments.
        Combines ~/.venv/environments.txt and ~/.uv/environments.txt.
    """
    environments = []
    seen = set()

    # Read from both registries
    for registry_path in [get_venv_registry_path(), get_uv_registry_path()]:
        for env_path in _read_registry_file(registry_path):
            if env_path not in seen:
                environments.append(env_path)
                seen.add(env_path)

    return environments


def register_environment(env_path: str, name: Optional[str] = None) -> bool:
    """Register an environment path in the appropriate registry.

    Auto-detects uv vs venv and writes to ~/.uv/ or ~/.venv/ accordingly.

    Args:
        env_path: Path to the environment directory (e.g., /path/to/.venv)
        name: Optional custom display name for the environment

    Returns:
        True if newly registered, False if already registered.
    """
    env_path = os.path.abspath(os.path.expanduser(env_path))

    if not os.path.isdir(env_path):
        raise ValueError(f"Environment path does not exist: {env_path}")

    # Check for bin/python or Scripts/python.exe (Windows)
    python_path = os.path.join(env_path, "bin", "python")
    python_path_win = os.path.join(env_path, "Scripts", "python.exe")
    if not os.path.exists(python_path) and not os.path.exists(python_path_win):
        raise ValueError(f"Not a valid Python environment: {env_path}")

    # Check if already registered in either registry
    existing = read_environments()
    if env_path in existing:
        return False

    # Detect source and use appropriate registry
    source = "uv" if is_uv_environment(env_path) else "venv"
    ensure_registry_dir(source)

    # Append to registry with optional name (tab-separated)
    registry_path = get_registry_path(source)
    with open(registry_path, "a", encoding="utf-8") as f:
        if name:
            f.write(f"{env_path}\t{name}\n")
        else:
            f.write(env_path + "\n")

    return True


def unregister_environment(env_path: str) -> bool:
    """Remove an environment path from both registries.

    Args:
        env_path: Path to the environment directory

    Returns:
        True if removed, False if not found.
    """
    env_path = os.path.abspath(os.path.expanduser(env_path))
    removed = False

    # Check both registries
    for registry_path in [get_venv_registry_path(), get_uv_registry_path()]:
        if not registry_path.exists():
            continue

        # Read all lines, filter out the target
        with open(registry_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        found = False
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                normalized = os.path.abspath(os.path.expanduser(stripped))
                if normalized == env_path:
                    found = True
                    continue
            new_lines.append(line)

        if found:
            with open(registry_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            removed = True

    return removed


def get_conda_environments() -> List[str]:
    """Get list of conda environment paths.

    Returns paths from both conda env list and ~/.conda/environments.txt.
    """
    environments = []
    seen = set()

    # Try conda env list
    try:
        result = subprocess.run(
            ["conda", "env", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for env_path in data.get("envs", []):
                if env_path not in seen:
                    environments.append(env_path)
                    seen.add(env_path)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass

    # Also check ~/.conda/environments.txt
    conda_registry = Path.home() / ".conda" / "environments.txt"
    if conda_registry.exists():
        try:
            with open(conda_registry, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        env_path = os.path.abspath(os.path.expanduser(line))
                        if env_path not in seen and os.path.isdir(env_path):
                            environments.append(env_path)
                            seen.add(env_path)
        except IOError:
            pass

    return environments


def list_environments() -> List[dict]:
    """List all registered environments with their status.

    Returns:
        List of dicts with 'path', 'type', 'exists', 'has_kernel', 'custom_name' keys.
        Types: 'venv', 'uv', 'conda'
    """
    environments = []
    seen = set()

    # Get venv environments from ~/.venv/environments.txt
    for env_path, custom_name in _read_registry_file(get_venv_registry_path(),
                                                      include_missing=True,
                                                      include_names=True):
        if env_path in seen:
            continue
        seen.add(env_path)
        kernel_path = os.path.join(env_path, "share", "jupyter", "kernels")
        has_kernel = _check_has_kernel(kernel_path)
        environments.append({
            "path": env_path,
            "type": "venv",
            "exists": os.path.isdir(env_path),
            "has_kernel": has_kernel,
            "custom_name": custom_name
        })

    # Get uv environments from ~/.uv/environments.txt
    for env_path, custom_name in _read_registry_file(get_uv_registry_path(),
                                                      include_missing=True,
                                                      include_names=True):
        if env_path in seen:
            continue
        seen.add(env_path)
        kernel_path = os.path.join(env_path, "share", "jupyter", "kernels")
        has_kernel = _check_has_kernel(kernel_path)
        environments.append({
            "path": env_path,
            "type": "uv",
            "exists": os.path.isdir(env_path),
            "has_kernel": has_kernel,
            "custom_name": custom_name
        })

    # Get conda environments (no custom names for conda)
    for env_path in get_conda_environments():
        if env_path in seen:
            continue
        seen.add(env_path)
        kernel_path = os.path.join(env_path, "share", "jupyter", "kernels")
        has_kernel = _check_has_kernel(kernel_path)
        environments.append({
            "path": env_path,
            "type": "conda",
            "exists": os.path.isdir(env_path),
            "has_kernel": has_kernel,
            "custom_name": None
        })

    return environments


def _check_has_kernel(kernel_path: str) -> bool:
    """Check if kernel path contains a kernel.json."""
    if not os.path.isdir(kernel_path):
        return False
    try:
        return any(
            os.path.exists(os.path.join(kernel_path, d, "kernel.json"))
            for d in os.listdir(kernel_path)
        )
    except OSError:
        return False


def cleanup_registries() -> Dict[str, List[Dict[str, str]]]:
    """Remove non-existent environments from both registries.

    Returns:
        Dict with 'removed' list of dicts containing 'path', 'type', and 'custom_name'.
    """
    removed = []

    for source, registry_path in [("venv", get_venv_registry_path()),
                                   ("uv", get_uv_registry_path())]:
        if not registry_path.exists():
            continue

        with open(registry_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                continue

            # Parse tab-separated format: path[\tname]
            parts = stripped.split('\t', 1)
            env_path = os.path.abspath(os.path.expanduser(parts[0]))
            custom_name = parts[1] if len(parts) > 1 else None

            if os.path.isdir(env_path):
                new_lines.append(line)
            else:
                removed.append({"path": env_path, "type": source, "custom_name": custom_name})

        # Write back if changed
        if len(new_lines) < len(lines):
            with open(registry_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

    return {"removed": removed}


def is_valid_environment(path: str) -> bool:
    """Check if path is a valid Python virtual environment.

    Returns True if path contains bin/python or Scripts/python.exe.
    """
    if not os.path.isdir(path):
        return False
    python_path = os.path.join(path, "bin", "python")
    python_path_win = os.path.join(path, "Scripts", "python.exe")
    return os.path.exists(python_path) or os.path.exists(python_path_win)


def is_conda_environment(path: str) -> bool:
    """Check if path is a conda environment.

    Conda environments have conda-meta directory.
    """
    return os.path.isdir(os.path.join(path, "conda-meta"))


def is_global_conda_environment(path: str) -> bool:
    """Check if path is a global/system conda environment.

    Only returns True for:
    - Known conda base installations (anaconda, miniconda, etc.)
    - Environments listed in conda env list or ~/.conda/environments.txt

    Does NOT return True for random directories that happen to have conda-meta.
    """
    if not is_conda_environment(path):
        return False

    abs_path = os.path.abspath(path)

    # Check if it's a known conda base installation
    basename = os.path.basename(abs_path).lower()
    base_names = {"conda", "anaconda", "anaconda3", "miniconda", "miniconda3",
                  "miniforge", "miniforge3", "mambaforge", "mambaforge3"}
    if basename in base_names:
        return True

    # Check if it's listed in conda's known environments
    known_conda_envs = set(get_conda_environments())
    if abs_path in known_conda_envs:
        return True

    return False


def scan_directory(root_path: str, max_depth: int = 7,
                   dry_run: bool = False) -> Dict[str, List]:
    """Scan directory tree for virtual environments.

    Searches for venv, uv, and conda environments. Registers found
    environments in appropriate registries and cleans up non-existent ones.

    Args:
        root_path: Directory to start scanning from
        max_depth: Maximum depth to recurse (default: 7, None = unlimited)
        dry_run: If True, only report without making changes

    Returns:
        Dict with 'registered', 'skipped', 'removed', 'conda_found', 'not_available' lists.
    """
    root_path = os.path.abspath(os.path.expanduser(root_path))

    if not os.path.isdir(root_path):
        raise ValueError(f"Directory does not exist: {root_path}")

    # Cleanup registries (or just check for not available in dry run)
    not_available = []
    if dry_run:
        # Check what would be removed without actually removing
        for source, registry_path in [("venv", get_venv_registry_path()),
                                       ("uv", get_uv_registry_path())]:
            if not registry_path.exists():
                continue
            with open(registry_path, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#"):
                        # Parse tab-separated format: path[\tname]
                        parts = stripped.split('\t', 1)
                        env_path = os.path.abspath(os.path.expanduser(parts[0]))
                        custom_name = parts[1] if len(parts) > 1 else None
                        if not os.path.isdir(env_path):
                            not_available.append({"path": env_path, "type": source, "custom_name": custom_name})
    else:
        cleanup_result = cleanup_registries()
        not_available = cleanup_result["removed"]

    registered = []
    skipped = []
    conda_found = []

    # Common venv directory names
    venv_names = {".venv", "venv", ".env", "env", ".virtualenv", "virtualenv"}

    def scan_recursive(current_path: str, depth: int):
        if max_depth is not None and depth > max_depth:
            return

        try:
            entries = os.listdir(current_path)
        except PermissionError:
            return

        for entry in entries:
            # Skip hidden directories (except known venv names)
            if entry.startswith(".") and entry not in venv_names:
                continue

            # Skip common non-environment directories
            skip_dirs = {
                # Version control
                ".git", ".hg", ".svn",
                # Node/JS
                "node_modules", ".npm", ".yarn", ".pnpm",
                # Python build/cache
                "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
                ".tox", ".nox", ".eggs", "__pypackages__",
                "dist", "build",
                # Package internals (don't recurse into installed packages)
                "site-packages", "lib", "lib64", "include",
                # IDE/Editor
                ".vscode", ".idea",
                # Other caches
                ".cache", ".coverage", "coverage", "htmlcov",
                # Jupyter
                ".ipynb_checkpoints",
            }
            if entry in skip_dirs or entry.endswith(".egg-info"):
                continue

            full_path = os.path.join(current_path, entry)

            if not os.path.isdir(full_path):
                continue

            # Check if this is a valid environment
            if is_valid_environment(full_path):
                if is_conda_environment(full_path):
                    conda_found.append(full_path)
                else:
                    if dry_run:
                        # In dry run, check if already registered
                        existing = read_environments()
                        if full_path in existing:
                            skipped.append(full_path)
                        else:
                            registered.append(full_path)
                    else:
                        # Try to register
                        try:
                            if register_environment(full_path):
                                registered.append(full_path)
                            else:
                                skipped.append(full_path)
                        except ValueError:
                            pass  # Not a valid environment
                # Don't recurse into environments
                continue

            # Recurse into subdirectory
            scan_recursive(full_path, depth + 1)

    scan_recursive(root_path, 0)

    return {
        "registered": registered,
        "skipped": skipped,
        "not_available": not_available,
        "conda_found": conda_found,
    }
