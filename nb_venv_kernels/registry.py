# -*- coding: utf-8 -*-
"""Registry for venv environments.

Manages ~/.venv/environments.txt - a simple text file listing registered
environment paths, one per line.
"""
import os
from pathlib import Path
from typing import List, Optional


def get_registry_path() -> Path:
    """Return path to environments registry file."""
    return Path.home() / ".venv" / "environments.txt"


def ensure_registry_dir() -> None:
    """Create ~/.venv directory if it doesn't exist."""
    registry_path = get_registry_path()
    registry_path.parent.mkdir(parents=True, exist_ok=True)


def read_environments() -> List[str]:
    """Read all registered environment paths from registry.

    Returns:
        List of absolute paths to registered environments.
        Empty list if registry doesn't exist.
    """
    registry_path = get_registry_path()
    if not registry_path.exists():
        return []

    environments = []
    with open(registry_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                # Resolve to absolute path and normalize
                env_path = os.path.abspath(os.path.expanduser(line))
                if os.path.isdir(env_path):
                    environments.append(env_path)

    return environments


def register_environment(env_path: str) -> bool:
    """Register an environment path in the registry.

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

    ensure_registry_dir()

    # Check if already registered
    existing = read_environments()
    if env_path in existing:
        return False

    # Append to registry
    registry_path = get_registry_path()
    with open(registry_path, "a", encoding="utf-8") as f:
        f.write(env_path + "\n")

    return True


def unregister_environment(env_path: str) -> bool:
    """Remove an environment path from the registry.

    Args:
        env_path: Path to the environment directory

    Returns:
        True if removed, False if not found.
    """
    env_path = os.path.abspath(os.path.expanduser(env_path))
    registry_path = get_registry_path()

    if not registry_path.exists():
        return False

    # Read all lines, filter out the target
    with open(registry_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    removed = False
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            normalized = os.path.abspath(os.path.expanduser(stripped))
            if normalized == env_path:
                removed = True
                continue
        new_lines.append(line)

    if removed:
        with open(registry_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

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
