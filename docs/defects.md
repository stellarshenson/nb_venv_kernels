# Defects - nb_venv_kernels

`[ ]` open, `[x]` fixed. Dated notes under each track how it evolved.

## Authors

- `@kj` Konrad Jelen

## Kernel discovery `KERNEL`

kernelspec listing and name resolution in VEnvKernelSpecManager

- [x] `DEF-KERNEL-1` **Stale notebook cell context menu when nb_venv_kernels installed** - MAJOR; right-click inside a notebook code cell editor (JL 4.6.1) opens a degraded/empty menu (no `jump to definition`, items do not highlight); cause: `VEnvKernelSpecManager.find_kernel_specs()` dropped the default `python3` spec (dedup vs the conda base resource_dir), so a notebook saved with `kernelspec.name=python3` could not bind a kernel - the failed kernel resolution left the jupyterlab-lsp virtual document disposed, and its context-menu hook then threw and aborted the Lumino menu build; fix: keep default names (`python3`/`python2`/`ir`) in `find_kernel_specs()` so standard notebooks resolve; `nb_venv_kernels/manager.py`
  - root-cause: 2026-09-29T13:21:56Z @kj find_kernel_specs() removed the default python3 spec as a duplicate of the conda base resource_dir, so notebooks saved with kernelspec.name=python3 could not bind a kernel
  - evidence: python3 notebook binds "Python 3 (ipykernel)", 0 disposed errors, 37-item menu incl. Jump to definition; DEF-1 guard test in TestDefaultKernelDedup; shipped in 1.2.40
  - test-tags: UNIT, MANUAL
  - repro: conda base plus nb_venv_kernels enabled; open a notebook saved with kernelspec.name=python3; right-click inside a code cell
  - log: 2026-07-01T00:00:00Z @kj reported: outside-cell menu correct and highlights; in-cell menu stale, no jump-to-definition, no hover highlight
  - log: 2026-07-01T00:00:00Z @kj investigating: ablation pins `nb_venv_kernels` as sole culprit; ruled out shipped CSS (empty), `schema/`, declarative `jupyter.lab.menus.context`, and any cell/`mousedown`/`contextmenu` handler; v1.2.37 UI-strip did not fix; reproducing in isolated container from `stellars/stellars-jupyterlab-ds` (jl-4.6.1)
  - log: 2026-07-01T00:00:00Z @kj isolated-repro NEGATIVE: container `nbvk-repro` from same image (nb_venv_kernels server+frontend+companion active); real 592KB notebook, 2K viewport, windowed rendering, kernel idle; cross-cell right-click x4 both directions - menu always correct (37 editor items incl. Jump to definition), connected, highlights on hover, zero notebook mutations at click time; bug did not reproduce, contradicts the re-render hypothesis
  - log: 2026-07-01T00:00:00Z @kj ROOT CAUSE: `VEnvKernelSpecManager.find_kernel_specs()` (`manager.py:419-421`) deletes the standard `python3` spec (dedup vs the conda base `resource_dir`), so `/api/kernelspecs` has no `python3`; a notebook saved with the universal default `kernelspec.name=python3` cannot auto-bind -> "Select Kernel"/"No Kernel" -> jupyterlab-lsp virtual document disposed -> right-click throws `isContextMenuOverToken: Virtual document of adapter disposed!`, aborting the Lumino context-menu build -> empty/degraded menu (no items, no highlight). Reproduced locally on `localhost:8899` (10 envs); two-arm test: `python3` notebook -> No Kernel + 36x disposed errors + empty menu, `conda-base-py` notebook -> kernel binds, errors gone, menu healthy. Fix: keep/alias `python3` in `find_kernel_specs()` so standard notebooks resolve
  - log: 2026-07-01T00:00:00Z @kj fixed+verified: guarded default names in `find_kernel_specs()` (`manager.py:404,418,428`); local lab now lists `python3`; the previously-broken `python3` notebook binds "Python 3 (ipykernel)", 0 disposed errors, full 37-item menu incl. Jump to definition. Verified by syncing the file into site-packages + restart (no version bump); proper build/commit pending approval
  - log: 2026-09-29T13:00:07Z @kj edited repro added "conda base plus nb_venv_kernels enabled; open a notebook saved with kernelspec.name=python3; right-click inside a code cell"; test-tags added "UNIT, MANUAL"; evidence added "python3 notebook binds "Python 3 (ipykernel)", 0 disposed errors, 37-item menu incl. Jump to definition; DEF-1 guard test in TestDefaultKernelDedup; shipped in 1.2.40"
