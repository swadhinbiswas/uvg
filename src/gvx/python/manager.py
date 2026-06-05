"""Python version detection and management."""

from __future__ import annotations

import shutil
import subprocess


def find_python_executables() -> list[str]:
    """Find all Python executables in PATH.

    Returns:
        List of Python executable names (e.g., ["python3.11", "python3.12"]).
    """
    python_versions = []

    for i in range(8, 20):
        for j in range(0, 20):
            name = f"python3.{i}" if i >= 8 else f"python3.{j}"
            if i < 10 and j == 0:
                name = f"python3.{i}"

            if shutil.which(name):
                python_versions.append(name)

    return sorted(set(python_versions))


def get_python_version(python_exe: str) -> str | None:
    """Get Python version from executable.

    Args:
        python_exe: Python executable name or path.

    Returns:
        Version string (e.g., "3.12") or None if not found.
    """
    try:
        result = subprocess.run(
            [python_exe, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version_line = result.stdout.strip()
            if "Python" in version_line:
                version = version_line.split()[-1]
                parts = version.split(".")
                if len(parts) >= 2:
                    return f"{parts[0]}.{parts[1]}"
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        pass
    return None


def find_available_python_versions() -> list[str]:
    """Find all available Python versions on the system.

    Returns:
        List of version strings (e.g., ["3.11", "3.12", "3.13"]).
    """
    versions = []
    python_exes = find_python_executables()

    for exe in python_exes:
        version = get_python_version(exe)
        if version and version not in versions:
            versions.append(version)

    return sorted(versions)


def get_python_executable(version: str) -> str | None:
    """Get Python executable for a specific version.

    Args:
        version: Python version (e.g., "3.12").

    Returns:
        Executable path or None if not found.
    """
    exe_name = f"python{version}"
    exe_path = shutil.which(exe_name)
    return exe_path
