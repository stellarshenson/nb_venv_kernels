# -*- coding: utf-8 -*-
"""Registry for venv/uv environments.

Manages two registry files:
- ~/.venv/environments.txt for venv environments
- ~/.uv/environments.txt for uv environments
"""
import os
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


def _read_registry_file(registry_path: Path) -> List[str]:
    """Read environments from a single registry file."""
    if not registry_path.exists():
        return []

    environments = []
    with open(registry_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                env_path = os.path.abspath(os.path.expanduser(line))
                if os.path.isdir(env_path):
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


def register_environment(env_path: str) -> bool:
    """Register an environment path in the appropriate registry.

    Auto-detects uv vs venv and writes to ~/.uv/ or ~/.venv/ accordingly.

    Args:
        env_path: Path to the environment directory (e.g., /path/to/.venv)

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

    # Append to registry
    registry_path = get_registry_path(source)
    with open(registry_path, "a", encoding="utf-8") as f:
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
        import subprocess
        result = subprocess.run(
            ["conda", "env", "list", "--json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            import json
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
        List of dicts with 'path', 'type', 'exists', 'has_kernel' keys.
        Types: 'venv', 'uv', 'conda'
    """
    environments = []
    seen = set()

    # Get venv environments from ~/.venv/environments.txt
    for env_path in _read_registry_file(get_venv_registry_path()):
        if env_path in seen:
            continue
        seen.add(env_path)
        kernel_path = os.path.join(env_path, "share", "jupyter", "kernels")
        has_kernel = _check_has_kernel(kernel_path)
        environments.append({
            "path": env_path,
            "type": "venv",
            "exists": os.path.isdir(env_path),
            "has_kernel": has_kernel
        })

    # Get uv environments from ~/.uv/environments.txt
    for env_path in _read_registry_file(get_uv_registry_path()):
        if env_path in seen:
            continue
        seen.add(env_path)
        kernel_path = os.path.join(env_path, "share", "jupyter", "kernels")
        has_kernel = _check_has_kernel(kernel_path)
        environments.append({
            "path": env_path,
            "type": "uv",
            "exists": os.path.isdir(env_path),
            "has_kernel": has_kernel
        })

    # Get conda environments
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
            "has_kernel": has_kernel
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


def cleanup_registries() -> Dict[str, List[str]]:
    """Remove non-existent environments from both registries.

    Returns:
        Dict with 'removed' list of paths that were removed.
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

            env_path = os.path.abspath(os.path.expanduser(stripped))
            if os.path.isdir(env_path):
                new_lines.append(line)
            else:
                removed.append(env_path)

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


def scan_directory(root_path: str, max_depth: int = 7) -> Dict[str, List[str]]:
    """Scan directory tree for virtual environments.

    Searches for venv, uv, and conda environments. Registers found
    environments in appropriate registries and cleans up non-existent ones.

    Args:
        root_path: Directory to start scanning from
        max_depth: Maximum depth to recurse (default: 7, None = unlimited)

    Returns:
        Dict with 'registered', 'skipped', 'removed', 'conda_found' lists.
    """
    root_path = os.path.abspath(os.path.expanduser(root_path))

    if not os.path.isdir(root_path):
        raise ValueError(f"Directory does not exist: {root_path}")

    # First cleanup registries
    cleanup_result = cleanup_registries()
    removed = cleanup_result["removed"]

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
        "removed": removed,
        "conda_found": conda_found,
    }
