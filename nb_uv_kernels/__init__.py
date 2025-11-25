try:
    from ._version import __version__
except ImportError:
    # Fallback when using the package in dev mode without installing
    # in editable mode with pip. It is highly recommended to install
    # the package from a stable release or in editable mode: https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs
    import warnings
    warnings.warn("Importing 'nb_uv_kernels' outside a proper installation.")
    __version__ = "dev"

from .manager import UvKernelSpecManager
from .routes import setup_route_handlers


def _jupyter_labextension_paths():
    return [{
        "src": "labextension",
        "dest": "nb_uv_kernels"
    }]


def _jupyter_server_extension_points():
    return [{
        "module": "nb_uv_kernels"
    }]


def _load_jupyter_server_extension(server_app):
    """Registers the API handler and configures the KernelSpecManager.

    Parameters
    ----------
    server_app: jupyterlab.labapp.LabApp
        JupyterLab application instance
    """
    setup_route_handlers(server_app.web_app)

    # Configure KernelSpecManager to use UvKernelSpecManager
    server_app.kernel_spec_manager_class = UvKernelSpecManager

    name = "nb_uv_kernels"
    server_app.log.info(f"Registered {name} server extension")
