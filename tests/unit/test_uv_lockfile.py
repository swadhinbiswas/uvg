"""Tests for UVG lockfile handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from uvg.uv.lockfile import LockfilePackage, UVGLockfile, UVLockfileParser


class TestLockfilePackage:
    def test_to_dict(self) -> None:
        pkg = LockfilePackage(
            name="numpy",
            version="2.3.0",
            wheel="numpy-2.3.0.whl",
            hash="sha256:abc",
            abi="cp312",
            platform="linux",
        )
        d = pkg.to_dict()
        assert d["name"] == "numpy"
        assert d["version"] == "2.3.0"

    def test_from_dict(self) -> None:
        d = {
            "name": "numpy",
            "version": "2.3.0",
            "wheel": "numpy-2.3.0.whl",
            "hash": "sha256:abc",
            "abi": "cp312",
            "platform": "linux",
            "dependencies": [],
        }
        pkg = LockfilePackage.from_dict(d)
        assert pkg.name == "numpy"
        assert pkg.version == "2.3.0"


class TestUVGLockfile:
    def test_to_dict(self) -> None:
        lockfile = UVGLockfile(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            fingerprint="runtime_abc123",
            packages=[
                LockfilePackage(
                    name="numpy",
                    version="2.3.0",
                    hash="sha256:abc",
                ),
            ],
        )
        d = lockfile.to_dict()
        assert d["metadata"]["python_version"] == "3.12"
        assert len(d["packages"]) == 1

    def test_from_dict(self) -> None:
        d = {
            "metadata": {
                "version": 1,
                "python_version": "3.12",
                "platform": "linux",
                "architecture": "x86_64",
                "fingerprint": "runtime_abc123",
                "metadata_version": 1,
            },
            "packages": [
                {
                    "name": "numpy",
                    "version": "2.3.0",
                    "wheel": "",
                    "hash": "sha256:abc",
                    "abi": "cp312",
                    "platform": "linux",
                    "dependencies": [],
                },
            ],
        }
        lockfile = UVGLockfile.from_dict(d)
        assert lockfile.python_version == "3.12"
        assert len(lockfile.packages) == 1

    def test_json_roundtrip(self) -> None:
        lockfile = UVGLockfile(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            fingerprint="runtime_abc123",
            packages=[
                LockfilePackage(
                    name="numpy",
                    version="2.3.0",
                    hash="sha256:abc",
                ),
            ],
        )
        json_str = lockfile.to_json()
        restored = UVGLockfile.from_json(json_str)
        assert restored.python_version == lockfile.python_version
        assert len(restored.packages) == 1

    def test_save_load(self, tmp_path: Path) -> None:
        lockfile = UVGLockfile(
            python_version="3.12",
            platform="linux",
            packages=[
                LockfilePackage(
                    name="numpy",
                    version="2.3.0",
                    hash="sha256:abc",
                ),
            ],
        )

        path = tmp_path / "uvg.lock"
        lockfile.save(path)
        loaded = UVGLockfile.load(path)
        assert len(loaded.packages) == 1

    def test_compute_hash(self) -> None:
        lockfile = UVGLockfile(
            python_version="3.12",
            packages=[
                LockfilePackage(
                    name="numpy",
                    version="2.3.0",
                    hash="sha256:abc",
                ),
            ],
        )
        hash1 = lockfile.compute_hash()
        hash2 = lockfile.compute_hash()
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_to_runtime_manifest(self) -> None:
        lockfile = UVGLockfile(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            fingerprint="runtime_abc123",
            packages=[
                LockfilePackage(
                    name="numpy",
                    version="2.3.0",
                    hash="sha256:abc",
                    abi="cp312",
                    platform="linux",
                ),
            ],
        )
        manifest = lockfile.to_runtime_manifest()
        assert manifest.has_package("numpy")
        assert manifest.fingerprint == "runtime_abc123"


class TestUVLockfileParser:
    def test_parse_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            UVLockfileParser.parse_uv_lock(tmp_path / "nonexistent.lock")

    def test_parse_basic(self, tmp_path: Path) -> None:
        lockfile_content = """version = 1
requires-python = ">=3.10"

[[package]]
name = "numpy"
version = "2.3.0"
source = { registry = "https://pypi.org/simple" }

[[package]]
name = "requests"
version = "2.31.0"
source = { registry = "https://pypi.org/simple" }
"""
        lockfile_path = tmp_path / "uv.lock"
        lockfile_path.write_text(lockfile_content, encoding="utf-8")

        result = UVLockfileParser.parse_uv_lock(lockfile_path)
        assert len(result.packages) == 2
        assert result.packages[0].name == "numpy"
        assert result.packages[1].name == "requests"
