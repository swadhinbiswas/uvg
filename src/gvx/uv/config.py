"""UV project configuration parsing.

Parses tool.uv sections from pyproject.toml including:
- tool.uv.workspace (members, exclude)
- tool.uv.sources (workspace, path, git, url)
- tool.uv.override-dependencies
- tool.uv.constraint-dependencies
- tool.uv.resolution
- tool.uv.prerelease
- tool.uv.exclude-newer
- tool.uv.dependency-metadata
- tool.uv.conflicts
- tool.uv.fork-strategy
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from gvx.auth.config import AuthConfig, AuthConfigParser


class SourceType(Enum):
    """Type of dependency source."""

    REGISTRY = "registry"
    WORKSPACE = "workspace"
    PATH = "path"
    GIT = "git"
    URL = "url"


@dataclass
class GitSource:
    """Git dependency source."""

    url: str
    tag: str | None = None
    branch: str | None = None
    rev: str | None = None
    subdirectory: str | None = None


@dataclass
class PathSource:
    """Path dependency source."""

    path: str
    editable: bool = False


@dataclass
class UrlSource:
    """URL dependency source."""

    url: str
    subdirectory: str | None = None


@dataclass
class DependencySource:
    """A dependency source definition."""

    type: SourceType = SourceType.REGISTRY
    workspace: bool = False
    path: PathSource | None = None
    git: GitSource | None = None
    url: UrlSource | None = None
    marker: str | None = None


@dataclass
class WorkspaceConfig:
    """UV workspace configuration from tool.uv.workspace."""

    members: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)


@dataclass
class OverrideDependency:
    """A dependency override."""

    name: str
    specifier: str
    marker: str | None = None


@dataclass
class ConstraintDependency:
    """A dependency constraint."""

    name: str
    specifier: str
    marker: str | None = None


@dataclass
class DependencyMetadata:
    """Static metadata for a dependency."""

    name: str
    version: str | None = None
    requires_dist: list[str] = field(default_factory=list)
    requires_python: str | None = None
    provides_extra: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for UV."""
        result: dict[str, Any] = {"name": self.name}
        if self.version:
            result["version"] = self.version
        if self.requires_dist:
            result["requires-dist"] = self.requires_dist
        if self.requires_python:
            result["requires-python"] = self.requires_python
        if self.provides_extra:
            result["provides-extra"] = self.provides_extra
        return result


@dataclass
class ConflictEntry:
    """A single conflict entry."""

    package: str | None = None
    extra: str | None = None
    group: str | None = None


class ResolutionStrategy(Enum):
    """Resolution strategy."""

    HIGHEST = "highest"
    LOWEST = "lowest"
    LOWEST_DIRECT = "lowest-direct"


class PreReleaseMode(Enum):
    """Pre-release handling mode."""

    DISALLOW = "disallow"
    ALLOW = "allow"
    IF_NEEDED = "if-needed"
    EXPLICIT = "explicit"


class ForkStrategy(Enum):
    """Fork strategy for multi-version resolution."""

    REQUIRES_PYTHON = "requires-python"
    FEWEST = "fewest"


@dataclass
class DependencyGroup:
    """A PEP 735 dependency group."""

    name: str
    dependencies: list[str] = field(default_factory=list)