- [x] `DEF-KERNEL-2` **Conda base env rendered as two launcher tiles** - MEDIUM; fresh env shows ONE conda base env as TWO tiles: `Python [conda env:base] *` (`conda-base-py`, nb_conda_kernels) and plain `Python 3` (`python3`, on-disk spec); cause: the DEF-1 fix spares default names from dedup while nb_conda_kernels contributes an alias for the SAME `resource_dir` - two names, two tiles; fix: collapse the alias onto the default name - `find_kernel_specs()` lists only `python3` (binding guarantee intact) and records `_default_name_overrides` so `get_kernel_spec("python3")` serves the env-labelled conda/venv spec; alias name stays resolvable; `nb_venv_kernels/manager.py`
  - root-cause: 2026-09-29T13:21:56Z @kj the DEF-KERNEL-1 fix kept python3 listed while nb_conda_kernels also listed conda-base-py for the same resource_dir, so one env had two names
  - evidence: live listing shows one python3 entry labelled "Python [conda env:base] *"; 20 TestDefaultKernelDedup tests plus real-conda integration test, suite 111 passed 1 skipped; shipped in 1.2.45
  - test-tags: UNIT, INTEGRATION
  - repro: fresh install with nb_conda_kernels and the on-disk python3 spec in conda base; open the Launcher
  - log: 2026-07-19T00:00:00Z @kj reported: two tiles for base env on fresh install; user wants envs properly named, no bare "Python 3" duplicate
  - log: 2026-07-19T00:00:00Z @kj analysis: rejected the drop-python3-from-listing proposal - identical to pre-1.2.40 code (the `get_kernel_spec` super() fallback existed then and DEF-1 still occurred: JupyterLab auto-bind consults the kernelspec LISTING, not name resolution)
  - log: 2026-07-19T00:00:00Z @kj fixed+verified: reverse collapse implemented; live listing shows a single `python3` entry displaying `Python [conda env:base] *`, zero resource_dir collisions, `conda-base-py` still resolvable by name; 7 new tests in `TestDefaultKernelDedup` (collapse, DEF-1 guard, alias resolution, no-collision no-op, venv variant, sort rank, stale-override clearing); full suite 100 passed. Tradeoff: notebooks saved with `kernelspec.name=conda-base-py` get the kernel picker once (name no longer listed), then re-save as `python3`
  - log: 2026-07-19T00:00:00Z @kj hardened after 2-round adversarial review (bug-hunter, qa-engineer, architect): allowlist seam (collapse cancelled unless both names allowed; base class filters system names itself), cold-start + TTL staleness (None sentinel, `get_kernel_spec` re-lists on lapse), single `invalidate_cache()` owner (manager x3 + routes refresh), realpath comparison for symlinked prefixes, `kspecs.pop` KeyError guard, dual-collision first-wins with second alias listed, `_rank_spec` extracted; `TestDefaultKernelDedup` grown to 18 tests (allowlist trio, cold start, invalidation wiring, TTL re-resolution, symlink, dual collision, ranks, venv_only)
  - log: 2026-09-29T13:00:07Z @kj edited repro added "fresh install with nb_conda_kernels and the on-disk python3 spec in conda base; open the Launcher"; test-tags added "UNIT, INTEGRATION"; evidence added "live listing shows one python3 entry labelled "Python [conda env:base] *"; 21 TestDefaultKernelDedup tests plus real-conda integration test, suite 111 passed 1 skipped; shipped in 1.2.45"
  - log: 2026-09-29T14:45:20Z @kj edited evidence "live listing shows one python3 entry labelled "Python [conda env:base] *"; 21 TestDefaultKernelDedup tests plus real-conda integration test, suite 111 passed 1 skipped; shipped in 1.2.45" -> "live listing shows one python3 entry labelled "Python [conda env:base] *"; 20 TestDefaultKernelDedup tests plus real-conda integration test, suite 111 passed 1 skipped; shipped in 1.2.45"
- [x] `DEF-KERNEL-5` **Kernel picker names differ from listing for venv and env folders** - MEDIUM; env at myproj/venv lists as myproj but the kernel shows Python [venv env:venv]; two such projects show venv and venv_1
  - evidence: reproduced before the fix (myproj/venv listed as myproj, kernel env:venv); TestEnvNaming passes for venv, .env, env, .venv; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5
  - test-tags: UNIT
  - repro: python -m venv myproj/venv, add ipykernel, register it; compare nb_venv_kernels list with the kernel picker
  - root-cause: 2026-09-29T13:21:50Z @kj the env-name rule is written five times with four variants; the kernel path maps only .venv to the parent folder
  - log: 2026-09-29T13:21:50Z @kj added
  - log: 2026-09-29T13:37:06Z @kj edited test-tags added "UNIT"
  - log: 2026-09-29T13:50:52Z @kj closed: fixed: registry.env_display_name and is_conda_base_dir are the one naming rule; five copies removed
