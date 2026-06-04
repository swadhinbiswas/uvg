# Runtime Architecture

**Date:** 2026-06-04
**Status:** APPROVED

---

## Overview

The runtime layer constructs isolated Python execution environments from the global content-addressable store. Each project receives a minimal runtime directory that exposes only its declared dependencies.

---

## Runtime Construction Pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Lockfile    │───▶│  Dependency  │───▶│  Fingerprint │───▶│  Cache Check │
│  (uvg.lock)  │    │  Graph       │    │  Computation │    │  (reuse?)    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────┬───────┘
                                                                   │
                                                    ┌──────────────┼──────────────┐
                                                    │              │              │
                                              ┌─────▼─────┐  ┌────▼────┐  ┌──────▼──────┐
                                              │  HIT:     │  │ MISS:   │  │ STALE:      │
                                              │  Reuse    │  │ Build   │  │ Rebuild     │
                                              │  runtime  │  │ runtime │  │ runtime     │
                                              └─────┬─────┘  └────┬────┘  └──────┬──────┘
                                                    │              │              │
                                                    └──────────────┼──────────────┘
                                                                   │
                                                           ┌───────▼───────┐
                                                           │  Runtime      │
                                                           │  Directory    │
                                                           └───────────────┘
```

---

## Runtime Directory Structure

```
project/.uvg/runtime/
│
├── manifest.json              # Dependency graph + metadata
├── fingerprint                # Fingerprint string
├── site-packages/             # Import path root
│   ├── numpy -> ~/.uvg/store/objects/sha256/<hash>/lib/python3.12/site-packages/numpy
│   ├── pandas -> ~/.uvg/store/objects/sha256/<hash>/lib/python3.12/site-packages/pandas
│   ├── requests -> ~/.uvg/store/objects/sha256/<hash>/lib/python3.12/site-packages/requests
│   ├── numpy-2.3.0.dist-info -> ~/.uvg/store/objects/sha256/<hash>/lib/python3.12/site-packages/numpy-2.3.0.dist-info
│   └── _uvg_runtime.pth       # .pth file for dynamic path extension
│
├── bin/                       # Entry point scripts
│   ├── pytest
│   ├── black
│   └── ruff
│
├── python -> /usr/bin/python3.12  # Interpreter symlink (optional)
│
└── uvg-runtime.json           # Runtime metadata
```

---

## Runtime Manifest (`manifest.json`)

```json
{
  "version": 1,
  "fingerprint": "runtime_8fa2d1c3",
  "python_version": "3.12",
  "platform": "linux",
  "architecture": "x86_64",
  "abi": "cp312",
  "created_at": "2026-06-04T12:00:00Z",
  "packages": {
    "numpy": {
      "version": "2.3.0",
      "hash": "sha256:a4f8d2e1b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0",
      "store_path": "~/.uvg/store/objects/sha256/a4f8d2...-cp312-linux-x86_64",
      "abi": "cp312",
      "platform": "manylinux_2_17_x86_64",
      "dependencies": [],
      "is_native": true
    },
    "pandas": {
      "version": "2.2.0",
      "hash": "sha256:b7f9e1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0",
      "store_path": "~/.uvg/store/objects/sha256/b7f9e1...-cp312-linux-x86_64",
      "abi": "cp312",
      "platform": "manylinux_2_17_x86_64",
      "dependencies": ["numpy>=1.26.0", "python-dateutil>=2.8.2"],
      "is_native": true
    }
  },
  "entry_points": {
    "pytest": {
      "module": "pytest",
      "function": "console_main",
      "script": "bin/pytest"
    }
  }
}
```

---

## Import Path Construction

### Method 1: Symlinks (Primary)

The `site-packages/` directory contains symlinks to store objects.

**Advantages:**
- Native Python support (no configuration needed)
- IDE compatibility (symlinks are followed)
- Tool compatibility (mypy, pyright, pytest all work)
- Fast construction (symlink creation is O(1))

**Disadvantages:**
- Some tools may not follow symlinks correctly
- Symlink count scales with dependency count

**Implementation:**
```python
for package in manifest.packages:
    source = package.store_path + "/lib/pythonX.Y/site-packages/" + package.name
    target = runtime_dir + "/site-packages/" + package.name
    os.symlink(source, target)