@dataclass
class UVProjectConfig:
    """Complete UV project configuration from pyproject.toml."""

    workspace: WorkspaceConfig | None = None
    sources: dict[str, DependencySource] = field(default_factory=dict)
    override_dependencies: list[OverrideDependency] = field(default_factory=list)
    constraint_dependencies: list[ConstraintDependency] = field(default_factory=list)
    resolution: ResolutionStrategy = ResolutionStrategy.HIGHEST
    prerelease: PreReleaseMode = PreReleaseMode.IF_NEEDED
    exclude_newer: str | None = None
    exclude_newer_package: dict[str, str] = field(default_factory=dict)
    environments: list[str] = field(default_factory=list)
    required_environments: list[str] = field(default_factory=list)
    dependency_metadata: list[DependencyMetadata] = field(default_factory=list)
    conflicts: list[list[ConflictEntry]] = field(default_factory=list)
    fork_strategy: ForkStrategy = ForkStrategy.REQUIRES_PYTHON
    dependency_groups: dict[str, DependencyGroup] = field(default_factory=dict)
    no_build_isolation: list[str] = field(default_factory=list)
    no_build_isolation_package: list[str] = field(default_factory=list)
    auth_config: AuthConfig = field(default_factory=AuthConfig)

    @property
    def has_overrides(self) -> bool:
        """Check if there are override dependencies."""
        return len(self.override_dependencies) > 0

    @property
    def has_constraints(self) -> bool:
        """Check if there are constraint dependencies."""
        return len(self.constraint_dependencies) > 0

    @property
    def has_workspace(self) -> bool:
        """Check if this is a workspace root."""
        return self.workspace is not None

    @property
    def has_dependency_metadata(self) -> bool:
        """Check if there is static dependency metadata."""
        return len(self.dependency_metadata) > 0

    @property
    def has_conflicts(self) -> bool:
        """Check if there are conflict declarations."""
        return len(self.conflicts) > 0

    @property
    def has_dependency_groups(self) -> bool:
        """Check if there are PEP 735 dependency groups."""
        return len(self.dependency_groups) > 0

    @property
    def has_build_isolation_config(self) -> bool:
        """Check if there is build isolation configuration."""
        return len(self.no_build_isolation) > 0 or len(self.no_build_isolation_package) > 0


def parse_pyproject_toml(content: str) -> UVProjectConfig:
    """Parse UV configuration from pyproject.toml content.

    Args:
        content: pyproject.toml file content.

    Returns:
        UVProjectConfig instance.
    """
    config = UVProjectConfig()

    lines = content.splitlines()
    current_section: str | None = None
    current_subsection: str | None = None
    in_array = False
    array_key: str | None = None
    dep_meta_buffer: dict[str, Any] = {}
    dep_group_name: str | None = None
    dep_group_deps: list[str] = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if not line or line.startswith("#"):
            continue

        if in_array:
            if line.endswith("]"):
                in_array = False
                line = line.rstrip("]").strip()
                if line and array_key:
                    _parse_array_item(config, array_key, line)
                array_key = None
            elif array_key:
                _parse_array_item(config, array_key, line)
            continue

        if line.startswith("[["):
            if dep_meta_buffer:
                config.dependency_metadata.append(_build_dependency_metadata(dep_meta_buffer))
                dep_meta_buffer = {}
            current_section = line.split("]]")[0].strip("[")
            current_subsection = None
            continue

        if line.startswith("["):
            if dep_meta_buffer:
                config.dependency_metadata.append(_build_dependency_metadata(dep_meta_buffer))
                dep_meta_buffer = {}
            if dep_group_name and dep_group_deps:
                config.dependency_groups[dep_group_name] = DependencyGroup(
                    name=dep_group_name, dependencies=dep_group_deps
                )
                dep_group_name = None
                dep_group_deps = []
            current_section = line.strip("[]").strip()
            current_subsection = None
            continue

        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if current_section == "tool.uv.dependency-metadata":
                dep_meta_buffer[key] = _parse_toml_value(value)
                continue

            if current_section == "dependency-groups":
                deps = _parse_inline_array(value)
                config.dependency_groups[key] = DependencyGroup(name=key, dependencies=deps)
                continue

            if value.startswith("[") and not value.endswith("]"):
                in_array = True
                array_key = key
                value = value.lstrip("[").strip()
                if value:
                    _parse_array_item(config, key, value)
                continue

            _parse_config_value(config, current_section, current_subsection, key, value)

    if dep_meta_buffer:
        config.dependency_metadata.append(_build_dependency_metadata(dep_meta_buffer))
    if dep_group_name and dep_group_deps:
        config.dependency_groups[dep_group_name] = DependencyGroup(name=dep_group_name, dependencies=dep_group_deps)

    return config


