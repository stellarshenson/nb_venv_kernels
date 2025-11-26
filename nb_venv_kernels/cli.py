# -*- coding: utf-8 -*-
"""CLI for nb_venv_kernels - register and manage venv/uv environments."""
import argparse
import json
import os
import sys
import threading
import time

from .registry import (
    register_environment,
    unregister_environment,
    list_environments,
    cleanup_registries,
    scan_directory,
)


class Spinner:
    """Animated spinner for long-running operations."""

    def __init__(self, message: str = "Scanning"):
        self.message = message
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.running = False
        self.thread = None

    def _spin(self):
        idx = 0
        while self.running:
            frame = self.frames[idx % len(self.frames)]
            sys.stderr.write(f"\r{frame} {self.message}...")
            sys.stderr.flush()
            idx += 1
            time.sleep(0.1)

    def start(self):
        # Only show spinner if stderr is a terminal
        if not sys.stderr.isatty():
            return
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self, final_message: str = None):
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)
        # Clear the spinner line completely
        if sys.stderr.isatty():
            sys.stderr.write("\r" + " " * 80 + "\r")
            sys.stderr.flush()
        if final_message:
            print(final_message)


def _is_conda_global(env_path: str) -> bool:
    """Check if conda environment is global (base installation)."""
    basename = os.path.basename(env_path).lower()
    base_names = {"conda", "anaconda", "anaconda3", "miniconda", "miniconda3",
                  "miniforge", "miniforge3", "mambaforge", "mambaforge3"}
    return basename in base_names


def _get_env_display_name(env_path: str, env_type: str) -> str:
    """Get display name for an environment.

    For venv/uv: use parent directory name (project name)
    For conda base: use 'base'
    For conda envs: use the env directory name
    """
    basename = os.path.basename(env_path)

    # For venv/uv, common venv folder names -> use parent (project) name
    if env_type in ("venv", "uv"):
        if basename in (".venv", "venv", ".env", "env", ".virtualenv", "virtualenv"):
            return os.path.basename(os.path.dirname(env_path))
        return basename

    # For conda
    if env_type == "conda":
        if _is_conda_global(env_path):
            return "base"
        return basename

    return basename


def _get_env_type_display(env_path: str, env_type: str) -> str:
    """Get display type for an environment."""
    if env_type == "conda":
        if _is_conda_global(env_path):
            return "conda (global)"
        return "conda (local)"
    return env_type


def _get_configured_scan_depth() -> int:
    """Get scan_depth from Jupyter config, default 7."""
    try:
        from .manager import VEnvKernelSpecManager
        manager = VEnvKernelSpecManager()
        return manager.scan_depth
    except Exception:
        return 7


def find_jupyter_config_dir():
    """Find the Jupyter config directory.

    Returns the first existing config directory from standard locations,
    or the conda prefix config if running in conda.
    """
    # Check JUPYTER_CONFIG_DIR environment variable first
    env_config = os.environ.get("JUPYTER_CONFIG_DIR")
    if env_config and os.path.isdir(env_config):
        return env_config

    # Check conda prefix (common in JupyterHub/Lab installations)
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        conda_config = os.path.join(conda_prefix, "etc", "jupyter")
        if os.path.isdir(conda_config):
            return conda_config

    # Standard locations
    candidates = [
        "/opt/conda/etc/jupyter",  # Common JupyterHub location
        os.path.expanduser("~/.jupyter"),
        "/usr/local/etc/jupyter",
        "/etc/jupyter",
    ]

    for path in candidates:
        if os.path.isdir(path):
            return path

    # Fall back to user directory (create if needed)
    return os.path.expanduser("~/.jupyter")


def get_backup_path(config_path):
    """Get backup file path for config."""
    return config_path + ".nb_venv_kernels.bak"


def update_jupyter_config(config_dir=None):
    """Update Jupyter config to use VEnvKernelSpecManager.

    Backs up existing config before making changes.

    Args:
        config_dir: Optional config directory. Auto-detected if not provided.

    Returns:
        Tuple of (config_path, was_updated, message)
    """
    if config_dir is None:
        config_dir = find_jupyter_config_dir()

    config_path = os.path.join(config_dir, "jupyter_config.json")
    backup_path = get_backup_path(config_path)
    manager_class = "nb_venv_kernels.VEnvKernelSpecManager"

    # Load existing config or start fresh
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError):
            config = {}

    # Check current settings
    notebook_class = config.get("NotebookApp", {}).get("kernel_spec_manager_class")
    server_class = config.get("ServerApp", {}).get("kernel_spec_manager_class")

    if notebook_class == manager_class and server_class == manager_class:
        return config_path, False, "Already configured"

    # Backup existing config before modifying (only if not already our config)
    if os.path.exists(config_path) and notebook_class != manager_class:
        try:
            import shutil
            shutil.copy2(config_path, backup_path)
        except IOError:
            pass  # Best effort backup

    # Update config
    if "NotebookApp" not in config:
        config["NotebookApp"] = {}
    if "ServerApp" not in config:
        config["ServerApp"] = {}

    config["NotebookApp"]["kernel_spec_manager_class"] = manager_class
    config["ServerApp"]["kernel_spec_manager_class"] = manager_class

    # Create directory if needed
    os.makedirs(config_dir, exist_ok=True)

    # Write config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    return config_path, True, "Updated"


