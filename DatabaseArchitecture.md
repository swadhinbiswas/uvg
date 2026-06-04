# Database Architecture

**Date:** 2026-06-04
**Status:** APPROVED

---

## Overview

UVG uses SQLite for all persistent indexing. SQLite provides ACID guarantees, concurrent access (WAL mode), and zero configuration. All databases are located in `~/.uvg/store/index/`.

---

## Database Files

| File | Purpose | Size (typical) |
|------|---------|----------------|
| `metadata.db` | Package object metadata | 5-50MB |
| `relationships.db` | Dependency relationships | 5-20MB |
| `fingerprints.db` | Runtime fingerprints | 1-10MB |

---

## metadata.db

### Schema

```sql
-- Package objects
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
    reference_count INTEGER NOT NULL DEFAULT 0,
    last_accessed TEXT,
    created_by TEXT NOT NULL DEFAULT 'uvg'
);

-- Package metadata (from dist-info)
CREATE TABLE package_metadata (
    hash TEXT PRIMARY KEY REFERENCES objects(hash),
    summary TEXT,
    description TEXT,
    author TEXT,
    author_email TEXT,
    license TEXT,
    home_page TEXT,
    classifiers TEXT,  -- JSON array
    requires_python TEXT,
    provides_extra TEXT  -- JSON array
);

-- Entry points
CREATE TABLE entry_points (
    id INTEGER PRIMARY KEY,
    object_hash TEXT NOT NULL REFERENCES objects(hash),
    group_name TEXT NOT NULL,
    name TEXT NOT NULL,
    module TEXT NOT NULL,
    function TEXT NOT NULL,
    UNIQUE(object_hash, group_name, name)
);

-- Shared libraries (for native packages)
CREATE TABLE shared_libraries (
    id INTEGER PRIMARY KEY,
    object_hash TEXT NOT NULL REFERENCES objects(hash),
    library_name TEXT NOT NULL,
    library_path TEXT NOT NULL,
    UNIQUE(object_hash, library_name)
);

-- Indexes
CREATE INDEX idx_objects_package ON objects(package_name, package_version);
CREATE INDEX idx_objects_python ON objects(python_version);
CREATE INDEX idx_objects_abi ON objects(abi_tag);
CREATE INDEX idx_objects_platform ON objects(platform_tag, architecture);
CREATE INDEX idx_objects_native ON objects(is_native);
CREATE INDEX idx_objects_accessed ON objects(last_accessed);
CREATE INDEX idx_entry_points_object ON entry_points(object_hash);
CREATE INDEX idx_entry_points_name ON entry_points(name);
CREATE INDEX idx_shared_libs_object ON shared_libraries(object_hash);
```

### Key Queries

```sql
-- Find all versions of a package for a Python version
SELECT * FROM objects
WHERE package_name = ? AND python_version = ?
ORDER BY package_version DESC;

-- Find object by wheel hash
SELECT * FROM objects WHERE wheel_hash = ?;

-- Find all native packages
SELECT * FROM objects WHERE is_native = 1;

-- Find unused objects (for garbage collection)
SELECT * FROM objects WHERE reference_count = 0;

-- Find stale objects (not accessed in N days)
SELECT * FROM objects
WHERE reference_count = 0
  AND last_accessed < datetime('now', '-30 days');

-- Count total store size
SELECT SUM(size_bytes) FROM objects;

-- Find all entry points for a package
SELECT ep.* FROM entry_points ep
JOIN objects o ON ep.object_hash = o.hash
WHERE o.package_name = ? AND o.package_version = ?;
```

---

## relationships.db

### Schema