```

### Method 2: `.pth` Files (Fallback)

A `.pth` file in a known `site-packages` location adds paths to `sys.path`.

**Advantages:**
- No symlinks needed
- Works with any Python installation
- Easy to inspect and debug

**Disadvantages:**
- Requires a `site-packages` location to place the `.pth` file
- Some environments restrict `.pth` file creation

**Implementation:**
```
# _uvg_runtime.pth
/home/user/.uvg/store/objects/sha256/a4f8d2.../lib/python3.12/site-packages
/home/user/.uvg/store/objects/sha256/b7f9e1.../lib/python3.12/site-packages
```

### Method 3: `PYTHONPATH` (Wrapper)

The `uvg run` wrapper sets `PYTHONPATH` before invoking Python.

**Advantages:**
- No filesystem modifications
- Works in restricted environments
- Easy to debug

**Disadvantages:**
- Requires wrapper script
- Not compatible with direct `python` invocation
- Environment variable pollution

**Implementation:**
```bash
#!/bin/bash
export PYTHONPATH="/home/user/.uvg/store/objects/sha256/a4f8d2.../lib/python3.12/site-packages:/home/user/.uvg/store/objects/sha256/b7f9e1.../lib/python3.12/site-packages:$PYTHONPATH"
exec python "$@"
```

### Recommended: Hybrid Approach

1. **Primary**: Symlinks in runtime `site-packages/`
2. **Fallback**: `.pth` files if symlinks fail
3. **Wrapper**: `uvg run` sets `PYTHONPATH` for guaranteed correctness

---

## Entry Point Scripts

Entry points are reconstructed from wheel metadata.

### Script Template

```python
#!/usr/bin/env python3
"""UVG entry point script for {name}."""
import sys
import os

# Inject runtime paths
_runtime_dir = os.path.dirname(os.path.abspath(__file__))
_manifest_path = os.path.join(_runtime_dir, "..", "manifest.json")

with open(_manifest_path) as f:
    import json
    manifest = json.load(f)

# Prepend runtime paths to sys.path
for pkg in manifest["packages"].values():
    site_pkgs = os.path.expanduser(os.path.join(pkg["store_path"], "lib", f"python{manifest['python_version']}", "site-packages"))
    if site_pkgs not in sys.path:
        sys.path.insert(0, site_pkgs)

# Import and execute
from {module} import {function}
sys.exit({function}())
```

### Script Generation

```python
def generate_entry_point(manifest, entry_point):
    script = ENTRY_POINT_TEMPLATE.format(
        name=entry_point.name,
        module=entry_point.module,
        function=entry_point.function
    )
    script_path = os.path.join(runtime_dir, "bin", entry_point.name)
    with open(script_path, "w") as f:
        f.write(script)
    os.chmod(script_path, 0o755)
```

---

## Runtime Fingerprinting

### Fingerprint Algorithm

```python
def compute_fingerprint(manifest: RuntimeManifest) -> str:
    components = [
        manifest.python_version,
        manifest.platform,
        manifest.architecture,
        manifest.abi,
        str(manifest.metadata_version),
    ]

    # Sorted package identifiers (deterministic order)
    for pkg in sorted(manifest.packages.values(), key=lambda p: p.name):
        components.append(f"{pkg.name}=={pkg.version}:{pkg.hash}")

    content = "|".join(components)
    hash_value = hashlib.sha256(content.encode()).hexdigest()
    return f"runtime_{hash_value[:8]}"
```

### Fingerprint Cache

```
~/.uvg/cache/fingerprints/
  runtime_8fa2d1c3/
    manifest.json          # Shared manifest
    site-packages/         # Shared symlinks
    bin/                   # Shared entry points
```

When a new project computes a fingerprint that already exists in the cache:
1. Skip runtime construction
2. Create symlinks from project runtime to cache
3. Update reference count

### Fingerprint Invalidation

Fingerprints are invalidated when:
- Any package hash changes
- Python version changes
- Platform changes
- Architecture changes
- ABI changes

---

## Runtime Reuse

### Scenario: Two Projects, Same Dependencies

```
Project A: numpy==2.3.0, pandas==2.2.0, requests==2.31.0 (Python 3.12)
Project B: numpy==2.3.0, pandas==2.2.0, requests==2.31.0 (Python 3.12)

Both compute: runtime_8fa2d1c3

Project A/.uvg/runtime/ -> ~/.uvg/cache/fingerprints/runtime_8fa2d1c3/
Project B/.uvg/runtime/ -> ~/.uvg/cache/fingerprints/runtime_8fa2d1c3/
```

Result: Zero additional construction time. Zero additional disk usage.

### Scenario: Two Projects, Overlapping Dependencies

```
Project A: numpy==2.3.0, pandas==2.2.0, requests==2.31.0 (Python 3.12)
Project C: numpy==2.3.0, pandas==2.2.0, scipy==1.14.0 (Python 3.12)

Project A: runtime_8fa2d1c3
Project C: runtime_7eb3c2d4

Store objects for numpy and pandas are shared.
Only scipy is added to the store.
Runtime construction for C creates new symlinks.
```

Result: Store deduplication. Runtime isolation maintained.

---

## Native Extension Handling

### ABI Validation

Before adding a native wheel to the store:

```python
def validate_native_wheel(wheel_path: Path, python_version: str) -> ValidationResult:
    wheel_info = parse_wheel_filename(wheel_path.name)

    # Check ABI compatibility
    if not is_abi_compatible(wheel_info.abi_tag, python_version):
        return ValidationResult.FAIL(f"ABI mismatch: {wheel_info.abi_tag} vs {python_version}")

    # Check platform compatibility
    if not is_platform_compatible(wheel_info.platform_tag):
        return ValidationResult.FAIL(f"Platform mismatch: {wheel_info.platform_tag}")

    # Check architecture compatibility
    if not is_arch_compatible(wheel_info.architecture):
        return ValidationResult.FAIL(f"Architecture mismatch: {wheel_info.architecture}")

    # Validate shared library dependencies
    missing_libs = check_shared_libraries(wheel_path)
    if missing_libs:
        return ValidationResult.WARN(f"Missing shared libraries: {missing_libs}")

    return ValidationResult.PASS
