# -*- coding: utf-8 -*-
"""CLI for nb_venv_kernels - register and manage venv/uv environments."""
import argparse
import json
import os
import sys
import threading
import time

from .manager import VEnvKernelSpecManager


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = "\033[32m"
    BLUE = "\033[94m"
    ORANGE = "\033[38;5;208m"
    RED = "\033[31m"
    RESET = "\033[0m"

    @classmethod
    def enabled(cls) -> bool:
        """Check if colors should be used."""
        return sys.stdout.isatty()

    @classmethod
    def red(cls, text: str) -> str:
        """Return text in red if colors enabled."""
        if cls.enabled():
            return f"{cls.RED}{text}{cls.RESET}"
        return text

    @classmethod
    def green(cls, text: str) -> str:
        return f"{cls.GREEN}{text}{cls.RESET}" if cls.enabled() else text

    @classmethod
    def blue(cls, text: str) -> str:
        return f"{cls.BLUE}{text}{cls.RESET}" if cls.enabled() else text

    @classmethod
    def orange(cls, text: str) -> str:
        return f"{cls.ORANGE}{text}{cls.RESET}" if cls.enabled() else text


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
            return "conda"
        return "conda (local)"
    return env_type


def _relative_path(path: str, base: str = None) -> str:
    """Convert absolute path to relative path for display."""
    from pathlib import Path
    if base is None:
        base = Path.cwd()
    else:
        base = Path(base)
    try:
        return str(Path(path).relative_to(base.resolve()))
    except ValueError:
        # Path is not relative to base, use os.path.relpath as fallback
        try:
            return os.path.relpath(path, str(base))
        except ValueError:
            # On Windows, relpath fails for paths on different drives
            return path


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
  scan --depth N      Maximum directory depth to scan (default: 7)
  scan --no-update    Dry run: scan and report without changes

Notes:
  - scan and register also cleanup non-existent environments from registries
  - conda environments found during scan are reported but not registered
    (they are discovered automatically via conda env list)

