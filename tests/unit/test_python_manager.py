"""Tests for Python version management."""

from __future__ import annotations

from pathlib import Path

from gvx.python.manager import (
    find_available_python_versions,
    find_python_executables,
    get_python_executable,
    get_python_version,
)


class TestPythonManager:
    """Test Python version management."""

    def test_find_python_executables(self) -> None:
        """Test finding Python executables."""
        executables = find_python_executables()
        assert isinstance(executables, list)
        # Should find at least one Python executable
        assert len(executables) > 0
        # All should start with "python"
        assert all(exe.startswith("python") for exe in executables)

    def test_get_python_version(self) -> None:
        """Test getting Python version from executable."""
        # Test with python3 (should exist on most systems)
        version = get_python_version("python3")
        if version:
            assert isinstance(version, str)
            assert "." in version
            parts = version.split(".")
            assert len(parts) >= 2
            assert parts[0] == "3"

    def test_find_available_python_versions(self) -> None:
        """Test finding available Python versions."""
        versions = find_available_python_versions()
        assert isinstance(versions, list)
        # Should find at least one version
        assert len(versions) > 0
        # All should be valid version strings
        for version in versions:
            assert isinstance(version, str)
            assert "." in version
            parts = version.split(".")
            assert len(parts) >= 2

    def test_get_python_executable(self) -> None:
        """Test getting Python executable for a version."""
        versions = find_available_python_versions()
        if versions:
            # Test with a version that exists
            version = versions[0]
            exe = get_python_executable(version)
            assert exe is not None
            assert Path(exe).exists()

        # Test with a version that doesn't exist
        exe = get_python_executable("99.99")
        assert exe is None
