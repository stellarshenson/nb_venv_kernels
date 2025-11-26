import json


async def test_list_environments(jp_fetch):
    """Test listing environments endpoint."""
    response = await jp_fetch("nb-venv-kernels", "environments")

    assert response.code == 200
    payload = json.loads(response.body)
    assert isinstance(payload, list)


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
    response = await jp_fetch(
        "nb-venv-kernels", "register",
        method="POST",
        body=json.dumps({})
    )

    assert response.code == 400
    payload = json.loads(response.body)
    assert "error" in payload


async def test_unregister_missing_path(jp_fetch):
    """Test unregister endpoint requires path."""
    response = await jp_fetch(
        "nb-venv-kernels", "unregister",
        method="POST",
        body=json.dumps({})
    )

    assert response.code == 400
    payload = json.loads(response.body)
    assert "error" in payload
