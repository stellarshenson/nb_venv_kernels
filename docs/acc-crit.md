# Acceptance Criteria - nb_venv_kernels

nb_venv_kernels lists Jupyter kernels from registered venv, uv and conda environments. `VEnvKernelSpecManager` replaces the server's kernel spec manager; a CLI, REST endpoints and two frontend commands manage the registries.

## Authors

- `@kj` Konrad Jelen

## Kernel discovery `KERNEL`

which kernels the kernelspec listing holds and how they are named

- [x] `ACC-KERNEL-1` **Venv kernels listed** - HIGH; a registered venv with ipykernel lists a kernel named venv-<env>-py
  - evidence: test_manager.py::TestVenvKernelDiscovery::test_venv_creation_and_registration passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: create venv with ipykernel, register, assert venv-<env>-py in find_kernel_specs()
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:36Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-2` **Uv kernels listed** - HIGH; an env whose pyvenv.cfg holds a uv line lists with metadata venv_source uv
  - evidence: test_manager.py::TestUvKernelDiscovery::test_uv_kernel_discovery passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: create uv-marked env, register, assert venv_source == uv
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:36Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-3` **Conda kernels listed** - HIGH; with nb_conda_kernels installed, conda envs with ipykernel appear in the listing
  - evidence: test_manager.py::TestCondaKernelDiscovery::test_conda_base_discovery passed (new-env variant skips on conda timing); make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: create conda env with ipykernel, assert its kernel in find_kernel_specs()
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:36Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-4` **Default display name** - MEDIUM; kernel display name reads Python [<source> env:<name>]
  - evidence: test_manager.py::TestKernelSpecDetails::test_kernel_display_name passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register venv myproj/.venv, assert display name Python [venv env:myproj]
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:36Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-5` **Name from project folder** - MEDIUM; an env folder named .venv, venv, .env or env takes the parent folder name, the same in the kernel picker and in the listing
  - evidence: test_manager.py::TestEnvNaming::test_env_folder_takes_project_name for venv, .env, env, .venv passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register myproj/venv, assert list name and kernel display name both use myproj
  - test-tags: UNIT
  - log: 2026-09-29T13:23:36Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-6` **Custom name** - MEDIUM; a name given at registration replaces the derived name in the display name
  - evidence: test_manager.py::TestKernelSpecDetails::test_kernel_display_name_with_custom_name passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register with -n custom, assert display name holds custom
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:36Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-7` **Unique kernel names** - MEDIUM; two envs with the same name get distinct kernel names through a _1 suffix
  - evidence: test_manager.py::TestKernelSpecDetails::test_kernel_names_unique_with_duplicate_custom_names passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register two envs with one custom name, assert two distinct kernel names
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:36Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-8` **Kernel runs the env python** - HIGH; a venv kernel runs <env>/bin/python with VIRTUAL_ENV set to the env path
  - evidence: test_manager.py::TestVenvKernelDiscovery::test_venv_kernel_spec_structure asserts argv[0] == <env>/bin/python and VIRTUAL_ENV; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register venv, assert argv[0] and env VIRTUAL_ENV
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:36Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-9` **Current env marked** - LOW; the env the server runs in gets ' *' appended to its display name and sorts first
  - evidence: test_manager.py::TestEnvNaming::test_current_env_marked and test_listing_sort_order passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: fake spec with venv_is_currently_running, assert first in listing
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-10` **Sort order** - MEDIUM; listing order is current env, conda, uv, venv, then system kernels
  - evidence: test_manager.py::test_listing_sort_order passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: fake one spec per source, assert find_kernel_specs() key order
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-11` **python3 stays listed** - CRITICAL; python3 stays in the listing when a conda or venv spec shares its resource_dir
  - evidence: test_manager.py::TestDefaultKernelDedup::test_conda_base_alias_collapsed_onto_python3 and test_venv_alias_collapsed_onto_python3 passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: fake conda alias on the python3 resource_dir, assert python3 in find_kernel_specs()
  - test-tags: UNIT, INTEGRATION
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:40Z @kj closed: met
- [x] `ACC-KERNEL-12` **One tile per env** - HIGH; an env whose alias shares the default spec resource_dir lists once, as python3 with the env display name
  - evidence: test_manager.py::TestCondaKernelDiscovery::test_conda_base_renders_single_listing_entry and TestDefaultKernelDedup::test_collapsed_python3_carries_env_display_name passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: real conda base, assert one listing entry per resource_dir
  - test-tags: UNIT, INTEGRATION
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-KERNEL-13` **Collapsed alias resolves** - MEDIUM; the collapsed alias name, e.g. conda-base-py, still resolves through get_kernel_spec()
  - evidence: test_manager.py::TestDefaultKernelDedup::test_collapsed_alias_still_resolvable_by_name passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: collapse conda-base-py, assert get_kernel_spec(conda-base-py) returns its spec
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-KERNEL-14` **Edge: env without ipykernel** - MEDIUM; a registered env without a kernelspec lists no kernel and raises no error
  - evidence: test_manager.py::TestMixedEnvironments::test_environment_without_ipykernel_registers_by_default passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register venv without ipykernel, assert find_kernel_specs() runs and lists none for it
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-KERNEL-15` **Edge: env folder deleted** - MEDIUM; a registered env whose folder is gone lists no kernel and raises no error
  - evidence: test_manager.py::TestEnvNaming::test_deleted_env_lists_no_kernel passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register venv, delete folder, assert find_kernel_specs() runs without it
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met

## Configuration `CONFIG`

VEnvKernelSpecManager traits set in jupyter_server_config.py

- [x] `ACC-CONFIG-16` **venv_only** - MEDIUM; venv_only=True hides system and conda kernels
  - evidence: test_manager.py::TestDefaultKernelDedup::test_venv_only_ignores_collapse_machinery passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: fake system and venv specs, venv_only=True, assert only venv listed
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-CONFIG-17` **env_filter** - MEDIUM; an env whose path matches the env_filter regex lists no kernel
  - evidence: test_manager.py::TestConfigTraits::test_env_filter_excludes_matching_path passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register two venvs, env_filter matching one, assert only the other listed
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-CONFIG-18` **name_format** - MEDIUM; name_format sets the kernel display name
  - evidence: test_manager.py::TestConfigTraits::test_name_format_sets_display_name passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: name_format={environment} ({source}), assert display name myproj (venv)
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-CONFIG-19` **require_kernelspec on** - MEDIUM; with require_kernelspec=True, registering an env without ipykernel fails
  - evidence: test_registry.py::TestEnvironmentRegistration::test_register_venv_without_kernelspec_rejected_when_required passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register venv without ipykernel with require_kernelspec, assert ValueError
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-CONFIG-20` **require_kernelspec off by default** - MEDIUM; by default an env without ipykernel is registered
  - evidence: test_registry.py::TestEnvironmentRegistration::test_register_venv_without_kernelspec_allowed_by_default passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register venv without ipykernel, assert registered
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met

## Registry `REG`

the ~/.venv and ~/.uv environments.txt registries

- [x] `ACC-REG-21` **Venv registry** - HIGH; registering a venv appends its path to ~/.venv/environments.txt
  - evidence: test_registry.py::TestEnvironmentRegistration::test_register_venv passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register venv, read the registry file
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-REG-22` **Uv registry** - HIGH; registering a uv env appends its path to ~/.uv/environments.txt
  - evidence: test_registry.py::TestUvDetection::test_uv_registered_in_uv_registry passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register uv env, read the uv registry file
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-REG-23` **Unregister** - HIGH; unregister removes the path from both registries
  - evidence: test_registry.py::TestEnvironmentRegistration::test_unregister_venv passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register then unregister, assert path absent
  - test-tags: UNIT
  - log: 2026-09-29T13:23:37Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-REG-24` **Edge: path missing** - MEDIUM; registering a path that does not exist fails with 'Environment path does not exist'
  - evidence: test_registry.py::TestEnvironmentRegistration::test_register_invalid_path matches the message; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register /nonexistent, assert ValueError message
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-REG-25` **Edge: not a Python env** - MEDIUM; registering a folder without bin/python fails with 'Not a valid Python environment'
  - evidence: test_registry.py::TestEnvironmentRegistration::test_register_non_venv_directory matches the message; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register empty dir, assert ValueError message
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-REG-26` **Edge: registered twice** - MEDIUM; registering an already registered path adds no second registry line
  - evidence: test_registry.py::TestEnvironmentRegistration::test_double_registration asserts one registry entry; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register twice, assert one line
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:41Z @kj closed: met
- [x] `ACC-REG-27` **Edge: name taken** - MEDIUM; a custom name already in use is stored with a _1 suffix
  - evidence: test_registry.py::TestEnvironmentRegistration::test_name_taken_gets_suffix passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register two envs with -n same, assert second stored as same_1
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-REG-28` **Rename** - LOW; registering a registered path with a new name replaces the stored name
  - evidence: test_registry.py::TestEnvironmentRegistration::test_update_custom_name passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register with name a then b, assert b stored
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met

## Scan `SCAN`

finding and registering environments under a folder

- [x] `ACC-SCAN-29` **Scan registers envs** - HIGH; scan registers every venv and uv env found under the path
  - evidence: test_registry.py::TestDirectoryScanning::test_scan_registers_environments passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: create venvs under tmp, scan, assert registered
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-SCAN-30` **Depth limit** - MEDIUM; scan does not look deeper than the depth argument
  - evidence: test_registry.py::TestDirectoryScanning::test_scan_depth_limit passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: env at depth 3, scan depth 2, assert not found
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-SCAN-31` **Dry run** - MEDIUM; a dry run reports actions and writes nothing to the registries
  - evidence: test_registry.py::TestDirectoryScanning::test_scan_dry_run passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: scan dry_run=True, assert registry unchanged
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-SCAN-32` **Removes missing envs** - MEDIUM; scan removes registry entries whose folder is gone and reports them as remove
  - evidence: test_registry.py::TestDirectoryScanning::test_scan_removes_deleted_env passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: register, delete folder, scan, assert entry gone
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-SCAN-33` **Skips cache folders** - LOW; scan skips the folders excluded in scan_config.json, such as uv caches
  - evidence: test_registry.py::TestScanExclusions::test_scan_skips_cache_directories passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: env inside a uv cache folder, scan, assert not found
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met

## CLI `CLI`

the nb_venv_kernels command-line tool

- [x] `ACC-CLI-34` **Help states real defaults** - LOW; help text states the scan depth default the scan uses, 10
  - evidence: test_cli.py::test_help_states_scan_depth_default passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: compare nb_venv_kernels --help and scan --help with scan_depth
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-CLI-35` **list --json** - MEDIUM; list --json prints a JSON object with environments and workspace_root
  - evidence: test_cli.py::test_list_json passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: run main() with list --json, parse stdout
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-CLI-36` **config enable** - MEDIUM; config enable sets ServerApp.kernel_spec_manager_class to VEnvKernelSpecManager in jupyter_config.json
  - evidence: test_cli.py::test_config_enable_sets_manager_class passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: config enable into tmp dir, read jupyter_config.json
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-CLI-37` **config disable** - MEDIUM; config disable restores jupyter_config.json as it was before config enable
  - evidence: test_cli.py::test_config_disable_restores_original and test_config_disable_without_prior_file_removes_setting passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: write config, enable, disable, assert file equals the original
  - test-tags: UNIT
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met

