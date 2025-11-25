try:
    from ._version import __version__
except ImportError:
    # Fallback when using the package in dev mode without installing
    # in editable mode with pip. It is highly recommended to install
    # the package from a stable release or in editable mode: https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs
    import warnings
    warnings.warn("Importing 'nb_venv_kernels' outside a proper installation.")
    __version__ = "dev"

from .manager import VEnvKernelSpecManager
from .routes import setup_route_handlers


def _jupyter_labextension_paths():
    return [{
        "src": "labextension",
        "dest": "nb_venv_kernels"
    }]


def _jupyter_server_extension_points():
    return [{
        "module": "nb_venv_kernels"
    }]


def _load_jupyter_server_extension(server_app):
    """Registers the API handler and configures the KernelSpecManager.

    Parameters
    ----------
    server_app: jupyterlab.labapp.LabApp
        JupyterLab application instance
    """
    log = server_app.log
    name = "nb_venv_kernels"

    log.info(f"{name} | Loading server extension...")

    setup_route_handlers(server_app.web_app)
    log.debug(f"{name} | Route handlers registered")

    # Configure KernelSpecManager to use VEnvKernelSpecManager
    # Note: This may not take effect if kernel_spec_manager is already instantiated
    server_app.kernel_spec_manager_class = VEnvKernelSpecManager
    log.info(f"{name} | Set kernel_spec_manager_class to VEnvKernelSpecManager")

    # Log registry status
    from .registry import get_registry_path, read_environments
    registry_path = get_registry_path()
    log.info(f"{name} | Registry path: {registry_path}")
    log.info(f"{name} | Registry exists: {registry_path.exists()}")

    envs = read_environments()
    log.info(f"{name} | Registered environments: {len(envs)}")
    for env in envs:
        log.debug(f"{name} |   - {env}")

    log.info(f"{name} | Server extension loaded successfully")
