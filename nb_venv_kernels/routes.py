import json
import os

from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join
import tornado

from .manager import (
    VEnvKernelSpecManager,
    get_workspace_root,
    is_path_within_workspace,
    path_relative_to_workspace,
)
from .registry import is_global_conda_environment


def get_venv_manager(handler):
    """Get VEnvKernelSpecManager, using server's instance if available.

    Uses server's kernel_spec_manager if it's a VEnvKernelSpecManager,
    otherwise creates a new instance (for testing or non-configured servers).
    """
    ksm = handler.kernel_spec_manager
    if isinstance(ksm, VEnvKernelSpecManager):
        return ksm
    # Fallback for tests or when not configured as kernel_spec_manager_class
    return VEnvKernelSpecManager()


class ListEnvironmentsHandler(APIHandler):
    """List all registered environments."""

    @tornado.web.authenticated
    def get(self):
        # Use server's kernel spec manager for immediate cache coherence
        manager = get_venv_manager(self)
        envs = manager.list_environments()
        # Use server's root_dir setting, fall back to get_workspace_root()
        workspace = self.settings.get("server_root_dir") or get_workspace_root()
        workspace = os.path.expanduser(workspace)  # Expand ~ if present

        # Convert paths to relative
        for env in envs:
            env["path"] = path_relative_to_workspace(env["path"], workspace)

        self.finish(json.dumps({
            "environments": envs,
            "workspace_root": workspace,
        }))


class ScanEnvironmentsHandler(APIHandler):
    """Scan directory for environments."""

    @tornado.web.authenticated
    def post(self):
        data = self.get_json_body() or {}
        # Use server's root_dir setting, fall back to get_workspace_root()
        workspace = self.settings.get("server_root_dir") or get_workspace_root()
        workspace = os.path.expanduser(workspace)  # Expand ~ if present
        path = os.path.expanduser(data.get("path", workspace))
        depth = data.get("depth")
        dry_run = data.get("dry_run", False)

        # Validate path is within workspace
        if not is_path_within_workspace(path, workspace):
            self.set_status(400)
            self.finish(json.dumps({
                "error": f"Scan path must be within workspace: {workspace}"
            }))
            return

        # Use server's kernel spec manager for immediate cache coherence
        manager = get_venv_manager(self)
        result = manager.scan_environments(path=path, max_depth=depth, dry_run=dry_run)

        # Convert paths to relative
        for env in result.get("environments", []):
            env["path"] = path_relative_to_workspace(env["path"], workspace)

        result["workspace_root"] = workspace
        self.finish(json.dumps(result))


class RegisterEnvironmentHandler(APIHandler):
    """Register an environment."""

    @tornado.web.authenticated
    def post(self):
        data = self.get_json_body() or {}
        path = data.get("path")

        if not path:
            self.set_status(400)
            self.finish(json.dumps({"error": "path is required"}))
            return

        # Expand and resolve path
        path = os.path.abspath(os.path.expanduser(path))

        # Validate path is within workspace (global conda environments exempt)
        workspace = self.settings.get("server_root_dir") or get_workspace_root()
        workspace = os.path.expanduser(workspace)
        if not is_path_within_workspace(path, workspace) and not is_global_conda_environment(path):
            self.set_status(400)
            self.finish(json.dumps({
                "error": f"Environment path must be within workspace: {workspace}"
            }))
            return

        # Use server's kernel spec manager for immediate cache coherence
        manager = get_venv_manager(self)
        result = manager.register_environment(path)
        self.finish(json.dumps(result))


class UnregisterEnvironmentHandler(APIHandler):
    """Unregister an environment."""

    @tornado.web.authenticated
    def post(self):
        data = self.get_json_body() or {}
        path = data.get("path")

        if not path:
            self.set_status(400)
            self.finish(json.dumps({"error": "path is required"}))
            return

        # Use server's kernel spec manager for immediate cache coherence
        manager = get_venv_manager(self)
        result = manager.unregister_environment(path)
        self.finish(json.dumps(result))


def setup_route_handlers(web_app):
    host_pattern = ".*$"
    base_url = web_app.settings["base_url"]

    handlers = [
        (url_path_join(base_url, "nb-venv-kernels", "environments"), ListEnvironmentsHandler),
        (url_path_join(base_url, "nb-venv-kernels", "scan"), ScanEnvironmentsHandler),
        (url_path_join(base_url, "nb-venv-kernels", "register"), RegisterEnvironmentHandler),
        (url_path_join(base_url, "nb-venv-kernels", "unregister"), UnregisterEnvironmentHandler),
    ]

    web_app.add_handlers(host_pattern, handlers)
