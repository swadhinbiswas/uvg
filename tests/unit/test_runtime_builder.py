"""Tests for runtime builder."""

from __future__ import annotations

from pathlib import Path

from uvg.core.models import PackageIdentity, WheelInfo
from uvg.runtime.builder import RuntimeBuilder
from uvg.store.object import compute_file_hash
from uvg.store.store import Store


class TestRuntimeBuilder:
    def test_build_basic(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        runtime_dir = tmp_path / "runtime"
        builder = RuntimeBuilder(
            runtime_dir=runtime_dir,
            store_path=tmp_store.store_path,
        )

        packages = {
            "test_pkg": {
                "version": "1.0.0",
                "wheel_hash": f"sha256:{wheel_hash}",
                "abi": wheel_info.abi_tag,
                "platform": wheel_info.platform_tag,
                "dependencies": [],
                "is_native": False,
            },
        }

        manifest = builder.build(
            packages=packages,
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi=wheel_info.abi_tag,
        )

        assert manifest.fingerprint.startswith("runtime_")
        assert manifest.has_package("test_pkg")
        assert (runtime_dir / "manifest.json").exists()
        assert (runtime_dir / "fingerprint").exists()
        assert (runtime_dir / "site-packages").exists()

    def test_build_creates_symlinks(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        runtime_dir = tmp_path / "runtime"
        builder = RuntimeBuilder(
            runtime_dir=runtime_dir,
            store_path=tmp_store.store_path,
        )

        packages = {
            "test_pkg": {
                "version": "1.0.0",
                "wheel_hash": f"sha256:{wheel_hash}",
                "abi": wheel_info.abi_tag,
                "platform": wheel_info.platform_tag,
                "dependencies": [],
                "is_native": False,
            },
        }

        builder.build(
            packages=packages,
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi=wheel_info.abi_tag,
        )

        symlink = runtime_dir / "site-packages" / "test_pkg"
        assert symlink.is_symlink()
        assert symlink.exists()

    def test_build_creates_entry_points(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        runtime_dir = tmp_path / "runtime"
        builder = RuntimeBuilder(
            runtime_dir=runtime_dir,
            store_path=tmp_store.store_path,
        )

        packages = {
            "test_pkg": {
                "version": "1.0.0",
                "wheel_hash": f"sha256:{wheel_hash}",
                "abi": wheel_info.abi_tag,
                "platform": wheel_info.platform_tag,
                "dependencies": [],
                "is_native": False,
            },
        }

        entry_points = {
            "test_cmd": {
                "module": "test_pkg",
                "function": "main",
            },
        }

        builder.build(
            packages=packages,
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi=wheel_info.abi_tag,
            entry_points=entry_points,
        )

        script = runtime_dir / "bin" / "test_cmd"
        assert script.exists()
        content = script.read_text()
        assert "test_pkg" in content
        assert "main" in content

    def test_build_idempotent_fingerprint(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        runtime_dir = tmp_path / "runtime"
        builder = RuntimeBuilder(
            runtime_dir=runtime_dir,
            store_path=tmp_store.store_path,
        )

        packages = {
            "test_pkg": {
                "version": "1.0.0",
                "wheel_hash": f"sha256:{wheel_hash}",
                "abi": wheel_info.abi_tag,
                "platform": wheel_info.platform_tag,
                "dependencies": [],
                "is_native": False,
            },
        }

        manifest1 = builder.build(
            packages=packages,
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi=wheel_info.abi_tag,
        )
        manifest2 = builder.build(
            packages=packages,
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi=wheel_info.abi_tag,
        )

        assert manifest1.fingerprint == manifest2.fingerprint

    def test_verify_passes(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        runtime_dir = tmp_path / "runtime"
        builder = RuntimeBuilder(
            runtime_dir=runtime_dir,
            store_path=tmp_store.store_path,
        )

        packages = {
            "test_pkg": {
                "version": "1.0.0",
                "wheel_hash": f"sha256:{wheel_hash}",
                "abi": wheel_info.abi_tag,
                "platform": wheel_info.platform_tag,
                "dependencies": [],
                "is_native": False,
            },
        }

        builder.build(
            packages=packages,
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi=wheel_info.abi_tag,
        )

        errors = builder.verify()
        assert len(errors) == 0

    def test_verify_missing_manifest(self, tmp_path: Path) -> None:
        runtime_dir = tmp_path / "runtime"
        runtime_dir.mkdir()

        builder = RuntimeBuilder(runtime_dir=runtime_dir)
        errors = builder.verify()
        assert len(errors) > 0
        assert "Manifest file missing" in errors

    def test_load_manifest(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        runtime_dir = tmp_path / "runtime"
        builder = RuntimeBuilder(
            runtime_dir=runtime_dir,
            store_path=tmp_store.store_path,
        )

        packages = {
            "test_pkg": {
                "version": "1.0.0",
                "wheel_hash": f"sha256:{wheel_hash}",
                "abi": wheel_info.abi_tag,
                "platform": wheel_info.platform_tag,
                "dependencies": [],
                "is_native": False,
            },
        }

        builder.build(
            packages=packages,
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi=wheel_info.abi_tag,
        )

        loaded = builder.load_manifest()
        assert loaded.has_package("test_pkg")

    def test_get_fingerprint(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        runtime_dir = tmp_path / "runtime"
        builder = RuntimeBuilder(
            runtime_dir=runtime_dir,
            store_path=tmp_store.store_path,
        )

        packages = {
            "test_pkg": {
                "version": "1.0.0",
                "wheel_hash": f"sha256:{wheel_hash}",
                "abi": wheel_info.abi_tag,
                "platform": wheel_info.platform_tag,
                "dependencies": [],
                "is_native": False,
            },
        }

        builder.build(
            packages=packages,
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi=wheel_info.abi_tag,
        )

        fp = builder.get_fingerprint()
        assert fp.startswith("runtime_")

    def test_get_python_path(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        runtime_dir = tmp_path / "runtime"
        builder = RuntimeBuilder(
            runtime_dir=runtime_dir,
            store_path=tmp_store.store_path,
        )

        packages = {
            "test_pkg": {
                "version": "1.0.0",
                "wheel_hash": f"sha256:{wheel_hash}",
                "abi": wheel_info.abi_tag,
                "platform": wheel_info.platform_tag,
                "dependencies": [],
                "is_native": False,
            },
        }

        builder.build(
            packages=packages,
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi=wheel_info.abi_tag,
        )

        paths = builder.get_python_path()
        assert len(paths) > 0
