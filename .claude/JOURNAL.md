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

7. **Task - Composition-based conda integration**: Rewrote manager to use composition instead of inheritance for CondaKernelSpecManager<br>
   **Result**: VEnvKernelSpecManager now creates separate CondaKernelSpecManager instance internally, fixes method override conflicts, properly combines system + venv + conda kernels, removes duplicate system kernels when conda provides same resource

8. **Task - Fix venv kernel invocation**: Changed kernel execution to use venv python directly with environment variables<br>
   **Result**: Removed runner script approach, kernel argv uses venv's python path directly, sets VIRTUAL_ENV and PATH env vars in kernel spec, keeps conda bin in PATH for pip/uv tools, clears CONDA_PREFIX to avoid conda activation confusion

9. **Task - Config backup/restore**: Added backup functionality to config enable/disable commands<br>
   **Result**: `config enable` backs up existing jupyter_config.json before modifying, `config disable` restores from backup if available, backup stored as *.nb_venv_kernels.bak

10. **Task - Clean debug code**: Removed verbose debug logging from manager.py<br>
    **Result**: Removed all debug/info logging, kept only error and warning logs for kernel.json load failures

11. **Task - Update README**: Updated README to reflect current implementation<br>
    **Result**: Changed runner script description to direct python + env vars approach, added config backup/restore note, fixed name_format default example

12. **Task - Auto-enable config on install**: Added auto-configuration via jupyter_server_config.d<br>
    **Result**: Created nb_venv_kernels.json config fragment that sets kernel_spec_manager_class and jpserver_extensions, updated README install instructions

13. **Task - Remove console error**: Simplified labextension to not require server extension API<br>
    **Result**: Removed API call from index.ts, deleted request.ts, extension now just logs activation message without calling server endpoints
