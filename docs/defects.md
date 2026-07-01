# Defects - nb_venv_kernels

`[ ]` open, `[x]` fixed. Dated notes under each track how it evolved.

## Contents

- [DEF-1: Stale notebook cell context menu when nb_venv_kernels installed](#def-1-stale-notebook-cell-context-menu-when-nb_venv_kernels-installed) - fixed

### DEF-1: Stale notebook cell context menu when nb_venv_kernels installed

- [x] HIGH right-click inside a notebook code cell editor (JL 4.6.1) opens a degraded/empty menu (no `jump to definition`, items do not highlight); cause: `VEnvKernelSpecManager.find_kernel_specs()` dropped the default `python3` spec (dedup vs the conda base resource_dir), so a notebook saved with `kernelspec.name=python3` could not bind a kernel - the failed kernel resolution left the jupyterlab-lsp virtual document disposed, and its context-menu hook then threw and aborted the Lumino menu build; fix: keep default names (`python3`/`python2`/`ir`) in `find_kernel_specs()` so standard notebooks resolve; `nb_venv_kernels/manager.py`
  - 2026-07-01 reported: outside-cell menu correct and highlights; in-cell menu stale, no jump-to-definition, no hover highlight
  - 2026-07-01 investigating: ablation pins `nb_venv_kernels` as sole culprit; ruled out shipped CSS (empty), `schema/`, declarative `jupyter.lab.menus.context`, and any cell/`mousedown`/`contextmenu` handler; v1.2.37 UI-strip did not fix; reproducing in isolated container from `stellars/stellars-jupyterlab-ds` (jl-4.6.1)
  - 2026-07-01 isolated-repro NEGATIVE: container `nbvk-repro` from same image (nb_venv_kernels server+frontend+companion active); real 592KB notebook, 2K viewport, windowed rendering, kernel idle; cross-cell right-click x4 both directions - menu always correct (37 editor items incl. Jump to definition), connected, highlights on hover, zero notebook mutations at click time; bug did not reproduce, contradicts the re-render hypothesis
  - 2026-07-01 ROOT CAUSE: `VEnvKernelSpecManager.find_kernel_specs()` (`manager.py:419-421`) deletes the standard `python3` spec (dedup vs the conda base `resource_dir`), so `/api/kernelspecs` has no `python3`; a notebook saved with the universal default `kernelspec.name=python3` cannot auto-bind -> "Select Kernel"/"No Kernel" -> jupyterlab-lsp virtual document disposed -> right-click throws `isContextMenuOverToken: Virtual document of adapter disposed!`, aborting the Lumino context-menu build -> empty/degraded menu (no items, no highlight). Reproduced locally on `localhost:8899` (10 envs); two-arm test: `python3` notebook -> No Kernel + 36x disposed errors + empty menu, `conda-base-py` notebook -> kernel binds, errors gone, menu healthy. Fix: keep/alias `python3` in `find_kernel_specs()` so standard notebooks resolve
  - 2026-07-01 fixed+verified: guarded default names in `find_kernel_specs()` (`manager.py:404,418,428`); local lab now lists `python3`; the previously-broken `python3` notebook binds "Python 3 (ipykernel)", 0 disposed errors, full 37-item menu incl. Jump to definition. Verified by syncing the file into site-packages + restart (no version bump); proper build/commit pending approval
