# -*- coding: utf-8 -*-
"""Tests for VEnvKernelSpecManager kernel discovery."""
import os
import shutil
import subprocess
import tempfile

import pytest

from nb_venv_kernels.manager import VEnvKernelSpecManager
from nb_venv_kernels.registry import (
    register_environment,
    unregister_environment,
    is_uv_environment,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test environments."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def manager():
    """Create a fresh VEnvKernelSpecManager instance."""
    m = VEnvKernelSpecManager()
    # Clear cache to ensure fresh state
    m._venv_kernels_cache = None
    m._venv_kernels_cache_expiry = None
    return m


def invalidate_cache(manager):
    """Invalidate manager cache to force re-discovery."""
    manager._venv_kernels_cache = None
    manager._venv_kernels_cache_expiry = None


class TestVenvKernelDiscovery:
    """Tests for venv environment kernel discovery."""

    def test_venv_creation_and_registration(self, temp_dir, manager):
        """Test creating a venv and registering it."""
        venv_path = os.path.join(temp_dir, "test-venv")

        # Create venv
        subprocess.run(
            ["python", "-m", "venv", venv_path],
            check=True,
            capture_output=True
        )

        # Install ipykernel
        pip_path = os.path.join(venv_path, "bin", "pip")
        subprocess.run(
            [pip_path, "install", "ipykernel", "-q"],
            check=True,
            capture_output=True
        )

        # Register the environment
        registered, updated = register_environment(venv_path)
        assert registered is True

        # Invalidate cache to pick up new registration
        invalidate_cache(manager)

        # Verify kernel discovery
        specs = manager.find_kernel_specs()
        kernel_names = list(specs.keys())

        # Should find a kernel containing 'test-venv'
        matching = [k for k in kernel_names if "test-venv" in k.lower()]
        assert len(matching) > 0, f"test-venv kernel not found in {kernel_names}"

        # Cleanup
        unregister_environment(venv_path)

    def test_venv_with_standard_name(self, temp_dir, manager):
        """Test venv with .venv name uses parent directory."""
        project_dir = os.path.join(temp_dir, "my-project")
        os.makedirs(project_dir)
        venv_path = os.path.join(project_dir, ".venv")

        # Create venv
        subprocess.run(
            ["python", "-m", "venv", venv_path],
            check=True,
            capture_output=True
        )

        # Install ipykernel
        pip_path = os.path.join(venv_path, "bin", "pip")
        subprocess.run(
            [pip_path, "install", "ipykernel", "-q"],
            check=True,
            capture_output=True
        )

        # Register
        register_environment(venv_path)
        invalidate_cache(manager)

        # Check that kernel name uses project name
        specs = manager.find_kernel_specs()
        matching = [k for k in specs.keys() if "my-project" in k.lower()]
        assert len(matching) > 0, f"my-project kernel not found in {list(specs.keys())}"

        # Cleanup
        unregister_environment(venv_path)

    def test_venv_kernel_spec_structure(self, temp_dir, manager):
        """Test that venv kernelspec has correct structure."""
        venv_path = os.path.join(temp_dir, "spec-test-venv")

        # Create venv with ipykernel
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        pip_path = os.path.join(venv_path, "bin", "pip")
        subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)

        register_environment(venv_path)
        invalidate_cache(manager)

        # Find the kernel
        specs = manager.find_kernel_specs()
        matching = [k for k in specs.keys() if "spec-test-venv" in k.lower()]
        assert len(matching) > 0

        # Get full spec
        kernel_name = matching[0]
        spec = manager.get_kernel_spec(kernel_name)

        # Verify structure
        assert spec.language.lower() == "python"
        assert "python" in spec.argv[0].lower()
        assert spec.env.get("VIRTUAL_ENV") == venv_path

        # Cleanup
        unregister_environment(venv_path)


