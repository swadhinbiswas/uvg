"""Tests for tool execution and PEP 723 script parsing."""

from pathlib import Path

import pytest

from gvx.tools.executor import ToolCache, ToolSpec
from gvx.tools.script import ScriptMetadata, ScriptParser, parse_script


class TestToolSpec:
    """Test ToolSpec class."""

    def test_basic(self) -> None:
        tool = ToolSpec(name="ruff")
        assert tool.name == "ruff"
        assert tool.version is None
        assert tool.extras == []

    def test_with_version(self) -> None:
        tool = ToolSpec(name="ruff", version="0.4.0")
        assert tool.name == "ruff"
        assert tool.version == "0.4.0"

    def test_with_extras(self) -> None:
        tool = ToolSpec(name="pytest", extras=["cov", "xdist"])
        assert tool.name == "pytest"
        assert tool.extras == ["cov", "xdist"]

    def test_to_requirement_basic(self) -> None:
        tool = ToolSpec(name="ruff")
        assert tool.to_requirement() == "ruff"

    def test_to_requirement_version(self) -> None:
        tool = ToolSpec(name="ruff", version="0.4.0")
        assert tool.to_requirement() == "ruff==0.4.0"

    def test_to_requirement_extras(self) -> None:
        tool = ToolSpec(name="pytest", extras=["cov"])
        assert tool.to_requirement() == "pytest[cov]"

    def test_cache_key(self) -> None:
        tool1 = ToolSpec(name="ruff")
        tool2 = ToolSpec(name="ruff")
        assert tool1.cache_key() == tool2.cache_key()

        tool3 = ToolSpec(name="black")
        assert tool1.cache_key() != tool3.cache_key()


class TestToolCache:
    """Test ToolCache class."""

    def test_init(self, tmp_path: Path) -> None:
        cache = ToolCache(cache_dir=tmp_path)
        assert cache.cache_dir == tmp_path
        assert cache._index == {}

    def test_register_and_get(self, tmp_path: Path) -> None:
        cache = ToolCache(cache_dir=tmp_path)
        tools = [ToolSpec(name="ruff")]
        env_path = tmp_path / "env1"
        env_path.mkdir()

        cache.register_environment(tools, env_path, "3.12.0")
        result = cache.get_environment(tools)
        assert result == env_path

    def test_get_nonexistent(self, tmp_path: Path) -> None:
        cache = ToolCache(cache_dir=tmp_path)
        tools = [ToolSpec(name="ruff")]
        assert cache.get_environment(tools) is None

    def test_cache_key_computation(self, tmp_path: Path) -> None:
        cache = ToolCache(cache_dir=tmp_path)
        tools1 = [ToolSpec(name="ruff"), ToolSpec(name="black")]
        tools2 = [ToolSpec(name="black"), ToolSpec(name="ruff")]

        key1 = cache._compute_cache_key(tools1)
        key2 = cache._compute_cache_key(tools2)
        assert key1 == key2

    def test_clear(self, tmp_path: Path) -> None:
        cache = ToolCache(cache_dir=tmp_path)
        tools = [ToolSpec(name="ruff")]
        env_path = tmp_path / "env1"
        env_path.mkdir()

        cache.register_environment(tools, env_path, "3.12.0")
        cache.clear()
        assert cache.get_environment(tools) is None
        assert not env_path.exists()


class TestScriptMetadata:
    """Test ScriptMetadata class."""

    def test_basic(self) -> None:
        meta = ScriptMetadata()
        assert not meta.has_dependencies
        assert meta.dependencies == []
        assert meta.requires_python is None

    def test_with_dependencies(self) -> None:
        meta = ScriptMetadata(dependencies=["requests>=2.0", "click"])
        assert meta.has_dependencies
        assert len(meta.dependencies) == 2

    def test_to_dict(self) -> None:
        meta = ScriptMetadata(
            dependencies=["requests"],
            requires_python=">=3.10",
            description="A test script",
        )
        result = meta.to_dict()
        assert result["dependencies"] == ["requests"]
        assert result["requires-python"] == ">=3.10"
        assert result["description"] == "A test script"


class TestScriptParser:
    """Test ScriptParser class."""

    def test_parse_no_metadata(self, tmp_path: Path) -> None:
        script = tmp_path / "script.py"
        script.write_text("print('hello')")

        parser = ScriptParser()
        meta = parser.parse(script)
        assert not meta.has_dependencies

    def test_parse_with_dependencies(self, tmp_path: Path) -> None:
        script = tmp_path / "script.py"
        script.write_text("""# /// script
# dependencies = ["requests>=2.0", "click"]
# requires-python = ">=3.10"
# ///

import requests
print(requests.get("https://example.com"))
""")

        parser = ScriptParser()
        meta = parser.parse(script)
        assert meta.has_dependencies
        assert meta.dependencies == ["requests>=2.0", "click"]
        assert meta.requires_python == ">=3.10"

    def test_parse_multiline_dependencies(self, tmp_path: Path) -> None:
        script = tmp_path / "script.py"
        script.write_text("""# /// script
# dependencies = [
#     "requests>=2.0",
#     "click>=8.0",
#     "rich>=13.0",
# ]
# ///

import requests
""")

        parser = ScriptParser()
        meta = parser.parse(script)
        assert meta.has_dependencies
        assert len(meta.dependencies) == 3
        assert "requests>=2.0" in meta.dependencies
        assert "click>=8.0" in meta.dependencies
        assert "rich>=13.0" in meta.dependencies

    def test_parse_no_metadata_block(self, tmp_path: Path) -> None:
        script = tmp_path / "script.py"
        script.write_text("""# This is a comment
# /// script
# This is not metadata
print("hello")
""")

        parser = ScriptParser()
        meta = parser.parse(script)
        assert not meta.has_dependencies

    def test_parse_content(self) -> None:
        content = """# /// script
# dependencies = ["requests"]
# ///
print("hello")
"""
        parser = ScriptParser()
        meta = parser.parse_content(content)
        assert meta.dependencies == ["requests"]

    def test_file_not_found(self, tmp_path: Path) -> None:
        parser = ScriptParser()
        with pytest.raises(FileNotFoundError):
            parser.parse(tmp_path / "nonexistent.py")


class TestParseScript:
    """Test parse_script function."""

    def test_parse_script(self, tmp_path: Path) -> None:
        script = tmp_path / "script.py"
        script.write_text("""# /// script
# dependencies = ["requests", "click"]
# requires-python = ">=3.10"
# description = "A test script"
# ///

import requests
""")

        meta = parse_script(script)
        assert meta.has_dependencies
        assert meta.dependencies == ["requests", "click"]
        assert meta.requires_python == ">=3.10"
        assert meta.description == "A test script"
