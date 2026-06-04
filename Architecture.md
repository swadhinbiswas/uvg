# UVG Architecture

**Date:** 2026-06-04
**Status:** APPROVED

---

## System Overview

UVG is a runtime layer that sits between UV (the resolver/installer) and the Python interpreter. It provides global storage, runtime construction, dependency intelligence, and diagnostics.

```
┌─────────────────────────────────────────────────────────┐
│                      User / CI / IDE                     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                      UVG CLI                            │
│  init | sync | run | doctor | scan | stats | workspace  │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼───────┐ ┌─────▼──────┐ ┌──────▼────────┐
│  Runtime Layer  │ │  Store     │ │ Intelligence  │
│  Construction   │ │  Layer     │ │  Layer        │
│                 │ │            │ │               │
│  Manifest Gen   │ │  CAS       │ │  Doctor       │
│  Fingerprinting │ │  Objects   │ │  Scan         │
│  Symlink Mgmt   │ │  Index     │ │  Stats        │
│  Entry Points   │ │  Cache     │ │  Analytics    │
└────────┬────────┘ └─────┬──────┘ └──────┬────────┘
         │                │               │
         └────────────────┼───────────────┘
                          │
┌─────────────────────────▼───────────────────────────────┐
│                    UV (Delegated)                        │
│  Resolution | Solving | Downloads | Wheels | Lock Files  │
└─────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Store Layer (`~/.uvg/store/`)

Content-addressable storage for all package artifacts.

```
~/.uvg/store/
  objects/
    sha256/
      <hash>/
        lib/pythonX.Y/site-packages/<package>/
        bin/
        share/
  index/
    metadata.db        # Package metadata
    relationships.db   # Dependency graphs
    fingerprints.db    # Runtime fingerprints
  cache/
    wheels/            # Downloaded wheels (before extraction)
    manifests/         # Generated manifests
    resolved/          # UV resolution results
```

**Key Properties:**
- Immutable objects (never modified after creation)
- Content-addressed (SHA-256 hash of wheel content)
- Platform-specific (separate objects per Python version, ABI, platform, arch)
- Atomic operations (write to temp, rename on success)

### 2. Runtime Layer (Per-Project)

Constructs the import path for each project.

```
project/.uvg/runtime/
  manifest.json        # Dependency graph + fingerprint
  site-packages/       # Symlinks to store objects
  bin/                 # Entry point scripts
  python               # Symlink to interpreter (optional)
```

**Construction Flow:**
1. Read lockfile (UV-generated or UVG-extended)
2. Resolve dependency graph
3. Compute runtime fingerprint
4. Check fingerprint cache (reuse if hit)
5. Create symlinks from store to runtime
6. Generate entry point scripts
7. Write manifest

### 3. Intelligence Layer

Dependency analysis, diagnostics, and analytics.

```
uvg doctor    # Diagnose: conflicts, missing, broken
uvg scan      # Scan: unused deps, import analysis
uvg stats     # Stats: storage, dependencies, workspace
```

**Data Sources:**
- Store index (what's stored)
- Runtime manifests (what's used)
- Import analysis (what's imported)
- Workspace graph (what's related)

### 4. CLI Layer

User-facing commands organized by domain.

```
uvg init              # Initialize UVG in a project
uvg sync              # Sync dependencies to runtime
uvg run <cmd>         # Run command with correct runtime
uvg add <pkg>         # Add dependency (delegates to UV)
uvg remove <pkg>      # Remove dependency (delegates to UV)
uvg doctor            # Diagnose dependency issues
uvg scan              # Scan for unused/missing deps
uvg stats             # Show storage and dependency stats
uvg workspace sync    # Sync all workspace projects
uvg workspace doctor  # Diagnose workspace issues
uvg workspace graph   # Visualize workspace graph
uvg workspace stats   # Workspace analytics
uvg verify            # Verify runtime integrity
uvg clean             # Clean unused store objects
uvg info              # Show UVG configuration and status
```

---

## Package Identity Model

A package is identified by a **7-tuple**:

```
(
  package_name,       # "numpy"
  package_version,    # "2.3.0"
  python_version,     # "3.12"
  abi_tag,            # "cp312"
  platform_tag,       # "linux"
  architecture,       # "x86_64"
  wheel_hash          # "sha256:a4f8d2..."
)
```

**Store Path:**
```
~/.uvg/store/objects/sha256/<wheel_hash>-<abi>-<platform>-<arch>/
```

**Example:**
```
~/.uvg/store/objects/sha256/a4f8d2e1b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0-cp312-linux-x86_64/
  lib/python3.12/site-packages/numpy/
  numpy-2.3.0.dist-info/
  bin/
```

---

## Runtime Fingerprinting

### Fingerprint Computation

```
fingerprint = SHA-256(
  python_version +
  sorted(dependency_graph) +
  sorted(wheel_hashes) +
  abi_tag +
  platform_tag +
  architecture +
  manifest_version
)
```

### Fingerprint Format

```
runtime_<first_8_chars_of_hash>
```

Example: `runtime_8fa2d1c3`

### Fingerprint Reuse

If two projects produce the same fingerprint, they share the same runtime artifact. The runtime is constructed once and referenced by both projects.

---

## Lockfile Design (`uvg.lock`)

```toml
[metadata]
version = 1
python_version = "3.12"
platform = "linux"
architecture = "x86_64"
fingerprint = "runtime_8fa2d1c3"

[[packages]]
name = "numpy"
version = "2.3.0"
wheel = "numpy-2.3.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
hash = "sha256:a4f8d2e1b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0"
abi = "cp312"
platform = "manylinux_2_17_x86_64"
dependencies = []

