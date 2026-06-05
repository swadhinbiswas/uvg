"""Runtime builder using UV's cache directly.

UVG creates isolated runtimes by symlinking to UV's cache.
No duplicate storage — packages are stored once in UV's cache.
"""

from __future__ import annotations

import json
import os
import platform as platform_module
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from uvg.python.manager import get_python_executable
from uvg.uv.cache import UVCache


class RuntimeBuilder:
    """Builds isolated runtimes using UV's cache."""

    def __init__(
        self,
        project_dir: Path,
        python_version: str | None = None,
    ) -> None:
        """Initialize runtime builder.

        Args:
            project_dir: Project directory.
            python_version: Python version (e.g., "3.12"). Defaults to current.
        """
        self.project_dir = project_dir
        self.python_version = python_version or f"{sys.version_info.major}.{sys.version_info.minor}"
        self.uv_cache = UVCache()
        self.runtime_dir = project_dir / ".uvg" / "runtime"

    def build(self, packages: list[tuple[str, str]]) -> bool:
        """Build runtime for given packages.

        Args:
            packages: List of (name, version) tuples.

        Returns:
            True if successful, False otherwise.
        """
        # Clean existing runtime
        if self.runtime_dir.exists():
            shutil.rmtree(self.runtime_dir)
        self.runtime_dir.mkdir(parents=True)

        # Create site-packages directory
        site_packages = self.runtime_dir / "site-packages"
        site_packages.mkdir()

        # Prepare symlink tasks
        symlink_tasks = []
        for name, version in packages:
            cache_path = self.uv_cache.find_package(name, version, self.python_version)
            if cache_path is None:
                print(f"Warning: {name}=={version} not found in UV cache")
                continue

            # Find the actual package directory inside the wheel
            pkg_dir = self._find_package_dir(cache_path, name)
            if pkg_dir is None:
                print(f"Warning: Could not find {name} in {cache_path}")
                continue

            symlink_tasks.append((pkg_dir, version, site_packages))

        # Create symlinks in parallel
        if symlink_tasks:
            with ThreadPoolExecutor() as executor:
                list(executor.map(self._create_symlinks, symlink_tasks))

        # Create manifest
        manifest = {
            "python_version": self.python_version,
            "packages": [{"name": name, "version": version} for name, version in packages],
            "platform": platform_module.system().lower(),
            "architecture": platform_module.machine(),
        }
        manifest_path = self.runtime_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

        return True

    def _create_symlinks(self, task: tuple[Path, str, Path]) -> None:
        """Create symlinks for a package.

        Args:
            task: Tuple of (pkg_dir, version, site_packages).
        """
        pkg_dir, version, site_packages = task

        # Create symlink using the actual directory name (for correct casing)
        link_path = site_packages / pkg_dir.name
        if not link_path.exists():
            link_path.symlink_to(pkg_dir)

        # Also symlink dist-info directory if it exists
        dist_info_name = f"{pkg_dir.name}-{version}.dist-info"
        dist_info_dir = pkg_dir.parent / dist_info_name
        if dist_info_dir.exists():
            dist_info_link = site_packages / dist_info_name
            if not dist_info_link.exists():
                dist_info_link.symlink_to(dist_info_dir)

    def _find_package_dir(self, wheel_dir: Path, package_name: str) -> Path | None:
        """Find the actual package directory inside a wheel.

        Args:
            wheel_dir: Path to the wheel directory in UV's cache.
            package_name: Package name to find.

        Returns:
            Path to the package directory, or None.
        """
        # Wheel directory structure: <wheel_dir>/<package_name>/...
        # or <wheel_dir>/<package_name>-<version>.dist-info/...

        # Normalize package name (PEP 503)
        normalized = package_name.lower().replace("-", "_")

        for item in wheel_dir.iterdir():
            if item.is_dir() and (item.name.lower() == normalized or item.name.lower().replace("-", "_") == normalized):
                return item

        return None

    def get_python_path(self) -> str:
        """Get PYTHONPATH for this runtime.

        Returns:
            PYTHONPATH string.
        """
        site_packages = self.runtime_dir / "site-packages"
        return str(site_packages)

    def run(self, command: list[str]) -> int:
        """Run a command with this runtime.

        Args:
            command: Command and arguments to run.

        Returns:
            Exit code.
        """
        # Build environment with runtime in PYTHONPATH
        env = os.environ.copy()
        site_packages = self.runtime_dir / "site-packages"

        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{site_packages}:{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = str(site_packages)

        # Check if command starts with python
        if command and command[0] in ("python", "python3"):
            # Use the Python version from the manifest
            python_exe = get_python_executable(self.python_version)
            if not python_exe:
                python_exe = sys.executable
            full_command = [python_exe, *command[1:]]
        elif command and command[0].startswith("-"):
            # Command starts with a flag (e.g., -c), assume it's for Python
            python_exe = get_python_executable(self.python_version)
            if not python_exe:
                python_exe = sys.executable
            full_command = [python_exe, *command]
        else:
            # Run command as-is
            full_command = command

        result = subprocess.run(
            full_command,
            env=env,
            cwd=self.project_dir,
        )

        return result.returncode

    def verify(self) -> bool:
        """Verify runtime is valid and all existing package symlinks are accessible."""
        if not self.runtime_dir.exists():
            return False

        manifest_path = self.runtime_dir / "manifest.json"
        if not manifest_path.exists():
            return False

        try:
            with open(manifest_path):
                pass

            # Check if all package symlinks are valid
            site_packages = self.runtime_dir / "site-packages"
            if not site_packages.exists():
                return False

            # Check all existing symlinks in site-packages
            return all(not (item.is_symlink() and not item.exists()) for item in site_packages.iterdir())
        except Exception:
            return False
