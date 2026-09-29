# -*- coding: utf-8 -*-
"""Tests for the nb_venv_kernels command-line tool."""
import json
import os
import sys

from nb_venv_kernels.cli import main, print_help, remove_jupyter_config, update_jupyter_config
from nb_venv_kernels.manager import VEnvKernelSpecManager

MANAGER_CLASS = "nb_venv_kernels.VEnvKernelSpecManager"


def run_cli(monkeypatch, capsys, *args):
    """Run the CLI entry point and return its stdout."""
    monkeypatch.setattr(sys, "argv", ["nb_venv_kernels", *args])
    try:
        main()
    except SystemExit as e:
        assert not e.code, f"CLI exited with {e.code}"
    return capsys.readouterr().out


def test_help_states_scan_depth_default(monkeypatch, capsys):
    """Both help texts state the depth the scan uses when --depth is not given."""
    expected = f"(default: {VEnvKernelSpecManager.scan_depth.default_value})"
    print_help()
    assert expected in capsys.readouterr().out
    assert expected in run_cli(monkeypatch, capsys, "scan", "--help")


def test_list_json(monkeypatch, capsys):
    """list --json prints one JSON object with environments and workspace_root."""
    payload = json.loads(run_cli(monkeypatch, capsys, "list", "--json"))
    assert isinstance(payload["environments"], list)
    assert "workspace_root" in payload


def test_config_enable_sets_manager_class(tmp_path):
    update_jupyter_config(config_dir=str(tmp_path))
    config = json.loads((tmp_path / "jupyter_config.json").read_text())
    assert config["ServerApp"]["kernel_spec_manager_class"] == MANAGER_CLASS


def test_config_disable_restores_original(tmp_path):
    """disable after enable leaves jupyter_config.json exactly as it was."""
    config_path = tmp_path / "jupyter_config.json"
    original = json.dumps({"ServerApp": {"root_dir": "/srv"}}, indent=2) + "\n"
    config_path.write_text(original)

    update_jupyter_config(config_dir=str(tmp_path))
    assert config_path.read_text() != original
    remove_jupyter_config(config_dir=str(tmp_path))

    assert config_path.read_text() == original
    assert not os.path.exists(str(config_path) + ".nb_venv_kernels.bak")


def test_config_disable_without_prior_file_removes_setting(tmp_path):
    """disable after enable on a fresh config dir leaves no manager class behind."""
    update_jupyter_config(config_dir=str(tmp_path))
    remove_jupyter_config(config_dir=str(tmp_path))
    config = json.loads((tmp_path / "jupyter_config.json").read_text())
    assert "kernel_spec_manager_class" not in json.dumps(config)


def test_list_sorts_by_type(monkeypatch, capsys):
    """list orders conda base, local conda, uv, then venv."""
    rows = [
        {"name": "aaa", "type": "venv", "exists": True, "has_kernel": True, "path": "/w/aaa/.venv"},
        {"name": "loc", "type": "conda (local)", "exists": True, "has_kernel": True, "path": "/w/envs/loc"},
        {"name": "u", "type": "uv", "exists": True, "has_kernel": True, "path": "/w/u/.venv"},
        {"name": "base", "type": "conda", "exists": True, "has_kernel": True, "path": "/opt/conda"},
    ]
    monkeypatch.setattr(VEnvKernelSpecManager, "list_environments", lambda self: [dict(r) for r in rows])
    payload = json.loads(run_cli(monkeypatch, capsys, "list", "--json"))
    assert [e["type"] for e in payload["environments"]] == ["conda", "conda (local)", "uv", "venv"]
