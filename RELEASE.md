# Release Notes

## Release 1.1.18

**CI/CD and Testing**
- Added browser check step to GitHub Actions workflow
- Added Playwright integration tests for UI components
- Comprehensive tier 2 test suite: kernel discovery (venv, uv, conda), registry operations, Python API
- Fixed route tests for actual API endpoints
- Fixed HTTPClientError handling in tests
- Fixed cache invalidation in test suite

**Bug Fixes**
- Fixed `list_environments()` to show non-existent entries with `exists=False`
- Fixed `scan_directory()` return keys for consistency
- Fixed module-level imports for json/subprocess in registry

**Documentation**
- Added integration tests documentation (doc/INTEGRATION_TESTS.md)
- Added screenshots: CLI list command, Kernel menu, scan results modal
- Added PayPal donation badge

**UI Polish**
- Harmonized "no" indicator across CLI and modal (lowercase, red color)
- Modal headers and summary format aligned with CLI output
