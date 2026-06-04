"""Tests for runtime manifest."""

from __future__ import annotations

from pathlib import Path

from uvg.runtime.manifest import ManifestEntryPoint, ManifestPackage, RuntimeManifest


class TestManifestPackage:
    def test_to_dict(self) -> None:
        pkg = ManifestPackage(
            name="numpy",
            version="2.3.0",
            wheel_hash="sha256:aaa",
            store_path="/store/numpy",
            abi="cp312",
            platform="linux",
        )
        d = pkg.to_dict()
        assert d["name"] == "numpy"
        assert d["version"] == "2.3.0"
        assert d["wheel_hash"] == "sha256:aaa"

    def test_from_dict(self) -> None:
        d = {
            "name": "numpy",
            "version": "2.3.0",
            "wheel_hash": "sha256:aaa",
            "store_path": "/store/numpy",
            "abi": "cp312",
            "platform": "linux",
            "dependencies": [],
            "is_native": True,
        }
        pkg = ManifestPackage.from_dict(d)
        assert pkg.name == "numpy"
        assert pkg.is_native is True

    def test_editable(self) -> None:
        pkg = ManifestPackage(
            name="my-pkg",
            version="0.1.0",
            wheel_hash="sha256:bbb",
            store_path="",
            abi="py3",
            platform="any",
            editable=True,
            source_path="/home/user/my-pkg/src",
        )
        d = pkg.to_dict()
        assert d["editable"] is True
        assert d["source_path"] == "/home/user/my-pkg/src"


class TestManifestEntryPoint:
    def test_to_dict(self) -> None:
        ep = ManifestEntryPoint(
            name="pytest",
            module="pytest",
            function="console_main",
        )
        d = ep.to_dict()
        assert d["name"] == "pytest"
        assert d["module"] == "pytest"
        assert d["function"] == "console_main"

    def test_from_dict(self) -> None:
        d = {
            "name": "black",
            "module": "black",
            "function": "main",
        }
        ep = ManifestEntryPoint.from_dict(d)
        assert ep.name == "black"


class TestRuntimeManifest:
    def test_to_dict(self) -> None:
        manifest = RuntimeManifest(
            version=1,
            fingerprint="runtime_abc123",
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            packages={
                "numpy": ManifestPackage(
                    name="numpy",
                    version="2.3.0",
                    wheel_hash="sha256:aaa",
                    store_path="/store/numpy",
                    abi="cp312",
                    platform="linux",
                ),
            },
            created_at="2026-06-04T12:00:00Z",
        )
        d = manifest.to_dict()
        assert d["fingerprint"] == "runtime_abc123"
        assert "numpy" in d["packages"]

    def test_from_dict(self) -> None:
        d = {
            "version": 1,
            "fingerprint": "runtime_abc123",
            "python_version": "3.12",
            "platform": "linux",
            "architecture": "x86_64",
            "abi": "cp312",
            "created_at": "2026-06-04T12:00:00Z",
            "packages": {
                "numpy": {
                    "name": "numpy",
                    "version": "2.3.0",
                    "wheel_hash": "sha256:aaa",
                    "store_path": "/store/numpy",
                    "abi": "cp312",
                    "platform": "linux",
                    "dependencies": [],
                    "is_native": True,
                },
            },
            "entry_points": {},
        }
        manifest = RuntimeManifest.from_dict(d)
        assert manifest.fingerprint == "runtime_abc123"
        assert manifest.has_package("numpy")

    def test_json_roundtrip(self, tmp_path: Path) -> None:
        manifest = RuntimeManifest(
            version=1,
            fingerprint="runtime_abc123",
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            packages={
                "numpy": ManifestPackage(
                    name="numpy",
                    version="2.3.0",
                    wheel_hash="sha256:aaa",
                    store_path="/store/numpy",
                    abi="cp312",
                    platform="linux",
                ),
            },
            created_at="2026-06-04T12:00:00Z",
        )

        json_str = manifest.to_json()
        restored = RuntimeManifest.from_json(json_str)
        assert restored.fingerprint == manifest.fingerprint
        assert restored.has_package("numpy")

    def test_save_load(self, tmp_path: Path) -> None:
        manifest = RuntimeManifest(
            version=1,
            fingerprint="runtime_abc123",
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            packages={
                "numpy": ManifestPackage(
                    name="numpy",
                    version="2.3.0",
                    wheel_hash="sha256:aaa",
                    store_path="/store/numpy",
                    abi="cp312",
                    platform="linux",
                ),
            },
            created_at="2026-06-04T12:00:00Z",
        )

        path = tmp_path / "manifest.json"
        manifest.save(path)
        loaded = RuntimeManifest.load(path)
        assert loaded.fingerprint == manifest.fingerprint
        assert loaded.has_package("numpy")

    def test_get_site_packages_paths(self) -> None:
        manifest = RuntimeManifest(
            packages={
                "numpy": ManifestPackage(
                    name="numpy",
                    version="2.3.0",
                    wheel_hash="sha256:aaa",
                    store_path="/store/numpy",
                    abi="cp312",
                    platform="linux",
                ),
                "my-pkg": ManifestPackage(
                    name="my-pkg",
                    version="0.1.0",
                    wheel_hash="sha256:bbb",
                    store_path="",
                    abi="py3",
                    platform="any",
                    editable=True,
                    source_path="/home/user/my-pkg/src",
                ),
            },
        )
        paths = manifest.get_site_packages_paths()
        assert "/store/numpy" in paths
        assert "/home/user/my-pkg/src" in paths

    def test_has_package(self) -> None:
        manifest = RuntimeManifest(
            packages={
                "numpy": ManifestPackage(
                    name="numpy",
                    version="2.3.0",
                    wheel_hash="sha256:aaa",
                    store_path="/store/numpy",
                    abi="cp312",
                    platform="linux",
                ),
            },
        )
        assert manifest.has_package("numpy")
        assert not manifest.has_package("pandas")