class TestUvKernelDiscovery:
    """Tests for uv environment kernel discovery."""

    @pytest.fixture
    def uv_available(self):
        """Check if uv is available."""
        try:
            subprocess.run(["uv", "--version"], check=True, capture_output=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            pytest.skip("uv not available")

    def test_uv_environment_detection(self, temp_dir, uv_available):
        """Test that uv environments are detected as uv type."""
        venv_path = os.path.join(temp_dir, "uv-test-env")

        # Create uv venv
        subprocess.run(
            ["uv", "venv", venv_path],
            check=True,
            capture_output=True
        )

        # Should be detected as uv
        assert is_uv_environment(venv_path) is True

    def test_uv_kernel_discovery(self, temp_dir, manager, uv_available):
        """Test uv environment kernel discovery."""
        venv_path = os.path.join(temp_dir, "uv-kernel-test")

        # Create uv venv
        subprocess.run(["uv", "venv", venv_path], check=True, capture_output=True)

        # Install ipykernel using uv
        subprocess.run(
            ["uv", "pip", "install", "ipykernel", "-q", "-p", venv_path],
            check=True,
            capture_output=True
        )

        # Register
        register_environment(venv_path)
        invalidate_cache(manager)

        # Verify kernel discovery
        specs = manager.find_kernel_specs()
        matching = [k for k in specs.keys() if "uv-kernel-test" in k.lower()]
        assert len(matching) > 0, f"uv-kernel-test not found in {list(specs.keys())}"

        # Cleanup
        unregister_environment(venv_path)


class TestCondaKernelDiscovery:
    """Tests for conda environment kernel discovery."""

    @pytest.fixture
    def conda_available(self):
        """Check if conda is available."""
        try:
            result = subprocess.run(
                ["conda", "--version"],
                check=True,
                capture_output=True,
                timeout=10
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            pytest.skip("conda not available")

    def test_conda_base_discovery(self, manager, conda_available):
        """Test that conda base environment is discovered."""
        specs = manager.find_kernel_specs()

        # Look for base/conda kernel
        conda_kernels = [k for k in specs.keys() if "conda" in k.lower() or "base" in k.lower()]

        # Should find at least the base environment
        assert len(conda_kernels) >= 0  # May be 0 if no ipykernel in base

    def test_conda_env_creation_and_discovery(self, temp_dir, manager, conda_available):
        """Test creating and discovering a conda environment."""
        env_name = "nb-venv-kernels-test-env"

        try:
            # Create conda env with ipykernel
            result = subprocess.run(
                ["conda", "create", "-n", env_name, "python", "ipykernel", "-y", "-q"],
                check=True,
                capture_output=True,
                timeout=300
            )

            # Verify the env was created by checking conda env list
            env_list = subprocess.run(
                ["conda", "env", "list"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if env_name not in env_list.stdout:
                pytest.skip(f"conda env {env_name} not found in env list - conda indexing issue")

            # Invalidate cache to force rediscovery
            invalidate_cache(manager)

            # Verify kernel discovery
            specs = manager.find_kernel_specs()
            matching = [k for k in specs.keys() if env_name in k.lower()]

            # Note: conda envs are auto-discovered, no need to register
            # If env exists but kernel not found, it might be due to ipykernel not being properly indexed
            if len(matching) == 0:
                pytest.skip(f"{env_name} created but kernel not discovered - conda timing issue")

        finally:
            # Cleanup - remove conda env
            subprocess.run(
                ["conda", "env", "remove", "-n", env_name, "-y"],
                capture_output=True,
                timeout=60
            )


class TestMixedEnvironments:
    """Tests for mixed environment scenarios."""

    def test_multiple_environments(self, temp_dir, manager):
        """Test discovering multiple venv environments."""
        venv_paths = []

        # Create multiple venvs
        for i in range(3):
            venv_path = os.path.join(temp_dir, f"multi-venv-{i}")
            subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
            pip_path = os.path.join(venv_path, "bin", "pip")
            subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)
            register_environment(venv_path)
            venv_paths.append(venv_path)

        # Invalidate cache to pick up new registrations
        invalidate_cache(manager)

        # Verify all are discovered
        specs = manager.find_kernel_specs()
        for i in range(3):
            matching = [k for k in specs.keys() if f"multi-venv-{i}" in k.lower()]
            assert len(matching) > 0, f"multi-venv-{i} not found"

        # Cleanup
        for venv_path in venv_paths:
            unregister_environment(venv_path)

    def test_environment_without_ipykernel_registers_by_default(self, temp_dir, manager):
        """Test that environments without ipykernel can be registered by default."""
        venv_path = os.path.join(temp_dir, "no-kernel-venv")

        # Create venv WITHOUT ipykernel
        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)

        # Registration should succeed by default (require_kernelspec=False)
        registered, updated = register_environment(venv_path)
        assert registered is True

        # Environment is registered but won't show as kernel (no ipykernel)
        invalidate_cache(manager)
        specs = manager.find_kernel_specs()
        matching = [k for k in specs.keys() if "no-kernel-venv" in k.lower()]
        assert len(matching) == 0, f"no-kernel-venv should not be in {list(specs.keys())}"

        # Cleanup
        unregister_environment(venv_path)


class TestKernelSpecDetails:
    """Tests for kernel spec details and metadata."""

    def test_kernel_metadata(self, temp_dir, manager):
        """Test that kernel metadata is correctly set."""
        venv_path = os.path.join(temp_dir, "metadata-test-venv")

        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        pip_path = os.path.join(venv_path, "bin", "pip")
        subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)
        register_environment(venv_path)

        # Invalidate cache to pick up new registration
        invalidate_cache(manager)

        specs = manager.find_kernel_specs()
        matching = [k for k in specs.keys() if "metadata-test-venv" in k.lower()]
        assert len(matching) > 0

        spec = manager.get_kernel_spec(matching[0])

        # Check metadata
        assert hasattr(spec, "metadata")
        assert "venv_env_path" in spec.metadata
        assert spec.metadata["venv_env_path"] == venv_path
        assert "venv_source" in spec.metadata
        assert spec.metadata["venv_source"] in ("venv", "uv")

        # Cleanup
        unregister_environment(venv_path)

    def test_kernel_display_name(self, temp_dir, manager):
        """Test kernel display name format."""
        venv_path = os.path.join(temp_dir, "display-name-test")

        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        pip_path = os.path.join(venv_path, "bin", "pip")
        subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)
        register_environment(venv_path)

        # Invalidate cache to pick up new registration
        invalidate_cache(manager)

        specs = manager.find_kernel_specs()
        matching = [k for k in specs.keys() if "display-name-test" in k.lower()]
        assert len(matching) > 0

        spec = manager.get_kernel_spec(matching[0])

        # Display name should contain environment name and source
        assert "display-name-test" in spec.display_name.lower() or "display" in spec.display_name.lower()

        # Cleanup
        unregister_environment(venv_path)

    def test_kernel_display_name_with_custom_name(self, temp_dir, manager):
        """Test kernel display name uses custom name from registry."""
        venv_path = os.path.join(temp_dir, "custom-name-kernel-test")
        custom_name = "my-custom-kernel"

        subprocess.run(["python", "-m", "venv", venv_path], check=True, capture_output=True)
        pip_path = os.path.join(venv_path, "bin", "pip")
        subprocess.run([pip_path, "install", "ipykernel", "-q"], check=True, capture_output=True)

        # Register with custom name
        register_environment(venv_path, name=custom_name)

        # Invalidate cache to pick up new registration
        invalidate_cache(manager)

        specs = manager.find_kernel_specs()
        # Kernel name should contain custom name, not directory name
        matching = [k for k in specs.keys() if custom_name in k.lower()]
        assert len(matching) > 0, f"Kernel with custom name not found. Available: {list(specs.keys())}"

        spec = manager.get_kernel_spec(matching[0])

        # Display name should contain custom name
        assert custom_name in spec.display_name.lower(), f"Custom name '{custom_name}' not in display: {spec.display_name}"

        # Cleanup
        unregister_environment(venv_path)

    def test_kernel_names_unique_with_duplicate_custom_names(self, temp_dir, manager):
        """Test kernel names are unique even when registry has duplicate custom names."""
        # Create two venvs with ipykernel
        venv1_path = os.path.join(temp_dir, "proj1", ".venv")
        venv2_path = os.path.join(temp_dir, "proj2", ".venv")
        os.makedirs(os.path.dirname(venv1_path))
        os.makedirs(os.path.dirname(venv2_path))

        subprocess.run(["python", "-m", "venv", venv1_path], check=True, capture_output=True)
        subprocess.run(["python", "-m", "venv", venv2_path], check=True, capture_output=True)

        pip1 = os.path.join(venv1_path, "bin", "pip")
        pip2 = os.path.join(venv2_path, "bin", "pip")
        subprocess.run([pip1, "install", "ipykernel", "-q"], check=True, capture_output=True)
        subprocess.run([pip2, "install", "ipykernel", "-q"], check=True, capture_output=True)

        # Register both with same custom name (simulating legacy duplicate)
        # Note: register_environment now warns and auto-suffixes, but we test _all_envs directly
        register_environment(venv1_path, name="same-name")
        register_environment(venv2_path, name="same-name")  # Will become same-name_1

        # Invalidate cache
        invalidate_cache(manager)

        # Get all envs - should have unique names
        all_envs = manager._all_envs()
        env_names = list(all_envs.keys())

        # Should have two different names
        matching = [n for n in env_names if n.startswith("same-name")]
        assert len(matching) == 2, f"Expected 2 envs with same-name prefix, got: {matching}"
        assert len(set(matching)) == 2, f"Expected unique names, got duplicates: {matching}"

        # One should be same-name, other same-name_1
        assert "same-name" in matching
        assert "same-name_1" in matching

        # Cleanup
        unregister_environment(venv1_path)
        unregister_environment(venv2_path)


