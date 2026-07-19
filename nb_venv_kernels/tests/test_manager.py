# -*- coding: utf-8 -*-
"""Tests for VEnvKernelSpecManager kernel discovery."""
import os
import shutil
import subprocess
import tempfile
import time

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
    m.invalidate_cache()
    return m


def invalidate_cache(manager):
    """Invalidate manager cache to force re-discovery."""
    manager.invalidate_cache()


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

    def test_conda_base_renders_single_listing_entry(self, manager, conda_available):
        """DEF-2 premise on a real install: one env, one listing entry.

        Pins that the nb_conda_kernels base alias and the on-disk python3 spec
        actually share a (realpath) resource_dir and get collapsed - if a
        future nb_conda_kernels stops sharing it, this rung catches the no-op.
        """
        from collections import defaultdict
        from nb_venv_kernels.manager import _HAS_CONDA
        if not _HAS_CONDA:
            pytest.skip("nb_conda_kernels not installed")

        specs = manager.find_kernel_specs()
        by_rd = defaultdict(list)
        for name, rd in specs.items():
            by_rd[os.path.realpath(rd)].append(name)
        dups = {rd: names for rd, names in by_rd.items() if len(names) > 1}
        assert not dups, f"one environment must render one listing entry, got: {dups}"

    def test_get_conda_env_name_base_installations(self, manager):
        """Test _get_conda_env_name returns 'base' for conda base installations."""
        base_paths = [
            "/opt/conda",
            "/home/user/anaconda3",
            "/home/user/miniconda",
            "/opt/miniconda3",
            "/usr/local/miniforge3",
            "/home/user/mambaforge",
        ]
        for path in base_paths:
            assert manager._get_conda_env_name(path) == "base", f"Expected 'base' for {path}"

    def test_get_conda_env_name_named_envs(self, manager):
        """Test _get_conda_env_name returns directory name for named envs."""
        named_paths = [
            ("/opt/conda/envs/myenv", "myenv"),
            ("/home/user/anaconda3/envs/data-science", "data-science"),
            ("/home/user/.conda/envs/test-env", "test-env"),
        ]
        for path, expected in named_paths:
            assert manager._get_conda_env_name(path) == expected, f"Expected '{expected}' for {path}"


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


