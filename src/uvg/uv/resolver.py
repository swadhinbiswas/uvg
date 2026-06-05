"""UV resolver integration.

Delegates dependency resolution to UV via subprocess calls.
Supports overrides, constraints, resolution strategy, and other UV features.
"""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from uvg.uv.config import (
    ConflictEntry,
    ConstraintDependency,
    DependencyMetadata,
    ForkStrategy,
    OverrideDependency,
    PreReleaseMode,
    ResolutionStrategy,
)


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
        overrides: list[OverrideDependency] | None = None,
        constraints: list[ConstraintDependency] | None = None,
        resolution: ResolutionStrategy = ResolutionStrategy.HIGHEST,
        prerelease: PreReleaseMode = PreReleaseMode.IF_NEEDED,
        exclude_newer: str | None = None,
        fork_strategy: ForkStrategy = ForkStrategy.REQUIRES_PYTHON,
        environments: list[str] | None = None,
        required_environments: list[str] | None = None,
        dependency_metadata: list[DependencyMetadata] | None = None,
        conflicts: list[list[ConflictEntry]] | None = None,
        groups: list[str] | None = None,
        all_groups: bool = False,
        no_build_isolation: list[str] | None = None,
    ) -> ResolutionResult:
        """Resolve dependencies using UV.

        Args:
            packages: Optional list of packages to resolve.
            python_version: Optional Python version constraint.
            overrides: Optional list of dependency overrides.
            constraints: Optional list of dependency constraints.
            resolution: Resolution strategy.
            prerelease: Pre-release handling mode.
            exclude_newer: Exclude packages newer than this date.
            fork_strategy: Fork strategy for multi-version resolution.
            environments: Platform environments to resolve for.
            required_environments: Required platform environments.
            dependency_metadata: Static metadata for dependencies.
            conflicts: Conflict declarations.
            groups: Dependency groups to include.
            all_groups: Include all dependency groups.
            no_build_isolation: Packages to build without isolation.

        Returns:
            ResolutionResult with resolved packages.
        """
        result = ResolutionResult()

        try:
            cmd = ["uv", "lock", "--no-install", "--quiet"]
            if python_version:
                cmd.extend(["--python-version", python_version])

            if resolution != ResolutionStrategy.HIGHEST:
                cmd.extend(["--resolution", resolution.value])

            if prerelease != PreReleaseMode.IF_NEEDED:
                cmd.extend(["--prerelease", prerelease.value])

            if exclude_newer:
                cmd.extend(["--exclude-newer", exclude_newer])

            if fork_strategy != ForkStrategy.REQUIRES_PYTHON:
                cmd.extend(["--fork-strategy", fork_strategy.value])

            if all_groups:
                cmd.append("--all-groups")
            elif groups:
                for group in groups:
                    cmd.extend(["--group", group])

            if environments:
                for env in environments:
                    cmd.extend(["--environment", env])

            if required_environments:
                for env in required_environments:
                    cmd.extend(["--required-environment", env])

            if no_build_isolation:
                for pkg in no_build_isolation:
                    cmd.extend(["--no-build-isolation-package", pkg])

            if overrides:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                    for override in overrides:
                        line = f"{override.name}{override.specifier}"
                        if override.marker:
                            line += f" ; {override.marker}"
                        f.write(line + "\n")
                    f.flush()
                    cmd.extend(["--override", f.name])

            if constraints:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                    for constraint in constraints:
                        line = f"{constraint.name}{constraint.specifier}"
                        if constraint.marker:
                            line += f" ; {constraint.marker}"
                        f.write(line + "\n")
                    f.flush()
                    cmd.extend(["--constraint", f.name])

            if dependency_metadata:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
                    f.write("[[tool.uv.dependency-metadata]]\n")
                    for meta in dependency_metadata:
                        meta_dict = meta.to_dict()
                        for key, val in meta_dict.items():
                            if isinstance(val, list):
                                f.write(f"{key} = {val}\n")
                            elif val is not None:
                                f.write(f'{key} = "{val}"\n')
                        f.write("\n")
                    f.flush()
                    cmd.extend(["--config-file", f.name])

            if conflicts:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
                    f.write("[tool.uv]\nconflicts = [\n")
                    for group_entries in conflicts:
                        f.write("  [\n")
                        for entry in group_entries:
                            parts: list[str] = []
                            if entry.package:
                                parts.append(f'package = "{entry.package}"')
                            if entry.extra:
                                parts.append(f'extra = "{entry.extra}"')
                            if entry.group:
                                parts.append(f'group = "{entry.group}"')
                            f.write(f"    {{ {', '.join(parts)} }},\n")
                        f.write("  ],\n")
                    f.write("]\n")
                    f.flush()
                    cmd.extend(["--config-file", f.name])

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
        group: str | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        """Add a package using UV.

        Args:
            package_spec: Package specification (e.g., "numpy>=2.0").
            dev: Whether to add as a dev dependency.
            group: Dependency group name.

        Returns:
            Subprocess result.
        """
        cmd = ["uv", "add"]
        if dev:
            cmd.append("--dev")
        if group:
            cmd.extend(["--group", group])
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