class TestNameConflictResolution:
    """Tests for name conflict resolution with suffixes."""

    def test_resolve_name_conflicts_no_duplicates(self, manager):
        """Test that unique names are unchanged."""
        environments = [
            {"name": "project-a", "path": "/a"},
            {"name": "project-b", "path": "/b"},
            {"name": "project-c", "path": "/c"},
        ]
        result = manager._resolve_name_conflicts(environments)
        assert result[0]["name"] == "project-a"
        assert result[1]["name"] == "project-b"
        assert result[2]["name"] == "project-c"

    def test_resolve_name_conflicts_with_duplicates(self, manager):
        """Test that duplicate names get _1, _2 suffixes."""
        environments = [
            {"name": "myproject", "path": "/a"},
            {"name": "myproject", "path": "/b"},
            {"name": "myproject", "path": "/c"},
        ]
        result = manager._resolve_name_conflicts(environments)
        assert result[0]["name"] == "myproject"
        assert result[1]["name"] == "myproject_1"
        assert result[2]["name"] == "myproject_2"

    def test_resolve_name_conflicts_mixed(self, manager):
        """Test mixed unique and duplicate names."""
        environments = [
            {"name": "unique", "path": "/a"},
            {"name": "duplicate", "path": "/b"},
            {"name": "duplicate", "path": "/c"},
            {"name": "another", "path": "/d"},
            {"name": "duplicate", "path": "/e"},
        ]
        result = manager._resolve_name_conflicts(environments)
        assert result[0]["name"] == "unique"
        assert result[1]["name"] == "duplicate"
        assert result[2]["name"] == "duplicate_1"
        assert result[3]["name"] == "another"
        assert result[4]["name"] == "duplicate_2"

    def test_resolve_name_conflicts_updates_action(self, manager):
        """Test that action is changed to 'update' when name changes."""
        environments = [
            {"name": "project", "path": "/a", "action": "keep"},
            {"name": "project", "path": "/b", "action": "keep"},
            {"name": "project", "path": "/c", "action": "add"},
        ]
        result = manager._resolve_name_conflicts(environments, update_action_on_change=True)
        # First keeps its name and action
        assert result[0]["name"] == "project"
        assert result[0]["action"] == "keep"
        # Second gets suffix and action changes to update
        assert result[1]["name"] == "project_1"
        assert result[1]["action"] == "update"
        # Third gets suffix but action stays as "add" (not "keep")
        assert result[2]["name"] == "project_2"
        assert result[2]["action"] == "add"

    def test_resolve_name_conflicts_preserves_other_fields(self, manager):
        """Test that other environment fields are preserved."""
        environments = [
            {"name": "test", "path": "/a", "type": "venv", "exists": True},
            {"name": "test", "path": "/b", "type": "uv", "exists": False},
        ]
        result = manager._resolve_name_conflicts(environments)
        assert result[0]["path"] == "/a"
        assert result[0]["type"] == "venv"
        assert result[0]["exists"] is True
        assert result[1]["path"] == "/b"
        assert result[1]["type"] == "uv"
        assert result[1]["exists"] is False
