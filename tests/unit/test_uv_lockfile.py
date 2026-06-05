"""Tests for UV lockfile parsing."""

from pathlib import Path

import pytest

from gvx.uv.lockfile import (
    LockfilePackage,
    GVXLockfile,
    UVLockfileParser,
)


class TestLockfilePackage:
    def test_to_dict(self) -> None:
        pkg = LockfilePackage(
            name="requests",
            version="2.31.0",
            wheel="requests-2.31.0-py3-none-any.whl",
            wheel_url="https://files.pythonhosted.org/packages/requests-2.31.0-py3-none-any.whl",
            hash="sha256:abc123",
            abi="none",
            platform="any",
            dependencies=["certifi", "urllib3"],
        )

        result = pkg.to_dict()
        assert result["name"] == "requests"
        assert result["version"] == "2.31.0"
        assert result["wheel"] == "requests-2.31.0-py3-none-any.whl"
        assert result["wheel_url"] == "https://files.pythonhosted.org/packages/requests-2.31.0-py3-none-any.whl"
        assert result["hash"] == "sha256:abc123"
        assert result["abi"] == "none"
        assert result["platform"] == "any"
        assert result["dependencies"] == ["certifi", "urllib3"]

    def test_from_dict(self) -> None:
        data = {
            "name": "requests",
            "version": "2.31.0",
            "wheel": "requests-2.31.0-py3-none-any.whl",
            "wheel_url": "https://files.pythonhosted.org/packages/requests-2.31.0-py3-none-any.whl",
            "hash": "sha256:abc123",
            "abi": "none",
            "platform": "any",
            "dependencies": ["certifi"],
        }

        pkg = LockfilePackage.from_dict(data)
        assert pkg.name == "requests"
        assert pkg.version == "2.31.0"
        assert pkg.wheel_url == "https://files.pythonhosted.org/packages/requests-2.31.0-py3-none-any.whl"


class TestGVXLockfile:
    def test_to_dict(self) -> None:
        lockfile = GVXLockfile(
            python_version=">=3.10",
            platform="linux_x86_64",
            architecture="x86_64",
            packages=[
                LockfilePackage(name="requests", version="2.31.0"),
            ],
        )

        result = lockfile.to_dict()
        assert result["metadata"]["python_version"] == ">=3.10"
        assert result["metadata"]["platform"] == "linux_x86_64"
        assert len(result["packages"]) == 1
        assert result["packages"][0]["name"] == "requests"

    def test_from_dict(self) -> None:
        data = {
            "metadata": {
                "version": 1,
                "python_version": ">=3.10",
                "platform": "linux_x86_64",
                "architecture": "x86_64",
                "fingerprint": "runtime_abc123",
                "metadata_version": 1,
            },
            "packages": [
                {
                    "name": "requests",
                    "version": "2.31.0",
                    "wheel": "requests-2.31.0-py3-none-any.whl",
                    "wheel_url": "https://example.com/requests.whl",
                    "hash": "sha256:abc",
                    "abi": "none",
                    "platform": "any",
                    "dependencies": [],
                },
            ],
        }

        lockfile = GVXLockfile.from_dict(data)
        assert lockfile.python_version == ">=3.10"
        assert lockfile.fingerprint == "runtime_abc123"
        assert len(lockfile.packages) == 1
        assert lockfile.packages[0].name == "requests"

    def test_save_load(self, tmp_path: Path) -> None:
        lockfile = GVXLockfile(
            python_version=">=3.10",
            platform="linux_x86_64",
            architecture="x86_64",
            packages=[LockfilePackage(name="requests", version="2.31.0")],
        )

        path = tmp_path / "gvx.lock"
        lockfile.save(path)

        loaded = GVXLockfile.load(path)
        assert loaded.python_version == ">=3.10"
        assert len(loaded.packages) == 1
        assert loaded.packages[0].name == "requests"


class TestUVLockfileParser:
    def test_parse_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            UVLockfileParser.parse_uv_lock(tmp_path / "nonexistent.lock")

    def test_parse_basic(self, tmp_path: Path) -> None:
        lockfile_content = """version = 1
requires-python = ">=3.10"

[[package]]
name = "requests"
version = "2.31.0"
source = { registry = "https://pypi.org/simple" }
wheels = [
    { url = "https://files.pythonhosted.org/packages/requests-2.31.0-py3-none-any.whl",
      hash = "sha256:abc123", size = 1000 },
]

[[package]]
name = "certifi"
version = "2023.7.22"
source = { registry = "https://pypi.org/simple" }
wheels = [
    { url = "https://files.pythonhosted.org/packages/certifi-2023.7.22-py3-none-any.whl",
      hash = "sha256:def456", size = 500 },
]
"""
        lockfile_path = tmp_path / "uv.lock"
        lockfile_path.write_text(lockfile_content, encoding="utf-8")

        result = UVLockfileParser.parse_uv_lock(lockfile_path)
        assert len(result.packages) == 2
        assert result.packages[0].name == "requests"
        assert result.packages[0].hash == "sha256:abc123"
        assert result.packages[1].name == "certifi"
        assert result.packages[1].hash == "sha256:def456"

    def test_parse_with_dependencies(self, tmp_path: Path) -> None:
        lockfile_content = """version = 1
requires-python = ">=3.10"

[[package]]
name = "requests"
version = "2.31.0"
source = { registry = "https://pypi.org/simple" }
dependencies = ["certifi", "urllib3"]
wheels = [
    { url = "https://files.pythonhosted.org/packages/requests-2.31.0-py3-none-any.whl",
      hash = "sha256:abc123", size = 1000 },
]

[[package]]
name = "certifi"
version = "2023.7.22"
source = { registry = "https://pypi.org/simple" }
wheels = [
    { url = "https://files.pythonhosted.org/packages/certifi-2023.7.22-py3-none-any.whl",
      hash = "sha256:def456", size = 500 },
]
"""
        lockfile_path = tmp_path / "uv.lock"
        lockfile_path.write_text(lockfile_content, encoding="utf-8")

        result = UVLockfileParser.parse_uv_lock(lockfile_path)
        assert len(result.packages) == 2
        requests_pkg = next(p for p in result.packages if p.name == "requests")
        assert "certifi" in requests_pkg.dependencies
        assert "urllib3" in requests_pkg.dependencies
