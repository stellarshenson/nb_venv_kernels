# Logs

- `build-<topic>.log` - `python -m build` output
- `copier-update-<template-version>.log` - `copier update` output
- `lint-check-<topic>.log` - `jlpm run lint:check` output
- `make-test-<topic>.log` - `make test` output (jest, pytest, endpoint auth check)
- `npm-<step>[-ui-tests].log` - jlpm upgrade and lockfile re-resolution, root or `ui-tests/`
- `pytest-<topic>-<round>.log` - pytest suite runs
- `release-<version>.log` - `make publish` output
