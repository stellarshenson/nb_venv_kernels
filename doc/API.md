# nb_venv_kernels API Reference

@nb_venv_kernels version: 1.1.36<br>
@created on: 2025-11-27

## REST API Endpoints

All endpoints require authentication via Jupyter server token.

**Cache Coherence**: API operations use the server's kernel spec manager singleton, so scan/register/unregister changes appear immediately in the kernel picker without page refresh.

### List Environments

**GET** `/nb-venv-kernels/environments`

Returns list of all registered environments with their status.

**Response:**

```json
[
  {
    "name": "my-project",
    "type": "uv",
    "exists": true,
    "has_kernel": true,
    "path": "/home/user/projects/my-project/.venv"
  },
  {
    "name": "base",
    "type": "conda",
    "exists": true,
    "has_kernel": true,
    "path": "/opt/conda"
  }
]
```

**Fields:**

- `name` - Display name derived from environment path
- `type` - Environment type: `venv`, `uv`, `conda`, or `conda (local)`
- `exists` - Whether environment directory exists
- `has_kernel` - Whether environment has an installed Jupyter kernel
- `path` - Absolute path to environment

### Scan Environments

**POST** `/nb-venv-kernels/scan`

Scan directory for environments and register them.

**Request Body:**

```json
{
  "path": "/home/user/workspace",
  "depth": 5,
  "dry_run": false
}
```

**Parameters:**

- `path` - Directory to scan (default: server working directory)
- `depth` - Maximum recursion depth (default: from server config, usually 7)
- `dry_run` - If true, report without making changes (default: false)

**Response:**

```json
{
  "environments": [
    {
      "action": "add",
      "name": "new-project",
      "type": "uv",
      "path": "/home/user/workspace/new-project/.venv"
    },
    {
      "action": "keep",
      "name": "existing-project",
      "type": "venv",
      "path": "/home/user/workspace/existing-project/.venv"
    },
    {
      "action": "remove",
      "name": "deleted-project",
      "type": "venv",
      "path": "/home/user/workspace/deleted-project/.venv"
    }
  ],
  "summary": {
    "add": 1,
    "keep": 1,
    "remove": 1
  },
  "dry_run": false
}
```

**Actions:**

- `add` - Environment newly discovered and registered
- `keep` - Environment already registered
- `remove` - Environment removed (no longer exists)

### Register Environment

**POST** `/nb-venv-kernels/register`

Register a single environment for kernel discovery.

**Request Body:**

```json
{
  "path": "/home/user/my-project/.venv"
}
```

**Response:**

```json
{
  "path": "/home/user/my-project/.venv",
  "registered": true,
  "error": null
}
```

**Fields:**

- `path` - Absolute path to registered environment
- `registered` - True if newly registered, false if already existed
- `error` - Error message if registration failed, null otherwise

**Workspace Boundary**: Path must be within the server's workspace root. Returns 400 error if outside workspace. Global conda environments (with `conda-meta` directory) are exempt from this restriction.

### Unregister Environment

**POST** `/nb-venv-kernels/unregister`

Remove an environment from kernel discovery.

**Request Body:**

```json
{
  "path": "/home/user/my-project/.venv"
}
```

**Response:**

```json
{
  "path": "/home/user/my-project/.venv",
  "unregistered": true
}
```

## Python API

### VEnvKernelSpecManager

The manager class provides programmatic access to environment management.

```python
from nb_venv_kernels import VEnvKernelSpecManager

manager = VEnvKernelSpecManager()
```

#### list_environments()

List all registered environments with their status.

```python
envs = manager.list_environments()
# Returns: List[Dict] with keys: name, type, exists, has_kernel, path
```

#### scan_environments(path, max_depth, dry_run)

Scan directory for environments and register them.

```python
result = manager.scan_environments(
    path="/home/user/workspace",
    max_depth=5,
    dry_run=False
)
# Returns: Dict with keys: environments, summary, dry_run
```

#### register_environment(path)

Register a single environment.

```python
result = manager.register_environment("/home/user/my-project/.venv")
# Returns: Dict with keys: path, registered, error
```

#### unregister_environment(path)

Remove an environment from kernel discovery.

```python
result = manager.unregister_environment("/home/user/my-project/.venv")
# Returns: Dict with keys: path, unregistered
```

## CLI

### JSON Output

All commands support `--json` flag for machine-readable output.

```bash
# List environments as JSON
nb_venv_kernels list --json

# Scan with JSON output (no spinner or text)
nb_venv_kernels scan /path/to/workspace --json

# Register with JSON output
nb_venv_kernels register /path/to/.venv --json
```

### Dry Run

The scan command supports `--dry-run` flag to preview changes without modifying registries.

```bash
nb_venv_kernels scan /path/to/workspace --dry-run
```

## JupyterLab Integration

The extension adds a "Scan for Python Environments" command accessible via:

- **Kernel menu** - Scan for Python Environments
- **Command palette** (Ctrl+Shift+C) - search "Scan for Python"

When triggered, it scans the workspace and displays results in a modal dialog showing:

- Environments found (action: add, keep, remove)
- Summary counts
- Color-coded actions (green=add, blue=keep, orange=remove)

New kernels appear immediately in the kernel picker after scan completes.
