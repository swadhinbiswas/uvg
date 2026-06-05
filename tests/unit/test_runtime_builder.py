"""Tests for runtime builder."""

from pathlib import Path

from gvx.runtime.builder import RuntimeBuilder


class TestRuntimeBuilder:
    """Test runtime builder functionality."""

    def test_build_empty(self, tmp_path: Path) -> None:
        """Test building runtime with no packages."""
        builder = RuntimeBuilder(tmp_path, "3.12")
        success = builder.build([])
        assert success

        # Check runtime directory exists
        assert builder.runtime_dir.exists()
        assert (builder.runtime_dir / "site-packages").exists()
        assert (builder.runtime_dir / "manifest.json").exists()

    def test_build_with_packages(self, tmp_path: Path) -> None:
        """Test building runtime with packages."""
        builder = RuntimeBuilder(tmp_path, "3.12")
        packages = [("requests", "2.31.0")]
        success = builder.build(packages)
        assert success

        # Check manifest
        manifest_path = builder.runtime_dir / "manifest.json"
        assert manifest_path.exists()

        import json

        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest["python_version"] == "3.12"
        assert len(manifest["packages"]) == 1
        assert manifest["packages"][0]["name"] == "requests"

    def test_get_python_path(self, tmp_path: Path) -> None:
        """Test getting PYTHONPATH."""
        builder = RuntimeBuilder(tmp_path, "3.12")
        builder.build([])

        python_path = builder.get_python_path()
        assert "site-packages" in python_path

    def test_run_command(self, tmp_path: Path) -> None:
        """Test running a command."""
        builder = RuntimeBuilder(tmp_path, "3.12")
        builder.build([])

        # Run a simple Python command
        exit_code = builder.run(["-c", "print('hello')"])
        assert exit_code == 0
