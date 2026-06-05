"""Tests for UV downloader."""

from gvx.uv.downloader import UVDownloader


class TestUVDownloader:
    """Test UV downloader functionality."""

    def test_init(self) -> None:
        """Test downloader initialization."""
        downloader = UVDownloader()
        assert downloader.uv_cache is not None

    def test_parse_wheel_name_simple(self) -> None:
        """Test parsing simple wheel filename."""
        downloader = UVDownloader()
        name, version = downloader._parse_wheel_name("requests-2.31.0-py3-none-any.whl")
        assert name == "requests"
        assert version == "2.31.0"

    def test_parse_wheel_name_complex(self) -> None:
        """Test parsing complex wheel filename."""
        downloader = UVDownloader()
        name, version = downloader._parse_wheel_name("numpy-1.24.3-cp312-cp312-manylinux_2_17_x86_64.whl")
        assert name == "numpy"
        assert version == "1.24.3"

    def test_parse_wheel_name_with_underscore(self) -> None:
        """Test parsing wheel filename with underscore."""
        downloader = UVDownloader()
        name, version = downloader._parse_wheel_name("my_package-1.0.0-py3-none-any.whl")
        assert name == "my_package"
        assert version == "1.0.0"