- [x] `DEF-KERNEL-6` **Manager options passed as arguments crash conda discovery** - MEDIUM; VEnvKernelSpecManager(name_format="{environment} ({source})") raises KeyError 'source' in nb_conda_kernels; venv_only=True warns that traitlets will raise; config files unaffected; `nb_venv_kernels/manager.py`
  - evidence: TestConfigTraits::test_name_format_sets_display_name passes; manager tests pass with traitlets DeprecationWarning as error; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5
  - test-tags: UNIT
  - repro: with nb_conda_kernels installed: python -c 'from nb_venv_kernels.manager import VEnvKernelSpecManager as M; M(name_format="{source}")'
  - root-cause: 2026-09-29T13:29:52Z @kj **init** forwards every keyword argument to CondaKernelSpecManager(**kwargs), which does not know this manager's traits
  - log: 2026-09-29T13:29:52Z @kj added
  - log: 2026-09-29T13:37:06Z @kj edited test-tags added "UNIT"
  - log: 2026-09-29T13:50:52Z @kj closed: fixed: CondaKernelSpecManager(parent=self) shares config and log only

## Frontend `FRONT`

scan command, refresh command and the scan results dialog in src/index.ts

- [x] `DEF-FRONT-3` **Scan results dialog renders environment names as HTML** - CRITICAL; a scanned project directory named like <img src=x onerror=...> runs script in JupyterLab; `src/index.ts` buildResultsContent
  - evidence: jest escaping tests pass and fail with escaping disabled; Playwright scan dialog test passes; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5
  - test-tags: UNIT, E2E
  - repro: create project dir named <img src=x onerror=alert(1)> holding a venv; run nb_venv_kernels:scan
  - root-cause: 2026-09-29T13:21:50Z @kj buildResultsContent puts env name, path, action and type into innerHTML without escaping
  - log: 2026-09-29T13:21:50Z @kj added
  - log: 2026-09-29T13:37:06Z @kj edited test-tags added "UNIT, E2E"
  - log: 2026-09-29T13:50:52Z @kj closed: fixed: every server string escaped before innerHTML; rendering moved to src/scanResults.ts

## CLI `CLI`

the nb_venv_kernels command-line tool

- [x] `DEF-CLI-4` **Help text states scan depth default 7** - MINOR; `nb_venv_kernels --help` and `scan --help` say default depth 7; the scan uses 10; `nb_venv_kernels/cli.py`
  - evidence: test_cli.py::test_help_states_scan_depth_default passes; make test 2026-09-29: pytest 133 passed 1 skipped, jest 5/5
  - test-tags: UNIT
  - repro: run nb_venv_kernels scan --help and compare with VEnvKernelSpecManager.scan_depth
  - root-cause: 2026-09-29T13:21:50Z @kj help strings hardcode 7 while the default comes from the scan_depth trait, which is 10
  - log: 2026-09-29T13:21:50Z @kj added
  - log: 2026-09-29T13:37:06Z @kj edited test-tags added "UNIT"
  - log: 2026-09-29T13:50:52Z @kj closed: fixed: both help strings read DEFAULT_SCAN_DEPTH from the scan_depth trait; README, API.md, MECHANICS corrected to 10
- [x] `DEF-CLI-7` **Local conda envs sort among venvs in list** - MINOR; nb_venv_kernels list puts 'conda (local)' rows after uv, among the venvs; sort_key matches only the type 'conda'; `nb_venv_kernels/cli.py`
  - evidence: test_cli.py::test_list_sorts_by_type passes and fails on the old sort; make test 2026-09-29: pytest 136 passed 1 skipped, jest 5/5
  - repro: register a venv named aaa and have a local conda env; run nb_venv_kernels list --json; conda (local) sorts after venv
  - test-tags: UNIT
  - root-cause: 2026-09-29T14:44:26Z @kj list_environments emits the type 'conda (local)', and sort_key tests only for 'conda' and 'uv', so it falls through to the venv rank
  - log: 2026-09-29T14:44:26Z @kj added
  - log: 2026-09-29T14:55:45Z @kj closed: fixed: sort_key keys on the type values list_environments emits (conda, conda (local), uv, then venv)
