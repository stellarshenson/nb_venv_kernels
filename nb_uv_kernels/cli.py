# -*- coding: utf-8 -*-
"""CLI for nb_uv_kernels - register and manage uv/venv environments."""
import argparse
import sys

from .registry import (
    register_environment,
    unregister_environment,
    list_environments,
)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="nb_uv_kernels",
        description="Manage uv/venv environments for Jupyter kernel discovery.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

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

    args = parser.parse_args()

    if args.command == "register":
        try:
            if register_environment(args.path):
                print(f"Registered: {args.path}")
            else:
                print(f"Already registered: {args.path}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "unregister":
        if unregister_environment(args.path):
            print(f"Unregistered: {args.path}")
        else:
            print(f"Not found in registry: {args.path}")

    elif args.command == "list":
        envs = list_environments()
        if not envs:
            print("No environments registered.")
            print("Use 'nb_uv_kernels register <path>' to register an environment.")
        else:
            print(f"{'PATH':<60} {'EXISTS':<8} {'KERNEL':<8}")
            print("-" * 76)
            for env in envs:
                exists = "yes" if env["exists"] else "NO"
                kernel = "yes" if env["has_kernel"] else "no"
                print(f"{env['path']:<60} {exists:<8} {kernel:<8}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