Examples:
  nb_venv_kernels scan                    # Scan current directory
  nb_venv_kernels scan /path/to/projects  # Scan specific directory
  nb_venv_kernels scan --depth 3          # Limit scan depth
  nb_venv_kernels scan --no-update        # Dry run mode
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
    register_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
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
    list_parser = subparsers.add_parser(
        "list",
        help="List all registered environments",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
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
        help="Maximum directory depth to scan (default: from config, usually 7)",
    )
    scan_parser.add_argument(
        "--no-update",
        action="store_true",
        help="Dry run: scan and report without registering or removing",
    )
    scan_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
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

    # Create manager instance for all commands
    manager = VEnvKernelSpecManager()

    if args.command == "register":
        result = manager.register_environment(args.path)

        if getattr(args, 'json', False):
            print(json.dumps(result, indent=2))
        else:
            if result.get("error"):
                print(f"Error: {result['error']}", file=sys.stderr)
                sys.exit(1)
            elif result["registered"]:
                print(f"Registered: {result['path']}")
            else:
                print(f"Already registered: {result['path']}")
            print()

    elif args.command == "unregister":
        result = manager.unregister_environment(args.path)
        if result["unregistered"]:
            print(f"Unregistered: {result['path']}")
        else:
            print(f"Not found in registry: {result['path']}")
        print()

    elif args.command == "list":
        envs = manager.list_environments()

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

        if getattr(args, 'json', False):
            # JSON output
            output = []
            for env in envs:
                output.append({
                    "name": _get_env_display_name(env['path'], env.get("type", "venv")),
                    "type": _get_env_type_display(env['path'], env.get("type", "venv")),
                    "exists": env["exists"],
                    "has_kernel": env["has_kernel"],
                    "path": env["path"],
                })
            print(json.dumps(output, indent=2))
        elif not envs:
            print("No environments found.")
            print("Use 'nb_venv_kernels register <path>' or 'nb_venv_kernels scan' to add environments.")
        else:
            print()
            print(f"{'name':<25} {'type':<16} {'exists':<8} {'kernel':<8} {'path'}")
            print("-" * 110)
            for env in envs:
                name = _get_env_display_name(env['path'], env.get("type", "venv"))
                env_type = _get_env_type_display(env['path'], env.get("type", "venv"))
                exists = "yes" if env["exists"] else Colors.red("no") + " " * 6
                kernel = "yes" if env["has_kernel"] else Colors.red("no") + " " * 6
                # Use relative path except for conda global
                if env.get("type") == "conda" and _is_conda_global(env['path']):
                    display_path = env['path']
                else:
                    display_path = _relative_path(env['path'])
                print(f"{name:<25} {env_type:<16} {exists:<8} {kernel:<8} {display_path}")
        print()

    elif args.command == "scan":
        scan_path = os.path.abspath(args.path)
        # Use configured depth if not specified via CLI
        depth = args.depth if args.depth is not None else manager.scan_depth
        dry_run = getattr(args, 'no_update', False)
        json_output = getattr(args, 'json', False)

        # No spinner for JSON output (machine-to-machine)
        spinner = None if json_output else Spinner(f"Scanning {scan_path}")

        try:
            if spinner:
                spinner.start()
            result = manager.scan_environments(scan_path, max_depth=depth, dry_run=dry_run)
            if spinner:
                spinner.stop()
        except ValueError as e:
            if spinner:
                spinner.stop()
            if json_output:
                print(json.dumps({"error": str(e)}))
            else:
                print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Sort environments by action order, then by type order, then by name
        action_order = {"add": 0, "keep": 1, "remove": 2}
        type_order = {"conda": 0, "uv": 1, "venv": 2}

        def sort_key(env):
            return (
                action_order.get(env["action"], 3),
                type_order.get(env["type"], 3),
                env["name"].lower()
            )

        environments = sorted(result["environments"], key=sort_key)

        def colorize_action(action):
            if action == "add":
                return Colors.green(action)
            elif action == "keep":
                return Colors.blue(action)
            elif action == "remove":
                return Colors.orange(action)
            return action

        # Summary counts
        total_add = result["summary"]["add"]
        total_keep = result["summary"]["keep"]
        total_remove = result["summary"]["remove"]

        if json_output:
            # Output result directly - manager already builds the right structure
            output = {
                "environments": environments,
                "summary": result["summary"],
                "dry_run": dry_run,
            }
            print(json.dumps(output, indent=2))
        else:
            if environments:
                print()
                print(f"{'action':<10} {'name':<25} {'type':<16} {'exists':<8} {'kernel':<8} {'path'}")
                print("-" * 130)
                for env in environments:
                    # Pad action before colorizing to maintain alignment
                    action_colored = colorize_action(env["action"]) + " " * (10 - len(env["action"]))
                    exists_str = "yes" if env["exists"] else Colors.red("no") + " " * 6
                    kernel_str = "yes" if env["has_kernel"] else Colors.red("no") + " " * 6
                    # Use relative path except for conda global
                    if env["type"] == "conda" and _is_conda_global(env["path"]):
                        display_path = env["path"]
                    else:
                        display_path = _relative_path(env["path"])
                    print(f"{action_colored} {env['name']:<25} {env['type']:<16} {exists_str:<8} {kernel_str:<8} {display_path}")
                print()

            if total_add == 0 and total_keep == 0 and total_remove == 0:
                print("No environments found.")
            else:
                parts = []
                # Use past tense for actual changes, present for dry run
                if dry_run:
                    if total_add > 0:
                        parts.append(f"{total_add} add")
                    if total_keep > 0:
                        parts.append(f"{total_keep} keep")
                    if total_remove > 0:
                        parts.append(f"{total_remove} remove")
                    summary = f"Summary: {', '.join(parts)} (no changes made)"
                else:
                    if total_add > 0:
                        parts.append(f"{total_add} added")
                    if total_keep > 0:
                        parts.append(f"{total_keep} kept")
                    if total_remove > 0:
                        parts.append(f"{total_remove} removed")
                    summary = f"Summary: {', '.join(parts)}"
                print(summary)
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
