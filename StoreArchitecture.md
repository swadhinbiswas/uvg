# Store Architecture

**Date:** 2026-06-04
**Status:** APPROVED

---

## Overview

The UVG store is a content-addressable, immutable object store for Python package artifacts. It is the foundation upon which all runtime construction, caching, and deduplication is built.

---

## Store Layout

```
~/.uvg/store/
│
├── objects/                    # Content-addressable objects
│   └── sha256/
│       ├── <hash>-<abi>-<platform>-<arch>/
│       │   ├── lib/
│       │   │   └── pythonX.Y/
│       │   │       └── site-packages/
│       │   │           ├── <package>/
│       │   │           └── <package>-<version>.dist-info/
│       │   ├── bin/
│       │   │   └── <entry-point-scripts>
│       │   ├── share/
│       │   │   └── <package-data>
│       │   └── .uvg-metadata.json
│       │
│       ├── <hash>-<abi>-<platform>-<arch>/
│       │   └── ...
│       │
│       └── ...
│
├── index/                      # Store indexes
│   ├── metadata.db             # Package metadata (SQLite)
│   ├── relationships.db        # Dependency relationships (SQLite)
│   └── fingerprints.db         # Runtime fingerprints (SQLite)
│
├── cache/                      # Transient cache
│   ├── wheels/                 # Downloaded wheels (before extraction)
│   ├── manifests/              # Generated manifests
│   └── resolved/               # UV resolution results
│
└── tmp/                        # Atomic operation staging
    └── <uuid>/                 # Temporary directories
```

---

## Object Naming Convention

Objects are named by their content hash plus platform metadata:

```
<sha256-hash>-<abi-tag>-<platform-tag>-<architecture>/
```

**Examples:**

```
a4f8d2e1b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0-cp312-manylinux_2_17_x86_64-x86_64/
b7f9e1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0-cp313-manylinux_2_17_x86_64-x86_64/
c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4-py3-any-any/
```

**Why include ABI/platform/arch in the name?**

1. Same wheel content for different ABIs are different objects
2. Enables O(1) lookup without reading metadata
3. Makes store structure human-readable
4. Enables platform-specific garbage collection

---

## Object Metadata (`.uvg-metadata.json`)

Each object contains a metadata file:

```json
{
  "version": 1,
  "package_name": "numpy",
  "package_version": "2.3.0",
  "python_version": "3.12",
  "abi_tag": "cp312",
  "platform_tag": "manylinux_2_17_x86_64",
  "architecture": "x86_64",
  "wheel_filename": "numpy-2.3.0-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
  "wheel_hash": "sha256:a4f8d2e1b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0",
  "extracted_at": "2026-06-04T12:00:00Z",
  "extracted_by": "uvg/0.1.0",
  "size_bytes": 52428800,
  "file_count": 1234,
  "is_native": true,
  "dependencies": [],
  "entry_points": {
    "f2py": "numpy.f2py.f2py2e:main"
  },
  "shared_libraries": [
    "libopenblas.so.0"
  ]
}
```

---

## Object Lifecycle

### Creation

```
1. Download wheel (via UV)
2. Verify wheel hash
3. Create temporary directory in store/tmp/
4. Extract wheel to temporary directory
5. Write .uvg-metadata.json
6. Validate native extensions (if applicable)
7. Atomically rename temp directory to final name
8. Update index (metadata.db)
```

### Reading

```
1. Lookup object by hash in index
2. Verify object exists on disk
3. Verify .uvg-metadata.json hash matches
4. Return object path
```

### Deletion

```
1. Check reference count (how many runtimes use this object)
2. If reference count == 0:
   a. Remove from index
   b. Remove from disk
3. If reference count > 0:
   a. Mark for deletion (soft delete)
   b. Delete when reference count reaches 0
```

---

## Immutability Guarantees

### Invariants

1. **Objects are never modified**: Once created, the object directory is read-only
2. **Objects are never overwritten**: A new object with the same hash is identical
3. **Objects are only deleted**: When no runtime references them
4. **Object creation is atomic**: Write to temp, rename on success

### Enforcement

```python
def create_object(wheel_path: Path, wheel_hash: str) -> ObjectPath:
    object_name = f"{wheel_hash}-{abi}-{platform}-{arch}"
    object_path = store_dir / "objects" / "sha256" / object_name

    if object_path.exists():
        # Object already exists (idempotent)
        return object_path

    # Create in temp directory
    temp_path = store_dir / "tmp" / str(uuid4())
    temp_path.mkdir(parents=True)

    try:
        # Extract wheel
        extract_wheel(wheel_path, temp_path)

        # Write metadata
        write_metadata(temp_path, wheel_hash)

        # Set read-only permissions
        set_readonly(temp_path)

        # Atomic rename
        temp_path.rename(object_path)

        # Update index
        index.add_object(object_path)

        return object_path

    except Exception:
        # Clean up temp directory on failure
        shutil.rmtree(temp_path)
        raise
```

---

## Index Design

### metadata.db

```sql
CREATE TABLE objects (
    hash TEXT PRIMARY KEY,
    package_name TEXT NOT NULL,
    package_version TEXT NOT NULL,
    python_version TEXT NOT NULL,
    abi_tag TEXT NOT NULL,
    platform_tag TEXT NOT NULL,
    architecture TEXT NOT NULL,
    wheel_filename TEXT NOT NULL,
    wheel_hash TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    file_count INTEGER NOT NULL,
    is_native BOOLEAN NOT NULL,
    extracted_at TEXT NOT NULL,
    reference_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_package ON objects(package_name, package_version);
CREATE INDEX idx_python ON objects(python_version);
CREATE INDEX idx_abi ON objects(abi_tag);
CREATE INDEX idx_platform ON objects(platform_tag);
CREATE INDEX idx_native ON objects(is_native);
```

