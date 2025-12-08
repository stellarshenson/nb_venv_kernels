# -*- coding: utf-8 -*-
"""Registry for venv/uv environments.

Manages two registry files:
- ~/.venv/environments.txt for venv environments
- ~/.uv/environments.txt for uv environments
"""
import json
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional, Tuple, Dict

from filelock import FileLock


def _get_registry_lock_path() -> Path:
    """Return path to the global registry lock file."""
    return Path.home() / ".venv" / "registry.lock"


@contextmanager
def _registry_lock():
    """Context manager for registry file locking (thread/multiprocess safe).

    Uses a single global lock for both venv and uv registries to avoid deadlocks.
    Cross-platform using filelock package.
    """
    lock_path = _get_registry_lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    lock = FileLock(str(lock_path))
    with lock:
        yield


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


def read_environments_with_names() -> List[Tuple[str, Optional[str]]]:
    """Read all registered environments with their custom names.

    Sanitizes duplicate names in the registry files by appending _1, _2, etc.
    If duplicates are found, the registry files are updated in place.
    Thread/multiprocess safe using file locking.

    Returns:
        List of (path, custom_name) tuples. custom_name is None if not set.
        Combines ~/.venv/environments.txt and ~/.uv/environments.txt.
    """
    environments, _ = _read_and_sanitize_registries()
    return environments


def sanitize_registry_names() -> List[Dict]:
    """Sanitize duplicate names in registries and return list of updated entries.

    Thread/multiprocess safe using file locking.

    Returns:
        List of dicts with 'path', 'type', 'old_name', 'new_name' for each updated entry.
    """
    _, updated = _read_and_sanitize_registries()
    return updated


