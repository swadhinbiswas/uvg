"""Package downloader using UV for parallel downloads.

UVG delegates all downloading to UV, which provides:
- Parallel downloads (multiple connections)
- Automatic retries
- Resume interrupted downloads
- Hash verification
- Cache reuse

UVG then finds packages in UV's cache for runtime creation.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from uvg.uv.cache import UVCache


class UVDownloader:
    """Downloads packages using UV's parallel download system."""

    def __init__(self) -> None:
        """Initialize downloader."""
        self.uv_cache = UVCache()

    def download(
        self,
        requirement: str,
        python_version: str,
    ) -> list[tuple[str, str]]:
        """Download packages using UV.

        Args:
            requirement: Package requirement (e.g., "requests==2.31.0", "numpy>=1.24").
            python_version: Target Python version (e.g., "3.12").

        Returns:
            List of (name, version) tuples that were downloaded.

        Raises:
            RuntimeError: If download fails.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Build uv pip install --target command
            cmd = [
                "uv",
                "pip",
                "install",
                requirement,
                "--target",
                str(tmp_path),
                "--python-version",
                python_version,
                "--quiet",
            ]

            # Run UV install (parallel, fast)
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300,
                check=False,
            )

            if result.returncode != 0:
                error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                # Provide more helpful error messages
                if "was not found in the package registry" in error_msg:
                    # Extract package name from requirement
                    package_name = requirement
                    for sep in ["==", ">=", "<=", "~=", "!="]:
                        package_name = package_name.split(sep)[0]
                    raise RuntimeError(
                        f"Package '{package_name}' not found in PyPI.\n"
                        f"  Suggestions:\n"
                        f"    - Check the package name spelling\n"
                        f"    - Verify the package exists on https://pypi.org\n"
                        f"    - Try searching: uv pip search {package_name}"
                    ) from None
                elif "No solution found when resolving dependencies" in error_msg:
                    raise RuntimeError(
                        f"Could not resolve dependencies for '{requirement}'.\n"
                        f"  Suggestions:\n"
                        f"    - Try a different version specifier\n"
                        f"    - Check for conflicting dependencies\n"
                        f"    - Run with --verbose for more details"
                    ) from None
                else:
                    raise RuntimeError(f"UV download failed: {error_msg}") from None

            # Find installed packages
            packages = self._find_installed_packages(tmp_path)
            if not packages:
                raise RuntimeError("No packages installed")

            return packages

    def download_multiple(
        self,
        requirements: list[str],
        python_version: str,
    ) -> list[tuple[str, str]]:
        """Download multiple packages using UV.

        Args:
            requirements: List of package requirements.
            python_version: Target Python version.

        Returns:
            List of (name, version) tuples that were downloaded.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Build uv pip install --target command with multiple packages
            cmd = [
                "uv",
                "pip",
                "install",
                *requirements,
                "--target",
                str(tmp_path),
                "--python-version",
                python_version,
                "--quiet",
            ]

            # Run UV install (parallel, fast)
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=600,
                check=False,
            )

            if result.returncode != 0:
                error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                # Provide more helpful error messages
                if "was not found in the package registry" in error_msg:
                    # Extract package name from first requirement
                    package_name = requirements[0] if requirements else "unknown"
                    for sep in ["==", ">=", "<=", "~=", "!="]:
                        package_name = package_name.split(sep)[0]
                    raise RuntimeError(
                        f"Package '{package_name}' not found in PyPI.\n"
                        f"  Suggestions:\n"
                        f"    - Check the package name spelling\n"
                        f"    - Verify the package exists on https://pypi.org\n"
                        f"    - Try searching: uv pip search {package_name}"
                    ) from None
                elif "No solution found when resolving dependencies" in error_msg:
                    raise RuntimeError(
                        f"Could not resolve dependencies for {requirements}.\n"
                        f"  Suggestions:\n"
                        f"    - Try different version specifiers\n"
                        f"    - Check for conflicting dependencies\n"
                        f"    - Run with --verbose for more details"
                    ) from None
                else:
                    raise RuntimeError(f"UV download failed: {error_msg}") from None

            # Find installed packages
            packages = self._find_installed_packages(tmp_path)
            if not packages:
                raise RuntimeError("No packages installed")

            return packages

    def _parse_wheel_name(self, wheel_filename: str) -> tuple[str, str]:
        """Parse package name and version from wheel filename.

        Args:
            wheel_filename: Wheel filename (e.g., "requests-2.31.0-py3-none-any.whl").

        Returns:
            Tuple of (name, version).
        """
        # Remove .whl extension
        base = wheel_filename[:-4]
        parts = base.split("-")

        # Wheel format: {name}-{version}(-{build})?-{python}-{abi}-{platform}.whl
        # Name and version are always first two parts
        name = parts[0]
        version = parts[1]

        return name, version

    def _find_installed_packages(self, target_dir: Path) -> list[tuple[str, str]]:
        """Find installed packages in target directory.

        Args:
            target_dir: Directory where packages were installed.

        Returns:
            List of (name, version) tuples.
        """
        packages = []

        # Look for .dist-info directories which contain package metadata
        for dist_info in target_dir.glob("*.dist-info"):
            metadata_file = dist_info / "METADATA"
            if metadata_file.exists():
                name, version = self._parse_metadata(metadata_file)
                if name and version:
                    packages.append((name, version))

        return packages

    def _parse_metadata(self, metadata_file: Path) -> tuple[str | None, str | None]:
        """Parse package name and version from METADATA file.

        Args:
            metadata_file: Path to METADATA file.

        Returns:
            Tuple of (name, version) or (None, None) if parsing fails.
        """
        name = None
        version = None

        try:
            with open(metadata_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Name:"):
                        name = line.split(":", 1)[1].strip()
                    elif line.startswith("Version:"):
                        version = line.split(":", 1)[1].strip()
                    elif name and version:
                        # Stop after finding both
                        break
        except Exception:
            return None, None

        return name, version
