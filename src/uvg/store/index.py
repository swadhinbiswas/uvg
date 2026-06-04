"""Store index using SQLite.

Provides persistent indexing for store objects, package metadata, and relationships.
"""

from __future__ import annotations

import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from uvg.core.exceptions import IndexCorruptionError

SCHEMA_VERSION = 1

METADATA_SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
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

CREATE TABLE IF NOT EXISTS package_metadata (
    hash TEXT PRIMARY KEY REFERENCES objects(hash),
    summary TEXT,
    description TEXT,
    author TEXT,
    author_email TEXT,
    license TEXT,
    home_page TEXT,
    classifiers TEXT,
    requires_python TEXT,
    provides_extra TEXT
);

CREATE TABLE IF NOT EXISTS entry_points (
    id INTEGER PRIMARY KEY,
    object_hash TEXT NOT NULL REFERENCES objects(hash),
    group_name TEXT NOT NULL,
    name TEXT NOT NULL,
    module TEXT NOT NULL,
    function TEXT NOT NULL,
    UNIQUE(object_hash, group_name, name)
);

CREATE TABLE IF NOT EXISTS shared_libraries (
    id INTEGER PRIMARY KEY,
    object_hash TEXT NOT NULL REFERENCES objects(hash),
    library_name TEXT NOT NULL,
    library_path TEXT NOT NULL,
    UNIQUE(object_hash, library_name)
);

CREATE INDEX IF NOT EXISTS idx_objects_package ON objects(package_name, package_version);
CREATE INDEX IF NOT EXISTS idx_objects_python ON objects(python_version);
CREATE INDEX IF NOT EXISTS idx_objects_abi ON objects(abi_tag);
CREATE INDEX IF NOT EXISTS idx_objects_platform ON objects(platform_tag, architecture);
CREATE INDEX IF NOT EXISTS idx_objects_native ON objects(is_native);
CREATE INDEX IF NOT EXISTS idx_objects_accessed ON objects(last_accessed);
CREATE INDEX IF NOT EXISTS idx_entry_points_object ON entry_points(object_hash);
CREATE INDEX IF NOT EXISTS idx_entry_points_name ON entry_points(name);
CREATE INDEX IF NOT EXISTS idx_shared_libs_object ON shared_libraries(object_hash);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT NOT NULL
);
"""

RELATIONSHIPS_SCHEMA = """
CREATE TABLE IF NOT EXISTS dependencies (
    id INTEGER PRIMARY KEY,
    parent_hash TEXT NOT NULL REFERENCES objects(hash),
    child_hash TEXT NOT NULL REFERENCES objects(hash),
    dependency_spec TEXT NOT NULL,
    is_direct BOOLEAN NOT NULL,
    depth INTEGER NOT NULL,
    UNIQUE(parent_hash, child_hash)
);

CREATE TABLE IF NOT EXISTS reverse_dependencies (
    id INTEGER PRIMARY KEY,
    child_hash TEXT NOT NULL REFERENCES objects(hash),
    parent_hash TEXT NOT NULL REFERENCES objects(hash),
    dependency_spec TEXT NOT NULL,
    UNIQUE(child_hash, parent_hash)
);

CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY,
    package_name TEXT NOT NULL,
    hash_a TEXT NOT NULL REFERENCES objects(hash),
    hash_b TEXT NOT NULL REFERENCES objects(hash),
    spec_a TEXT NOT NULL,
    spec_b TEXT NOT NULL,
    detected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_deps_parent ON dependencies(parent_hash);
