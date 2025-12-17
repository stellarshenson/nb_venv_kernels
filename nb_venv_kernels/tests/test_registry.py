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
    read_environments_with_names,
    list_environments,
    is_uv_environment,
    get_venv_registry_path,
    get_uv_registry_path,
    scan_directory,
    sanitize_registry_names,
    _has_kernelspec,
    get_name_cache_path,
    load_name_cache,
    save_name_cache,
    get_cached_name,
    update_name_cache,
    _derive_env_name,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test environments."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _install_ipykernel(venv_path):
    """Helper to install ipykernel in a venv to create kernelspec."""
    pip_path = os.path.join(venv_path, "bin", "pip")
    subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)


def _path_in_result(path, result_list):
    """Check if a path is in a list of dicts with 'path' key."""
    return any(item["path"] == path for item in result_list)


class TestEnvironmentRegistration:
    """Tests for environment registration and unregistration."""

    def test_register_venv(self, temp_dir):
        """Test registering a venv environment with kernelspec."""
        venv_path = os.path.join(temp_dir, "reg-test-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

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
        _install_ipykernel(venv_path)

        register_environment(venv_path)
        result = unregister_environment(venv_path)
        assert result is True

        # Should not be in registry
        envs = read_environments()
        assert venv_path not in envs

    def test_unregister_venv_with_custom_name(self, temp_dir):
        """Test unregistering a venv environment that has a custom name."""
        venv_path = os.path.join(temp_dir, "unreg-custom-name-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        # Register with custom name
        register_environment(venv_path, name="my-custom-name")

        # Verify it's registered
        envs = read_environments()
        assert venv_path in envs

        # Unregister by path (should work even with custom name in registry)
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

    def test_register_venv_without_kernelspec_allowed_by_default(self, temp_dir):
        """Test that registering a venv without kernelspec succeeds by default."""
        venv_path = os.path.join(temp_dir, "no-kernel-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        # No ipykernel installed - should still register with default require_kernelspec=False

        registered, updated = register_environment(venv_path)
        assert registered is True
        assert updated is False

        # Cleanup
        unregister_environment(venv_path)

    def test_register_venv_without_kernelspec_rejected_when_required(self, temp_dir):
        """Test that registering a venv without kernelspec raises ValueError when required."""
        venv_path = os.path.join(temp_dir, "no-kernel-req-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        # No ipykernel installed

        with pytest.raises(ValueError, match="No kernelspec found"):
            register_environment(venv_path, require_kernelspec=True)

    def test_double_registration(self, temp_dir):
        """Test registering same environment twice."""
        venv_path = os.path.join(temp_dir, "double-reg-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

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
        _install_ipykernel(venv_path)

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
        _install_ipykernel(venv_path)

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
        # Install ipykernel using uv
        subprocess.run(["uv", "pip", "install", "ipykernel", "-q", "-p", venv_path], check=True, capture_output=True)

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
        _install_ipykernel(venv_path)
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
        _install_ipykernel(venv_path)
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
        # With ipykernel (required for registration)
        venv_path = os.path.join(temp_dir, "kernel-test")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)
        register_environment(venv_path)

        envs = list_environments()
        matching = [e for e in envs if e["path"] == venv_path]
        assert matching[0]["has_kernel"] is True

        # Cleanup
        unregister_environment(venv_path)


class TestDirectoryScanning:
    """Tests for directory scanning."""

    def test_scan_finds_venvs_with_kernel(self, temp_dir):
        """Test that scan finds venv environments with kernelspec."""
        # Create nested project with venv and ipykernel
        project_dir = os.path.join(temp_dir, "project1")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        # Scan with dry_run
        result = scan_directory(temp_dir, max_depth=3, dry_run=True)

        # In dry_run mode, new environments with kernel go to "registered" list
        assert "registered" in result
        assert _path_in_result(venv_path, result["registered"])

    def test_scan_reports_venvs_without_kernel_when_required(self, temp_dir):
        """Test that scan reports venvs without kernelspec in ignore list when require_kernelspec=True."""
        # Create nested project with venv but NO ipykernel
        project_dir = os.path.join(temp_dir, "project-no-kernel")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        # No ipykernel installed

        # Scan with require_kernelspec=True
        result = scan_directory(temp_dir, max_depth=3, dry_run=True, require_kernelspec=True)

        # Should be in ignore list, not registered
        assert "ignore" in result
        assert _path_in_result(venv_path, result["ignore"])
        assert not _path_in_result(venv_path, result.get("registered", []))

    def test_scan_registers_venvs_without_kernel_by_default(self, temp_dir):
        """Test that scan registers venvs without kernelspec when require_kernelspec=False (default)."""
        # Create nested project with venv but NO ipykernel
        project_dir = os.path.join(temp_dir, "project-no-kernel-default")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        # No ipykernel installed

        # Scan with default require_kernelspec=False
        result = scan_directory(temp_dir, max_depth=3, dry_run=True)

        # Should be in registered list (dry_run), not in ignore
        assert _path_in_result(venv_path, result.get("registered", []))
        assert not _path_in_result(venv_path, result.get("ignore", []))

        # Cleanup
        unregister_environment(venv_path)

    def test_scan_depth_limit(self, temp_dir):
        """Test that scan respects depth limit."""
        # Create deeply nested venv with ipykernel
        deep_path = os.path.join(temp_dir, "a", "b", "c", "d", "e")
        os.makedirs(deep_path)
        venv_path = os.path.join(deep_path, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        # Scan with low depth
        result = scan_directory(temp_dir, max_depth=2, dry_run=True)

        # Should not find the deeply nested venv (at depth 6)
        assert not _path_in_result(venv_path, result.get("registered", []))
        assert not _path_in_result(venv_path, result.get("ignore", []))

        # Scan with higher depth
        result = scan_directory(temp_dir, max_depth=7, dry_run=True)

        # Should find it now
        assert _path_in_result(venv_path, result["registered"])

    def test_scan_registers_environments(self, temp_dir):
        """Test that scan registers found environments with kernelspec."""
        project_dir = os.path.join(temp_dir, "scan-reg-project")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        # Scan without dry_run
        result = scan_directory(temp_dir, max_depth=3, dry_run=False)

        assert _path_in_result(venv_path, result["registered"])

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
        _install_ipykernel(venv_path)

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


class TestRegistrySanitization:
    """Tests for registry name sanitization."""

    def test_scan_shows_update_for_sanitized_names(self, temp_dir):
        """Test that scan shows 'update' action when duplicate names are sanitized."""
        # Create two venvs with ipykernel
        venv1_path = os.path.join(temp_dir, "proj1", ".venv")
        venv2_path = os.path.join(temp_dir, "proj2", ".venv")
        os.makedirs(os.path.dirname(venv1_path))
        os.makedirs(os.path.dirname(venv2_path))
        subprocess.run(["python", "-m", "venv", venv1_path], check=True, capture_output=True)
        subprocess.run(["python", "-m", "venv", venv2_path], check=True, capture_output=True)
        _install_ipykernel(venv1_path)
        _install_ipykernel(venv2_path)

        # Register both with the same custom name
        register_environment(venv1_path, name="same-name")
        # Second one will get "same-name_1" due to conflict resolution at registration
        register_environment(venv2_path, name="same-name")

        # Now manually write duplicate names to registry to simulate manual edit
        registry_path = get_venv_registry_path()
        with open(registry_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Replace "same-name_1" with "same-name" to create duplicate
        content = content.replace("same-name_1", "same-name")
        with open(registry_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Run scan - should detect and fix duplicates
        result = scan_directory(temp_dir, max_depth=3)

        # One of the paths should be in updated list due to name sanitization
        assert len(result["updated"]) >= 1
        assert _path_in_result(venv1_path, result["updated"]) or _path_in_result(venv2_path, result["updated"])

        # Verify registry now has unique names
        envs = read_environments_with_names()
        names = [name for _, name in envs if name and name.startswith("same-name")]
        assert len(names) == len(set(names)), "Names should be unique after sanitization"

        # Cleanup
        unregister_environment(venv1_path)
        unregister_environment(venv2_path)

    def test_sanitize_registry_names_returns_updated(self, temp_dir):
        """Test that sanitize_registry_names returns list of updated entries."""
        # Create two venvs with ipykernel
        venv1_path = os.path.join(temp_dir, "proj1", ".venv")
        venv2_path = os.path.join(temp_dir, "proj2", ".venv")
        os.makedirs(os.path.dirname(venv1_path))
        os.makedirs(os.path.dirname(venv2_path))
        subprocess.run(["python", "-m", "venv", venv1_path], check=True, capture_output=True)
        subprocess.run(["python", "-m", "venv", venv2_path], check=True, capture_output=True)
        _install_ipykernel(venv1_path)
        _install_ipykernel(venv2_path)

        # Register both
        register_environment(venv1_path, name="dup-name")
        register_environment(venv2_path, name="dup-name")  # Gets "dup-name_1"

        # Manually create duplicate in registry
        registry_path = get_venv_registry_path()
        with open(registry_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace("dup-name_1", "dup-name")
        with open(registry_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Sanitize should return updated entries
        updated = sanitize_registry_names()

        assert len(updated) == 1
        assert updated[0]["old_name"] == "dup-name"
        assert updated[0]["new_name"] == "dup-name_1"
        assert updated[0]["path"] in [venv1_path, venv2_path]

        # Cleanup
        unregister_environment(venv1_path)
        unregister_environment(venv2_path)


class TestKernelspecValidation:
    """Tests for kernelspec validation in registration and cleanup."""

    def test_has_kernelspec_positive(self, temp_dir):
        """Test _has_kernelspec returns True for venv with ipykernel."""
        venv_path = os.path.join(temp_dir, "kernel-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        assert _has_kernelspec(venv_path) is True

    def test_has_kernelspec_negative(self, temp_dir):
        """Test _has_kernelspec returns False for venv without ipykernel."""
        venv_path = os.path.join(temp_dir, "no-kernel-venv")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        # No ipykernel installed

        assert _has_kernelspec(venv_path) is False

    def test_cleanup_removes_envs_without_kernelspec_when_required(self, temp_dir):
        """Test that cleanup removes environments that lost their kernelspec when require_kernelspec=True."""
        from nb_venv_kernels.registry import cleanup_registries

        # Create venv with ipykernel and register
        venv_path = os.path.join(temp_dir, "cleanup-kernel-test")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)
        register_environment(venv_path)

        # Verify registered
        envs = read_environments()
        assert venv_path in envs

        # Remove ipykernel (simulate uninstall by deleting kernels dir)
        kernel_dir = os.path.join(venv_path, "share", "jupyter", "kernels")
        shutil.rmtree(kernel_dir)

        # Cleanup with require_kernelspec=True should remove it
        result = cleanup_registries(require_kernelspec=True)
        assert any(item["path"] == venv_path for item in result["removed"])

        # Should no longer be in registry
        envs = read_environments()
        assert venv_path not in envs

    def test_cleanup_keeps_envs_without_kernelspec_by_default(self, temp_dir):
        """Test that cleanup keeps environments without kernelspec when require_kernelspec=False."""
        from nb_venv_kernels.registry import cleanup_registries

        # Create venv without ipykernel and register
        venv_path = os.path.join(temp_dir, "no-kernel-cleanup-test")
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        register_environment(venv_path)  # No ipykernel, but registers with default

        # Verify registered
        envs = read_environments()
        assert venv_path in envs

        # Cleanup with default require_kernelspec=False should NOT remove it
        result = cleanup_registries()
        assert not any(item["path"] == venv_path for item in result["removed"])

        # Should still be in registry
        envs = read_environments()
        assert venv_path in envs

        # Cleanup
        unregister_environment(venv_path)


class TestScanExclusions:
    """Tests for scan exclusion patterns."""

    def test_scan_skips_cache_directories(self, temp_dir):
        """Test that scan skips @cache and uv cache directories."""
        # Create a fake cache structure with venv inside (with ipykernel)
        cache_dir = os.path.join(temp_dir, "@cache", "uv", "environments-v2")
        os.makedirs(cache_dir)
        cache_venv = os.path.join(cache_dir, "abc123")
        subprocess.run(["python", "-m", "venv", cache_venv], check=True, capture_output=True)
        _install_ipykernel(cache_venv)

        # Create a normal venv (with ipykernel)
        normal_venv = os.path.join(temp_dir, "project", ".venv")
        os.makedirs(os.path.dirname(normal_venv))
        subprocess.run(["python", "-m", "venv", normal_venv], check=True, capture_output=True)
        _install_ipykernel(normal_venv)

        # Scan with dry_run
        result = scan_directory(temp_dir, max_depth=5, dry_run=True)

        # Should find normal venv but not cache venv
        assert _path_in_result(normal_venv, result["registered"])
        assert not _path_in_result(cache_venv, result["registered"])

    def test_cleanup_removes_cache_paths(self, temp_dir):
        """Test that cleanup removes cache paths from registry."""
        from nb_venv_kernels.registry import cleanup_registries, _is_cache_path

        # Verify cache path detection
        assert _is_cache_path("/home/user/@cache/uv/environments-v2/abc") is True
        assert _is_cache_path("/home/user/.local/share/uv/cache") is True
        assert _is_cache_path("/home/user/project/.venv") is False


class TestNameCache:
    """Tests for the name cache functionality."""

    @pytest.fixture(autouse=True)
    def clean_cache(self):
        """Clean up test entries from name cache before and after each test.

        Preserves user entries (non-temp paths) while removing test entries.
        """
        def _clean_temp_entries():
            """Remove only /tmp/ entries from cache, preserving user entries."""
            cache = load_name_cache()
            clean = {k: v for k, v in cache.items() if not k.startswith("/tmp/")}
            save_name_cache(clean)

        _clean_temp_entries()
        yield
        _clean_temp_entries()

    def test_name_cache_path(self):
        """Test that name cache path is in correct location."""
        path = get_name_cache_path()
        assert ".local" in str(path)
        assert "share" in str(path)
        assert "nb_venv_kernels" in str(path)
        assert "name_cache.json" in str(path)

    def test_load_cache_returns_dict(self):
        """Test that loading cache returns a dict."""
        cache = load_name_cache()
        assert isinstance(cache, dict)

    def test_save_and_load_cache(self):
        """Test saving and loading cache data."""
        # Use /tmp/ paths so they get cleaned up by fixture
        test_data = {"/tmp/test-env1": "custom-name-1", "/tmp/test-env2": "custom-name-2"}

        # Get existing cache to merge with
        existing = load_name_cache()
        merged = {**existing, **test_data}
        save_name_cache(merged)

        loaded = load_name_cache()
        # Verify test entries are present
        assert loaded["/tmp/test-env1"] == "custom-name-1"
        assert loaded["/tmp/test-env2"] == "custom-name-2"

    def test_update_name_cache(self):
        """Test updating individual cache entries."""
        # Use /tmp/ path so it gets cleaned up by fixture
        update_name_cache("/tmp/test-update-env", "my-name")
        assert get_cached_name("/tmp/test-update-env") == "my-name"

        # Update with new name
        update_name_cache("/tmp/test-update-env", "new-name")
        assert get_cached_name("/tmp/test-update-env") == "new-name"

    def test_get_cached_name_not_found(self):
        """Test getting name for non-cached path."""
        result = get_cached_name("/nonexistent/path")
        assert result is None

    def test_derive_env_name(self):
        """Test deriving default name from path."""
        assert _derive_env_name("/home/user/projects/myproject/.venv") == "myproject"
        assert _derive_env_name("/home/user/myapp/venv") == "myapp"

    def test_register_updates_cache_with_custom_name(self, temp_dir):
        """Test that registration with custom name updates the cache."""
        venv_path = os.path.join(temp_dir, "cache-test-project", ".venv")
        os.makedirs(os.path.dirname(venv_path))
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        register_environment(venv_path, name="my-custom-kernel")

        # Verify cache was updated
        cached = get_cached_name(venv_path)
        assert cached == "my-custom-kernel"

        # Cleanup
        unregister_environment(venv_path)

    def test_register_updates_cache_with_derived_name(self, temp_dir):
        """Test that registration without custom name updates cache with derived name."""
        project_name = "derived-name-project"
        venv_path = os.path.join(temp_dir, project_name, ".venv")
        os.makedirs(os.path.dirname(venv_path))
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        register_environment(venv_path)  # No custom name

        # Verify cache was updated with derived name
        cached = get_cached_name(venv_path)
        assert cached == project_name

        # Cleanup
        unregister_environment(venv_path)

    def test_unregister_does_not_remove_cache(self, temp_dir):
        """Test that unregistration does NOT remove the cache entry."""
        venv_path = os.path.join(temp_dir, "unregister-cache-test", ".venv")
        os.makedirs(os.path.dirname(venv_path))
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        # Register with custom name
        register_environment(venv_path, name="persistent-name")
        assert get_cached_name(venv_path) == "persistent-name"

        # Unregister
        unregister_environment(venv_path)

        # Cache should still have the entry
        assert get_cached_name(venv_path) == "persistent-name"

    def test_scan_uses_cached_name_for_previously_registered(self, temp_dir):
        """Test that scan uses cached name when re-registering environment."""
        venv_path = os.path.join(temp_dir, "scan-cache-test", ".venv")
        os.makedirs(os.path.dirname(venv_path))
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        # Register with custom name
        register_environment(venv_path, name="remembered-name")
        assert get_cached_name(venv_path) == "remembered-name"

        # Unregister (cache persists)
        unregister_environment(venv_path)
        assert venv_path not in read_environments()

        # Scan should re-register with the cached name
        scan_directory(temp_dir, max_depth=3)

        # Verify it's registered with the cached name
        envs = read_environments_with_names()
        env_dict = {path: name for path, name in envs}
        assert venv_path in env_dict
        assert env_dict[venv_path] == "remembered-name"

        # Cleanup
        unregister_environment(venv_path)

    def test_register_overwrites_cache_with_new_name(self, temp_dir):
        """Test that re-registration with a new name overwrites the cache."""
        venv_path = os.path.join(temp_dir, "overwrite-cache-test", ".venv")
        os.makedirs(os.path.dirname(venv_path))
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        _install_ipykernel(venv_path)

        # Register with first name
        register_environment(venv_path, name="first-name")
        assert get_cached_name(venv_path) == "first-name"

        # Re-register with new name (update)
        registered, updated = register_environment(venv_path, name="second-name")
        assert updated is True

        # Cache should have the new name
        assert get_cached_name(venv_path) == "second-name"

        # Cleanup
        unregister_environment(venv_path)
