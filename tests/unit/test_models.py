"""Tests for core models."""

from __future__ import annotations

import pytest

from gvx.core.models import PackageIdentity, Version, WheelInfo


class TestVersion:
    def test_parse_simple(self) -> None:
        v = Version.parse("2.3.0")
        assert v.major == 2
        assert v.minor == 3
        assert v.patch == 0
        assert v.prerelease == ""

    def test_parse_two_parts(self) -> None:
        v = Version.parse("1.0")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0

    def test_parse_prerelease(self) -> None:
        v = Version.parse("1.0.0-alpha.1")
        assert v.major == 1
        assert v.minor == 0
        assert v.patch == 0
        assert v.prerelease == "alpha.1"

    def test_str(self) -> None:
        v = Version(major=2, minor=3, patch=0)
        assert str(v) == "2.3.0"

    def test_str_prerelease(self) -> None:
        v = Version(major=1, minor=0, patch=0, prerelease="beta.1")
        assert str(v) == "1.0.0-beta.1"

    def test_invalid_version(self) -> None:
        with pytest.raises(ValueError):
            Version.parse("invalid")

    def test_invalid_version_parts(self) -> None:
        with pytest.raises(ValueError):
            Version.parse("1")


class TestWheelInfo:
    def test_parse_simple(self) -> None:
        info = WheelInfo.parse("numpy-2.3.0-cp312-cp312-manylinux_2_17_x86_64.whl")
        assert info.distribution == "numpy"
        assert info.version.major == 2
        assert info.version.minor == 3
        assert info.version.patch == 0
        assert info.python_tag == "cp312"
        assert info.abi_tag == "cp312"
        assert info.platform_tag == "manylinux_2_17_x86_64"

    def test_parse_pure_python(self) -> None:
        info = WheelInfo.parse("requests-2.31.0-py3-none-any.whl")
        assert info.distribution == "requests"
        assert info.python_tag == "py3"
        assert info.abi_tag == "none"
        assert info.platform_tag == "any"

    def test_not_wheel(self) -> None:
        with pytest.raises(ValueError):
            WheelInfo.parse("not-a-wheel.tar.gz")

    def test_invalid_parts(self) -> None:
        with pytest.raises(ValueError):
            WheelInfo.parse("invalid.whl")


class TestPackageIdentity:
    def test_object_name(self) -> None:
        identity = PackageIdentity(
            name="numpy",
            version=Version.parse("2.3.0"),
            python_version="3.12",
            abi_tag="cp312",
            platform_tag="manylinux_2_17_x86_64",
            architecture="x86_64",
            wheel_hash="sha256:a4f8d2e1b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0",
        )
        assert identity.object_name.startswith("a4f8d2e1b3c4d5e6")
        assert "cp312" in identity.object_name
        assert "manylinux_2_17_x86_64" in identity.object_name
        assert "x86_64" in identity.object_name

    def test_str(self) -> None:
        identity = PackageIdentity(
            name="numpy",
            version=Version.parse("2.3.0"),
            python_version="3.12",
            abi_tag="cp312",
            platform_tag="linux",
            architecture="x86_64",
            wheel_hash="sha256:abc123",
        )
        assert "numpy" in str(identity)
        assert "2.3.0" in str(identity)
        assert "3.12" in str(identity)

    def test_frozen(self) -> None:
        identity = PackageIdentity(
            name="numpy",
            version=Version.parse("2.3.0"),
            python_version="3.12",
            abi_tag="cp312",
            platform_tag="linux",
            architecture="x86_64",
            wheel_hash="sha256:abc123",
        )
        with pytest.raises(AttributeError):
            identity.name = "pandas"
