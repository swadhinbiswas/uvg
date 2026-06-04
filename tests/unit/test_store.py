"""Tests for the main store implementation."""

from __future__ import annotations

from pathlib import Path

import pytest

from uvg.core.exceptions import HashMismatchError, ObjectNotFoundError
from uvg.core.models import PackageIdentity, WheelInfo
from uvg.store.object import compute_file_hash
from uvg.store.store import Store


class TestStore:
    def test_initialization(self, tmp_path: Path) -> None:
        store = Store(store_path=tmp_path / "store")
        assert store.store_path.exists()
        assert store.objects_path.exists()
        assert store.index_path.exists()
        assert store.cache_path.exists()
        assert store.tmp_path.exists()

    def test_create_object(self, tmp_store: Store, sample_wheel: Path) -> None:
        wheel_hash = compute_file_hash(sample_wheel)
        wheel_info = WheelInfo.parse(sample_wheel.name)
        identity = PackageIdentity(
            name=wheel_info.distribution,
            version=wheel_info.version,
            python_version="3.12",
            abi_tag=wheel_info.abi_tag,
            platform_tag=wheel_info.platform_tag,
            architecture="x86_64",
            wheel_hash=f"sha256:{wheel_hash}",
        )

        obj = tmp_store.create_object(sample_wheel, f"sha256:{wheel_hash}", identity)
        assert obj.path.exists()
        assert obj.metadata.package_name == "test_pkg"

    def test_create_object_hash_mismatch(self, tmp_store: Store, sample_wheel: Path) -> None:
        wheel_info = WheelInfo.parse(sample_wheel.name)
        identity = PackageIdentity(
            name=wheel_info.distribution,
            version=wheel_info.version,
            python_version="3.12",
            abi_tag=wheel_info.abi_tag,
            platform_tag=wheel_info.platform_tag,
            architecture="x86_64",
            wheel_hash="sha256:wrong_hash",
        )

        with pytest.raises(HashMismatchError):
            tmp_store.create_object(sample_wheel, "sha256:wrong_hash", identity)

    def test_create_object_idempotent(self, tmp_store: Store, sample_wheel: Path) -> None:
        wheel_hash = compute_file_hash(sample_wheel)
        wheel_info = WheelInfo.parse(sample_wheel.name)
        identity = PackageIdentity(
            name=wheel_info.distribution,
            version=wheel_info.version,
            python_version="3.12",
            abi_tag=wheel_info.abi_tag,
            platform_tag=wheel_info.platform_tag,
            architecture="x86_64",
            wheel_hash=f"sha256:{wheel_hash}",
        )

        obj1 = tmp_store.create_object(sample_wheel, f"sha256:{wheel_hash}", identity)
        obj2 = tmp_store.create_object(sample_wheel, f"sha256:{wheel_hash}", identity)
        assert obj1.path == obj2.path

    def test_get_object(self, tmp_store: Store, sample_wheel: Path) -> None:
        wheel_hash = compute_file_hash(sample_wheel)
        wheel_info = WheelInfo.parse(sample_wheel.name)
        identity = PackageIdentity(
            name=wheel_info.distribution,
            version=wheel_info.version,
            python_version="3.12",
            abi_tag=wheel_info.abi_tag,
            platform_tag=wheel_info.platform_tag,
            architecture="x86_64",
            wheel_hash=f"sha256:{wheel_hash}",
        )

        tmp_store.create_object(sample_wheel, f"sha256:{wheel_hash}", identity)
        obj = tmp_store.get_object(f"sha256:{wheel_hash}")
        assert obj is not None

    def test_get_object_not_found(self, tmp_store: Store) -> None:
        with pytest.raises(ObjectNotFoundError):
            tmp_store.get_object("sha256:nonexistent")

    def test_has_object(self, tmp_store: Store, sample_wheel: Path) -> None:
        wheel_hash = compute_file_hash(sample_wheel)
        wheel_info = WheelInfo.parse(sample_wheel.name)
        identity = PackageIdentity(
            name=wheel_info.distribution,
            version=wheel_info.version,
            python_version="3.12",
            abi_tag=wheel_info.abi_tag,
            platform_tag=wheel_info.platform_tag,
            architecture="x86_64",
            wheel_hash=f"sha256:{wheel_hash}",
        )

        tmp_store.create_object(sample_wheel, f"sha256:{wheel_hash}", identity)
        assert tmp_store.has_object(f"sha256:{wheel_hash}")
        assert not tmp_store.has_object("sha256:nonexistent")

    def test_delete_object(self, tmp_store: Store, sample_wheel: Path) -> None:
        wheel_hash = compute_file_hash(sample_wheel)
        wheel_info = WheelInfo.parse(sample_wheel.name)
        identity = PackageIdentity(
            name=wheel_info.distribution,
            version=wheel_info.version,
            python_version="3.12",
            abi_tag=wheel_info.abi_tag,
            platform_tag=wheel_info.platform_tag,
            architecture="x86_64",
            wheel_hash=f"sha256:{wheel_hash}",
        )

        tmp_store.create_object(sample_wheel, f"sha256:{wheel_hash}", identity)
        assert tmp_store.has_object(f"sha256:{wheel_hash}")

        tmp_store.delete_object(f"sha256:{wheel_hash}")
        assert not tmp_store.has_object(f"sha256:{wheel_hash}")

    def test_get_info(self, tmp_store: Store) -> None:
        info = tmp_store.get_info()
        assert "store_path" in info
        assert "object_count" in info
        assert "total_size_bytes" in info
        assert info["object_count"] == 0

    def test_list_objects(self, tmp_store: Store) -> None:
        objects = tmp_store.list_objects()
        assert isinstance(objects, list)
        assert len(objects) == 0

    def test_native_wheel_detection(self, tmp_store: Store, native_wheel: Path) -> None:
        wheel_hash = compute_file_hash(native_wheel)
        wheel_info = WheelInfo.parse(native_wheel.name)
        identity = PackageIdentity(
            name=wheel_info.distribution,
            version=wheel_info.version,
            python_version="3.12",
            abi_tag=wheel_info.abi_tag,
            platform_tag=wheel_info.platform_tag,
            architecture="x86_64",
            wheel_hash=f"sha256:{wheel_hash}",
        )

        obj = tmp_store.create_object(native_wheel, f"sha256:{wheel_hash}", identity)
        assert obj.metadata.is_native is True
