"""Tests for store object management."""

from __future__ import annotations

from pathlib import Path

import pytest

from uvg.core.exceptions import StoreCorruptionError
from uvg.store.object import ObjectMetadata, StoreObject, compute_file_hash


class TestComputeFileHash:
    def test_hash_file(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello world")

        hash_value = compute_file_hash(file_path)
        assert hash_value
        assert len(hash_value) == 64

    def test_hash_consistency(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.txt"
        file_path.write_text("hello world")

        hash1 = compute_file_hash(file_path)
        hash2 = compute_file_hash(file_path)
        assert hash1 == hash2

    def test_hash_different_content(self, tmp_path: Path) -> None:
        file1 = tmp_path / "test1.txt"
        file2 = tmp_path / "test2.txt"
        file1.write_text("hello")
        file2.write_text("world")

        hash1 = compute_file_hash(file1)
        hash2 = compute_file_hash(file2)
        assert hash1 != hash2


class TestObjectMetadata:
    def test_to_dict(self) -> None:
        metadata = ObjectMetadata(
            package_name="numpy",
            package_version="2.3.0",
            python_version="3.12",
            abi_tag="cp312",
            platform_tag="manylinux_2_17_x86_64",
            architecture="x86_64",
            wheel_hash="sha256:abc123",
        )
        d = metadata.to_dict()
        assert d["package_name"] == "numpy"
        assert d["package_version"] == "2.3.0"

    def test_from_dict(self) -> None:
        d = {
            "version": 1,
            "package_name": "numpy",
            "package_version": "2.3.0",
            "python_version": "3.12",
            "abi_tag": "cp312",
            "platform_tag": "manylinux_2_17_x86_64",
            "architecture": "x86_64",
            "wheel_filename": "numpy-2.3.0.whl",
            "wheel_hash": "sha256:abc123",
            "extracted_at": "2026-06-04T12:00:00Z",
            "extracted_by": "uvg/0.0.1",
            "size_bytes": 1000,
            "file_count": 10,
            "is_native": False,
            "dependencies": [],
            "entry_points": {},
            "shared_libraries": [],
        }
        metadata = ObjectMetadata.from_dict(d)
        assert metadata.package_name == "numpy"
        assert metadata.package_version == "2.3.0"

    def test_json_roundtrip(self) -> None:
        metadata = ObjectMetadata(
            package_name="numpy",
            package_version="2.3.0",
            python_version="3.12",
            abi_tag="cp312",
            platform_tag="manylinux_2_17_x86_64",
            architecture="x86_64",
            wheel_hash="sha256:abc123",
        )
        json_str = metadata.to_json()
        restored = ObjectMetadata.from_json(json_str)
        assert restored.package_name == metadata.package_name
        assert restored.package_version == metadata.package_version


class TestStoreObject:
    def test_metadata_path(self, tmp_path: Path) -> None:
        obj_path = tmp_path / "test-object"
        obj_path.mkdir()
        obj = StoreObject(obj_path)
        assert obj.metadata_path == obj_path / ".uvg-metadata.json"

    def test_metadata_missing(self, tmp_path: Path) -> None:
        obj_path = tmp_path / "test-object"
        obj_path.mkdir()
        obj = StoreObject(obj_path)
        with pytest.raises(StoreCorruptionError):
            _ = obj.metadata

    def test_metadata_corrupt(self, tmp_path: Path) -> None:
        obj_path = tmp_path / "test-object"
        obj_path.mkdir()
        (obj_path / ".uvg-metadata.json").write_text("not json")
        obj = StoreObject(obj_path)
        with pytest.raises(StoreCorruptionError):
            _ = obj.metadata

    def test_metadata_valid(self, tmp_path: Path) -> None:
        obj_path = tmp_path / "test-object"
        obj_path.mkdir()
        metadata = ObjectMetadata(
            package_name="numpy",
            package_version="2.3.0",
            python_version="3.12",
            abi_tag="cp312",
            platform_tag="manylinux_2_17_x86_64",
            architecture="x86_64",
            wheel_hash="sha256:abc123",
        )
        (obj_path / ".uvg-metadata.json").write_text(metadata.to_json())
        obj = StoreObject(obj_path)
        assert obj.metadata.package_name == "numpy"

    def test_get_size(self, tmp_path: Path) -> None:
        obj_path = tmp_path / "test-object"
        obj_path.mkdir()
        (obj_path / "file1.txt").write_text("hello")
        (obj_path / "file2.txt").write_text("world")
        obj = StoreObject(obj_path)
        assert obj.get_size() > 0

    def test_get_file_count(self, tmp_path: Path) -> None:
        obj_path = tmp_path / "test-object"
        obj_path.mkdir()
        (obj_path / "file1.txt").write_text("hello")
        (obj_path / "file2.txt").write_text("world")
        obj = StoreObject(obj_path)
        assert obj.get_file_count() == 2

    def test_repr(self, tmp_path: Path) -> None:
        obj_path = tmp_path / "test-object"
        obj_path.mkdir()
        metadata = ObjectMetadata(
            package_name="numpy",
            package_version="2.3.0",
            wheel_hash="sha256:abc123",
        )
        (obj_path / ".uvg-metadata.json").write_text(metadata.to_json())
        obj = StoreObject(obj_path)
        assert "numpy" in repr(obj)
        assert "2.3.0" in repr(obj)
