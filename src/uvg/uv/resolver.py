"""UV resolver integration.

Delegates dependency resolution to UV via subprocess calls.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ResolvedPackage:
    """A resolved package from UV."""

    name: str
    version: str
    wheel_url: str = ""
    wheel_hash: str = ""
    dependencies: list[str] = field(default_factory=list)
    is_direct: bool = False


@dataclass
class ResolutionResult:
    """Result of a dependency resolution."""

    packages: list[ResolvedPackage] = field(default_factory=list)
    python_version: str = ""
    platform: str = ""
    architecture: str = ""
    resolver_version: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if resolution succeeded.

        Returns:
            True if no errors.
        """
        return len(self.errors) == 0


class UVResolver:
    """Resolves dependencies using UV.

    Delegates to UV's SAT-based resolver for dependency
    resolution and lock file generation.
    """

    def __init__(self, project_dir: Path | None = None) -> None:
        """Initialize UV resolver.

        Args:
            project_dir: Project directory containing pyproject.toml.
        """
        self.project_dir = project_dir or Path.cwd()

    def resolve(
        self,
        packages: list[str] | None = None,
        python_version: str | None = None,
    ) -> ResolutionResult:
        """Resolve dependencies using UV.

        Args:
            packages: Optional list of packages to resolve.
            python_version: Optional Python version constraint.

        Returns:
            ResolutionResult with resolved packages.
        """
        result = ResolutionResult()

        try:
            cmd = ["uv", "lock", "--no-install", "--quiet"]
            if python_version:
                cmd.extend(["--python-version", python_version])

            subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                timeout=60,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            result.errors.append(f"UV resolution failed: {e.stderr.decode()}")
            return result
        except FileNotFoundError:
            result.errors.append("UV not found. Install UV: https://docs.astral.sh/uv/")
            return result

        return result

    def add_package(
        self,
        package_spec: str,
        dev: bool = False,
    ) -> subprocess.CompletedProcess[bytes]:
        """Add a package using UV.

        Args:
            package_spec: Package specification (e.g., "numpy>=2.0").
            dev: Whether to add as a dev dependency.

        Returns:
            Subprocess result.
        """
        cmd = ["uv", "add"]
        if dev:
            cmd.append("--dev")
        cmd.append(package_spec)

        return subprocess.run(
            cmd,
            cwd=self.project_dir,
            capture_output=True,
            timeout=120,
        )

    def remove_package(self, package_name: str) -> subprocess.CompletedProcess[bytes]:
        """Remove a package using UV.

        Args:
            package_name: Package name to remove.

        Returns:
            Subprocess result.
        """
        return subprocess.run(
            ["uv", "remove", package_name],
            cwd=self.project_dir,
            capture_output=True,
            timeout=60,
        )

    def sync(self) -> subprocess.CompletedProcess[bytes]:
        """Sync dependencies using UV.

        Returns:
            Subprocess result.
        """
        return subprocess.run(
            ["uv", "sync", "--no-install"],
            cwd=self.project_dir,
            capture_output=True,
            timeout=120,
        )