CREATE INDEX IF NOT EXISTS idx_deps_child ON dependencies(child_hash);
CREATE INDEX IF NOT EXISTS idx_deps_depth ON dependencies(depth);
CREATE INDEX IF NOT EXISTS idx_reverse_child ON reverse_dependencies(child_hash);
CREATE INDEX IF NOT EXISTS idx_reverse_parent ON reverse_dependencies(parent_hash);
CREATE INDEX IF NOT EXISTS idx_conflicts_package ON conflicts(package_name);
"""

FINGERPRINTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS fingerprints (
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

CREATE TABLE IF NOT EXISTS fingerprint_packages (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT NOT NULL REFERENCES fingerprints(fingerprint),
    package_name TEXT NOT NULL,
    package_version TEXT NOT NULL,
    object_hash TEXT NOT NULL REFERENCES objects(hash),
    UNIQUE(fingerprint, package_name)
);

CREATE TABLE IF NOT EXISTS fingerprint_stats (
    fingerprint TEXT PRIMARY KEY REFERENCES fingerprints(fingerprint),
    total_uses INTEGER NOT NULL DEFAULT 0,
    last_used TEXT,
    avg_construction_time_ms REAL,
    total_construction_time_ms REAL
);

CREATE INDEX IF NOT EXISTS idx_fp_packages_fingerprint ON fingerprint_packages(fingerprint);
CREATE INDEX IF NOT EXISTS idx_fp_packages_package ON fingerprint_packages(package_name, package_version);
CREATE INDEX IF NOT EXISTS idx_fp_stats_uses ON fingerprint_stats(total_uses DESC);
"""


def _configure_connection(conn: sqlite3.Connection) -> None:
    """Configure a SQLite connection with optimal settings.

    Args:
        conn: SQLite connection to configure.
    """
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA cache_size=-10000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row


