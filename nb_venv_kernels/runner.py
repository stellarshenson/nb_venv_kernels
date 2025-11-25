# -*- coding: utf-8 -*-
"""Runner script for launching kernels in uv/venv environments.

This module activates a virtual environment and executes the kernel command.
Called by Jupyter with: python -m nb_venv_kernels.runner <env_path> <command...>
"""
from __future__ import print_function

import os
import sys
import subprocess

try:
    from shlex import quote
except ImportError:
    from pipes import quote


def exec_in_env(env_path, *command):
    """Activate environment and execute command.

    Args:
        env_path: Path to the virtual environment
        command: Command and arguments to execute
    """
    is_current_env = env_path == sys.prefix

    if sys.platform.startswith("win"):
        # Windows: use Scripts/activate.bat
        if is_current_env:
            subprocess.Popen(list(command)).wait()
        else:
            activate = os.path.join(env_path, "Scripts", "activate.bat")
            ecomm = [
                os.environ["COMSPEC"],
                "/S", "/U", "/C",
                "@echo", "off", "&&",
                "chcp", "65001", "&&",
                "call", activate, "&&",
            ] + list(command)
            subprocess.Popen(ecomm).wait()
    else:
        # Unix: source bin/activate
        quoted_command = [quote(c) for c in command]

        if is_current_env:
            os.execvp(command[0], command)
        else:
            activate = os.path.join(env_path, "bin", "activate")
            # Deactivate conda first if active, then activate venv
            deactivate_conda = (
                "unset CONDA_PREFIX CONDA_DEFAULT_ENV CONDA_PROMPT_MODIFIER "
                "CONDA_SHLVL CONDA_PYTHON_EXE CONDA_EXE; "
                "export PATH=$(echo $PATH | sed -e 's|[^:]*conda[^:]*:||g'); "
            )
            ecomm = "{} . '{}' && exec {}".format(
                deactivate_conda, activate, " ".join(quoted_command)
            )
            shell = "sh" if "bsd" in sys.platform else "bash"
            os.execvp(shell, [shell, "-c", ecomm])


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m nb_venv_kernels.runner <env_path> <command...>", file=sys.stderr)
        sys.exit(1)

    env_path = sys.argv[1]
    command = sys.argv[2:]

    exec_in_env(env_path, *command)
