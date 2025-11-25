# -*- coding: utf-8 -*-
"""CLI for nb_venv_kernels - register and manage venv/uv environments."""
import argparse
import json
import os
import sys

from .registry import (
    register_environment,
    unregister_environment,
    list_environments,
)


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


def update_jupyter_config(config_dir=None):
    """Update Jupyter config to use VEnvKernelSpecManager.

    Args:
        config_dir: Optional config directory. Auto-detected if not provided.

    Returns:
        Tuple of (config_path, was_updated, message)
    """
    if config_dir is None:
        config_dir = find_jupyter_config_dir()

    config_path = os.path.join(config_dir, "jupyter_config.json")
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

    Args:
        config_dir: Optional config directory. Auto-detected if not provided.

    Returns:
        Tuple of (config_path, was_updated, message)
    """
    if config_dir is None:
        config_dir = find_jupyter_config_dir()

    config_path = os.path.join(config_dir, "jupyter_config.json")
    manager_class = "nb_venv_kernels.VEnvKernelSpecManager"

    if not os.path.exists(config_path):
        return config_path, False, "Config file does not exist"

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except (json.JSONDecodeError, IOError):
        return config_path, False, "Could not read config file"

    modified = False

    # Remove our manager if it's set
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
  list                List all registered environments
  config enable       Enable VEnvKernelSpecManager in Jupyter config
  config disable      Disable VEnvKernelSpecManager in Jupyter config
  config show         Show current config location and status

Examples:
  nb_venv_kernels register /path/to/.venv
  nb_venv_kernels list
  nb_venv_kernels config enable
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
            print("No environments registered.")
            print("Use 'nb_venv_kernels register <path>' to register an environment.")
        else:
            print(f"{'PATH':<60} {'EXISTS':<8} {'KERNEL':<8}")
            print("-" * 76)
            for env in envs:
                exists = "yes" if env["exists"] else "NO"
                kernel = "yes" if env["has_kernel"] else "no"
                print(f"{env['path']:<60} {exists:<8} {kernel:<8}")
        print()

    elif args.command == "config":
        if args.action == "enable":
            config_path, updated, message = update_jupyter_config(args.path)
            if updated:
                print(f"Configured: {config_path}")
                print("Restart JupyterLab for changes to take effect.")
            else:
                print(f"{message}: {config_path}")
            print()

        elif args.action == "disable":
            config_path, updated, message = remove_jupyter_config(args.path)
            if updated:
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
