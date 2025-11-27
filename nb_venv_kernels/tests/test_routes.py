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
