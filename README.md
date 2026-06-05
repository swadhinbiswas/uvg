# UVG

**Global Package Manager for Python - Zero Duplication, Instant Runtimes**

[![Python versions](https://img.shields.io/pypi/pyversions/uvg.svg)](https://pypi.org/project/uvg/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

UVG is a global package manager that uses UV's cache directly for parallel downloads and shared storage, with symlinks from project runtimes to UV's cache.

**Key Benefits:**
- **Zero duplication** - Packages stored once in UV's cache, shared across all projects
- **Instant runtimes** - Symlinks instead of copies, O(1) environment creation
- **Multi-Python** - Switch between Python versions seamlessly
- **Portable lockfiles** - Move projects between machines instantly
- **CI/CD ready** - Export/import runtimes for deployment

---

## Installation

### Prerequisites

UVG requires [UV](https://docs.astral.sh/uv/) to be installed:

```bash
# Install UV (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install UV (Windows)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### Install UVG

```bash
# From PyPI (recommended)
pip install uvg

# Or via UV
uv pip install uvg

# Or from source
git clone https://github.com/swadhin/uvg.git
cd uvg
pip install -e .
```

### Verify Installation

```bash
uvg --version
uvg info
```

---

## Quick Start

### 1. Initialize a Project

```bash
mkdir myproject && cd myproject
uvg init
```

This creates a `uvg.lock` file in your project.

### 2. Add Packages

```bash
# Add single package
uvg add requests

# Add multiple packages
uvg add flask django

# Add with version constraint
uvg add "numpy>=1.24"
```

### 3. Build Runtime

```bash
uvg sync
```

This creates a runtime at `.uvg/runtime/` with symlinks to UV's cache.

### 4. Run Commands

```bash
# Run Python with project runtime
uvg run -- python script.py

# Run with specific Python version
uvg run -- python --version
```

---

## Multi-Python Support

### Switch Python Version

```bash
# List available Python versions
uvg list

# Switch to Python 3.11
uvg use 3.11

# Switch to Python 3.12
uvg use 3.12
```

UVG automatically rebuilds the runtime for the new Python version.

---

## Workspace Support (Monorepo)

UVG supports monorepos with multiple projects:

```bash
# List all projects in workspace
uvg workspace list

# Sync all projects
uvg workspace sync

# Show workspace statistics
uvg workspace stats

# Show shared dependencies
uvg workspace shared

# Show dependency graph
uvg workspace graph

# Health check all projects
uvg workspace doctor
```

---

## CI/CD Integration

### Export Runtime

Package your runtime for deployment:

```bash
uvg export -o runtime.tar.gz
```

### Import Runtime

Restore runtime on another machine:

```bash
uvg import runtime.tar.gz
```

The imported runtime works instantly without re-downloading packages.

---

## CLI Reference

### Basic Commands

| Command | Description |
|---------|-------------|
| `uvg init [--python VERSION]` | Initialize project |
| `uvg add PACKAGE...` | Add package(s) |
| `uvg sync [--python VERSION]` | Build runtime from lockfile |
| `uvg run -- COMMAND` | Run command with runtime |
| `uvg clean` | Clean runtime directory |
| `uvg info` | Show UVG information |

### Python Version Management

| Command | Description |
|---------|-------------|
| `uvg use VERSION` | Switch Python version |
| `uvg list` | List available Python versions |

### Export/Import

| Command | Description |
|---------|-------------|
| `uvg export [-o FILE]` | Export runtime to tarball |
| `uvg import FILE [--force]` | Import runtime from tarball |

### Workspace Commands

| Command | Description |
|---------|-------------|
| `uvg workspace list` | List all projects |
| `uvg workspace sync` | Sync all projects |
| `uvg workspace stats` | Show statistics |
| `uvg workspace graph` | Show dependency graph |
| `uvg workspace shared` | Show shared dependencies |
| `uvg workspace doctor` | Health check all projects |

---

## How It Works

### Architecture

```
~/.cache/uv/wheels-v6/pypi/     # UV's global cache
  requests/
    2.34.2-py3-none-any/
      requests/
      requests-2.34.2.dist-info/

myproject/
  uvg.lock                       # Project lockfile
  .uvg/runtime/
    manifest.json
    site-packages/
      requests -> ~/.cache/uv/...  # Symlink, not copy
      requests-2.34.2.dist-info -> ~/.cache/uv/...
```

### Key Features

1. **Global Cache** - Uses UV's cache directly, no duplicate storage
2. **Symlink Runtimes** - Instant environment creation via symlinks
3. **Parallel Downloads** - UV handles parallel downloads with retries
4. **Case-Insensitive** - Handles different package name casings
5. **Hash-Based Cache** - Supports UV's built wheel cache format

---

## Requirements

- Python 3.10+
- UV 0.10.0+
- Linux, macOS, or Windows

---

## Development

### Setup

```bash
git clone https://github.com/swadhin/uvg.git
cd uvg
uv sync --dev
```

### Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=uvg

# Run linting
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/
```

### Building

```bash
# Build package
uv run python -m build

# Install locally
pip install -e .
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.

---

## Links

- **Documentation**: [https://uvg.opencodehub.space](https://uvg.opencodehub.space)
- **Source Code**: [https://github.com/swadhin/uvg](https://github.com/swadhin/uvg)
- **Bug Tracker**: [https://github.com/swadhin/uvg/issues](https://github.com/swadhin/uvg/issues)
- **UV Documentation**: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