## REST API `API`

the /nb-venv-kernels/* server endpoints

- [x] `ACC-API-38` **Every endpoint authenticated** - CRITICAL; every /nb-venv-kernels/* handler requires an authenticated user
  - evidence: .github/scripts/check_auth.py: 'All endpoints of the extension require authentication.'; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: run .github/scripts/check_auth.py
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:38Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-API-39` **List environments** - HIGH; GET /nb-venv-kernels/environments returns environments with paths relative to the workspace
  - evidence: test_routes.py::test_list_environments_paths_relative passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: jp_fetch environments, assert keys and relative paths
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-API-40` **Scan** - HIGH; POST /nb-venv-kernels/scan returns an action per env and a summary
  - evidence: test_routes.py::test_scan_environments and test_api.py::TestScanEnvironmentsAPI passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: jp_fetch scan, assert environments and summary
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-API-41` **Edge: scan outside workspace** - HIGH; POST /nb-venv-kernels/scan with a path outside the workspace returns 400
  - evidence: test_routes.py::test_scan_outside_workspace_denied passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: jp_fetch scan with path /, assert 400
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:50:42Z @kj closed: met
- [x] `ACC-API-42` **Edge: register outside workspace** - HIGH; POST /nb-venv-kernels/register outside the workspace returns 400 unless the path is a global conda env
  - evidence: test_routes.py::test_register_outside_workspace_denied passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: jp_fetch register /tmp path, assert 400
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:50:43Z @kj closed: met
- [x] `ACC-API-43` **Edge: missing path** - MEDIUM; POST register or unregister without path returns 400 'path is required'
  - evidence: test_routes.py::test_register_missing_path and test_unregister_missing_path passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: jp_fetch without path, assert 400
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:50:43Z @kj closed: met
- [x] `ACC-API-44` **Refresh** - MEDIUM; POST /nb-venv-kernels/refresh drops the kernel cache so the next listing reads the registries again
  - evidence: test_routes.py::test_refresh_drops_kernel_cache passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: warm the cache, jp_fetch refresh, assert the cache is empty
  - test-tags: INTEGRATION
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:50:43Z @kj closed: met

## Frontend `FRONT`

the scan and refresh commands and the scan results dialog

- [x] `ACC-FRONT-45` **Activation message** - LOW; the extension logs 'JupyterLab extension nb_venv_kernels is activated!' once
  - evidence: ui-tests 'should emit an activation console message' passed; Playwright 3/3 on a scratch-HOME test server 2026-09-29
  - test: galata: collect console, load lab, count the message
  - test-tags: E2E
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:50:43Z @kj closed: met
- [x] `ACC-FRONT-46` **Scan command** - HIGH; command nb_venv_kernels:scan runs a scan and opens 'Environment Scan Results'
  - evidence: ui-tests 'scan command opens the scan results dialog' passed; Playwright 3/3 on a scratch-HOME test server 2026-09-29
  - test: galata: execute the command, wait for the dialog title
  - test-tags: E2E
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:50:43Z @kj closed: met
- [x] `ACC-FRONT-47` **Refresh command** - MEDIUM; command nb_venv_kernels:refresh is registered
  - evidence: ui-tests 'should register refresh command' and jest 'registers exactly the scan and refresh commands' passed; Playwright 3/3 on a scratch-HOME test server 2026-09-29
  - test: galata: assert app.commands.hasCommand
  - test-tags: E2E
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:50:43Z @kj closed: met
- [x] `ACC-FRONT-48` **No own menu or palette entry** - MEDIUM; the extension adds no Kernel-menu item and no command palette entry
  - evidence: jest 'adds no Kernel-menu item and no command palette entry of its own' passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: jest: assert plugin requires/optional hold no mainmenu or commandpalette token
  - test-tags: UNIT
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:40:23Z @kj edited test "galata: search the palette for Scan for Virtual Environments, assert no match" -> "jest: assert plugin requires/optional hold no mainmenu or commandpalette token"; test-tags "E2E" -> "UNIT"
  - log: 2026-09-29T13:50:43Z @kj closed: met
- [x] `ACC-FRONT-49` **Names shown as text** - CRITICAL; the results dialog shows env names and paths as text, never as HTML
  - evidence: jest buildResultsContent escaping tests passed, and fail with escaping disabled; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: jest: buildResultsContent with name <img src=x onerror=alert(1)>, assert no img element and the name as text
  - test-tags: UNIT
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:33:05Z @kj edited test "jest: buildResultsContent with name <img onerror>, assert escaped" -> "jest: read src/index.ts without comments, assert no IMainMenu, ICommandPalette or addItem"; test-tags "UNIT" -> "UNIT"
  - log: 2026-09-29T13:34:24Z @kj edited test "jest: read src/index.ts without comments, assert no IMainMenu, ICommandPalette or addItem" -> "jest: assert plugin requires/optional hold no mainmenu or commandpalette token"
  - log: 2026-09-29T13:40:23Z @kj edited test "jest: assert plugin requires/optional hold no mainmenu or commandpalette token" -> "jest: buildResultsContent with name <img src=x onerror=alert(1)>, assert no img element and the name as text"; test-tags "UNIT" -> "UNIT"
  - log: 2026-09-29T13:50:43Z @kj closed: met
- [x] `ACC-FRONT-50` **Result row order** - LOW; dialog rows are sorted by action, then type, then name
  - evidence: jest 'orders rows by action, then type, then name' passed; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5, auth check OK
  - test: jest: shuffled envs, assert row order
  - test-tags: UNIT
  - log: 2026-09-29T13:23:39Z @kj added
  - log: 2026-09-29T13:50:43Z @kj closed: met
