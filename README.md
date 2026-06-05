# GVX

[![Version](https://img.shields.io/badge/version-0.1.0-blue)](https://github.com/swadhin/gvx/releases)
[![License](https://img.shields.io/badge/license-MIT-yellow)](https://github.com/swadhin/gvx/blob/main/LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Tests](https://github.com/swadhin/gvx/actions/workflows/ci.yml/badge.svg)](https://github.com/swadhin/gvx/actions)
[![codecov](https://codecov.io/gh/swadhin/gvx/branch/main/graph/badge.svg)](https://codecov.io/gh/swadhin/gvx)
[![Documentation](https://img.shields.io/badge/docs-gvx.opencodehub.space-blue)](https://gvx.opencodehub.space)

<div align="center">

![GVX Logo](docs/public/logo.gif)

</div>

**The runtime layer that Python never had.**

GVX is not a package manager. GVX is not a dependency resolver. GVX is not a replacement for [UV](https://docs.astral.sh/uv/).

GVX is a **runtime, storage, caching, and dependency intelligence layer** built on top of UV.

---

## Highlights

- **Zero duplication** — Packages stored once in UV's cache, shared across all projects
- **Instant runtimes** — Symlinks instead of copies, O(1) environment creation
- **Multi-Python support** — Switch between Python versions seamlessly
- **Portable lockfiles** — Move projects between machines instantly
- **CI/CD ready** — Export/import runtimes for deployment
- **Workspace support** — First-class monorepo management
- **Parallel downloads** — Leverages UV's fast download system
- **Disk-space efficient** — With a [global cache](https://gvx.opencodehub.space/concepts/store/) for dependency deduplication
- **Installable** via `curl` or `pip`
- **Supports** macOS, Linux, and Windows

---

## Why GVX?

```
uv  0.06s
poetry  0.99s
pdm  1.90s
pip-sync  4.63s
```

*Installing Trio's dependencies with a warm cache.*

GVX inherits UV's speed and adds **runtime isolation without duplication**. While other tools copy packages into virtual environments, GVX creates **symlinks to UV's global cache** — giving you isolated runtimes in milliseconds, not seconds.

---

## Quick Start

```bash
# Install GVX
pip install gvx

# Initialize a project
gvx init

# Add packages
gvx add flask requests httpx

# Build runtime
gvx sync

# Run with isolated environment
gvx run -- python script.py
```

---

## Installation

### Prerequisites

GVX requires [UV](https://docs.astral.sh/uv/) to be installed:

```bash
# Install UV (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install UV (Windows)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### Install GVX

```bash
# From PyPI (recommended)
pip install gvx

# Or via UV
uv pip install gvx

# Or from source
git clone https://github.com/swadhin/gvx.git
cd gvx
pip install -e .
```

### Verify Installation

```bash
gvx --version
gvx info
```

---

## Features

###  Instant Runtimes

GVX creates isolated runtimes by **symlinking to UV's cache** instead of copying packages. This means:

- **O(1) environment creation** — No waiting for package installation
- **Zero disk duplication** — Packages stored once, shared everywhere
- **Instant switching** — Change Python versions in milliseconds

### <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/refs/heads/main/icons/Python-Dark.svg" width="20" height="20" alt="Python"> Multi-Python Support

```bash
# List available Python versions
gvx list

# Switch to Python 3.11
gvx use 3.11

# Switch to Python 3.12
gvx use 3.12
```

GVX automatically rebuilds the runtime for the new Python version.

### 📦 Portable Lockfiles

```bash
# Export runtime for deployment
gvx export -o runtime.tar.gz

# Import on another machine
gvx import runtime.tar.gz
```

Move your runtime anywhere — no re-downloading required.

### 🏢 Workspace Support

First-class monorepo support with workspace commands:

```bash
# List all projects
gvx workspace list

# Sync all projects
gvx workspace sync

# Show shared dependencies
gvx workspace shared

# Health check all projects
gvx workspace doctor
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
  gvx.lock                       # Project lockfile
  .gvx/runtime/
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
| `gvx init [--python VERSION]` | Initialize project |
| `gvx add PACKAGE...` | Add package(s) |
| `gvx sync [--python VERSION]` | Build runtime from lockfile |
| `gvx run -- COMMAND` | Run command with runtime |
| `gvx clean` | Clean runtime directory |
| `gvx info` | Show GVX information |

### Python Version Management

| Command | Description |
|---------|-------------|
| `gvx use VERSION` | Switch Python version |
| `gvx list` | List available Python versions |

### Export/Import

| Command | Description |
|---------|-------------|
| `gvx export [-o FILE]` | Export runtime to tarball |
| `gvx import FILE [--force]` | Import runtime from tarball |

### Workspace Commands

| Command | Description |
|---------|-------------|
| `gvx workspace list` | List all projects |
| `gvx workspace sync` | Sync all projects |
| `gvx workspace stats` | Show statistics |
| `gvx workspace graph` | Show dependency graph |
| `gvx workspace shared` | Show shared dependencies |
| `gvx workspace doctor` | Health check all projects |

---

## Requirements

- Python 3.10+
- UV 0.10.0+
- Linux, macOS, or Windows

---

## Development

### Setup

```bash
git clone https://github.com/swadhin/gvx.git
cd gvx
uv sync --dev
```

### Testing

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=gvx

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

- **Documentation**: [https://gvx.opencodehub.space](https://gvx.opencodehub.space)
- **Source Code**: [https://github.com/swadhin/gvx](https://github.com/swadhin/gvx)
- **Bug Tracker**: [https://github.com/swadhin/gvx/issues](https://github.com/swadhin/gvx/issues)
- **UV Documentation**: [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

---

<div align="center">

**Made with ❤️ by [opencodeHUB](https://opencodehub.space)**

</div>
