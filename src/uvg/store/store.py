"""Main store implementation.

Provides the content-addressable store for package objects.
"""

from __future__ import annotations

import os
import shutil
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from uvg.core.exceptions import (
    HashMismatchError,
    ObjectNotFoundError,
)
from uvg.core.models import PackageIdentity
from uvg.store.index import DatabasePool, FingerprintIndex, MetadataIndex
from uvg.store.object import ObjectMetadata, StoreObject, compute_file_hash


class Store:
    """Content-addressable store for package objects.

    The store is organized as:
    ~/.uvg/store/
        objects/sha256/<hash>-<abi>-<platform>-<arch>/
        index/
            metadata.db
            relationships.db
            fingerprints.db
        cache/
        tmp/
    """

    METADATA_DB = "metadata.db"
    RELATIONSHIPS_DB = "relationships.db"
    FINGERPRINTS_DB = "fingerprints.db"

    def __init__(self, store_path: Path | None = None) -> None:
        """Initialize the store.

        Args:
            store_path: Path to the store directory. Defaults to ~/.uvg/store.
        """
        if store_path is None:
            store_path = Path.home() / ".uvg" / "store"

        self.store_path = store_path
        self.objects_path = store_path / "objects" / "sha256"
        self.index_path = store_path / "index"
        self.cache_path = store_path / "cache"
        self.tmp_path = store_path / "tmp"

        self._ensure_directories()

        self.metadata_db = DatabasePool(self.index_path / self.METADATA_DB)
        self.metadata_db.initialize()
        self.metadata_index = MetadataIndex(self.metadata_db)

        self.fingerprints_db = DatabasePool(self.index_path / self.FINGERPRINTS_DB)
        self.fingerprints_db.initialize()
        self.fingerprint_index = FingerprintIndex(self.fingerprints_db)

    def _ensure_directories(self) -> None:
        """Create store directories if they do not exist."""
        self.objects_path.mkdir(parents=True, exist_ok=True)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        self.tmp_path.mkdir(parents=True, exist_ok=True)

    def create_object(self, wheel_path: Path, wheel_hash: str, identity: PackageIdentity) -> StoreObject:
        """Create a new store object from a wheel file.

        Args:
            wheel_path: Path to the wheel file.
            wheel_hash: Expected SHA-256 hash of the wheel.
            identity: Package identity information.

        Returns:
            The created StoreObject.

        Raises:
            HashMismatchError: If the wheel hash does not match.
            ObjectExistsError: If an object with this hash already exists.
            StoreCorruptionError: If object creation fails.
        """
        actual_hash = compute_file_hash(wheel_path)
        if actual_hash != wheel_hash.removeprefix("sha256:"):
            raise HashMismatchError(
                expected=wheel_hash,
                actual=f"sha256:{actual_hash}",
                context=f"Wheel {wheel_path.name}",
            )

        object_name = identity.object_name
        object_path = self.objects_path / object_name

        if object_path.exists():
            return StoreObject(object_path)

        temp_path = self.tmp_path / f"creating-{wheel_hash[:8]}-{id(self)}"

        try:
            self._extract_wheel(wheel_path, temp_path, identity)
            self._write_metadata(temp_path, identity, wheel_path.name)
            self._set_readonly(temp_path)
            temp_path.rename(object_path)
            self._index_object(object_path, identity, wheel_path.name)

            return StoreObject(object_path)

        except Exception:
            if temp_path.exists():
                shutil.rmtree(temp_path)
            raise

    def _extract_wheel(self, wheel_path: Path, dest_path: Path, identity: PackageIdentity) -> None:
        """Extract a wheel file to a directory.

        Args:
            wheel_path: Path to the wheel file.
            dest_path: Destination directory.
            identity: Package identity information.
        """
        import zipfile

        site_packages_dir = dest_path / "lib" / f"python{identity.python_version}" / "site-packages"
        site_packages_dir.mkdir(parents=True)

        with zipfile.ZipFile(wheel_path, "r") as zf:
            zf.extractall(site_packages_dir)

    def _write_metadata(self, object_path: Path, identity: PackageIdentity, wheel_filename: str) -> None:
        """Write metadata file to object directory.

        Args:
            object_path: Path to the object directory.
            identity: Package identity information.
            wheel_filename: Original wheel filename.
        """
        metadata = ObjectMetadata(
            package_name=identity.name,
            package_version=str(identity.version),
            python_version=identity.python_version,
            abi_tag=identity.abi_tag,
            platform_tag=identity.platform_tag,
            architecture=identity.architecture,
            wheel_filename=wheel_filename,
            wheel_hash=identity.wheel_hash,
            extracted_at=datetime.now(timezone.utc).isoformat(),
            extracted_by="uvg/0.0.1",
            size_bytes=0,
            file_count=0,
            is_native=self._is_native_wheel(object_path),
        )

        metadata_path = object_path / StoreObject.METADATA_FILE
        metadata_path.write_text(metadata.to_json(), encoding="utf-8")

    def _is_native_wheel(self, object_path: Path) -> bool:
        """Check if a wheel contains native extensions.

        Args:
            object_path: Path to the extracted wheel.

        Returns:
            True if the wheel contains native extensions.
        """
        native_extensions = (".so", ".pyd", ".dylib")
        return any(file_path.suffix in native_extensions for file_path in object_path.rglob("*"))

    def _set_readonly(self, path: Path) -> None:
        """Set read-only permissions on a directory tree.

        Args:
            path: Path to the directory.
        """
        for root, dirs, files in os.walk(str(path)):
            for d in dirs:
                dir_path = Path(root) / d
                current = dir_path.stat().st_mode
                dir_path.chmod(current & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)
            for f in files:
                file_path = Path(root) / f
                current = file_path.stat().st_mode
                file_path.chmod(current & ~stat.S_IWUSR & ~stat.S_IWGRP & ~stat.S_IWOTH)

    def _index_object(self, object_path: Path, identity: PackageIdentity, wheel_filename: str) -> None:
        """Add an object to the index.

        Args:
            object_path: Path to the object directory.
            identity: Package identity information.
            wheel_filename: Original wheel filename.
        """
        obj = StoreObject(object_path)
        size_bytes = obj.get_size()
        file_count = obj.get_file_count()

        obj_data: dict[str, Any] = {
            "hash": identity.wheel_hash,
            "package_name": identity.name,
            "package_version": str(identity.version),
            "python_version": identity.python_version,
            "abi_tag": identity.abi_tag,
            "platform_tag": identity.platform_tag,
            "architecture": identity.architecture,
            "wheel_filename": wheel_filename,
            "wheel_hash": identity.wheel_hash,
            "size_bytes": size_bytes,
            "file_count": file_count,
            "is_native": obj.metadata.is_native,
            "extracted_at": obj.metadata.extracted_at,
        }

        self.metadata_index.add_object(obj_data)

    def get_object(self, wheel_hash: str) -> StoreObject:
        """Get a store object by hash.

        Args:
            wheel_hash: SHA-256 hash of the object.

        Returns:
            The StoreObject.

        Raises:
            ObjectNotFoundError: If the object is not found.
        """
        index_data = self.metadata_index.get_object(wheel_hash)
        if index_data is None:
            raise ObjectNotFoundError(wheel_hash)

        stored_hash = index_data.get("wheel_hash", index_data.get("hash", ""))
        hash_short = stored_hash.removeprefix("sha256:")[:16]
        abi = index_data.get("abi_tag", "")
        platform = index_data.get("platform_tag", "")
        arch = index_data.get("architecture", "")
        object_path = self.objects_path / f"{hash_short}-{abi}-{platform}-{arch}"

        if not object_path.exists():
            raise ObjectNotFoundError(wheel_hash)

        return StoreObject(object_path)

    def has_object(self, wheel_hash: str) -> bool:
        """Check if an object exists in the store.

        Args:
            wheel_hash: SHA-256 hash of the object.

        Returns:
            True if the object exists.
        """
        return self.metadata_index.get_object(wheel_hash) is not None

    def delete_object(self, wheel_hash: str) -> None:
        """Delete a store object by hash.

        Args:
            wheel_hash: SHA-256 hash of the object.

        Raises:
            ObjectNotFoundError: If the object is not found.
        """
        index_data = self.metadata_index.get_object(wheel_hash)
        if index_data is None:
            raise ObjectNotFoundError(wheel_hash)

        stored_hash = index_data.get("wheel_hash", index_data.get("hash", ""))
        hash_short = stored_hash.removeprefix("sha256:")[:16]
        abi = index_data.get("abi_tag", "")
        platform = index_data.get("platform_tag", "")
        arch = index_data.get("architecture", "")
        object_path = self.objects_path / f"{hash_short}-{abi}-{platform}-{arch}"

        if object_path.exists():
            for root, dirs, files in os.walk(str(object_path)):
                for d in dirs:
                    dir_path = Path(root) / d
                    current = dir_path.stat().st_mode
                    dir_path.chmod(current | stat.S_IWUSR)
                for f in files:
                    file_path = Path(root) / f
                    current = file_path.stat().st_mode
                    file_path.chmod(current | stat.S_IWUSR)
            shutil.rmtree(object_path)

        self.metadata_index.delete_object(wheel_hash)

    def get_info(self) -> dict[str, Any]:
        """Get store information.

        Returns:
            Dictionary with store statistics.
        """
        return {
            "store_path": str(self.store_path),
            "object_count": self.metadata_index.get_object_count(),
            "total_size_bytes": self.metadata_index.get_total_size(),
            "total_size_mb": round(self.metadata_index.get_total_size() / (1024 * 1024), 2),
        }

    def list_objects(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """List objects in the store.

        Args:
            limit: Maximum number of objects to return.
            offset: Number of objects to skip.

        Returns:
            List of object metadata dictionaries.
        """
        return self.metadata_index.list_objects(limit, offset)

    def find_packages(self, name: str, version: str, python_version: str) -> list[StoreObject]:
        """Find packages by name, version, and Python version.

        Args:
            name: Package name.
            version: Package version.
            python_version: Python version.

        Returns:
            List of matching StoreObjects.
        """
        objects_data = self.metadata_index.find_by_package(name, version, python_version)
        objects = []
        for obj_data in objects_data:
            try:
                obj = self.get_object(obj_data["hash"])
                objects.append(obj)
            except ObjectNotFoundError:
                continue
        return objects
