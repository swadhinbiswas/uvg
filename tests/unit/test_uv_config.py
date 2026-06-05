"""Tests for UV project configuration parsing."""

from pathlib import Path

import pytest

from gvx.uv.config import (
    ConflictEntry,
    ConstraintDependency,
    DependencyGroup,
    DependencyMetadata,
    DependencySource,
    ForkStrategy,
    GitSource,
    OverrideDependency,
    PathSource,
    PreReleaseMode,
    ResolutionStrategy,
    SourceType,
    UrlSource,
    UVProjectConfig,
    WorkspaceConfig,
    load_project_config,
    parse_pyproject_toml,
    parse_sources_section,
)


class TestParsePyprojectToml:
    """Test parse_pyproject_toml function."""

    def test_empty_config(self) -> None:
        config = parse_pyproject_toml("")
        assert config.workspace is None
        assert not config.sources
        assert not config.override_dependencies
        assert not config.constraint_dependencies
        assert config.resolution == ResolutionStrategy.HIGHEST

    def test_workspace_config(self) -> None:
        content = """
[tool.uv.workspace]
members = ["packages/*", "libs/*"]
exclude = ["packages/seeds"]
"""
        config = parse_pyproject_toml(content)
        assert config.workspace is not None
        assert config.workspace.members == ["packages/*", "libs/*"]
        assert config.workspace.exclude == ["packages/seeds"]

    def test_resolution_strategy(self) -> None:
        content = """
[tool.uv]
resolution = "lowest"
"""
        config = parse_pyproject_toml(content)
        assert config.resolution == ResolutionStrategy.LOWEST

    def test_resolution_lowest_direct(self) -> None:
        content = """
[tool.uv]
resolution = "lowest-direct"
"""
        config = parse_pyproject_toml(content)
        assert config.resolution == ResolutionStrategy.LOWEST_DIRECT

    def test_prerelease_mode(self) -> None:
        content = """
[tool.uv]
prerelease = "allow"
"""
        config = parse_pyproject_toml(content)
        assert config.prerelease == PreReleaseMode.ALLOW

    def test_exclude_newer(self) -> None:
        content = """
[tool.uv]
exclude-newer = "2024-01-01"
"""
        config = parse_pyproject_toml(content)
        assert config.exclude_newer == "2024-01-01"

    def test_override_dependencies(self) -> None:
        content = """
[tool.uv]
override-dependencies = [
    "pydantic>=2.0",
    "numpy>=1.24",
]
"""
        config = parse_pyproject_toml(content)
        assert len(config.override_dependencies) == 2
        assert config.override_dependencies[0].name == "pydantic"
        assert config.override_dependencies[0].specifier == ">=2.0"
        assert config.override_dependencies[1].name == "numpy"
        assert config.override_dependencies[1].specifier == ">=1.24"

    def test_constraint_dependencies(self) -> None:
        content = """
[tool.uv]
constraint-dependencies = [
    "urllib3<2.0",
    "requests>=2.28",
]
"""
        config = parse_pyproject_toml(content)
        assert len(config.constraint_dependencies) == 2
        assert config.constraint_dependencies[0].name == "urllib3"
        assert config.constraint_dependencies[0].specifier == "<2.0"

    def test_environments(self) -> None:
        content = """
[tool.uv]
environments = [
    "sys_platform == 'darwin'",
    "sys_platform == 'linux'",
]
"""
        config = parse_pyproject_toml(content)
        assert len(config.environments) == 2
        assert "sys_platform == 'darwin'" in config.environments

    def test_required_environments(self) -> None:
        content = """
[tool.uv]
required-environments = [
    "sys_platform == 'darwin' and platform_machine == 'x86_64'",
]
"""
        config = parse_pyproject_toml(content)
        assert len(config.required_environments) == 1

    def test_has_overrides_property(self) -> None:
        config = UVProjectConfig()
        assert not config.has_overrides
        config.override_dependencies = [OverrideDependency(name="foo", specifier=">=1.0")]
        assert config.has_overrides

    def test_has_constraints_property(self) -> None:
        config = UVProjectConfig()
        assert not config.has_constraints
        config.constraint_dependencies = [ConstraintDependency(name="foo", specifier=">=1.0")]
        assert config.has_constraints

    def test_has_workspace_property(self) -> None:
        config = UVProjectConfig()
        assert not config.has_workspace
        config.workspace = WorkspaceConfig(members=["packages/*"])
        assert config.has_workspace


