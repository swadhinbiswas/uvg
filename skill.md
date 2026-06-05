# GVX Engineering Skill

---

## Engineering Philosophy

GVX is infrastructure. Infrastructure must be correct, maintainable, and secure.

We optimize for:
1. **Correctness**: Code must do what it claims to do
2. **Maintainability**: Code must be understandable by future engineers
3. **Scalability**: Code must handle growth in packages, projects, and users
4. **Security**: Code must protect against tampering, leakage, and attack
5. **Performance**: Code must meet defined performance targets

We do not optimize for:
- Speed of development over quality
- Cleverness over clarity
- Features over stability
- Shortcuts over correctness

---

## Architecture Rules

### 1. Delegate, Don't Duplicate

Never reimplement what UV does well. UV handles resolution, downloading, and lock generation. GVX handles storage, runtime construction, and intelligence.

### 2. Content Over Names

Packages are identified by content hash, not by name. The 7-tuple identity is non-negotiable.

### 3. Immutability

Store objects are never modified. They are only created and replaced. This eliminates entire classes of bugs.

### 4. Strict Isolation

Projects see only their declared dependencies. No leakage. No contamination. No ambiguity.

### 5. Fingerprint Everything

Deterministic fingerprints enable caching, reuse, and verification. Same inputs always produce the same fingerprint.

### 6. Security First

Hash verification, integrity validation, supply chain checks. Not optional. Not bolted on. Built in.

### 7. Performance Matters

Cold runtime: <2s. Warm runtime: <200ms. Storage duplication: <5%. These are requirements, not aspirations.

### 8. Test Everything

No code ships without tests. No feature ships without benchmarks. No change ships without documentation.

---

## Code Standards

### Typing

- **Strict mode**: `mypy --strict`
- **No `Any`**: Without explicit justification in a comment
- **No `# type: ignore`**: Without explanation of why
- **All public APIs**: Fully typed
- **Generics**: Preferred over `Any`
- **Protocol**: Preferred over inheritance for interfaces
- **Dataclasses/TypedDict**: For structured data

```python
# GOOD
class PackageIdentity(NamedTuple):
    name: str
    version: Version
    python_version: str
    abi_tag: str
    platform_tag: str
    architecture: str
    wheel_hash: str

# BAD
def get_package(name, version, python_ver, abi, platform, arch, hash):
    ...
```

### Error Handling

- **Custom exceptions**: For domain-specific errors
- **Exception hierarchy**: Base exception per subsystem
- **Error messages**: Actionable and specific
- **No bare `except`**: Always catch specific exceptions
- **No silent failures**: Log or raise

```python
# GOOD
class StoreError(Exception):
    """Base exception for store operations."""

class ObjectNotFoundError(StoreError):
    """Raised when a store object is not found."""

class HashMismatchError(StoreError):
    """Raised when a hash verification fails."""

def get_object(hash: str) -> ObjectPath:
    path = self._index.lookup(hash)
    if path is None:
        raise ObjectNotFoundError(f"Object not found: {hash}")
    return path

# BAD
def get_object(hash):
    try:
        return self.store[hash]
    except:
        return None
```

### Naming

- **Functions**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`
- **Modules**: `snake_case`
- **Packages**: `snake_case`

### Imports

- Standard library first
- Third-party second
- Local third
- Sorted within groups
- No wildcard imports
- One import per line

```python
# GOOD
import hashlib
import json
import os
from pathlib import Path

import sqlite3

from gvx.store.object import StoreObject
from gvx.store.index import DatabasePool

# BAD
from gvx.store import *
import os, json, hashlib
```

### Documentation

- **Docstrings**: Google style for all public APIs
- **Parameters**: Typed and described
- **Returns**: Typed and described
- **Raises**: Documented
- **Examples**: Included for complex APIs

```python
def create_object(wheel_path: Path, wheel_hash: str) -> ObjectPath:
    """Create a new store object from a wheel file.

    Args:
        wheel_path: Path to the wheel file.
        wheel_hash: SHA-256 hash of the wheel content.

    Returns:
        The path to the created store object.

    Raises:
        HashMismatchError: If the wheel hash does not match.
        ObjectExistsError: If an object with this hash already exists.
        StoreError: If the object creation fails.

    Example:
        >>> store.create_object(Path("numpy-2.3.0.whl"), "sha256:a4f8d2...")
        PosixPath("~/.gvx/store/objects/sha256/a4f8d2...")
    """