def remove_jupyter_config(config_dir=None):
    """Remove VEnvKernelSpecManager from Jupyter config.

    Restores from backup if available, otherwise removes our settings.

    Args:
        config_dir: Optional config directory. Auto-detected if not provided.

    Returns:
        Tuple of (config_path, was_updated, message)
    """
    if config_dir is None:
        config_dir = find_jupyter_config_dir()

    config_path = os.path.join(config_dir, "jupyter_config.json")
    backup_path = get_backup_path(config_path)
    manager_class = "nb_venv_kernels.VEnvKernelSpecManager"

    if not os.path.exists(config_path):
        return config_path, False, "Config file does not exist"

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except (json.JSONDecodeError, IOError):
        return config_path, False, "Could not read config file"

    # Check if we're configured
    notebook_class = config.get("NotebookApp", {}).get("kernel_spec_manager_class")
    server_class = config.get("ServerApp", {}).get("kernel_spec_manager_class")

    if notebook_class != manager_class and server_class != manager_class:
        return config_path, False, "VEnvKernelSpecManager not configured"

    # Try to restore from backup first
    if os.path.exists(backup_path):
        try:
            import shutil
            shutil.copy2(backup_path, config_path)
            os.remove(backup_path)
            return config_path, True, "Restored from backup"
        except IOError:
            pass  # Fall through to manual removal

    # No backup - manually remove our settings
    modified = False
    for app in ["NotebookApp", "ServerApp"]:
        if app in config and config[app].get("kernel_spec_manager_class") == manager_class:
            del config[app]["kernel_spec_manager_class"]
            modified = True
            # Clean up empty dicts
            if not config[app]:
                del config[app]

    if not modified:
        return config_path, False, "VEnvKernelSpecManager not configured"

    # Write updated config
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

    return config_path, True, "Removed"