def _read_and_sanitize_registries() -> Tuple[List[Tuple[str, Optional[str]]], List[Dict]]:
    """Read registries and sanitize duplicate names.

    Internal function that does the actual work for both read_environments_with_names()
    and sanitize_registry_names().

    Returns:
        Tuple of (environments, updated_entries):
        - environments: List of (path, custom_name) tuples
        - updated_entries: List of dicts with path, type, old_name, new_name
    """
    with _registry_lock():
        environments = []
        updated_entries = []
        seen_paths = set()
        seen_names = set()
        updates_needed = {}  # registry_path -> {old_line -> (new_line, env_path, old_name, new_name)}

        # Read from both registries and detect duplicates
        for registry_path in [get_venv_registry_path(), get_uv_registry_path()]:
            if not registry_path.exists():
                continue

            source = "uv" if registry_path == get_uv_registry_path() else "venv"

            with open(registry_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for line in lines:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                parts = stripped.split('\t', 1)
                env_path = os.path.abspath(os.path.expanduser(parts[0]))
                custom_name = parts[1] if len(parts) > 1 else None

                if env_path in seen_paths:
                    continue  # Skip duplicate paths

                # Check for duplicate names
                if custom_name and custom_name in seen_names:
                    unique_name = _make_unique_name(custom_name, seen_names)
                    # Track update needed
                    if registry_path not in updates_needed:
                        updates_needed[registry_path] = {}
                    updates_needed[registry_path][stripped] = {
                        "new_line": f"{env_path}\t{unique_name}",
                        "path": env_path,
                        "type": source,
                        "old_name": custom_name,
                        "new_name": unique_name,
                    }
                    custom_name = unique_name

                if custom_name:
                    seen_names.add(custom_name)
                seen_paths.add(env_path)
                environments.append((env_path, custom_name))

        # Apply updates to registry files if needed
        for registry_path, updates in updates_needed.items():
            with open(registry_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped in updates:
                    new_lines.append(updates[stripped]["new_line"] + "\n")
                    updated_entries.append({
                        "path": updates[stripped]["path"],
                        "type": updates[stripped]["type"],
                        "old_name": updates[stripped]["old_name"],
                        "new_name": updates[stripped]["new_name"],
                    })
                else:
                    new_lines.append(line)

            with open(registry_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        return environments, updated_entries


def _get_all_custom_names() -> set:
    """Get all custom names currently in use across registries."""
    names = set()
    for registry_path in [get_venv_registry_path(), get_uv_registry_path()]:
        if not registry_path.exists():
            continue
        with open(registry_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    parts = stripped.split('\t', 1)
                    if len(parts) > 1:
                        names.add(parts[1])
    return names


def _make_unique_name(name: str, existing_names: set) -> str:
    """Make a name unique by appending _1, _2, etc. if needed."""
    if name not in existing_names:
        return name
    suffix = 1
    while f"{name}_{suffix}" in existing_names:
        suffix += 1
    return f"{name}_{suffix}"


def _has_kernelspec(env_path: str) -> bool:
    """Check if environment has a valid Jupyter kernelspec.

    Returns True if env_path/share/jupyter/kernels/*/kernel.json exists.
    """
    kernel_path = os.path.join(env_path, "share", "jupyter", "kernels")
    return _check_has_kernel(kernel_path)


def register_environment(env_path: str, name: Optional[str] = None,
                         require_kernelspec: bool = False) -> Tuple[bool, bool]:
    """Register an environment path in the appropriate registry.

    Auto-detects uv vs venv and writes to ~/.uv/ or ~/.venv/ accordingly.
    If already registered, updates the custom name if different.
    If custom name conflicts, appends suffix and warns to stderr.
    Thread/multiprocess safe using file locking.

    Args:
        env_path: Path to the environment directory (e.g., /path/to/.venv)
        name: Optional custom display name for the environment
        require_kernelspec: If True, only register environments with ipykernel installed

    Returns:
        Tuple of (registered, updated):
        - (True, False) if newly registered
        - (False, True) if already registered but name was updated
        - (False, False) if already registered with same name

    Raises:
        ValueError: If path doesn't exist, not a valid Python environment,
                   or (when require_kernelspec=True) doesn't have ipykernel installed.
    """
    import sys

    env_path = os.path.abspath(os.path.expanduser(env_path))

    if not os.path.isdir(env_path):
        raise ValueError(f"Environment path does not exist: {env_path}")

    # Check for bin/python or Scripts/python.exe (Windows)
    python_path = os.path.join(env_path, "bin", "python")
    python_path_win = os.path.join(env_path, "Scripts", "python.exe")
    if not os.path.exists(python_path) and not os.path.exists(python_path_win):
        raise ValueError(f"Not a valid Python environment: {env_path}")

    # Check for kernelspec (ipykernel must be installed) - only if required
    if require_kernelspec and not _has_kernelspec(env_path):
        raise ValueError(f"No kernelspec found (ipykernel not installed): {env_path}")

    # Detect source and use appropriate registry
    source = "uv" if is_uv_environment(env_path) else "venv"
    registry_path = get_registry_path(source)

    with _registry_lock():
        # Check if already registered (check both registries)
        for check_source, check_registry in [("venv", get_venv_registry_path()),
                                              ("uv", get_uv_registry_path())]:
            if not check_registry.exists():
                continue

            with open(check_registry, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                parts = stripped.split('\t', 1)
                existing_path = os.path.abspath(os.path.expanduser(parts[0]))
                existing_name = parts[1] if len(parts) > 1 else None

                if existing_path == env_path:
                    # Already registered - check if name needs updating
                    # If name is None, preserve existing name (no update)
                    if name is None or existing_name == name:
                        return (False, False)  # No change needed

                    # Check for name conflicts before updating
                    existing_names = _get_all_custom_names()
                    # Remove current name from set (we're updating this entry)
                    if existing_name:
                        existing_names.discard(existing_name)
                    unique_name = _make_unique_name(name, existing_names)
                    if unique_name != name:
                        print(f"Warning: Name '{name}' already in use, using '{unique_name}'", file=sys.stderr)

                    # Update the line with new name
                    lines[i] = f"{env_path}\t{unique_name}\n"

                    with open(check_registry, "w", encoding="utf-8") as f:
                        f.writelines(lines)
                    return (False, True)  # Updated name

        # Not registered - add new entry
        # Check for name conflicts if custom name provided
        final_name = name
        if name:
            existing_names = _get_all_custom_names()
            unique_name = _make_unique_name(name, existing_names)
            if unique_name != name:
                print(f"Warning: Name '{name}' already in use, using '{unique_name}'", file=sys.stderr)
            final_name = unique_name

        ensure_registry_dir(source)
        with open(registry_path, "a", encoding="utf-8") as f:
            if final_name:
                f.write(f"{env_path}\t{final_name}\n")
            else:
                f.write(env_path + "\n")

        return (True, False)  # Newly registered


def unregister_environment(env_path: str) -> bool:
    """Remove an environment path from both registries.

    Thread/multiprocess safe using file locking.

    Args:
        env_path: Path to the environment directory

    Returns:
        True if removed, False if not found.
    """
    env_path = os.path.abspath(os.path.expanduser(env_path))
    removed = False

    with _registry_lock():
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
                    # Parse tab-separated format: path[\tname]
                    parts = stripped.split('\t', 1)
                    path_part = parts[0]
                    normalized = os.path.abspath(os.path.expanduser(path_part))
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
        env_valid = is_valid_environment(env_path)
        kernel_path = os.path.join(env_path, "share", "jupyter", "kernels")
        has_kernel = _check_has_kernel(kernel_path) if env_valid else False
        environments.append({
            "path": env_path,
            "type": "venv",
            "exists": env_valid,
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
        env_valid = is_valid_environment(env_path)
        kernel_path = os.path.join(env_path, "share", "jupyter", "kernels")
        has_kernel = _check_has_kernel(kernel_path) if env_valid else False
        environments.append({
            "path": env_path,
            "type": "uv",
            "exists": env_valid,
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


def _load_scan_config() -> Dict:
    """Load scan configuration from JSON file."""
    config_path = Path(__file__).parent / "scan_config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"skip_directories": [], "exclude_path_patterns": []}


def _get_skip_directories() -> set:
    """Get set of directory names to skip during scan."""
    config = _load_scan_config()
    return set(config.get("skip_directories", []))


def _is_cache_path(path: str) -> bool:
    """Check if path matches any exclude pattern from config."""
    config = _load_scan_config()
    patterns = config.get("exclude_path_patterns", [])
    return any(pattern in path for pattern in patterns)


def cleanup_registries(require_kernelspec: bool = False) -> Dict[str, List[Dict[str, str]]]:
    """Remove invalid environments from both registries.

    Removes environments that:
    - Don't exist on disk
    - Are cache paths (uv cache directories)
    - Don't have a valid kernelspec (only when require_kernelspec=True)

    Args:
        require_kernelspec: If True, also remove environments without ipykernel installed

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

            # Remove if invalid or cache path
            is_valid = is_valid_environment(env_path) and not _is_cache_path(env_path)
            # Also check kernelspec only if required
            if require_kernelspec:
                is_valid = is_valid and _has_kernelspec(env_path)

            if is_valid:
                new_lines.append(line)
            else:
                removed.append({"path": env_path, "type": source, "custom_name": custom_name})

        # Write back if changed
        if len(new_lines) < len(lines):
            with open(registry_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

    return {"removed": removed}


def _has_python_executable(path: str) -> bool:
    """Check if path contains a Python executable (bin/python or Scripts/python.exe)."""
    python_path = os.path.join(path, "bin", "python")
    python_path_win = os.path.join(path, "Scripts", "python.exe")
    return os.path.exists(python_path) or os.path.exists(python_path_win)


def is_valid_environment(path: str) -> bool:
    """Check if path is a valid Python virtual environment (venv or uv).

    Returns True if path is a directory containing bin/python or Scripts/python.exe.
    """
    if not os.path.isdir(path):
        return False
    return _has_python_executable(path)


def is_valid_venv_environment(path: str) -> bool:
    """Check if path is a valid venv environment.

    A valid venv has:
    - Directory exists
    - Contains bin/python or Scripts/python.exe
    - Is NOT a uv environment (no uv marker in pyvenv.cfg)
    """
    if not os.path.isdir(path):
        return False
    if not _has_python_executable(path):
        return False
    # Must not be uv
    return not is_uv_environment(path)


def is_valid_uv_environment(path: str) -> bool:
    """Check if path is a valid uv environment.

    A valid uv environment has:
    - Directory exists
    - Contains bin/python or Scripts/python.exe
    - Has uv marker in pyvenv.cfg
    """
    if not os.path.isdir(path):
        return False
    if not _has_python_executable(path):
        return False
    return is_uv_environment(path)


def is_valid_conda_environment(path: str) -> bool:
    """Check if path is a valid conda environment.

    A valid conda environment has:
    - Directory exists
    - Contains conda-meta directory
    """
    if not os.path.isdir(path):
        return False
    return os.path.isdir(os.path.join(path, "conda-meta"))


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


def scan_directory(root_path: str, max_depth: int = 10,
                   dry_run: bool = False,
                   require_kernelspec: bool = False) -> Dict[str, List]:
    """Scan directory tree for virtual environments.

    Searches for venv, uv, and conda environments. Registers found
    environments in appropriate registries and cleans up non-existent ones.
    Also sanitizes duplicate names in registries.

    Args:
        root_path: Directory to start scanning from
        max_depth: Maximum depth to recurse (default: 10, None = unlimited)
        dry_run: If True, only report without making changes
        require_kernelspec: If True, only register environments with ipykernel installed.
                           Environments without kernelspec are reported in 'ignore' list.
                           If False (default), all valid environments are registered.

    Returns:
        Dict with 'registered', 'updated', 'skipped', 'ignore', 'conda_found', 'not_available' lists.
    """
    root_path = os.path.abspath(os.path.expanduser(root_path))

    if not os.path.isdir(root_path):
        raise ValueError(f"Directory does not exist: {root_path}")

    # Sanitize duplicate names in registries (updates registry in place)
    # This happens even in dry_run since it's fixing existing data, not adding new
    sanitized = sanitize_registry_names()
    sanitized_paths = {entry["path"] for entry in sanitized}

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
                        if not is_valid_environment(env_path):
                            not_available.append({"path": env_path, "type": source, "custom_name": custom_name})
    else:
        cleanup_result = cleanup_registries(require_kernelspec=require_kernelspec)
        not_available = cleanup_result["removed"]

    registered = []
    updated = []
    skipped = []
    ignore = []
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

            # Skip directories from config
            skip_dirs = _get_skip_directories()
            if entry in skip_dirs or entry.endswith(".egg-info"):
                continue

            # Skip uv cache path patterns
            if entry == "uv" and ("/share/" in current_path or current_path.endswith("share")):
                continue

            full_path = os.path.join(current_path, entry)

            if not os.path.isdir(full_path):
                continue

            # Check if this is a valid environment
            if is_valid_environment(full_path):
                if is_conda_environment(full_path):
                    conda_found.append(full_path)
                else:
                    # Check if environment has kernelspec (ipykernel installed)
                    has_kernel = _has_kernelspec(full_path)
                    if require_kernelspec and not has_kernel:
                        # Only ignore if require_kernelspec is True
                        ignore.append(full_path)
                    elif dry_run:
                        # In dry run, check if already registered
                        existing = read_environments()
                        if full_path in existing:
                            skipped.append(full_path)
                        else:
                            registered.append(full_path)
                    else:
                        # Try to register
                        try:
                            was_registered, was_updated = register_environment(
                                full_path, require_kernelspec=require_kernelspec
                            )
                            if was_registered:
                                registered.append(full_path)
                            elif was_updated:
                                updated.append(full_path)
                            else:
                                skipped.append(full_path)
                        except ValueError:
                            # Only happens if require_kernelspec=True and no kernel
                            ignore.append(full_path)
                # Don't recurse into environments
                continue

            # Recurse into subdirectory
            scan_recursive(full_path, depth + 1)

    scan_recursive(root_path, 0)

    # Add sanitized entries to updated list (name was changed due to duplicate)
    # and remove them from skipped if they were there
    for entry in sanitized:
        path = entry["path"]
        if path not in updated:
            updated.append(path)
        if path in skipped:
            skipped.remove(path)

    return {
        "registered": registered,
        "updated": updated,
        "skipped": skipped,
        "ignore": ignore,
        "not_available": not_available,
        "conda_found": conda_found,
    }