def _parse_toml_value(value: str) -> Any:
    """Parse a TOML value."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return _parse_inline_array(value)
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    return value


def _build_dependency_metadata(data: dict[str, Any]) -> DependencyMetadata:
    """Build DependencyMetadata from parsed data."""
    requires_dist = data.get("requires-dist", data.get("requires_dist", []))
    if isinstance(requires_dist, str):
        requires_dist = [requires_dist]
    provides_extra = data.get("provides-extra", data.get("provides_extra", []))
    if isinstance(provides_extra, str):
        provides_extra = [provides_extra]

    return DependencyMetadata(
        name=str(data.get("name", "")),
        version=data.get("version"),
        requires_dist=requires_dist if isinstance(requires_dist, list) else [],
        requires_python=data.get("requires-python", data.get("requires_python")),
        provides_extra=provides_extra if isinstance(provides_extra, list) else [],
    )


def _parse_array_item(config: UVProjectConfig, key: str, value: str) -> None:
    """Parse a single array item."""
    value = value.strip().rstrip(",").strip()
    if not value:
        return

    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]

    if not value:
        return

    if key == "members" and config.workspace:
        config.workspace.members.append(value)
    elif key == "exclude" and config.workspace:
        config.workspace.exclude.append(value)
    elif key == "override-dependencies":
        _parse_dependency_spec(config.override_dependencies, value)
    elif key == "constraint-dependencies":
        _parse_dependency_spec(config.constraint_dependencies, value)
    elif key == "environments":
        config.environments.append(value)
    elif key == "required-environments":
        config.required_environments.append(value)


def _parse_dependency_spec(deps: list[Any], value: str) -> None:
    """Parse a dependency specification string."""
    match = re.match(r"^([a-zA-Z0-9_-]+)\s*(.*)$", value)
    if match:
        name = match.group(1).lower()
        specifier = match.group(2).strip().rstrip(";").strip()
        marker = None
        if ";" in value:
            marker = value.split(";", 1)[1].strip()
        deps.append(OverrideDependency(name=name, specifier=specifier, marker=marker))


def _parse_config_value(
    config: UVProjectConfig,
    section: str | None,
    subsection: str | None,
    key: str,
    value: str,
) -> None:
    """Parse a configuration value."""
    value = value.strip().strip('"').strip("'")

    if section == "tool.uv.workspace":
        if key == "members":
            if config.workspace is None:
                config.workspace = WorkspaceConfig()
            if value.startswith("["):
                config.workspace.members = _parse_inline_array(value)
        elif key == "exclude":
            if config.workspace is None:
                config.workspace = WorkspaceConfig()
            if value.startswith("["):
                config.workspace.exclude = _parse_inline_array(value)

    elif section == "tool.uv":
        if key == "resolution":
            with contextlib.suppress(ValueError):
                config.resolution = ResolutionStrategy(value)
        elif key == "prerelease":
            with contextlib.suppress(ValueError):
                config.prerelease = PreReleaseMode(value)
        elif key == "exclude-newer":
            config.exclude_newer = value
        elif key == "fork-strategy":
            with contextlib.suppress(ValueError):
                config.fork_strategy = ForkStrategy(value)
        elif key == "no-build-isolation":
            config.no_build_isolation = _parse_inline_array(value)
        elif key == "no-build-isolation-package":
            config.no_build_isolation_package = _parse_inline_array(value)


def _parse_inline_array(value: str) -> list[str]:
    """Parse an inline TOML array."""
    value = value.strip("[]").strip()
    if not value:
        return []
    items = []
    for item in value.split(","):
        item = item.strip().strip('"').strip("'")
        if item:
            items.append(item)
    return items


def _parse_conflicts_section(content: str) -> list[list[ConflictEntry]]:
    """Parse tool.uv.conflicts section from pyproject.toml.

    Args:
        content: pyproject.toml file content.

    Returns:
        List of conflict groups.
    """
    conflicts: list[list[ConflictEntry]] = []
    lines = content.splitlines()
    in_conflicts = False
    current_group: list[ConflictEntry] = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("[tool.uv") and not stripped.startswith("[["):
            in_conflicts = False
            if current_group:
                conflicts.append(current_group)
                current_group = []
            continue

        if stripped.startswith("conflicts") and "=" in stripped:
            in_conflicts = True
            value = stripped.split("=", 1)[1].strip()
            if value.startswith("["):
                _parse_conflicts_value(conflicts, value)
            continue

        if in_conflicts:
            if stripped.startswith("[["):
                if current_group:
                    conflicts.append(current_group)
                    current_group = []
                continue

            if "{" in stripped:
                entry = _parse_conflict_entry(stripped)
                if entry:
                    current_group.append(entry)

    if current_group:
        conflicts.append(current_group)

    return conflicts


def _parse_conflicts_value(conflicts: list[list[ConflictEntry]], value: str) -> None:
    """Parse conflicts array value."""
    value = value.strip()
    if not value.startswith("[["):
        return

    groups = value.split("],")
    current_group: list[ConflictEntry] = []

    for group_str in groups:
        group_str = group_str.strip().strip("[").strip()
        if not group_str:
            continue

        if group_str.startswith("[") and current_group:
            conflicts.append(current_group)
            current_group = []

        if "{" in group_str:
            entry = _parse_conflict_entry(group_str)
            if entry:
                current_group.append(entry)

    if current_group:
        conflicts.append(current_group)


def _parse_conflict_entry(line: str) -> ConflictEntry | None:
    """Parse a single conflict entry like { extra = "extra1" }."""
    line = line.strip()
    if "{" not in line:
        return None

    data = _parse_source_table(line)
    return ConflictEntry(
        package=data.get("package"),
        extra=data.get("extra"),
        group=data.get("group"),
    )


def parse_sources_section(content: str) -> dict[str, DependencySource]:
    """Parse tool.uv.sources section from pyproject.toml.

    Args:
        content: pyproject.toml file content.

    Returns:
        Dict mapping package name to DependencySource.
    """
    sources: dict[str, DependencySource] = {}
    lines = content.splitlines()
    in_sources = False
    current_package: str | None = None
    current_source: dict[str, Any] = {}

    for line in lines:
        stripped = line.strip()

        if stripped == "[tool.uv.sources]":
            in_sources = True
            continue

        if in_sources:
            if stripped.startswith("[") and not stripped.startswith("[["):
                if current_package and current_source:
                    sources[current_package] = _build_dependency_source(current_source)
                    current_package = None
                    current_source = {}
                if not stripped.startswith("[tool.uv"):
                    in_sources = False
                continue

            if "=" in stripped:
                key, value = stripped.split("=", 1)
                key = key.strip()
                value = value.strip()

                if not key.startswith("[") and "{" in value:
                    current_package = key
                    current_source = _parse_source_table(value)
                    sources[current_package] = _build_dependency_source(current_source)
                    current_package = None
                    current_source = {}
                elif current_package is None:
                    sources[key] = _build_dependency_source(_parse_source_table(value))

    if current_package and current_source:
        sources[current_package] = _build_dependency_source(current_source)

    return sources


def _parse_source_table(value: str) -> dict[str, Any]:
    """Parse a source table value like { workspace = true }."""
    result: dict[str, Any] = {}
    value = value.strip("{}").strip()
    if not value:
        return result

    for pair in value.split(","):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if v.lower() == "true":
                result[k] = True
            elif v.lower() == "false":
                result[k] = False
            else:
                result[k] = v

    return result


def _build_dependency_source(data: dict[str, Any]) -> DependencySource:
    """Build a DependencySource from parsed data."""
    source = DependencySource()

    if data.get("workspace"):
        source.type = SourceType.WORKSPACE
        source.workspace = True
    elif "path" in data:
        source.type = SourceType.PATH
        source.path = PathSource(
            path=str(data["path"]),
            editable=data.get("editable", False),
        )
    elif "git" in data:
        source.type = SourceType.GIT
        source.git = GitSource(
            url=str(data["git"]),
            tag=data.get("tag"),
            branch=data.get("branch"),
            rev=data.get("rev"),
            subdirectory=data.get("subdirectory"),
        )
    elif "url" in data:
        source.type = SourceType.URL
        source.url = UrlSource(
            url=str(data["url"]),
            subdirectory=data.get("subdirectory"),
        )
    else:
        source.type = SourceType.REGISTRY

    if "marker" in data:
        source.marker = str(data["marker"])

    return source


def load_project_config(pyproject_path: Path) -> UVProjectConfig:
    """Load UV project configuration from a pyproject.toml file.

    Args:
        pyproject_path: Path to pyproject.toml.

    Returns:
        UVProjectConfig instance.

    Raises:
        FileNotFoundError: If pyproject.toml does not exist.
    """
    if not pyproject_path.exists():
        raise FileNotFoundError(f"pyproject.toml not found: {pyproject_path}")

    content = pyproject_path.read_text(encoding="utf-8")
    config = parse_pyproject_toml(content)
    config.sources = parse_sources_section(content)
    config.conflicts = _parse_conflicts_section(content)
    config.auth_config = AuthConfigParser().parse(content)
    return config
