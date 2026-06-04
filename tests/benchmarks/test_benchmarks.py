"""Benchmark tests for UVG core operations.

Measures performance of critical paths to ensure
performance targets are met.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from uvg.core.models import PackageIdentity, WheelInfo
from uvg.runtime.builder import RuntimeBuilder
from uvg.runtime.fingerprint import FingerprintInput, compute_fingerprint
from uvg.store.object import compute_file_hash
from uvg.store.store import Store


def _create_wheel(tmp_path: Path, name: str, version: str) -> Path:
    """Create a test wheel file.

    Args:
        tmp_path: Temporary directory.
        name: Package name.
        version: Package version.

    Returns:
        Path to the wheel file.
    """
    wheel_path = tmp_path / f"{name}-{version}-py3-none-any.whl"
    content = {
        f"{name}/__init__.py": f'"""{name}."""\n__version__ = "{version}"\n',
        f"{name}-{version}.dist-info/METADATA": f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n",
        f"{name}-{version}.dist-info/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        ),
        f"{name}-{version}.dist-info/RECORD": "",
    }
    with zipfile.ZipFile(wheel_path, "w") as zf:
        for fname, fcontent in content.items():
            zf.writestr(fname, fcontent)
    return wheel_path


class TestStoreBenchmarks:
    def test_object_creation(self, benchmark, tmp_path: Path) -> None:
        """Benchmark store object creation."""
        wheel = _create_wheel(tmp_path, "benchpkg", "1.0.0")
        store = Store(store_path=tmp_path / "store")

        def _create() -> None:
            wheel_hash = compute_file_hash(wheel)
            wheel_info = WheelInfo.parse(wheel.name)
            identity = PackageIdentity(
                name=wheel_info.distribution,
                version=wheel_info.version,
                python_version="3.12",
                abi_tag=wheel_info.abi_tag,
                platform_tag=wheel_info.platform_tag,
                architecture="x86_64",
                wheel_hash=f"sha256:{wheel_hash}",
            )
            store.create_object(wheel, f"sha256:{wheel_hash}", identity)

        benchmark(_create)

    def test_object_lookup(self, benchmark, tmp_path: Path) -> None:
        """Benchmark store object lookup."""
        wheel = _create_wheel(tmp_path, "benchpkg", "1.0.0")
        store = Store(store_path=tmp_path / "store")
        wheel_hash = compute_file_hash(wheel)
        wheel_info = WheelInfo.parse(wheel.name)
        identity = PackageIdentity(
            name=wheel_info.distribution,
            version=wheel_info.version,
            python_version="3.12",
            abi_tag=wheel_info.abi_tag,
            platform_tag=wheel_info.platform_tag,
            architecture="x86_64",
            wheel_hash=f"sha256:{wheel_hash}",
        )
        store.create_object(wheel, f"sha256:{wheel_hash}", identity)

        def _lookup() -> None:
            store.get_object(f"sha256:{wheel_hash}")

        benchmark(_lookup)


class TestFingerprintBenchmarks:
    def test_fingerprint_computation(self, benchmark) -> None:
        """Benchmark fingerprint computation."""
        packages = {f"pkg{i}": (f"{i}.0.0", f"sha256:{'a' * 64}") for i in range(100)}
        fp_input = FingerprintInput.create(
            python_version="3.12",
            platform="linux",
            architecture="x86_64",
            abi="cp312",
            manifest_version=1,
            packages=packages,
        )

        benchmark(compute_fingerprint, fp_input)


class TestRuntimeBenchmarks:
    def test_runtime_construction(self, benchmark, tmp_path: Path) -> None:
        """Benchmark runtime construction with 10 packages."""
        store = Store(store_path=tmp_path / "store")
        wheels = []
        package_info = {}

        for i in range(10):
            wheel = _create_wheel(tmp_path, f"pkg{i}", f"{i}.0.0")
            wheels.append(wheel)
            wheel_hash = compute_file_hash(wheel)
            wheel_info = WheelInfo.parse(wheel.name)
            identity = PackageIdentity(
                name=wheel_info.distribution,
                version=wheel_info.version,
                python_version="3.12",
                abi_tag=wheel_info.abi_tag,
                platform_tag=wheel_info.platform_tag,
                architecture="x86_64",
                wheel_hash=f"sha256:{wheel_hash}",
            )
            store.create_object(wheel, f"sha256:{wheel_hash}", identity)
            package_info[f"pkg{i}"] = {
                "version": f"{i}.0.0",
                "wheel_hash": f"sha256:{wheel_hash}",
                "abi": wheel_info.abi_tag,
                "platform": wheel_info.platform_tag,
                "dependencies": [],
                "is_native": False,
            }

        runtime_dir = tmp_path / "runtime"
        builder = RuntimeBuilder(
            runtime_dir=runtime_dir,
            store_path=store.store_path,
        )

        def _build() -> None:
            builder.build(
                packages=package_info,
                python_version="3.12",
                platform="linux",
                architecture="x86_64",
                abi="py3",
            )

        benchmark(_build)
