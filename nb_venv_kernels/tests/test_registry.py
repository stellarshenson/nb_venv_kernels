# -*- coding: utf-8 -*-
"""Tests for environment registry operations."""
import os
import shutil
import subprocess
import tempfile

import pytest

from nb_venv_kernels.registry import (
    register_environment,
    unregister_environment,
    read_environments,
    list_environments,
    is_uv_environment,
    get_venv_registry_path,
    get_uv_registry_path,
    scan_directory,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test environments."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


class TestEnvironmentRegistration:
    """Tests for environment registration and unregistration."""

    def test_register_venv(self, temp_dir):
        """Test registering a venv environment."""
        venv_path = os.path.join(temp_dir, "reg-test-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        registered, updated = register_environment(venv_path)
        assert registered is True
        assert updated is False

        # Should be in registry
        envs = read_environments()
        assert venv_path in envs

        # Cleanup
        unregister_environment(venv_path)

    def test_unregister_venv(self, temp_dir):
        """Test unregistering a venv environment."""
        venv_path = os.path.join(temp_dir, "unreg-test-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        register_environment(venv_path)
        result = unregister_environment(venv_path)
        assert result is True

        # Should not be in registry
        envs = read_environments()
        assert venv_path not in envs

    def test_register_invalid_path(self):
        """Test registering an invalid path."""
        with pytest.raises(ValueError):
            register_environment("/nonexistent/path/to/venv")

    def test_register_non_venv_directory(self, temp_dir):
        """Test registering a directory that is not a venv."""
        non_venv = os.path.join(temp_dir, "not-a-venv")
        os.makedirs(non_venv)

        with pytest.raises(ValueError):
            register_environment(non_venv)

    def test_double_registration(self, temp_dir):
        """Test registering same environment twice."""
        venv_path = os.path.join(temp_dir, "double-reg-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        # First registration
        registered1, updated1 = register_environment(venv_path)
        assert registered1 is True
        assert updated1 is False

        # Second registration should return (False, False) - already registered, no change
        registered2, updated2 = register_environment(venv_path)
        assert registered2 is False
        assert updated2 is False

        # Cleanup
        unregister_environment(venv_path)

    def test_register_with_custom_name(self, temp_dir):
        """Test registering an environment with a custom name."""
        venv_path = os.path.join(temp_dir, "named-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        # Register with custom name
        registered, updated = register_environment(venv_path, name="my-custom-name")
        assert registered is True
        assert updated is False

        # Verify custom name is stored
        from ..registry import list_environments
        envs = list_environments()
        env = next((e for e in envs if e["path"] == venv_path), None)
        assert env is not None
        assert env["custom_name"] == "my-custom-name"

        # Cleanup
        unregister_environment(venv_path)

    def test_update_custom_name(self, temp_dir):
        """Test updating the custom name of an already registered environment."""
        venv_path = os.path.join(temp_dir, "update-name-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        # First registration without name
        registered1, updated1 = register_environment(venv_path)
        assert registered1 is True
        assert updated1 is False

        # Register again with custom name - should update
        registered2, updated2 = register_environment(venv_path, name="new-name")
        assert registered2 is False  # Not newly registered
        assert updated2 is True  # But name was updated

        # Verify custom name is stored
        from ..registry import list_environments
        envs = list_environments()
        env = next((e for e in envs if e["path"] == venv_path), None)
        assert env is not None
        assert env["custom_name"] == "new-name"

        # Update to a different name
        registered3, updated3 = register_environment(venv_path, name="another-name")
        assert registered3 is False
        assert updated3 is True

        # Verify new name
        envs = list_environments()
        env = next((e for e in envs if e["path"] == venv_path), None)
        assert env["custom_name"] == "another-name"

        # Register with same name - should not update
        registered4, updated4 = register_environment(venv_path, name="another-name")
        assert registered4 is False
        assert updated4 is False  # No change

        # Passing None preserves existing name (no update)
        registered5, updated5 = register_environment(venv_path, name=None)
        assert registered5 is False
        assert updated5 is False  # Name preserved, no change

        # Verify name is still there
        envs = list_environments()
        env = next((e for e in envs if e["path"] == venv_path), None)
        assert env["custom_name"] == "another-name"

        # Cleanup
        unregister_environment(venv_path)

    def test_unregister_nonexistent(self):
        """Test unregistering an environment that is not registered."""
        result = unregister_environment("/some/nonexistent/path")
        assert result is False


class TestUvDetection:
    """Tests for uv environment detection."""

    @pytest.fixture
    def uv_available(self):
        """Check if uv is available."""
        try:
            subprocess.run(["uv", "--version"], check=True, capture_output=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("uv not available")

    def test_uv_detection_positive(self, temp_dir, uv_available):
        """Test that uv environments are correctly detected."""
        venv_path = os.path.join(temp_dir, "uv-detect-test")
        subprocess.run(["uv", "venv", venv_path], check=True, capture_output=True)

        assert is_uv_environment(venv_path) is True

    def test_uv_detection_negative(self, temp_dir):
        """Test that regular venvs are not detected as uv."""
        venv_path = os.path.join(temp_dir, "venv-detect-test")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        assert is_uv_environment(venv_path) is False

    def test_uv_registered_in_uv_registry(self, temp_dir, uv_available):
        """Test that uv environments go to uv registry."""
        venv_path = os.path.join(temp_dir, "uv-registry-test")
        subprocess.run(["uv", "venv", venv_path], check=True, capture_output=True)

        register_environment(venv_path)

        # Check uv registry
        uv_registry = get_uv_registry_path()
        if uv_registry.exists():
            with open(uv_registry, "r") as f:
                uv_envs = [line.strip() for line in f if line.strip()]
            assert venv_path in uv_envs

        # Cleanup
        unregister_environment(venv_path)


class TestListEnvironments:
    """Tests for listing environments."""

    def test_list_environments_structure(self, temp_dir):
        """Test that list_environments returns correct structure."""
        venv_path = os.path.join(temp_dir, "list-test-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        register_environment(venv_path)

        envs = list_environments()

        # Should be a list
        assert isinstance(envs, list)

        # Find our environment
        matching = [e for e in envs if e["path"] == venv_path]
        assert len(matching) == 1

        env = matching[0]
        assert "path" in env
        assert "type" in env
        assert "exists" in env
        assert "has_kernel" in env

        # Cleanup
        unregister_environment(venv_path)

    def test_list_environments_exists_flag(self, temp_dir):
        """Test that exists flag is correctly set."""
        venv_path = os.path.join(temp_dir, "exists-test-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        register_environment(venv_path)

        envs = list_environments()
        matching = [e for e in envs if e["path"] == venv_path]
        assert matching[0]["exists"] is True

        # Delete the venv but keep registration
        shutil.rmtree(venv_path)

        envs = list_environments()
        matching = [e for e in envs if e["path"] == venv_path]
        assert matching[0]["exists"] is False

        # Cleanup
        unregister_environment(venv_path)

    def test_list_environments_has_kernel_flag(self, temp_dir):
        """Test that has_kernel flag is correctly set."""
        # Without ipykernel
        venv_path = os.path.join(temp_dir, "no-kernel-test")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        register_environment(venv_path)

        envs = list_environments()
        matching = [e for e in envs if e["path"] == venv_path]
        assert matching[0]["has_kernel"] is False

        # Install ipykernel
        pip_path = os.path.join(venv_path, "bin", "pip")
        subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)

        envs = list_environments()
        matching = [e for e in envs if e["path"] == venv_path]
        assert matching[0]["has_kernel"] is True

        # Cleanup
        unregister_environment(venv_path)


class TestDirectoryScanning:
    """Tests for directory scanning."""

    def test_scan_finds_venvs(self, temp_dir):
        """Test that scan finds venv environments."""
        # Create nested project with venv
        project_dir = os.path.join(temp_dir, "project1")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        # Scan with dry_run
        result = scan_directory(temp_dir, max_depth=3, dry_run=True)

        # In dry_run mode, new environments go to "registered" list
        assert "registered" in result
        assert venv_path in result["registered"]

    def test_scan_depth_limit(self, temp_dir):
        """Test that scan respects depth limit."""
        # Create deeply nested venv
        deep_path = os.path.join(temp_dir, "a", "b", "c", "d", "e")
        os.makedirs(deep_path)
        venv_path = os.path.join(deep_path, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        # Scan with low depth
        result = scan_directory(temp_dir, max_depth=2, dry_run=True)

        # Should not find the deeply nested venv (at depth 6)
        assert venv_path not in result.get("registered", [])

        # Scan with higher depth
        result = scan_directory(temp_dir, max_depth=7, dry_run=True)

        # Should find it now
        assert venv_path in result["registered"]

    def test_scan_registers_environments(self, temp_dir):
        """Test that scan registers found environments."""
        project_dir = os.path.join(temp_dir, "scan-reg-project")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        # Scan without dry_run
        result = scan_directory(temp_dir, max_depth=3, dry_run=False)

        assert venv_path in result["registered"]

        # Should now be in registry
        envs = read_environments()
        assert venv_path in envs

        # Cleanup
        unregister_environment(venv_path)

    def test_scan_dry_run(self, temp_dir):
        """Test that dry_run does not modify registry."""
        project_dir = os.path.join(temp_dir, "dry-run-project")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        # Get initial state
        initial_envs = read_environments()

        # Scan with dry_run
        scan_directory(temp_dir, max_depth=3, dry_run=True)

        # Registry should be unchanged
        after_envs = read_environments()
        assert set(initial_envs) == set(after_envs)


class TestRegistryPaths:
    """Tests for registry path functions."""

    def test_venv_registry_path(self):
        """Test venv registry path is in home directory."""
        path = get_venv_registry_path()
        assert ".venv" in str(path)
        assert "environments.txt" in str(path)

    def test_uv_registry_path(self):
        """Test uv registry path is in home directory."""
        path = get_uv_registry_path()
        assert ".uv" in str(path)
        assert "environments.txt" in str(path)