```sql
-- Direct and transitive dependencies
CREATE TABLE dependencies (
    id INTEGER PRIMARY KEY,
    parent_hash TEXT NOT NULL REFERENCES objects(hash),
    child_hash TEXT NOT NULL REFERENCES objects(hash),
    dependency_spec TEXT NOT NULL,
    is_direct BOOLEAN NOT NULL,
    depth INTEGER NOT NULL,
    UNIQUE(parent_hash, child_hash)
);

-- Reverse dependencies (what depends on this package?)
CREATE TABLE reverse_dependencies (
    id INTEGER PRIMARY KEY,
    child_hash TEXT NOT NULL REFERENCES objects(hash),
    parent_hash TEXT NOT NULL REFERENCES objects(hash),
    dependency_spec TEXT NOT NULL,
    UNIQUE(child_hash, parent_hash)
);

-- Dependency conflicts (incompatible versions)
CREATE TABLE conflicts (
    id INTEGER PRIMARY KEY,
    package_name TEXT NOT NULL,
    hash_a TEXT NOT NULL REFERENCES objects(hash),
    hash_b TEXT NOT NULL REFERENCES objects(hash),
    spec_a TEXT NOT NULL,
    spec_b TEXT NOT NULL,
    detected_at TEXT NOT NULL
);

-- Indexes
CREATE INDEX idx_deps_parent ON dependencies(parent_hash);
CREATE INDEX idx_deps_child ON dependencies(child_hash);
CREATE INDEX idx_deps_depth ON dependencies(depth);
CREATE INDEX idx_reverse_child ON reverse_dependencies(child_hash);
CREATE INDEX idx_reverse_parent ON reverse_dependencies(parent_hash);
CREATE INDEX idx_conflicts_package ON conflicts(package_name);
```

### Key Queries

```sql
-- Get all dependencies of a package (transitive)
WITH RECURSIVE dep_tree AS (
    SELECT parent_hash, child_hash, dependency_spec, depth
    FROM dependencies
    WHERE parent_hash = ?
    UNION ALL
    SELECT d.parent_hash, d.child_hash, d.dependency_spec, d.depth
    FROM dependencies d
    JOIN dep_tree dt ON d.parent_hash = dt.child_hash
)
SELECT * FROM dep_tree;

-- Get reverse dependencies (what uses this package?)
SELECT o.package_name, o.package_version, rd.dependency_spec
FROM reverse_dependencies rd
JOIN objects o ON rd.parent_hash = o.hash
WHERE rd.child_hash = ?;

-- Find dependency conflicts
SELECT c.package_name, o1.package_version as version_a, o2.package_version as version_b,
       c.spec_a, c.spec_b
FROM conflicts c
JOIN objects o1 ON c.hash_a = o1.hash
JOIN objects o2 ON c.hash_b = o2.hash
WHERE c.package_name = ?;

-- Get dependency depth for a package
SELECT MAX(depth) FROM dependencies WHERE parent_hash = ?;
```

---

## fingerprints.db

### Schema

```sql
-- Runtime fingerprints
CREATE TABLE fingerprints (
    fingerprint TEXT PRIMARY KEY,
    python_version TEXT NOT NULL,
    platform TEXT NOT NULL,
    architecture TEXT NOT NULL,
    abi TEXT NOT NULL,
    manifest_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    reference_count INTEGER NOT NULL DEFAULT 0,
    runtime_path TEXT NOT NULL,
    last_used TEXT
);

-- Packages in a fingerprint
CREATE TABLE fingerprint_packages (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT NOT NULL REFERENCES fingerprints(fingerprint),
    package_name TEXT NOT NULL,
    package_version TEXT NOT NULL,
    object_hash TEXT NOT NULL REFERENCES objects(hash),
    UNIQUE(fingerprint, package_name)
);

-- Fingerprint usage statistics
CREATE TABLE fingerprint_stats (
    fingerprint TEXT PRIMARY KEY REFERENCES fingerprints(fingerprint),
    total_uses INTEGER NOT NULL DEFAULT 0,
    last_used TEXT,
    avg_construction_time_ms REAL,
    total_construction_time_ms REAL
);

-- Indexes
CREATE INDEX idx_fp_packages_fingerprint ON fingerprint_packages(fingerprint);
CREATE INDEX idx_fp_packages_package ON fingerprint_packages(package_name, package_version);
CREATE INDEX idx_fp_stats_uses ON fingerprint_stats(total_uses DESC);
```

### Key Queries

```sql
-- Check if fingerprint exists
SELECT * FROM fingerprints WHERE fingerprint = ?;

-- Get all packages in a fingerprint
SELECT fp.package_name, fp.package_version, o.*
FROM fingerprint_packages fp
JOIN objects o ON fp.object_hash = o.hash
WHERE fp.fingerprint = ?;

-- Find fingerprints using a specific package
SELECT DISTINCT f.fingerprint, f.python_version, f.platform
FROM fingerprints f
JOIN fingerprint_packages fp ON f.fingerprint = fp.fingerprint
WHERE fp.object_hash = ?;

-- Get most used fingerprints (for cache optimization)
SELECT f.*, fs.total_uses
FROM fingerprints f
JOIN fingerprint_stats fs ON f.fingerprint = fs.fingerprint
ORDER BY fs.total_uses DESC
LIMIT 10;

-- Find stale fingerprints (not used in N days)
SELECT * FROM fingerprints
WHERE last_used < datetime('now', '-30 days');
```