class TestParseSourcesSection:
    """Test parse_sources_section function."""

    def test_workspace_source(self) -> None:
        content = """
[tool.uv.sources]
bird-feeder = { workspace = true }
"""
        sources = parse_sources_section(content)
        assert "bird-feeder" in sources
        assert sources["bird-feeder"].type == SourceType.WORKSPACE
        assert sources["bird-feeder"].workspace is True

    def test_path_source(self) -> None:
        content = """
[tool.uv.sources]
my-lib = { path = "../my-lib" }
"""
        sources = parse_sources_section(content)
        assert "my-lib" in sources
        assert sources["my-lib"].type == SourceType.PATH
        assert sources["my-lib"].path is not None
        assert sources["my-lib"].path.path == "../my-lib"

    def test_path_source_editable(self) -> None:
        content = """
[tool.uv.sources]
my-lib = { path = "../my-lib", editable = true }
"""
        sources = parse_sources_section(content)
        assert sources["my-lib"].path is not None
        assert sources["my-lib"].path.editable is True

    def test_git_source(self) -> None:
        content = """
[tool.uv.sources]
my-lib = { git = "https://github.com/user/repo", tag = "v1.0.0" }
"""
        sources = parse_sources_section(content)
        assert "my-lib" in sources
        assert sources["my-lib"].type == SourceType.GIT
        assert sources["my-lib"].git is not None
        assert sources["my-lib"].git.url == "https://github.com/user/repo"
        assert sources["my-lib"].git.tag == "v1.0.0"

    def test_git_source_with_branch(self) -> None:
        content = """
[tool.uv.sources]
my-lib = { git = "https://github.com/user/repo", branch = "main" }
"""
        sources = parse_sources_section(content)
        assert sources["my-lib"].git is not None
        assert sources["my-lib"].git.branch == "main"

    def test_url_source(self) -> None:
        content = """
[tool.uv.sources]
my-lib = { url = "https://example.com/my-lib.whl" }
"""
        sources = parse_sources_section(content)
        assert "my-lib" in sources
        assert sources["my-lib"].type == SourceType.URL
        assert sources["my-lib"].url is not None
        assert sources["my-lib"].url.url == "https://example.com/my-lib.whl"

    def test_registry_source(self) -> None:
        content = """
[tool.uv.sources]
requests = {}
"""
        sources = parse_sources_section(content)
        assert "requests" in sources
        assert sources["requests"].type == SourceType.REGISTRY

    def test_multiple_sources(self) -> None:
        content = """
[tool.uv.sources]
bird-feeder = { workspace = true }
tqdm = { git = "https://github.com/tqdm/tqdm" }
requests = {}
"""
        sources = parse_sources_section(content)
        assert len(sources) == 3
        assert sources["bird-feeder"].type == SourceType.WORKSPACE
        assert sources["tqdm"].type == SourceType.GIT
        assert sources["requests"].type == SourceType.REGISTRY


class TestDependencySource:
    """Test DependencySource class."""

    def test_default(self) -> None:
        source = DependencySource()
        assert source.type == SourceType.REGISTRY
        assert not source.workspace
        assert source.path is None
        assert source.git is None
        assert source.url is None

    def test_workspace_source(self) -> None:
        source = DependencySource(type=SourceType.WORKSPACE, workspace=True)
        assert source.type == SourceType.WORKSPACE
        assert source.workspace is True


class TestGitSource:
    """Test GitSource class."""

    def test_basic(self) -> None:
        git = GitSource(url="https://github.com/user/repo")
        assert git.url == "https://github.com/user/repo"
        assert git.tag is None
        assert git.branch is None
        assert git.rev is None

    def test_with_tag(self) -> None:
        git = GitSource(url="https://github.com/user/repo", tag="v1.0.0")
        assert git.tag == "v1.0.0"