def print_help():
    """Print rich help output."""
    print("""nb_venv_kernels - Jupyter kernel discovery for uv/venv environments

Usage:
  nb_venv_kernels <command> [options]

Commands:
  register <path>     Register an environment for kernel discovery
  unregister <path>   Remove an environment from kernel discovery
  scan [path]         Scan directory for environments and register them
  list                List all registered environments
  config enable       Enable VEnvKernelSpecManager in Jupyter config
  config disable      Disable VEnvKernelSpecManager in Jupyter config
  config show         Show current config location and status

Options:
  scan --depth N      Maximum directory depth to scan (default: 5)

Notes:
  - scan and register also cleanup non-existent environments from registries
  - conda environments found during scan are reported but not registered
    (they are discovered automatically via conda env list)

Examples:
  nb_venv_kernels scan                    # Scan current directory
  nb_venv_kernels scan /path/to/projects  # Scan specific directory
  nb_venv_kernels scan --depth 3          # Limit scan depth
  nb_venv_kernels register /path/to/.venv
  nb_venv_kernels list
""")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="nb_venv_kernels",
        description="Manage uv/venv environments for Jupyter kernel discovery.",
        add_help=False,
    )
    parser.add_argument(
        "-h", "--help",
        action="store_true",
        help="Show this help message",
    )

    subparsers = parser.add_subparsers(dest="command")

    # register command
    register_parser = subparsers.add_parser(
        "register",
        help="Register an environment for kernel discovery",
    )
    register_parser.add_argument(
        "path",
        help="Path to the environment directory (e.g., .venv or /path/to/.venv)",
    )

    # unregister command
    unregister_parser = subparsers.add_parser(
        "unregister",
        help="Remove an environment from kernel discovery",
    )
    unregister_parser.add_argument(
        "path",
        help="Path to the environment directory",
    )

    # list command
    subparsers.add_parser(
        "list",
        help="List all registered environments",
    )

    # scan command
    scan_parser = subparsers.add_parser(
        "scan",
        help="Scan directory for environments and register them",
    )
    scan_parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory)",
    )
    scan_parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help="Maximum directory depth to scan (default: from config, usually 5)",
    )

    # config command
    config_parser = subparsers.add_parser(
        "config",
        help="Manage Jupyter configuration",
    )
    config_parser.add_argument(
        "action",
        choices=["enable", "disable", "show"],
        help="enable/disable/show VEnvKernelSpecManager config",
    )
    config_parser.add_argument(
        "--path",
        help="Custom config directory path",
        default=None,
    )

    args = parser.parse_args()

    if args.help or args.command is None:
        print_help()
        sys.exit(0)

    if args.command == "register":
        # Cleanup non-existent environments first
        cleanup_result = cleanup_registries()
        if cleanup_result["removed"]:
            print("Cleaned up non-existent environments:")
            for path in cleanup_result["removed"]:
                print(f"  - {path}")
            print()

        try:
            if register_environment(args.path):
                print(f"Registered: {args.path}")
            else:
                print(f"Already registered: {args.path}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print()

    elif args.command == "unregister":
        if unregister_environment(args.path):
            print(f"Unregistered: {args.path}")
        else:
            print(f"Not found in registry: {args.path}")
        print()

    elif args.command == "list":
        envs = list_environments()
        if not envs:
            print("No environments found.")
            print("Use 'nb_venv_kernels register <path>' or 'nb_venv_kernels scan' to add environments.")
        else:
            # Sort: conda global first, then conda local, uv, venv; by name within each
            def sort_key(e):
                env_type = e.get("type", "venv")
                name = _get_env_display_name(e["path"], env_type).lower()
                if env_type == "conda":
                    if _is_conda_global(e["path"]):
                        return (0, name)  # conda global first
                    return (1, name)  # conda local
                elif env_type == "uv":
                    return (2, name)
                else:
                    return (3, name)  # venv

            envs.sort(key=sort_key)

            print(f"{'NAME':<25} {'TYPE':<16} {'EXISTS':<8} {'KERNEL':<8} {'PATH'}")
            print("-" * 110)
            for env in envs:
                name = _get_env_display_name(env['path'], env.get("type", "venv"))
                env_type = _get_env_type_display(env['path'], env.get("type", "venv"))
                exists = "yes" if env["exists"] else "NO"
                kernel = "yes" if env["has_kernel"] else "no"
                print(f"{name:<25} {env_type:<16} {exists:<8} {kernel:<8} {env['path']}")
        print()

    elif args.command == "scan":
        scan_path = os.path.abspath(args.path)
        # Use configured depth if not specified via CLI
        depth = args.depth if args.depth is not None else _get_configured_scan_depth()
        spinner = Spinner(f"Scanning {scan_path}")

        try:
            spinner.start()
            result = scan_directory(scan_path, max_depth=depth)
            spinner.stop()
        except ValueError as e:
            spinner.stop()
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Report removed (non-existent) environments
        if result["removed"]:
            print("Removed non-existent environments:")
            for path in result["removed"]:
                print(f"  - {path}")
            print()

        # Report newly registered environments in a table
        if result["registered"]:
            print(f"{'REGISTERED':<60} {'TYPE':<8}")
            print("-" * 68)
            for path in result["registered"]:
                # Detect type
                from .registry import is_uv_environment
                env_type = "uv" if is_uv_environment(path) else "venv"
                print(f"{path:<60} {env_type:<8}")
            print()

        # Report conda environments found (not registered)
        if result["conda_found"]:
            print("Conda environments found (discovered automatically via conda):")
            for path in result["conda_found"]:
                print(f"  - {path}")
            print()

        # Summary
        total = len(result["registered"])
        removed = len(result["removed"])
        conda = len(result["conda_found"])

        if total == 0 and removed == 0 and conda == 0:
            print("No new environments found.")
        else:
            parts = []
            if total > 0:
                parts.append(f"{total} registered")
            if removed > 0:
                parts.append(f"{removed} removed")
            if conda > 0:
                parts.append(f"{conda} conda found")
            print(f"Summary: {', '.join(parts)}")
        print()

    elif args.command == "config":
        if args.action == "enable":
            config_path, updated, message = update_jupyter_config(args.path)
            if updated:
                print(f"Configured: {config_path}")
                backup_path = get_backup_path(config_path)
                if os.path.exists(backup_path):
                    print(f"Backup saved: {backup_path}")
                print("Restart JupyterLab for changes to take effect.")
            else:
                print(f"{message}: {config_path}")
            print()

        elif args.action == "disable":
            config_path, updated, message = remove_jupyter_config(args.path)
            if updated:
                if message == "Restored from backup":
                    print(f"Restored: {config_path}")
                else:
                    print(f"Removed from: {config_path}")
                print("Restart JupyterLab for changes to take effect.")
            else:
                print(f"{message}: {config_path}")
            print()

        elif args.action == "show":
            config_dir = args.path or find_jupyter_config_dir()
            config_path = os.path.join(config_dir, "jupyter_config.json")
            print(f"Config directory: {config_dir}")
            print(f"Config file: {config_path}")

            if os.path.exists(config_path):
                try:
                    with open(config_path, "r") as f:
                        config = json.load(f)
                    manager = config.get("ServerApp", {}).get("kernel_spec_manager_class", "not set")
                    print(f"kernel_spec_manager_class: {manager}")
                except (json.JSONDecodeError, IOError):
                    print("Status: Could not read config file")
            else:
                print("Status: Config file does not exist")
            print()

    else:
        print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
