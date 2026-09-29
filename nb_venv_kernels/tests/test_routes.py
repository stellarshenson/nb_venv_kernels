import json

import pytest
from tornado.httpclient import HTTPClientError


async def test_list_environments(jp_fetch):
    """Test listing environments endpoint."""
    response = await jp_fetch("nb-venv-kernels", "environments")

    assert response.code == 200
    payload = json.loads(response.body)
    assert isinstance(payload, dict)
    assert "environments" in payload
    assert "workspace_root" in payload
    assert isinstance(payload["environments"], list)


async def test_scan_environments(jp_fetch):
    """Test scan environments endpoint."""
    response = await jp_fetch(
        "nb-venv-kernels", "scan",
        method="POST",
        body=json.dumps({"dry_run": True})
    )

    assert response.code == 200
    payload = json.loads(response.body)
    assert "environments" in payload
    assert "summary" in payload
    assert "dry_run" in payload
    assert payload["dry_run"] is True


async def test_register_missing_path(jp_fetch):
    """Test register endpoint requires path."""
    with pytest.raises(HTTPClientError) as exc_info:
        await jp_fetch(
            "nb-venv-kernels", "register",
            method="POST",
            body=json.dumps({})
        )

    assert exc_info.value.code == 400


async def test_unregister_missing_path(jp_fetch):
    """Test unregister endpoint requires path."""
    with pytest.raises(HTTPClientError) as exc_info:
        await jp_fetch(
            "nb-venv-kernels", "unregister",
            method="POST",
            body=json.dumps({})
        )

    assert exc_info.value.code == 400


async def test_register_outside_workspace_denied(jp_fetch):
    """Test that registering environments outside workspace is denied."""
    with pytest.raises(HTTPClientError) as exc_info:
        await jp_fetch(
            "nb-venv-kernels", "register",
            method="POST",
            body=json.dumps({"path": "/tmp/fake-venv"})
        )

    assert exc_info.value.code == 400
    # Response body should mention workspace restriction
    response_body = exc_info.value.response.body.decode()
    assert "workspace" in response_body.lower()


async def test_scan_outside_workspace_denied(jp_fetch):
    """Scanning a path outside the workspace is refused with 400."""
    with pytest.raises(HTTPClientError) as exc_info:
        await jp_fetch(
            "nb-venv-kernels", "scan",
            method="POST",
            body=json.dumps({"path": "/"})
        )

    assert exc_info.value.code == 400
    assert "workspace" in exc_info.value.response.body.decode().lower()


async def test_refresh_drops_kernel_cache(jp_fetch, jp_serverapp):
    """refresh empties the server manager's cache so the next listing rebuilds."""
    from nb_venv_kernels.manager import VEnvKernelSpecManager

    manager = VEnvKernelSpecManager()
    jp_serverapp.web_app.settings["kernel_spec_manager"] = manager
    manager.find_kernel_specs()
    assert manager._venv_kernels_cache is not None

    response = await jp_fetch("nb-venv-kernels", "refresh", method="POST", body="")

    assert json.loads(response.body) == {"refreshed": True}
    assert manager._venv_kernels_cache is None
    assert manager._default_name_overrides is None


async def test_list_environments_paths_relative(jp_fetch, jp_root_dir):
    """Listed paths are relative to the server workspace."""
    import subprocess

    from nb_venv_kernels.registry import register_environment, unregister_environment

    venv_path = str(jp_root_dir / "relproj" / ".venv")
    subprocess.run(["python", "-m", "venv", "--without-pip", venv_path],
                   check=True, capture_output=True)
    register_environment(venv_path)
    try:
        response = await jp_fetch("nb-venv-kernels", "environments")
        paths = [e["path"] for e in json.loads(response.body)["environments"]]
        assert "relproj/.venv" in paths
        assert venv_path not in paths
    finally:
        unregister_environment(venv_path)
