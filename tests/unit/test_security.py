"""Tests for security verification."""

from __future__ import annotations

from pathlib import Path

from uvg.core.models import PackageIdentity, WheelInfo
from uvg.runtime.builder import RuntimeBuilder
from uvg.runtime.manifest import ManifestPackage, RuntimeManifest
from uvg.security.verifier import SecurityVerifier, VerificationReport
from uvg.store.object import compute_file_hash
from uvg.store.store import Store


class TestVerificationReport:
    def test_passed_empty(self) -> None:
        report = VerificationReport()
        assert report.passed

    def test_passed_with_pass(self) -> None:
        report = VerificationReport()
        report.add_pass("test", "ok")
        assert report.passed

    def test_passed_with_fail(self) -> None:
        report = VerificationReport()
        report.add_fail("test", "bad")
        assert not report.passed

    def test_has_warnings(self) -> None:
        report = VerificationReport()
        report.add_warn("test", "warning")
        assert report.has_warnings

    def test_failure_count(self) -> None:
        report = VerificationReport()
        report.add_fail("test1", "bad")
        report.add_fail("test2", "bad")
        report.add_pass("test3", "ok")
        assert report.failure_count == 2

    def test_warning_count(self) -> None:
        report = VerificationReport()
        report.add_warn("test1", "warn")
        report.add_warn("test2", "warn")
        assert report.warning_count == 2


class TestSecurityVerifier:
    def test_verify_store_empty(self, tmp_path: Path) -> None:
        store = Store(store_path=tmp_path / "store")
        verifier = SecurityVerifier(store=store)
        report = verifier.verify_store()
        assert report.passed

    def test_verify_store_with_object(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        verifier = SecurityVerifier(store=tmp_store)
        report = verifier.verify_store()
        assert report.passed

    def test_verify_runtime_missing(self, tmp_path: Path) -> None:
        verifier = SecurityVerifier()
        report = verifier.verify_runtime(tmp_path / "nonexistent")
        assert not report.passed
        assert report.failure_count > 0

    def test_verify_runtime_valid(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        verifier = SecurityVerifier(store=tmp_store)
        report = verifier.verify_runtime(runtime_dir)
        assert report.passed

    def test_verify_lockfile_missing(self, tmp_path: Path) -> None:
        verifier = SecurityVerifier()
        report = verifier.verify_lockfile(tmp_path / "nonexistent.lock")
        assert not report.passed

    def test_verify_lockfile_valid(self, tmp_path: Path) -> None:
        manifest = RuntimeManifest(
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
        )

        lockfile_path = tmp_path / "uvg.lock"
        manifest.save(lockfile_path)

        verifier = SecurityVerifier()
        report = verifier.verify_lockfile(lockfile_path)
        assert report.passed

    def test_verify_all(self, tmp_path: Path, tmp_store: Store, sample_wheel: Path) -> None:
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

        manifest = builder.load_manifest()
        manifest.save(tmp_path / "uvg.lock")

        verifier = SecurityVerifier(store=tmp_store)
        report = verifier.verify_all(
            runtime_dir=runtime_dir,
            lockfile_path=tmp_path / "uvg.lock",
        )

        assert report.passed