### relationships.db

```sql
CREATE TABLE dependencies (
    id INTEGER PRIMARY KEY,
    parent_hash TEXT NOT NULL REFERENCES objects(hash),
    child_hash TEXT NOT NULL REFERENCES objects(hash),
    dependency_spec TEXT NOT NULL,
    is_direct BOOLEAN NOT NULL,
    depth INTEGER NOT NULL
);

CREATE TABLE reverse_dependencies (
    id INTEGER PRIMARY KEY,
    child_hash TEXT NOT NULL REFERENCES objects(hash),
    parent_hash TEXT NOT NULL REFERENCES objects(hash),
    dependency_spec TEXT NOT NULL
);

CREATE INDEX idx_parent ON dependencies(parent_hash);
CREATE INDEX idx_child ON dependencies(child_hash);
CREATE INDEX idx_reverse ON reverse_dependencies(child_hash);
```

### fingerprints.db

```sql
CREATE TABLE fingerprints (
    fingerprint TEXT PRIMARY KEY,
    python_version TEXT NOT NULL,
    platform TEXT NOT NULL,
    architecture TEXT NOT NULL,
    abi TEXT NOT NULL,
    manifest_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    reference_count INTEGER NOT NULL DEFAULT 0,
    runtime_path TEXT NOT NULL
);

CREATE TABLE fingerprint_packages (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT NOT NULL REFERENCES fingerprints(fingerprint),
    package_name TEXT NOT NULL,
    package_version TEXT NOT NULL,
    object_hash TEXT NOT NULL REFERENCES objects(hash)
);

CREATE INDEX idx_fingerprint ON fingerprint_packages(fingerprint);
CREATE INDEX idx_package ON fingerprint_packages(package_name, package_version);
```

---

## Cache Design

### Wheel Cache

```
~/.uvg/store/cache/wheels/
  <hash>.whl              # Downloaded wheel
  <hash>.whl.meta         # Download metadata
```

Wheels are cached before extraction. If extraction fails, the wheel can be re-extracted without re-downloading.

### Manifest Cache

```
~/.uvg/store/cache/manifests/
  runtime_8fa2d1c3.json   # Cached manifest
```

Manifests are cached by fingerprint. Cache hits skip manifest generation.

### Resolution Cache

```
~/.uvg/store/cache/resolved/
  <hash>.json             # UV resolution result
```

UV resolution results are cached to avoid re-resolution for unchanged dependencies.

---

## Storage Efficiency

### Deduplication

| Level | Mechanism | Savings |
|-------|-----------|---------|
| Object | Content-addressable | 80-90% for shared deps |
| File | Hard links (within object) | 5-10% for common files |
| Wheel | Cached before extraction | Eliminates re-downloads |

### Space Accounting

```
~/.uvg/store/
  objects/    45GB    # Package objects
  index/      50MB    # SQLite databases
  cache/      5GB     # Cached wheels and manifests
  tmp/        0MB     # Cleaned after operations
  Total:      50GB
```

### Garbage Collection

```python
def garbage_collect(store: Store, threshold: float = 0.8):
    """Remove objects with zero reference count."""
    unused = store.index.find_unused_objects()

    for obj in unused:
        if obj.reference_count == 0:
            store.delete_object(obj.hash)

    # Check storage threshold
    usage = store.get_usage()
    if usage > threshold:
        # Aggressive GC: remove objects not used in 30 days
        stale = store.index.find_stale_objects(days=30)
        for obj in stale:
            if obj.reference_count == 0:
                store.delete_object(obj.hash)
```

---

## Concurrency Control

### Object Creation

```python
import fcntl

def create_object_locked(wheel_hash: str) -> ObjectPath:
    object_name = f"{wheel_hash}-{abi}-{platform}-{arch}"
    object_path = store_dir / "objects" / "sha256" / object_name

    # Acquire lock for this object hash
    lock_path = store_dir / "locks" / object_name
    lock_path.parent.mkdir(exist_ok=True)

    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)

        try:
            if object_path.exists():
                return object_path

            # Create object (atomic)
            return create_object(wheel_path, wheel_hash)

        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
```

### Index Updates

SQLite WAL mode enables concurrent reads with serialized writes:

```python
import sqlite3

def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn
```

---

## Store Operations

### `uvg store info`

```
Store: ~/.uvg/store
Objects: 1,234
Total Size: 45.2GB
Unique Packages: 456
Python Versions: 3.10, 3.11, 3.12, 3.13
Native Packages: 89
Pure Python: 367
```

### `uvg store list`

```
Package              Version   Python  ABI     Platform        Size
numpy                2.3.0     3.12    cp312   linux-x86_64    50MB
numpy                2.3.0     3.13    cp313   linux-x86_64    52MB
numpy                1.26.4    3.12    cp312   linux-x86_64    48MB
pandas               2.2.0     3.12    cp312   linux-x86_64    45MB
requests             2.31.0    3.12    py3     any             500KB
...
```

### `uvg store gc`

```
Scanning store for unused objects...
Found 23 unused objects (1.2GB)
Deleting...
Freed 1.2GB
Store size: 44.0GB
```

---

## Store Architecture Invariants

1. **Objects are immutable**: Never modified after creation
2. **Objects are content-addressed**: Hash determines path
3. **Objects are platform-specific**: Separate per ABI/platform/arch
4. **Objects are atomic**: Created in temp, renamed on success
5. **Index is consistent**: SQLite WAL mode guarantees
6. **Cache is transient**: Can be safely deleted
7. **GC is safe**: Only deletes unreferenced objects