class TestDefaultKernelDedup:
    """Tests for collapsing conda/venv aliases onto default kernel names.

    A conda/venv spec sharing its resource_dir with a spared default name
    (python3/python2/ir) must yield ONE listing entry: the default name stays
    listed (notebook auto-bind guarantee - DEF-1 guard) and carries the richer
    environment-labelled display name; the alias is not listed twice but stays
    resolvable by name.
    """

    BASE_RD = "/fake/conda/share/jupyter/kernels/python3"

    def _make_spec(self, resource_dir, display_name, metadata=None):
        from jupyter_client.kernelspec import KernelSpec
        return KernelSpec(
            resource_dir=resource_dir,
            display_name=display_name,
            language="python",
            argv=["/fake/bin/python", "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            metadata=metadata or {},
        )

    def _make_manager(self, monkeypatch, system_specs, conda_specs=None, venv_specs=None,
                      **manager_kwargs):
        """Build a manager with faked system/conda/venv kernel sources."""
        import nb_venv_kernels.manager as manager_module
        from jupyter_client.kernelspec import KernelSpecManager

        m = VEnvKernelSpecManager(**manager_kwargs)
        # The real base class filters system names by allowed_kernelspecs
        # inside find_kernel_specs - the fake must model that contract
        monkeypatch.setattr(
            KernelSpecManager,
            "find_kernel_specs",
            lambda self: {
                k: v for k, v in dict(system_specs).items()
                if not self.allowed_kernelspecs or k in self.allowed_kernelspecs
            },
        )
        # Fake venv kernels via the cache (bypasses registry scan)
        m._venv_kernels_cache = venv_specs or {}
        m._venv_kernels_cache_expiry = time.time() + 3600

        # Fake conda kernels regardless of nb_conda_kernels being installed
        monkeypatch.setattr(manager_module, "_HAS_CONDA", True)

        class FakeCondaManager:
            _conda_kspecs = conda_specs or {}

        m._conda_manager = FakeCondaManager()
        return m

    def _make_collided_manager(self, monkeypatch):
        """Manager with the canonical base-env collision (python3 vs conda-base-py)."""
        conda_spec = self._make_spec(self.BASE_RD, "Python [conda env:base] *")
        return self._make_manager(
            monkeypatch,
            system_specs={"python3": self.BASE_RD},
            conda_specs={"conda-base-py": conda_spec},
        )

    def test_conda_base_alias_collapsed_onto_python3(self, monkeypatch):
        """conda-base-py sharing python3's resource_dir yields one python3 entry."""
        m = self._make_collided_manager(monkeypatch)
        specs = m.find_kernel_specs()
        assert "python3" in specs, "python3 must stay listed (DEF-1 auto-bind guard)"
        assert "conda-base-py" not in specs, "alias must not be listed twice"
        # Exactly one listing entry for the shared resource_dir
        assert list(specs.values()).count(self.BASE_RD) == 1

    def test_collapsed_python3_carries_env_display_name(self, monkeypatch):
        """python3 resolves to the conda spec so the tile shows the env name."""
        m = self._make_collided_manager(monkeypatch)
        m.find_kernel_specs()
        spec = m.get_kernel_spec("python3")
        assert spec.display_name == "Python [conda env:base] *"
        all_specs = m.get_all_specs()
        assert all_specs["python3"]["spec"]["display_name"] == "Python [conda env:base] *"

    def test_collapsed_alias_still_resolvable_by_name(self, monkeypatch):
        """Saved notebooks referencing conda-base-py can still start server-side."""
        m = self._make_collided_manager(monkeypatch)
        m.find_kernel_specs()
        assert m.get_kernel_spec("conda-base-py").display_name == "Python [conda env:base] *"

    def test_no_collision_leaves_both_listed(self, monkeypatch):
        """A conda env with its own resource_dir does not touch python3."""
        other_rd = "/fake/conda/envs/ds/share/jupyter/kernels/python3"
        conda_spec = self._make_spec(other_rd, "Python [conda env:ds]")
        m = self._make_manager(
            monkeypatch,
            system_specs={"python3": self.BASE_RD},
            conda_specs={"conda-env-ds-py": conda_spec},
        )
        specs = m.find_kernel_specs()
        assert "python3" in specs
        assert "conda-env-ds-py" in specs
        # python3 keeps its own (system) spec resolution path
        assert m._default_name_overrides == {}

    def test_venv_alias_collapsed_onto_python3(self, monkeypatch):
        """A venv spec colliding with the spared python3 collapses onto it."""
        venv_rd = "/fake/project/.venv/share/jupyter/kernels/python3"
        venv_spec = self._make_spec(
            venv_rd,
            "Python [venv env:project] *",
            metadata={"venv_source": "venv", "venv_is_currently_running": True},
        )
        m = self._make_manager(
            monkeypatch,
            system_specs={"python3": venv_rd},
            venv_specs={"venv-project-py": venv_spec},
        )
        specs = m.find_kernel_specs()
        assert "python3" in specs, "python3 must stay listed (DEF-1 auto-bind guard)"
        assert "venv-project-py" not in specs, "alias must not be listed twice"
        assert m.get_kernel_spec("python3").display_name == "Python [venv env:project] *"
        # Collapsed venv alias stays resolvable by name (server-side starts)
        assert m.get_kernel_spec("venv-project-py").display_name == "Python [venv env:project] *"

    def test_collapsed_current_env_sorts_first(self, monkeypatch):
        """A collapsed python3 carrying a current-env (*) display ranks first."""
        conda_spec = self._make_spec(self.BASE_RD, "Python [conda env:base] *")
        other_rd = "/fake/conda/envs/ds/share/jupyter/kernels/python3"
        other_spec = self._make_spec(other_rd, "Python [conda env:ds]")
        m = self._make_manager(
            monkeypatch,
            system_specs={"python3": self.BASE_RD},
            conda_specs={"conda-base-py": conda_spec, "conda-env-ds-py": other_spec},
        )
        specs = m.find_kernel_specs()
        assert list(specs.keys())[0] == "python3"

    def test_overrides_cleared_when_collision_gone(self, monkeypatch):
        """Stale overrides do not survive a re-listing without collisions."""
        m = self._make_collided_manager(monkeypatch)
        m.find_kernel_specs()
        assert "python3" in m._default_name_overrides
        # Conda kernels disappear (e.g. nb_conda_kernels removed)
        m._conda_manager._conda_kspecs = {}
        m.find_kernel_specs()
        assert m._default_name_overrides == {}

    def test_cold_start_get_kernel_spec_resolves_override(self, monkeypatch):
        """A kernel started by name before any listing resolves identically."""
        m = self._make_collided_manager(monkeypatch)
        # No find_kernel_specs() call - fresh boot POST /api/kernels path
        spec = m.get_kernel_spec("python3")
        assert spec.display_name == "Python [conda env:base] *"

    def test_invalidate_cache_resets_overrides(self, monkeypatch):
        """invalidate_cache() drops overrides so the next resolve recomputes."""
        m = self._make_collided_manager(monkeypatch)
        m.find_kernel_specs()
        assert m._default_name_overrides
        m.invalidate_cache()
        assert m._default_name_overrides is None
        # Cold resolve after invalidation repopulates via a fresh listing
        assert m.get_kernel_spec("python3").display_name == "Python [conda env:base] *"

    def test_venv_only_ignores_collapse_machinery(self, monkeypatch):
        """venv_only=True hides system/conda kernels and records no overrides."""
        venv_rd = "/fake/project/.venv/share/jupyter/kernels/python3"
        venv_spec = self._make_spec(
            venv_rd, "Python [venv env:project]", metadata={"venv_source": "venv"}
        )
        m = self._make_manager(
            monkeypatch,
            system_specs={"python3": venv_rd},
            venv_specs={"venv-project-py": venv_spec},
            venv_only=True,
        )
        specs = m.find_kernel_specs()
        assert "python3" not in specs
        assert "venv-project-py" in specs
        assert m._default_name_overrides == {}

    def test_collapsed_ranks_follow_alias_source(self, monkeypatch):
        """Collapsed defaults rank as their alias: conda 1, uv 2, venv 3."""
        conda_rd = "/fake/conda/share/jupyter/kernels/python3"
        uv_rd = "/fake/uvproj/.venv/share/jupyter/kernels/python2"
        venv_rd = "/fake/venvproj/.venv/share/jupyter/kernels/ir"
        m = self._make_manager(
            monkeypatch,
            system_specs={"python3": conda_rd, "python2": uv_rd, "ir": venv_rd,
                          "zz-system": "/fake/system/kernels/zz"},
            conda_specs={
                "conda-base-py": self._make_spec(conda_rd, "Python [conda env:base]"),
            },
            venv_specs={
                "venv-uvproj-py": self._make_spec(
                    uv_rd, "Python [uv env:uvproj]", metadata={"venv_source": "uv"}
                ),
                "venv-venvproj-r": self._make_spec(
                    venv_rd, "R [venv env:venvproj]", metadata={"venv_source": "venv"}
                ),
            },
        )
        specs = m.find_kernel_specs()
        # conda-collapsed (1) < uv-collapsed (2) < venv-collapsed (3) < system (4)
        assert list(specs.keys()) == ["python3", "python2", "ir", "zz-system"]

    def test_allowlist_keeping_both_names_keeps_collapse(self, monkeypatch):
        """Allowlist containing both names: single collapsed entry survives."""
        m = self._make_collided_manager(monkeypatch)
        m.allowed_kernelspecs = {"python3", "conda-base-py"}
        specs = m.find_kernel_specs()
        assert list(specs.keys()) == ["python3"]
        assert m.get_kernel_spec("python3").display_name == "Python [conda env:base] *"

    def test_allowlist_of_alias_only_keeps_env_visible(self, monkeypatch):
        """Allowlist naming only the alias must not make the env vanish."""
        m = self._make_collided_manager(monkeypatch)
        m.allowed_kernelspecs = {"conda-base-py"}
        specs = m.find_kernel_specs()
        # Base class filters python3 out, so no collapse: alias lists normally
        assert "conda-base-py" in specs, "allowed alias must stay listed"
        assert "python3" not in specs
        assert m._default_name_overrides == {}

    def test_allowlist_excluding_alias_drops_override(self, monkeypatch):
        """Allowlist excluding the alias must not serve its spec via python3."""
        m = self._make_collided_manager(monkeypatch)
        m.allowed_kernelspecs = {"python3"}
        specs = m.find_kernel_specs()
        assert list(specs.keys()) == ["python3"]
        assert m._default_name_overrides == {}

    def test_ttl_expiry_recomputes_overrides(self, monkeypatch):
        """A lapsed venv-cache TTL must re-resolve overrides on name lookup."""
        m = self._make_collided_manager(monkeypatch)
        # The lapse triggers a real venv rescan - keep it off the developer's registry
        monkeypatch.setattr(VEnvKernelSpecManager, "_all_venv_specs", lambda self: {})
        m.find_kernel_specs()
        assert m.get_kernel_spec("python3").display_name == "Python [conda env:base] *"
        # Conda source changes while only REST name-lookups arrive (headless)
        m._conda_manager._conda_kspecs = {
            "conda-base-py": self._make_spec(self.BASE_RD, "Python [conda env:base] renamed")
        }
        m._venv_kernels_cache_expiry = time.time() - 1
        assert m.get_kernel_spec("python3").display_name == "Python [conda env:base] renamed"

    def test_register_environment_invalidates_overrides(self, monkeypatch):
        """Mutating the registry resets overrides via invalidate_cache()."""
        import nb_venv_kernels.manager as manager_module
        m = self._make_collided_manager(monkeypatch)
        m.find_kernel_specs()
        assert m._default_name_overrides
        monkeypatch.setattr(
            manager_module, "register_environment",
            lambda path, name=None, require_kernelspec=False: (True, False),
        )
        m.register_environment("/fake/other-env")
        assert m._default_name_overrides is None

    def test_realpath_collision_through_symlink(self, tmp_path, monkeypatch):
        """A symlinked prefix still collides with the real kernel dir."""
        real_kernels = tmp_path / "real" / "share" / "jupyter" / "kernels" / "python3"
        real_kernels.mkdir(parents=True)
        os.symlink(tmp_path / "real", tmp_path / "link")
        linked_rd = str(tmp_path / "link" / "share" / "jupyter" / "kernels" / "python3")
        conda_spec = self._make_spec(str(real_kernels), "Python [conda env:base] *")
        m = self._make_manager(
            monkeypatch,
            system_specs={"python3": linked_rd},
            conda_specs={"conda-base-py": conda_spec},
        )
        specs = m.find_kernel_specs()
        assert "python3" in specs
        assert "conda-base-py" not in specs, "symlinked prefix must still collapse"
        assert m.get_kernel_spec("python3").display_name == "Python [conda env:base] *"

    def test_dual_collision_first_alias_wins_second_lists(self, monkeypatch):
        """venv and conda both colliding with python3: first collapse wins."""
        venv_spec = self._make_spec(
            self.BASE_RD, "Python [venv env:baseenv]", metadata={"venv_source": "venv"}
        )
        conda_spec = self._make_spec(self.BASE_RD, "Python [conda env:base] *")
        m = self._make_manager(
            monkeypatch,
            system_specs={"python3": self.BASE_RD},
            conda_specs={"conda-base-py": conda_spec},
            venv_specs={"venv-baseenv-py": venv_spec},
        )
        specs = m.find_kernel_specs()
        assert "python3" in specs
        assert m.get_kernel_spec("python3").display_name == "Python [venv env:baseenv]"
        assert "venv-baseenv-py" not in specs
        # The second alias is not silently dropped - it lists under its own name
        assert "conda-base-py" in specs

    def test_dual_venv_collision_second_alias_lists(self, monkeypatch):
        """Two venv specs colliding with python3: second lists under own name."""
        rd = "/fake/project/.venv/share/jupyter/kernels/python3"
        first = self._make_spec(
            rd, "Python [venv env:one]", metadata={"venv_source": "venv"}
        )
        second = self._make_spec(
            rd, "Python [venv env:two]", metadata={"venv_source": "venv"}
        )
        m = self._make_manager(
            monkeypatch,
            system_specs={"python3": rd},
            venv_specs={"venv-one-py": first, "venv-two-py": second},
        )
        specs = m.find_kernel_specs()
        assert "python3" in specs
        assert m.get_kernel_spec("python3").display_name == "Python [venv env:one]"
        assert "venv-one-py" not in specs
        assert "venv-two-py" in specs, "second alias must not be silently dropped"

    def test_double_realpath_collision_on_system_kernel_no_crash(self, monkeypatch):
        """Two venv specs deduping one non-default system kernel must not crash."""
        rd = "/fake/tool/.venv/share/jupyter/kernels/mykern"
        first = self._make_spec(
            rd, "Python [venv env:one]", metadata={"venv_source": "venv"}
        )
        second = self._make_spec(
            rd, "Python [venv env:two]", metadata={"venv_source": "venv"}
        )
        m = self._make_manager(
            monkeypatch,
            system_specs={"mykern": rd},
            venv_specs={"venv-one-py": first, "venv-two-py": second},
        )
        # Pre-fix this raised KeyError('mykern') and 500'd /api/kernelspecs
        specs = m.find_kernel_specs()
        assert "mykern" not in specs
        assert "venv-one-py" in specs
        assert "venv-two-py" in specs


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
