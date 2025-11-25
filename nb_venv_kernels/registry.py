# -*- coding: utf-8 -*-
"""Registry for venv/uv environments.

Manages two registry files:
- ~/.venv/environments.txt for venv environments
- ~/.uv/environments.txt for uv environments
"""
import os
from pathlib import Path
from typing import List, Optional


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


def list_environments() -> List[dict]:
    """List all registered environments with their status.

    Returns:
        List of dicts with 'path', 'exists', 'has_kernel' keys.
    """
    environments = []
    for env_path in read_environments():
        kernel_path = os.path.join(env_path, "share", "jupyter", "kernels")
        has_kernel = os.path.isdir(kernel_path) and any(
            os.path.exists(os.path.join(kernel_path, d, "kernel.json"))
            for d in os.listdir(kernel_path)
        ) if os.path.isdir(kernel_path) else False

        environments.append({
            "path": env_path,
            "exists": os.path.isdir(env_path),
            "has_kernel": has_kernel
        })

    return environments