```

### Shared Library Path Preservation

For packages that bundle shared libraries (torch, tensorflow):

```python
def configure_library_paths(manifest: RuntimeManifest, package: Package):
    if package.is_native and package.has_shared_libraries:
        lib_path = os.path.join(package.store_path, "lib")
        # Set LD_LIBRARY_PATH for Linux
        os.environ["LD_LIBRARY_PATH"] = f"{lib_path}:{os.environ.get('LD_LIBRARY_PATH', '')}"
        # Set DYLD_LIBRARY_PATH for macOS
        os.environ["DYLD_LIBRARY_PATH"] = f"{lib_path}:{os.environ.get('DYLD_LIBRARY_PATH', '')}"
```

---

## Editable Installs

Editable installs point to source directories instead of store objects.

### Manifest Entry

```json
{
  "my-package": {
    "version": "0.1.0",
    "editable": true,
    "source_path": "/home/user/projects/my-package/src",
    "is_native": false
  }
}
```

### Runtime Construction

```python
if package.editable:
    # Symlink to source directory
    os.symlink(package.source_path, os.path.join(runtime_dir, "site-packages", package.name))
else:
    # Symlink to store object
    os.symlink(package.store_path, os.path.join(runtime_dir, "site-packages", package.name))
```

---

## Performance Characteristics

### Construction Time

| Scenario | Time | Notes |
|----------|------|-------|
| First runtime (100 packages) | ~1.5s | Symlink creation |
| Cached runtime (fingerprint hit) | <50ms | Symlink to cache |
| Partial update (1 package changed) | <200ms | Update affected symlinks |
| Editable install | <100ms | Single symlink |

### Disk Usage

| Component | Size | Notes |
|-----------|------|-------|
| Runtime directory | ~100KB | Symlinks + manifest |
| Store object (numpy) | ~50MB | Extracted wheel |
| Store object (requests) | ~500KB | Pure Python |
| Fingerprint cache | ~100KB | Shared runtime |

### Memory Usage

| Component | Size | Notes |
|-----------|------|-------|
| Manifest in memory | ~50KB | JSON parsed |
| Fingerprint cache index | ~100KB | SQLite |
| Store index | ~1MB | SQLite |

---

## Error Recovery

### Broken Symlink

```python
def repair_broken_symlinks(runtime_dir: Path):
    manifest = load_manifest(runtime_dir)
    for symlink in runtime_dir.glob("site-packages/*"):
        if not symlink.exists():
            package_name = symlink.name
            if package_name in manifest.packages:
                recreate_symlink(manifest.packages[package_name], symlink)
            else:
                symlink.unlink()  # Remove orphaned symlink
```

### Missing Store Object

```python
def repair_missing_store_object(runtime_dir: Path, package_name: str):
    manifest = load_manifest(runtime_dir)
    package = manifest.packages[package_name]

    if not os.path.exists(package.store_path):
        # Re-download and extract
        download_wheel(package.name, package.version, package.hash)
        extract_to_store(package)
        recreate_symlink(package, runtime_dir / "site-packages" / package_name)
```

---

## Runtime Lifecycle

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Created    │───▶│  Active     │───▶│  Updated    │───▶│  Active     │
│  (sync)     │    │  (in use)   │    │  (sync)     │    │  (new ver)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                        │
                        │ (unused for 30 days)
                        ▼
                  ┌─────────────┐
                  │  Garbage    │
                  │  Collected  │
                  └─────────────┘
```

---

## Runtime Verification

```python
def verify_runtime(runtime_dir: Path) -> VerificationReport:
    manifest = load_manifest(runtime_dir)
    report = VerificationReport()

    # Verify manifest integrity
    if not verify_manifest_hash(manifest):
        report.add_error("Manifest hash mismatch")

    # Verify all store objects exist
    for pkg in manifest.packages.values():
        if not os.path.exists(pkg.store_path):
            report.add_error(f"Missing store object: {pkg.name}")

    # Verify all symlinks are valid
    for symlink in runtime_dir.glob("site-packages/*"):
        if symlink.is_symlink() and not symlink.exists():
            report.add_error(f"Broken symlink: {symlink.name}")

    # Verify hashes
    for pkg in manifest.packages.values():
        if not verify_package_hash(pkg):
            report.add_error(f"Hash mismatch: {pkg.name}")

    return report
```

---

## Runtime Architecture Invariants

1. **Runtimes are isolated**: No cross-project visibility
2. **Symlinks are atomic**: Created in temp, moved to final location
3. **Manifests are authoritative**: Runtime state matches manifest
4. **Fingerprints are deterministic**: Same inputs = same fingerprint
5. **Entry points are reconstructed**: Always match manifest
6. **Native extensions are validated**: Before store insertion
7. **Editable installs are supported**: Source directory symlinks
