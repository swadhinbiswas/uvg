"""Shared test fixtures for UVG tests."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def sample_wheel(tmp_path: Path) -> Path:
    """Create a sample wheel file for testing."""
    wheel_path = tmp_path / "test_pkg-1.0.0-py3-none-any.whl"

    wheel_content = {
        "test_pkg/__init__.py": '"""Test package."""\n__version__ = "1.0.0"\n',
        "test_pkg-1.0.0.dist-info/METADATA": "Metadata-Version: 2.1\nName: test-pkg\nVersion: 1.0.0\n",
        "test_pkg-1.0.0.dist-info/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
        ),
        "test_pkg-1.0.0.dist-info/RECORD": "",
    }

    with zipfile.ZipFile(wheel_path, "w") as zf:
        for name, content in wheel_content.items():
            zf.writestr(name, content)

    return wheel_path


@pytest.fixture
def native_wheel(tmp_path: Path) -> Path:
    """Create a sample native wheel file for testing."""
    wheel_path = tmp_path / "native_pkg-1.0.0-cp312-cp312-manylinux_2_17_x86_64.whl"

    wheel_content = {
        "native_pkg/__init__.py": '"""Native package."""\n',
        "native_pkg/_native.so": b"\x00" * 100,
        "native_pkg-1.0.0.dist-info/METADATA": ("Metadata-Version: 2.1\nName: native-pkg\nVersion: 1.0.0\n"),
        "native_pkg-1.0.0.dist-info/WHEEL": (
            "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: false\nTag: cp312-cp312-manylinux_2_17_x86_64\n"
        ),
        "native_pkg-1.0.0.dist-info/RECORD": "",
    }

    with zipfile.ZipFile(wheel_path, "w") as zf:
        for name, content in wheel_content.items():
            zf.writestr(name, content)

    return wheel_path
