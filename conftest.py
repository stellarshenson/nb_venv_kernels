from pathlib import Path

import pytest

pytest_plugins = ("pytest_jupyter.jupyter_server", )


@pytest.fixture(autouse=True)
def _scratch_home(tmp_path, monkeypatch):
    """Registries, their lock and the name cache resolve under a per-test directory."""
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))


@pytest.fixture
def jp_server_config(jp_server_config):
    return {
        "ServerApp": {
            "jpserver_extensions": {"nb_venv_kernels": True},
            # Test against a server which requires authentication on all endpoints
            "allow_unauthenticated_access": False,
        }
    }