```

---

## Testing Standards

### Unit Tests

- Test every public function
- Test edge cases
- Test error conditions
- Mock external dependencies
- Use fixtures for common setup
- Use parametrization for multiple inputs

```python
class TestStoreObject:
    def test_create_object(self, tmp_path: Path, sample_wheel: Path):
        store = Store(tmp_path)
        obj = store.create_object(sample_wheel, "sha256:abc123")
        assert obj.exists()
        assert obj.metadata.package_name == "numpy"

    def test_create_object_hash_mismatch(self, tmp_path: Path, sample_wheel: Path):
        store = Store(tmp_path)
        with pytest.raises(HashMismatchError):
            store.create_object(sample_wheel, "sha256:wrong_hash")

    @pytest.mark.parametrize("python_version", ["3.10", "3.11", "3.12", "3.13"])
    def test_python_version_isolation(self, tmp_path: Path, python_version: str):
        ...
```

### Integration Tests

- Test end-to-end workflows
- Test with real UV
- Test with real packages
- Test native extensions
- Test multiple Python versions

```python
class TestUVIntegration:
    def test_add_numpy(self, tmp_project: Project):
        result = run_gvx(tmp_project, "add", "numpy==2.3.0")
        assert result.returncode == 0
        assert tmp_project.runtime.has_package("numpy")

    def test_run_import_numpy(self, tmp_project: Project):
        run_gvx(tmp_project, "add", "numpy==2.3.0")
        result = run_gvx(tmp_project, "run", "python", "-c", "import numpy")
        assert result.returncode == 0
```

### Performance Tests

- Benchmark critical paths
- Compare against baseline
- Report regression
- Use `pytest-benchmark`

```python
def test_runtime_construction_benchmark(benchmark, tmp_project: Project):
    benchmark(run_gvx_sync, tmp_project)
    # Must complete in <2s
```

### Coverage

- **Line coverage**: >95%
- **Branch coverage**: >90%
- **No uncovered critical paths**

---

## Security Standards

### Hash Verification

- Every wheel is verified before extraction
- Every store object is verified on read
- Every runtime is verified before execution

### Input Validation

- All paths are validated and sanitized
- All hashes are validated
- All versions are validated
- All registry URLs are validated

### Credential Handling

- Credentials stored in system keyring
- Never logged
- Never in error messages
- Never in stack traces

### File Permissions

- Store: 700/440
- Runtime: 700
- No world-writable files
- No setuid/setgid

---

## Benchmarking Standards

### Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Cold runtime | <2s | Time to construct runtime from scratch |
| Warm runtime | <200ms | Time to construct runtime from cache |
| Dependency lookup | O(1) | Time to find package in store |
| Storage duplication | <5% | Percentage of duplicate content |
| Store insertion | <5s | Time to add package to store |
| Sync (100 packages) | <2s | Time to sync 100 packages |

### Benchmark Execution

```bash
uv run pytest tests/benchmarks/ -v --benchmark-only
uv run pytest tests/benchmarks/ -v --benchmark-compare
```

### Benchmark Reporting

- Include in PR description
- Compare against baseline
- Flag regressions >10%

---

## Performance Standards

### Time Complexity

| Operation | Target | Notes |
|-----------|--------|-------|
| Store lookup | O(1) | Hash-indexed |
| Runtime construction | O(n) | n = package count |
| Fingerprint computation | O(n log n) | Sorting required |
| Dependency resolution | Delegated | UV handles this |
| Import path construction | O(n) | Symlink creation |

### Space Complexity

| Component | Target | Notes |
|-----------|--------|-------|
| Store object | Wheel size | Extracted wheel |
| Runtime directory | O(n) | n = package count |
| Index database | O(m) | m = object count |
| Fingerprint cache | O(k) | k = unique fingerprints |

---

## Review Standards

### Code Review Checklist

- [ ] Code follows style guide
- [ ] All public APIs are typed
- [ ] All public APIs have docstrings
- [ ] Tests cover all code paths
- [ ] Error handling is robust
- [ ] Security considerations addressed
- [ ] Performance is acceptable
- [ ] Documentation is updated
- [ ] No TODO comments without issue link
- [ ] No placeholder code
- [ ] No disabled tests
- [ ] No disabled typing

### PR Requirements

- [ ] Clear description
- [ ] Linked issues
- [ ] Test results
- [ ] Benchmark results (if applicable)
- [ ] Migration guide (if breaking)

---

## Forbidden Patterns

### Never Generate

- TODO code
- `pass` statements in non-abstract methods
- Placeholder functions
- Fake implementations
- Temporary hacks
- Disabled typing
- Disabled tests
- Unfinished features
- `# type: ignore` without comment
- `Any` without justification
- Bare `except`
- Silent failures
- Global mutable state
- Circular imports

### Always Include

- Type hints
- Docstrings
- Tests
- Error handling
- Input validation
- Logging (for operations)
- Benchmarks (for performance-critical code)