class TestPathSource:
    """Test PathSource class."""

    def test_basic(self) -> None:
        path = PathSource(path="../my-lib")
        assert path.path == "../my-lib"
        assert not path.editable

    def test_editable(self) -> None:
        path = PathSource(path="../my-lib", editable=True)
        assert path.editable is True


class TestUrlSource:
    """Test UrlSource class."""

    def test_basic(self) -> None:
        url = UrlSource(url="https://example.com/pkg.whl")
        assert url.url == "https://example.com/pkg.whl"
        assert url.subdirectory is None


class TestLoadProjectConfig:
    """Test load_project_config function."""

    def test_load_from_file(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"

[tool.uv.workspace]
members = ["packages/*"]

[tool.uv]
resolution = "lowest"
override-dependencies = [
    "pydantic>=2.0",
]
""")

        config = load_project_config(pyproject)
        assert config.workspace is not None
        assert config.workspace.members == ["packages/*"]
        assert config.resolution == ResolutionStrategy.LOWEST
        assert len(config.override_dependencies) == 1
        assert config.override_dependencies[0].name == "pydantic"

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_project_config(tmp_path / "nonexistent" / "pyproject.toml")


class TestOverrideDependency:
    """Test OverrideDependency class."""

    def test_basic(self) -> None:
        override = OverrideDependency(name="pydantic", specifier=">=2.0")
        assert override.name == "pydantic"
        assert override.specifier == ">=2.0"
        assert override.marker is None

    def test_with_marker(self) -> None:
        override = OverrideDependency(name="pydantic", specifier=">=2.0", marker="sys_platform == 'linux'")
        assert override.marker == "sys_platform == 'linux'"


class TestConstraintDependency:
    """Test ConstraintDependency class."""

    def test_basic(self) -> None:
        constraint = ConstraintDependency(name="urllib3", specifier="<2.0")
        assert constraint.name == "urllib3"
        assert constraint.specifier == "<2.0"


class TestResolutionStrategy:
    """Test ResolutionStrategy enum."""

    def test_values(self) -> None:
        assert ResolutionStrategy.HIGHEST.value == "highest"
        assert ResolutionStrategy.LOWEST.value == "lowest"
        assert ResolutionStrategy.LOWEST_DIRECT.value == "lowest-direct"


class TestPreReleaseMode:
    """Test PreReleaseMode enum."""

    def test_values(self) -> None:
        assert PreReleaseMode.DISALLOW.value == "disallow"
        assert PreReleaseMode.ALLOW.value == "allow"
        assert PreReleaseMode.IF_NEEDED.value == "if-needed"
        assert PreReleaseMode.EXPLICIT.value == "explicit"


class TestForkStrategy:
    """Test ForkStrategy enum."""

    def test_values(self) -> None:
        assert ForkStrategy.REQUIRES_PYTHON.value == "requires-python"
        assert ForkStrategy.FEWEST.value == "fewest"

    def test_default(self) -> None:
        config = UVProjectConfig()
        assert config.fork_strategy == ForkStrategy.REQUIRES_PYTHON


class TestDependencyMetadata:
    """Test DependencyMetadata class."""

    def test_basic(self) -> None:
        meta = DependencyMetadata(name="chumpy", version="0.70")
        assert meta.name == "chumpy"
        assert meta.version == "0.70"
        assert meta.requires_dist == []
        assert meta.requires_python is None
        assert meta.provides_extra == []

    def test_with_dependencies(self) -> None:
        meta = DependencyMetadata(
            name="flash-attn",
            version="2.6.3",
            requires_dist=["torch", "einops"],
            requires_python=">=3.8",
            provides_extra=["dev"],
        )
        assert meta.name == "flash-attn"
        assert meta.requires_dist == ["torch", "einops"]
        assert meta.requires_python == ">=3.8"
        assert meta.provides_extra == ["dev"]

    def test_to_dict(self) -> None:
        meta = DependencyMetadata(
            name="chumpy",
            version="0.70",
            requires_dist=["numpy>=1.8.1", "scipy>=0.13.0"],
        )
        result = meta.to_dict()
        assert result["name"] == "chumpy"
        assert result["version"] == "0.70"
        assert result["requires-dist"] == ["numpy>=1.8.1", "scipy>=0.13.0"]

    def test_to_dict_minimal(self) -> None:
        meta = DependencyMetadata(name="chumpy")
        result = meta.to_dict()
        assert result == {"name": "chumpy"}

    def test_has_dependency_metadata(self) -> None:
        config = UVProjectConfig()
        assert not config.has_dependency_metadata
        config.dependency_metadata = [DependencyMetadata(name="chumpy")]
        assert config.has_dependency_metadata


class TestConflictEntry:
    """Test ConflictEntry class."""

    def test_extra_conflict(self) -> None:
        entry = ConflictEntry(extra="extra1")
        assert entry.extra == "extra1"
        assert entry.package is None
        assert entry.group is None

    def test_group_conflict(self) -> None:
        entry = ConflictEntry(group="group1")
        assert entry.group == "group1"

    def test_package_conflict(self) -> None:
        entry = ConflictEntry(package="member1", extra="extra1")
        assert entry.package == "member1"
        assert entry.extra == "extra1"


class TestConflictsParsing:
    """Test conflicts parsing."""

    def test_has_conflicts(self) -> None:
        config = UVProjectConfig()
        assert not config.has_conflicts
        config.conflicts = [[ConflictEntry(extra="extra1"), ConflictEntry(extra="extra2")]]
        assert config.has_conflicts


class TestLoadProjectConfigPhase2:
    """Test Phase 2 features in load_project_config."""

    def test_fork_strategy(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"

[tool.uv]
fork-strategy = "fewest"
""")
        config = load_project_config(pyproject)
        assert config.fork_strategy == ForkStrategy.FEWEST

    def test_dependency_metadata(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"

[[tool.uv.dependency-metadata]]
name = "chumpy"
version = "0.70"
requires-dist = ["numpy>=1.8.1", "scipy>=0.13.0"]
""")
        config = load_project_config(pyproject)
        assert len(config.dependency_metadata) == 1
        assert config.dependency_metadata[0].name == "chumpy"
        assert config.dependency_metadata[0].version == "0.70"


class TestDependencyGroups:
    """Test PEP 735 dependency groups."""

    def test_parse_dependency_groups(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"

[dependency-groups]
test = ["pytest>=8.0", "pytest-cov>=5.0"]
lint = ["ruff>=0.4", "mypy>=1.8"]
dev = ["pytest>=8.0", "ruff>=0.4"]
""")
        config = load_project_config(pyproject)
        assert config.has_dependency_groups
        assert "test" in config.dependency_groups
        assert "lint" in config.dependency_groups
        assert "dev" in config.dependency_groups
        assert config.dependency_groups["test"].dependencies == ["pytest>=8.0", "pytest-cov>=5.0"]
        assert config.dependency_groups["lint"].dependencies == ["ruff>=0.4", "mypy>=1.8"]

    def test_dependency_group_dataclass(self) -> None:
        group = DependencyGroup(name="test", dependencies=["pytest", "coverage"])
        assert group.name == "test"
        assert group.dependencies == ["pytest", "coverage"]

    def test_no_dependency_groups(self) -> None:
        config = UVProjectConfig()
        assert not config.has_dependency_groups


class TestBuildIsolation:
    """Test build isolation configuration."""

    def test_parse_no_build_isolation(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"

[tool.uv]
no-build-isolation = ["flash-attn", "triton"]
""")
        config = load_project_config(pyproject)
        assert config.has_build_isolation_config
        assert config.no_build_isolation == ["flash-attn", "triton"]

    def test_parse_no_build_isolation_package(self, tmp_path: Path) -> None:
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
name = "test-project"
version = "0.1.0"

[tool.uv]
no-build-isolation-package = ["flash-attn"]
""")
        config = load_project_config(pyproject)
        assert config.has_build_isolation_config
        assert config.no_build_isolation_package == ["flash-attn"]

    def test_no_build_isolation_config(self) -> None:
        config = UVProjectConfig()
        assert not config.has_build_isolation_config
        config.no_build_isolation = ["pkg"]
        assert config.has_build_isolation_config
