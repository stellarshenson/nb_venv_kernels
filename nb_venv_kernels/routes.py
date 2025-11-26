import json
import os

from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join
import tornado

from .manager import VEnvKernelSpecManager


class ListEnvironmentsHandler(APIHandler):
    """List all registered environments."""

    @tornado.web.authenticated
    def get(self):
        manager = VEnvKernelSpecManager()
        envs = manager.list_environments()
        self.finish(json.dumps(envs))


class ScanEnvironmentsHandler(APIHandler):
    """Scan directory for environments."""

    @tornado.web.authenticated
    def post(self):
        data = self.get_json_body() or {}
        path = data.get("path", os.getcwd())
        depth = data.get("depth")
        dry_run = data.get("dry_run", False)

        manager = VEnvKernelSpecManager()
        result = manager.scan_environments(path=path, max_depth=depth, dry_run=dry_run)
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

        manager = VEnvKernelSpecManager()
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

        manager = VEnvKernelSpecManager()
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