[[packages]]
name = "pandas"
version = "2.2.0"
wheel = "pandas-2.2.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl"
hash = "sha256:b7f9e1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0"
abi = "cp312"
platform = "manylinux_2_17_x86_64"
dependencies = ["numpy>=1.26.0", "python-dateutil>=2.8.2", "pytz>=2020.1", "tzdata>=2022.7"]

[[packages]]
name = "requests"
version = "2.31.0"
wheel = "requests-2.31.0-py3-none-any.whl"
hash = "sha256:c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4"
abi = "py3"
platform = "any"
dependencies = ["urllib3>=1.21.1,<3", "certifi>=2017.4.17", "charset-normalizer>=2,<4", "idna>=2.5,<4"]
```

---

## Data Flow

### `uvg sync`

```
1. Read pyproject.toml / requirements.txt
2. Delegate to UV for resolution (if lockfile missing/stale)
3. Read uvg.lock (or uv.lock)
4. Compute runtime fingerprint
5. Check fingerprint cache
   - HIT: Reuse existing runtime
   - MISS: Construct new runtime
6. For each package in lockfile:
   a. Check store for object
   b. If missing: download wheel (via UV), extract to store
   c. Create symlink in runtime site-packages
7. Generate entry point scripts
8. Write manifest.json
9. Update fingerprint cache
```

### `uvg run <cmd>`

```
1. Read runtime manifest
2. Construct PYTHONPATH from manifest
3. Set environment variables
4. Execute command with correct interpreter
```

### `uvg doctor`

```
1. Read runtime manifest
2. Verify all store objects exist
3. Verify all hashes match
4. Check for broken symlinks
5. Check for missing dependencies
6. Check for version conflicts
7. Report findings
```

### `uvg scan`

```
1. Parse all Python files in project
2. Extract import statements
3. Compare imports to manifest dependencies
4. Report:
   - Unused dependencies (in manifest, not imported)
   - Missing dependencies (imported, not in manifest)
   - Implicit dependencies (transitive, directly imported)
```

---

## Concurrency Model

### Store Access

- **Reads**: Concurrent, no locking required (immutable objects)
- **Writes**: File-level locking per object hash
- **Index Updates**: SQLite with WAL mode (concurrent reads, serialized writes)

### Runtime Construction

- **Per-project**: Independent, no cross-project locking
- **Fingerprint cache**: SQLite with WAL mode

### Global Lock

A global lock file (`~/.uvg/lock`) coordinates:
- Store object creation
- Index updates
- Cache invalidation

---

## Error Handling

### Store Errors

| Error | Recovery |
|-------|----------|
| Object missing | Re-download from registry |
| Hash mismatch | Delete and re-download |
| Corrupt index | Rebuild from store objects |
| Lock timeout | Retry with backoff |

### Runtime Errors

| Error | Recovery |
|-------|----------|
| Broken symlink | Re-sync runtime |
| Missing manifest | Re-sync runtime |
| Fingerprint mismatch | Re-compute and re-sync |
| Entry point failure | Regenerate scripts |

### Intelligence Errors

| Error | Recovery |
|-------|----------|
| Parse failure | Skip file, report warning |
| Import resolution failure | Report as potential issue |
| Graph inconsistency | Re-scan workspace |

---

## Extensibility

### Plugin System

UVG supports plugins for:
- Custom registry adapters
- Custom storage backends
- Custom intelligence rules
- Custom report formats

### Plugin Interface

```python
class UVGPlugin:
    def name(self) -> str: ...
    def version(self) -> str: ...
    def register(self, registry: PluginRegistry) -> None: ...
```

### Plugin Discovery

Plugins are discovered from:
- `~/.uvg/plugins/`
- `pyproject.toml` entry points
- `UVG_PLUGIN_PATH` environment variable

---

## Configuration

### Global Configuration (`~/.uvg/config.toml`)

```toml
[store]
path = "~/.uvg/store"
max_size = "50GB"
gc_threshold = "80%"

[cache]
path = "~/.uvg/cache"
max_size = "10GB"

[registries]
default = "https://pypi.org/simple"
private = ["https://registry.company.com/simple"]

[security]
hash_verification = true
offline_mode = false
supply_chain_validation = true

[performance]
parallel_downloads = 8
parallel_extraction = 4
```

### Project Configuration (`pyproject.toml`)

```toml
[tool.uvg]
python_version = "3.12"
runtime_dir = ".uvg/runtime"
fingerprint_cache = true
```

---

## Architecture Invariants

1. **Store objects are immutable**: Once created, never modified
2. **Fingerprints are deterministic**: Same inputs always produce same output
3. **Runtimes are isolated**: Projects see only their dependencies
4. **Hashes are verified**: Every object is verified on read
5. **Operations are atomic**: Partial failures leave consistent state
6. **Delegation is explicit**: UV handles resolution; UVG handles storage
7. **Intelligence is comprehensive**: All dependency data is available

---

## Non-Goals

- Replace UV's resolver
- Replace UV's wheel download
- Replace UV's lock file
- Replace Python's import system
- Replace build systems
- Replace Python version managers

---

## Architecture Decisions

### Why Content-Addressable Storage?

- Eliminates duplication
- Enables verification
- Supports multiple versions
- Enables caching and reuse

### Why Symlinks for Runtimes?

- Instant construction
- Zero copy overhead
- Store updates propagate automatically
- Minimal disk usage

### Why SQLite for Index?

- Zero configuration
- ACID guarantees
- Concurrent access (WAL mode)
- Single file, easy backup

### Why Delegate to UV?

- UV's resolver is excellent
- UV's wheel download is fast
- UV's lock file is well-designed
- No reason to reimplement

### Why Fingerprinting?

- Enables runtime reuse
- Enables cache hits
- Enables verification
- Enables analytics