---

## Database Configuration

### SQLite PRAGMA Settings

```sql
-- Enable WAL mode for concurrent access
PRAGMA journal_mode=WAL;

-- Normal synchronous (OS flushes to disk)
PRAGMA synchronous=NORMAL;

-- Busy timeout (wait for locks)
PRAGMA busy_timeout=5000;

-- Cache size (10MB)
PRAGMA cache_size=-10000;

-- Memory-mapped I/O (64MB)
PRAGMA mmap_size=67108864;

-- Foreign keys
PRAGMA foreign_keys=ON;

-- Optimize
PRAGMA optimize;
```

### Connection Pool

```python
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path

class DatabasePool:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.local = threading.local()

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self.local, "connection"):
            self.local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=5.0,
            )
            self.local.connection.execute("PRAGMA journal_mode=WAL")
            self.local.connection.execute("PRAGMA synchronous=NORMAL")
            self.local.connection.execute("PRAGMA busy_timeout=5000")
            self.local.connection.execute("PRAGMA foreign_keys=ON")
            self.local.connection.row_factory = sqlite3.Row
        return self.local.connection

    @contextmanager
    def transaction(self):
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def close(self):
        if hasattr(self.local, "connection"):
            self.local.connection.close()
            del self.local.connection
```

---

## Database Migration

### Migration Table

```sql
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL
);
```

### Migration Strategy

```python
MIGRATIONS = {
    1: """
        CREATE TABLE objects (...);
        CREATE TABLE package_metadata (...);
        CREATE TABLE entry_points (...);
    """,
    2: """
        CREATE TABLE dependencies (...);
        CREATE TABLE reverse_dependencies (...);
        CREATE TABLE conflicts (...);
    """,
    3: """
        CREATE TABLE fingerprints (...);
        CREATE TABLE fingerprint_packages (...);
        CREATE TABLE fingerprint_stats (...);
    """,
}

def migrate(db: DatabasePool):
    current_version = db.execute(
        "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
    ).fetchone()[0]

    for version in range(current_version + 1, len(MIGRATIONS) + 1):
        with db.transaction():
            db.execute(MIGRATIONS[version])
            db.execute(
                "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
                (version, f"Migration {version}")
            )
```

---

## Database Backup

### Automatic Backup

```python
import shutil
from datetime import datetime

def backup_databases(store_dir: Path):
    backup_dir = store_dir / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True)

    for db_file in ["metadata.db", "relationships.db", "fingerprints.db"]:
        src = store_dir / "index" / db_file
        dst = backup_dir / db_file
        shutil.copy2(src, dst)

    # Keep only last 7 backups
    backups = sorted(backup_dir.parent.iterdir())
    for old_backup in backups[:-7]:
        shutil.rmtree(old_backup)
```

---

## Database Performance

### Expected Performance

| Operation | Time | Notes |
|-----------|------|-------|
| Object lookup by hash | <1ms | Primary key |
| Object lookup by name | <5ms | Indexed |
| Dependency tree query | <10ms | Recursive CTE |
| Fingerprint lookup | <1ms | Primary key |
| Insert object | <5ms | WAL mode |
| Update reference count | <2ms | Single row |
| GC query (unused) | <20ms | Indexed scan |

### Index Sizes

| Index | Size (10K objects) | Notes |
|-------|-------------------|-------|
| idx_objects_package | ~500KB | Name + version |
| idx_objects_python | ~200KB | Python version |
| idx_deps_parent | ~1MB | Dependency tree |
| idx_fp_packages | ~500KB | Fingerprint packages |

---

## Database Architecture Invariants

1. **ACID guarantees**: SQLite provides atomicity, consistency, isolation, durability
2. **WAL mode**: Concurrent reads, serialized writes
3. **Foreign keys**: Referential integrity enforced
4. **Migrations**: Schema changes are versioned and reversible
5. **Backups**: Automatic daily backups with retention
6. **Thread safety**: Connection-per-thread model
7. **Performance**: All queries indexed, sub-20ms target
