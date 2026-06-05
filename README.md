# UVG

[![PyPI version](https://img.shields.io/pypi/v/uvg.svg)](https://pypi.org/project/uvg/)
[![License](https://img.shields.io/pypi/l/uvg.svg)](https://github.com/swadhin/uvg/blob/main/LICENSE)
[![Python versions](https://img.shields.io/pypi/pyversions/uvg.svg)](https://pypi.org/project/uvg/)
[![Tests](https://github.com/swadhin/uvg/actions/workflows/ci.yml/badge.svg)](https://github.com/swadhin/uvg/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-uvg.opencodehub.space-blue)](https://uvg.opencodehub.space)

**The runtime layer that Python never had.**

UVG is not a package manager. UVG is not a dependency resolver. UVG is not a replacement for [UV](https://docs.astral.sh/uv/).

UVG is a **runtime, storage, caching, and dependency intelligence layer** built on top of UV.

---

## Highlights

- **Zero duplication** — Packages stored once in UV's cache, shared across all projects
- **Instant runtimes** — Symlinks instead of copies, O(1) environment creation
- **Multi-Python support** — Switch between Python versions seamlessly
- **Portable lockfiles** — Move projects between machines instantly
- **CI/CD ready** — Export/import runtimes for deployment
- **Workspace support** — First-class monorepo management
- **Parallel downloads** — Leverages UV's fast download system
- **Disk-space efficient** — With a [global cache](https://uvg.opencodehub.space/concepts/store/) for dependency deduplication
- **Installable** via `curl` or `pip`
- **Supports** macOS, Linux, and Windows

---

## Why UVG?

```
uv  0.06s
poetry  0.99s
pdm  1.90s
pip-sync  4.63s
```

*Installing Trio's dependencies with a warm cache.*

UVG inherits UV's speed and adds **runtime isolation without duplication**. While other tools copy packages into virtual environments, UVG creates **symlinks to UV's global cache** — giving you isolated runtimes in milliseconds, not seconds.

---

## Quick Start

```bash
# Install UVG
pip install uvg

# Initialize a project
uvg init

# Add packages
uvg add flask requests httpx

# Build runtime
uvg sync

# Run with isolated environment
uvg run -- python script.py
```

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

## Features

###  Instant Runtimes

UVG creates isolated runtimes by **symlinking to UV's cache** instead of copying packages. This means:

- **O(1) environment creation** — No waiting for package installation
- **Zero disk duplication** — Packages stored once, shared everywhere
- **Instant switching** — Change Python versions in milliseconds

### 🐍 Multi-Python Support

```bash
# List available Python versions
uvg list

# Switch to Python 3.11
uvg use 3.11

# Switch to Python 3.12
uvg use 3.12
```

UVG automatically rebuilds the runtime for the new Python version.

### 📦 Portable Lockfiles

```bash
# Export runtime for deployment
uvg export -o runtime.tar.gz

# Import on another machine
uvg import runtime.tar.gz
```

Move your runtime anywhere — no re-downloading required.

### 🏢 Workspace Support

First-class monorepo support with workspace commands:

```bash
# List all projects
uvg workspace list

# Sync all projects
uvg workspace sync

# Show shared dependencies
uvg workspace shared

# Health check all projects
uvg workspace doctor
```

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

### Key Design Decisions

1. **Global Cache** — Uses UV's cache directly, no duplicate storage
2. **Symlink Runtimes** — Instant environment creation via symlinks
3. **Parallel Downloads** — UV handles parallel downloads with retries
4. **Case-Insensitive** — Handles different package name casings
5. **Hash-Based Cache** — Supports UV's built wheel cache format

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

MIT License — see [LICENSE](LICENSE) for details.

---

## Links

- **Documentation**: [https://uvg.opencodehub.space](https://uvg.opencodehub.space)
- **Source Code**: [https://github.com/swadhin/uvg](https://github.com/swadhin/uvg)
- **Bug Tracker**: [https://github.com/swadhin/uvg/issues](https://github.com/swadhin/uvg/issues)
- **UV Documentation**: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

---

<div align="center">

**Made with ❤️ by [opencodeHUB](https://opencodehub.space)**

</div>
