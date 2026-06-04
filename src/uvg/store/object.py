"""Store object management.

Handles creation, retrieval, and verification of content-addressable store objects.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from uvg.core.exceptions import StoreCorruptionError
from uvg.core.models import PackageIdentity


@dataclass
class ObjectMetadata:
    """Metadata stored with each store object."""

    version: int = 1
    package_name: str = ""
    package_version: str = ""
    python_version: str = ""
    abi_tag: str = ""
    platform_tag: str = ""
    architecture: str = ""
    wheel_filename: str = ""
    wheel_hash: str = ""
    extracted_at: str = ""
    extracted_by: str = ""
    size_bytes: int = 0
    file_count: int = 0
    is_native: bool = False
    dependencies: list[str] | None = None
    entry_points: dict[str, str] | None = None
    shared_libraries: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert metadata to dictionary.

        Returns:
            Dictionary representation of metadata.
        """
        return {
            "version": self.version,
            "package_name": self.package_name,
            "package_version": self.package_version,
            "python_version": self.python_version,
            "abi_tag": self.abi_tag,
            "platform_tag": self.platform_tag,
            "architecture": self.architecture,
            "wheel_filename": self.wheel_filename,
            "wheel_hash": self.wheel_hash,
            "extracted_at": self.extracted_at,
            "extracted_by": self.extracted_by,
            "size_bytes": self.size_bytes,
            "file_count": self.file_count,
            "is_native": self.is_native,
            "dependencies": self.dependencies or [],
            "entry_points": self.entry_points or {},
            "shared_libraries": self.shared_libraries or [],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ObjectMetadata:
        """Create metadata from dictionary.

        Args:
            data: Dictionary representation of metadata.

        Returns:
            ObjectMetadata instance.
        """
        return cls(
            version=data.get("version", 1),
            package_name=data.get("package_name", ""),
            package_version=data.get("package_version", ""),
            python_version=data.get("python_version", ""),
            abi_tag=data.get("abi_tag", ""),
            platform_tag=data.get("platform_tag", ""),
            architecture=data.get("architecture", ""),
            wheel_filename=data.get("wheel_filename", ""),
            wheel_hash=data.get("wheel_hash", ""),
            extracted_at=data.get("extracted_at", ""),
            extracted_by=data.get("extracted_by", ""),
            size_bytes=data.get("size_bytes", 0),
            file_count=data.get("file_count", 0),
            is_native=data.get("is_native", False),
            dependencies=data.get("dependencies", []),
            entry_points=data.get("entry_points", {}),
            shared_libraries=data.get("shared_libraries", []),
        )

    def to_json(self) -> str:
        """Serialize metadata to JSON string.

        Returns:
            JSON string representation.
        """
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> ObjectMetadata:
        """Deserialize metadata from JSON string.

        Args:
            json_str: JSON string representation.

        Returns:
            ObjectMetadata instance.
        """
        return cls.from_dict(json.loads(json_str))


def compute_file_hash(file_path: Path, algorithm: str = "sha256") -> str:
    """Compute the hash of a file.

    Args:
        file_path: Path to the file.
        algorithm: Hash algorithm to use.

    Returns:
        Hex digest of the file hash.
    """
    h = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_directory_hash(directory: Path, algorithm: str = "sha256") -> str:
    """Compute a combined hash of all files in a directory.

    Args:
        directory: Path to the directory.
        algorithm: Hash algorithm to use.

    Returns:
        Hex digest of the combined directory hash.
    """
    h = hashlib.new(algorithm)
    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file():
            file_hash = compute_file_hash(file_path, algorithm)
            h.update(file_hash.encode())
    return h.hexdigest()


class StoreObject:
    """Represents a content-addressable store object.

    Store objects are immutable and identified by their content hash.
    """

    METADATA_FILE = ".uvg-metadata.json"

    def __init__(self, path: Path) -> None:
        """Initialize a store object.

        Args:
            path: Path to the store object directory.
        """
        self.path = path
        self._metadata: ObjectMetadata | None = None

    @property
    def metadata_path(self) -> Path:
        """Path to the metadata file.

        Returns:
            Path to .uvg-metadata.json.
        """
        return self.path / self.METADATA_FILE

    @property
    def metadata(self) -> ObjectMetadata:
        """Load and return object metadata.

        Returns:
            ObjectMetadata instance.

        Raises:
            StoreCorruptionError: If metadata file is missing or corrupt.
        """
        if self._metadata is None:
            if not self.metadata_path.exists():
                raise StoreCorruptionError(f"Metadata file missing: {self.metadata_path}")
            try:
                content = self.metadata_path.read_text(encoding="utf-8")
                self._metadata = ObjectMetadata.from_json(content)
            except (json.JSONDecodeError, KeyError) as e:
                raise StoreCorruptionError(f"Corrupt metadata: {self.metadata_path}: {e}") from e
        return self._metadata

    @property
    def hash(self) -> str:
        """Get the object's content hash.

        Returns:
            SHA-256 hash string.
        """
        return self.metadata.wheel_hash

    @property
    def package_identity(self) -> PackageIdentity:
        """Get the package identity from metadata.

        Returns:
            PackageIdentity instance.
        """
        from uvg.core.models import Version

        return PackageIdentity(
            name=self.metadata.package_name,
            version=Version.parse(self.metadata.package_version),
            python_version=self.metadata.python_version,
            abi_tag=self.metadata.abi_tag,
            platform_tag=self.metadata.platform_tag,
            architecture=self.metadata.architecture,
            wheel_hash=self.metadata.wheel_hash,
        )

    def verify_integrity(self) -> bool:
        """Verify the integrity of the store object.

        Returns:
            True if integrity check passes.

        Raises:
            StoreCorruptionError: If integrity check fails.
        """
        if not self.path.exists():
            raise StoreCorruptionError(f"Object directory missing: {self.path}")

        if not self.metadata_path.exists():
            raise StoreCorruptionError(f"Metadata file missing: {self.metadata_path}")

        return True

    def get_size(self) -> int:
        """Get the total size of the object in bytes.

        Returns:
            Total size in bytes.
        """
        total = 0
        for file_path in self.path.rglob("*"):
            if file_path.is_file():
                total += file_path.stat().st_size
        return total

    def get_file_count(self) -> int:
        """Get the total number of files in the object.

        Returns:
            Total file count.
        """
        return sum(1 for f in self.path.rglob("*") if f.is_file())

    def __repr__(self) -> str:
        return f"StoreObject({self.metadata.package_name}=={self.metadata.package_version})"
