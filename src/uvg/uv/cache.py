"""UV cache integration.

UVG uses UV's cache directly — no duplicate storage.
UV downloads packages in parallel to ~/.cache/uv/, UVG just finds and symlinks to them.
"""

from __future__ import annotations

import platform as platform_module
from pathlib import Path


class UVCache:
    """Wrapper around UV's cache directory."""

    def __init__(self, cache_path: Path | None = None) -> None:
        """Initialize UV cache wrapper.

        Args:
            cache_path: Path to UV cache. Defaults to ~/.cache/uv.
        """
        if cache_path is None:
            cache_path = Path.home() / ".cache" / "uv"
        self.cache_path = cache_path
        self.wheels_path = cache_path / "wheels-v6" / "pypi"

    def find_package(
        self,
        name: str,
        version: str,
        python_version: str,
    ) -> Path | None:
        """Find a package in UV's cache.

        Args:
            name: Package name.
            version: Package version.
            python_version: Python version (e.g., "3.12").

        Returns:
            Path to the cached package, or None if not found.
        """
        # UV cache structure: wheels-v6/pypi/<name>/<version>-<python>-<abi>-<platform>
        # or <version>-<hash> for built wheels
        package_dir = self.wheels_path / name.lower()
        if not package_dir.exists():
            return None

        current_platform = self._get_platform_tag()
        normalized_name = name.lower().replace("-", "_")

        # Try to find exact match
        for wheel_dir in package_dir.iterdir():
            if not wheel_dir.is_dir():
                continue

            # Check if it matches version
            if not wheel_dir.name.startswith(f"{version}-"):
                continue

            # Check if it's a standard wheel (py3-...) or hash-based build
            # Hash-based builds have format: <version>-<hash>
            # Standard wheels have format: <version>-<python>-<abi>-<platform>
            parts = wheel_dir.name.split("-")

            # If it's a hash-based build (only 2 parts: version and hash)
            if len(parts) == 2:
                # Check if the directory contains the package (with normalized name)
                for item in wheel_dir.iterdir():
                    if item.is_dir() and item.name.lower().replace("-", "_") == normalized_name:
                        return wheel_dir
            # Standard wheel format
            elif len(parts) >= 3 and (current_platform in wheel_dir.name or "any" in wheel_dir.name):
                return wheel_dir

        return None

    def find_all_packages(
        self,
        python_version: str,
    ) -> list[tuple[str, str, Path]]:
        """Find all cached packages for a Python version.

        Args:
            python_version: Python version (e.g., "3.12").

        Returns:
            List of (name, version, path) tuples.
        """
        packages: list[tuple[str, str, Path]] = []
        python_tag = "py3"  # UV uses py3 for all Python 3.x
        current_platform = self._get_platform_tag()

        if not self.wheels_path.exists():
            return packages

        for package_dir in self.wheels_path.iterdir():
            if not package_dir.is_dir():
                continue

            name = package_dir.name

            for wheel_dir in package_dir.iterdir():
                if not wheel_dir.is_dir():
                    continue

                # Parse version from directory name
                parts = wheel_dir.name.split("-")
                if len(parts) < 2:
                    continue

                version = parts[0]

                # Check Python and platform compatibility
                if python_tag in wheel_dir.name and (current_platform in wheel_dir.name or "any" in wheel_dir.name):
                    packages.append((name, version, wheel_dir))

        return packages

    def _get_platform_tag(self) -> str:
        """Get platform tag for current system.

        Returns:
            Platform tag (e.g., "manylinux2014_x86_64", "macosx_11_0_arm64").
        """
        system = platform_module.system().lower()
        machine = platform_module.machine()

        if system == "linux":
            return f"manylinux2014_{machine}"
        elif system == "darwin":
            # macOS
            import platform as plat

            mac_ver = plat.mac_ver()[0]
            major, minor = mac_ver.split(".")[:2]
            return f"macosx_{major}_{minor}_{machine}"
        elif system == "windows":
            if machine == "AMD64":
                return "win_amd64"
            else:
                return f"win_{machine}"
        else:
            return f"{system}_{machine}"