class DatabasePool:
    """Thread-safe SQLite connection pool.

    Uses thread-local storage for connection-per-thread model.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize database pool.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self.local = threading.local()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create a connection for the current thread.

        Returns:
            SQLite connection.
        """
        if not hasattr(self.local, "connection"):
            self.local.connection = sqlite3.connect(
                str(self.db_path),
                timeout=5.0,
            )
            _configure_connection(self.local.connection)
        conn: sqlite3.Connection = self.local.connection
        return conn

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Execute code within a database transaction.

        Yields:
            SQLite connection.

        Raises:
            IndexCorruptionError: If a database error occurs.
        """
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise IndexCorruptionError(f"Database error: {e}") from e

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        """Execute a query outside of an explicit transaction.

        Args:
            query: SQL query string.
            params: Query parameters.

        Returns:
            Cursor with results.
        """
        conn = self._get_connection()
        return conn.execute(query, params)

    def executemany(self, query: str, params: list[tuple[Any, ...]]) -> sqlite3.Cursor:
        """Execute a query with multiple parameter sets.

        Args:
            query: SQL query string.
            params: List of parameter tuples.

        Returns:
            Cursor with results.
        """
        conn = self._get_connection()
        return conn.executemany(query, params)

    def close(self) -> None:
        """Close the connection for the current thread."""
        if hasattr(self.local, "connection"):
            self.local.connection.close()
            del self.local.connection

    def initialize(self) -> None:
        """Initialize the database schema.

        Creates all tables if they do not exist.
        """
        with self.transaction() as conn:
            conn.executescript(METADATA_SCHEMA)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, description) VALUES (?, ?)",
                (1, "Initial schema"),
            )


class MetadataIndex:
    """Index for package metadata in metadata.db."""

    def __init__(self, db_pool: DatabasePool) -> None:
        """Initialize metadata index.

        Args:
            db_pool: Database connection pool.
        """
        self.db = db_pool

    def add_object(self, obj_data: dict[str, Any]) -> None:
        """Add an object to the index.

        Args:
            obj_data: Object metadata dictionary.
        """
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO objects (
                    hash, package_name, package_version, python_version,
                    abi_tag, platform_tag, architecture, wheel_filename,
                    wheel_hash, size_bytes, file_count, is_native,
                    extracted_at, reference_count, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    obj_data["hash"],
                    obj_data["package_name"],
                    obj_data["package_version"],
                    obj_data["python_version"],
                    obj_data["abi_tag"],
                    obj_data["platform_tag"],
                    obj_data["architecture"],
                    obj_data["wheel_filename"],
                    obj_data["wheel_hash"],
                    obj_data["size_bytes"],
                    obj_data["file_count"],
                    obj_data["is_native"],
                    obj_data["extracted_at"],
                    obj_data.get("created_by", "uvg"),
                ),
            )

    def get_object(self, obj_hash: str) -> dict[str, Any] | None:
        """Get an object by hash.

        Args:
            obj_hash: Object hash.

        Returns:
            Object metadata dictionary or None.
        """
        cursor = self.db.execute(
            "SELECT * FROM objects WHERE hash = ?",
            (obj_hash,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def find_by_package(self, name: str, version: str, python_version: str) -> list[dict[str, Any]]:
        """Find objects by package name, version, and Python version.

        Args:
            name: Package name.
            version: Package version.
            python_version: Python version.

        Returns:
            List of object metadata dictionaries.
        """
        cursor = self.db.execute(
            "SELECT * FROM objects WHERE package_name = ? AND package_version = ? AND python_version = ?",
            (name, version, python_version),
        )
        return [dict(row) for row in cursor.fetchall()]

    def find_unused_objects(self) -> list[dict[str, Any]]:
        """Find objects with zero reference count.

        Returns:
            List of unused object metadata dictionaries.
        """
        cursor = self.db.execute("SELECT * FROM objects WHERE reference_count = 0")
        return [dict(row) for row in cursor.fetchall()]

    def update_reference_count(self, obj_hash: str, count: int) -> None:
        """Update the reference count for an object.

        Args:
            obj_hash: Object hash.
            count: New reference count.
        """
        with self.db.transaction():
            self.db.execute(
                "UPDATE objects SET reference_count = ? WHERE hash = ?",
                (obj_hash, count),
            )

    def get_total_size(self) -> int:
        """Get the total size of all objects in bytes.

        Returns:
            Total size in bytes.
        """
        cursor = self.db.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM objects")
        row = cursor.fetchone()
        return int(row[0]) if row else 0

    def get_object_count(self) -> int:
        """Get the total number of objects.

        Returns:
            Object count.
        """
        cursor = self.db.execute("SELECT COUNT(*) FROM objects")
        row = cursor.fetchone()
        return int(row[0]) if row else 0

    def list_objects(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """List objects with pagination.

        Args:
            limit: Maximum number of objects to return.
            offset: Number of objects to skip.

        Returns:
            List of object metadata dictionaries.
        """
        cursor = self.db.execute(
            "SELECT * FROM objects ORDER BY extracted_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        return [dict(row) for row in cursor.fetchall()]

    def delete_object(self, obj_hash: str) -> None:
        """Delete an object from the index.

        Args:
            obj_hash: Object hash.
        """
        with self.db.transaction():
            self.db.execute("DELETE FROM objects WHERE hash = ?", (obj_hash,))


class FingerprintIndex:
    """Index for runtime fingerprints in fingerprints.db."""

    def __init__(self, db_pool: DatabasePool) -> None:
        """Initialize fingerprint index.

        Args:
            db_pool: Database connection pool.
        """
        self.db = db_pool

    def add_fingerprint(self, fp_data: dict[str, Any]) -> None:
        """Add a fingerprint to the index.

        Args:
            fp_data: Fingerprint metadata dictionary.
        """
        with self.db.transaction():
            self.db.execute(
                """
                INSERT OR IGNORE INTO fingerprints (
                    fingerprint, python_version, platform, architecture,
                    abi, manifest_hash, created_at, reference_count, runtime_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                """,
                (
                    fp_data["fingerprint"],
                    fp_data["python_version"],
                    fp_data["platform"],
                    fp_data["architecture"],
                    fp_data["abi"],
                    fp_data["manifest_hash"],
                    fp_data["created_at"],
                    fp_data["runtime_path"],
                ),
            )

    def get_fingerprint(self, fingerprint: str) -> dict[str, Any] | None:
        """Get a fingerprint by ID.

        Args:
            fingerprint: Fingerprint string.

        Returns:
            Fingerprint metadata dictionary or None.
        """
        cursor = self.db.execute(
            "SELECT * FROM fingerprints WHERE fingerprint = ?",
            (fingerprint,),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def increment_reference(self, fingerprint: str) -> None:
        """Increment the reference count for a fingerprint.

        Args:
            fingerprint: Fingerprint string.
        """
        with self.db.transaction():
            self.db.execute(
                "UPDATE fingerprints SET reference_count = reference_count + 1 WHERE fingerprint = ?",
                (fingerprint,),
            )

    def decrement_reference(self, fingerprint: str) -> None:
        """Decrement the reference count for a fingerprint.

        Args:
            fingerprint: Fingerprint string.
        """
        with self.db.transaction():
            self.db.execute(
                "UPDATE fingerprints SET reference_count = MAX(0, reference_count - 1) WHERE fingerprint = ?",
                (fingerprint,),
            )
