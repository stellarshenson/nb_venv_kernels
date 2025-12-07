# -*- coding: utf-8 -*-
"""Tests for VEnvKernelSpecManager Python API."""
import os
import shutil
import subprocess
import tempfile

import pytest

from nb_venv_kernels.manager import VEnvKernelSpecManager
from nb_venv_kernels.registry import unregister_environment


def _install_ipykernel(venv_path):
    """Helper to install ipykernel in a venv to create kernelspec."""
    pip_path = os.path.join(venv_path, "bin", "pip")
    subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test environments."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def manager():
    """Create a fresh VEnvKernelSpecManager instance."""
    return VEnvKernelSpecManager()


class TestListEnvironmentsAPI:
    """Tests for list_environments() API method."""

    def test_list_environments_returns_list(self, manager):
        """Test that list_environments returns a list."""
        result = manager.list_environments()
        assert isinstance(result, list)

    def test_list_environments_entry_structure(self, temp_dir, manager):
        """Test structure of list_environments entries."""
        venv_path = os.path.join(temp_dir, "api-list-test")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        result = manager.register_environment(venv_path)
        assert result["registered"] is True

        envs = manager.list_environments()
        matching = [e for e in envs if e["path"] == venv_path]

        assert len(matching) == 1
        env = matching[0]

        # Required fields
        assert "name" in env
        assert "type" in env
        assert "exists" in env
        assert "has_kernel" in env
        assert "path" in env

        # Cleanup
        manager.unregister_environment(venv_path)


class TestScanEnvironmentsAPI:
    """Tests for scan_environments() API method."""

    def test_scan_environments_returns_dict(self, temp_dir, manager):
        """Test that scan_environments returns a dict."""
        result = manager.scan_environments(path=temp_dir, dry_run=True)

        assert isinstance(result, dict)
        assert "environments" in result
        assert "summary" in result
        assert "dry_run" in result

    def test_scan_environments_summary_structure(self, temp_dir, manager):
        """Test structure of scan summary."""
        result = manager.scan_environments(path=temp_dir, dry_run=True)

        summary = result["summary"]
        assert "add" in summary
        assert "keep" in summary
        assert "remove" in summary

    def test_scan_environments_finds_venvs(self, temp_dir, manager):
        """Test that scan finds venv environments."""
        project_dir = os.path.join(temp_dir, "scan-api-project")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        result = manager.scan_environments(path=temp_dir, max_depth=3, dry_run=True)

        # Should find the venv
        env_paths = [e["path"] for e in result["environments"]]
        assert venv_path in env_paths

    def test_scan_environments_dry_run(self, temp_dir, manager):
        """Test that dry_run does not register environments."""
        project_dir = os.path.join(temp_dir, "dry-run-api-project")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        # Scan with dry_run
        manager.scan_environments(path=temp_dir, max_depth=3, dry_run=True)

        # Should NOT be in environments list
        envs = manager.list_environments()
        env_paths = [e["path"] for e in envs]
        assert venv_path not in env_paths

    def test_scan_environments_registers(self, temp_dir, manager):
        """Test that scan without dry_run registers environments."""
        project_dir = os.path.join(temp_dir, "register-api-project")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        # Scan without dry_run
        manager.scan_environments(path=temp_dir, max_depth=3, dry_run=False)

        # Should be in environments list
        envs = manager.list_environments()
        env_paths = [e["path"] for e in envs]
        assert venv_path in env_paths

        # Cleanup
        unregister_environment(venv_path)


class TestRegisterEnvironmentAPI:
    """Tests for register_environment() API method."""

    def test_register_environment_success(self, temp_dir, manager):
        """Test successful environment registration."""
        venv_path = os.path.join(temp_dir, "api-reg-test")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        result = manager.register_environment(venv_path)

        assert isinstance(result, dict)
        assert result["path"] == venv_path
        assert result["registered"] is True
        assert result["updated"] is False
        assert result["error"] is None

        # Cleanup
        manager.unregister_environment(venv_path)

    def test_register_environment_invalid_path(self, manager):
        """Test registering invalid path."""
        result = manager.register_environment("/nonexistent/path")

        assert result["registered"] is False
        assert result["updated"] is False
        assert result["error"] is not None

    def test_register_environment_double_registration(self, temp_dir, manager):
        """Test double registration returns False."""
        venv_path = os.path.join(temp_dir, "double-api-reg")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        result1 = manager.register_environment(venv_path)
        assert result1["registered"] is True
        assert result1["updated"] is False

        result2 = manager.register_environment(venv_path)
        assert result2["registered"] is False
        assert result2["updated"] is False

        # Cleanup
        manager.unregister_environment(venv_path)

    def test_register_environment_with_name(self, temp_dir, manager):
        """Test registering an environment with a custom name."""
        venv_path = os.path.join(temp_dir, "api-named-reg")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        result = manager.register_environment(venv_path, name="my-api-env")

        assert result["registered"] is True
        assert result["updated"] is False
        assert result["name"] == "my-api-env"

        # Cleanup
        manager.unregister_environment(venv_path)

    def test_register_environment_update_name(self, temp_dir, manager):
        """Test updating the custom name of an already registered environment."""
        venv_path = os.path.join(temp_dir, "api-update-name")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        # First registration without name
        result1 = manager.register_environment(venv_path)
        assert result1["registered"] is True
        assert result1["updated"] is False

        # Update with a custom name
        result2 = manager.register_environment(venv_path, name="new-name")
        assert result2["registered"] is False
        assert result2["updated"] is True
        assert result2["name"] == "new-name"

        # Same name should not update
        result3 = manager.register_environment(venv_path, name="new-name")
        assert result3["registered"] is False
        assert result3["updated"] is False

        # Cleanup
        manager.unregister_environment(venv_path)


