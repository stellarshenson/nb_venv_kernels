# Claude Code Journal

This journal tracks substantive work on documents, diagrams, and documentation content.

---

1. **Task - Document conda kernel discovery**: Created NB_CONDA_ENV_DISCOVERY.md documenting nb_conda_kernels discovery mechanism<br>
   **Result**: Comprehensive documentation covering 5-step discovery flow, runner script, caching strategy, and configuration options

2. **Task - Implement nb_venv_kernels core**: Implemented full kernel discovery system for uv/venv environments<br>
   **Result**: Created registry.py (environment registry at ~/.uv/environments.txt), runner.py (venv activation), manager.py (VEnvKernelSpecManager), cli.py (register/unregister/list commands), updated pyproject.toml and README.md

3. **Task - Simplify GitHub workflows**: Streamlined CI/CD workflows based on jupyterlab_tabular_data_viewer_extension reference<br>
   **Result**: Consolidated build.yml with Python tests and CLI verification, removed unnecessary workflows (update-integration-tests.yml, enforce-label.yml), kept release workflows

4. **Task - Rewrite README modus primaris**: Condensed README to essential information only<br>
   **Result**: Concise README with key features, install, usage, configuration, uninstall - removed contributing section and comparison table

5. **Task - Add config CLI command**: Added `nb_venv_kernels config` command for managing Jupyter configuration<br>
   **Result**: Implemented enable/disable/show subcommands in cli.py, auto-detects config location (JUPYTER_CONFIG_DIR, CONDA_PREFIX, standard paths), updated README with new commands and simplified install flow

6. **Task - Rename and fix kernel discovery**: Renamed UvKernelSpecManager to VEnvKernelSpecManager, fixed kernel discovery bug<br>
   **Result**: Renamed all `uv_` references to `venv_`, changed registry path from `~/.uv/` to `~/.venv/`, fixed find_kernel_specs to properly combine base kernels with venv kernels without double-discovery, added `is_uv_environment()` helper to detect uv-created environments, updated display name format to use `{source}` (uv/venv) prefix