class TestUnregisterEnvironmentAPI:
    """Tests for unregister_environment() API method."""

    def test_unregister_environment_success(self, temp_dir, manager):
        """Test successful environment unregistration."""
        venv_path = os.path.join(temp_dir, "api-unreg-test")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        manager.register_environment(venv_path)
        result = manager.unregister_environment(venv_path)

        assert isinstance(result, dict)
        assert result["path"] == venv_path
        assert result["unregistered"] is True

    def test_unregister_nonexistent(self, manager):
        """Test unregistering non-registered environment."""
        result = manager.unregister_environment("/some/random/path")

        assert result["unregistered"] is False


class TestKernelSpecMethods:
    """Tests for kernel spec methods."""

    def test_find_kernel_specs(self, manager):
        """Test find_kernel_specs returns dict."""
        specs = manager.find_kernel_specs()
        assert isinstance(specs, dict)

    def test_get_kernel_spec_valid(self, temp_dir, manager):
        """Test get_kernel_spec for valid kernel."""
        venv_path = os.path.join(temp_dir, "spec-api-test")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        pip_path = os.path.join(venv_path, "bin", "pip")
        subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)

        manager.register_environment(venv_path)

        # Find the kernel
        specs = manager.find_kernel_specs()
        matching = [k for k in specs.keys() if "spec-api-test" in k.lower()]

        if matching:
            kernel_name = matching[0]
            spec = manager.get_kernel_spec(kernel_name)

            assert spec is not None
            assert hasattr(spec, "argv")
            assert hasattr(spec, "display_name")
            assert hasattr(spec, "language")

        # Cleanup
        manager.unregister_environment(venv_path)

    def test_get_all_specs(self, manager):
        """Test get_all_specs returns dict with full info."""
        specs = manager.get_all_specs()

        assert isinstance(specs, dict)
        # Each entry should have spec key
        for name, info in specs.items():
            assert "spec" in info


class TestCacheInvalidation:
    """Tests for cache invalidation."""

    def test_register_invalidates_cache(self, temp_dir, manager):
        """Test that register invalidates the kernel cache."""
        venv_path = os.path.join(temp_dir, "cache-test-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        pip_path = os.path.join(venv_path, "bin", "pip")
        subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)

        # Prime the cache
        specs1 = manager.find_kernel_specs()
        matching1 = [k for k in specs1.keys() if "cache-test-venv" in k.lower()]
        assert len(matching1) == 0  # Not registered yet

        # Register
        manager.register_environment(venv_path)

        # Cache should be invalidated, new kernel should appear
        specs2 = manager.find_kernel_specs()
        matching2 = [k for k in specs2.keys() if "cache-test-venv" in k.lower()]
        assert len(matching2) > 0

        # Cleanup
        manager.unregister_environment(venv_path)

    def test_unregister_invalidates_cache(self, temp_dir, manager):
        """Test that unregister invalidates the kernel cache."""
        venv_path = os.path.join(temp_dir, "cache-unreg-test")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        pip_path = os.path.join(venv_path, "bin", "pip")
        subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)

        manager.register_environment(venv_path)

        # Kernel should exist
        specs1 = manager.find_kernel_specs()
        matching1 = [k for k in specs1.keys() if "cache-unreg-test" in k.lower()]
        assert len(matching1) > 0

        # Unregister
        manager.unregister_environment(venv_path)

        # Cache should be invalidated, kernel should be gone
        specs2 = manager.find_kernel_specs()
        matching2 = [k for k in specs2.keys() if "cache-unreg-test" in k.lower()]
        assert len(matching2) == 0
