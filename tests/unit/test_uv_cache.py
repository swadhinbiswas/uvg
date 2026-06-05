"""Tests for UV cache integration."""

from pathlib import Path

from uvg.uv.cache import UVCache


class TestUVCache:
    """Test UV cache wrapper."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        cache = UVCache()
        assert cache.cache_path == Path.home() / ".cache" / "uv"
        assert cache.wheels_path == cache.cache_path / "wheels-v6" / "pypi"

    def test_init_custom_path(self, tmp_path: Path) -> None:
        """Test custom cache path."""
        cache = UVCache(tmp_path)
        assert cache.cache_path == tmp_path
        assert cache.wheels_path == tmp_path / "wheels-v6" / "pypi"

    def test_find_package_not_found(self, tmp_path: Path) -> None:
        """Test finding non-existent package."""
        cache = UVCache(tmp_path)
        result = cache.find_package("nonexistent", "1.0.0", "3.12")
        assert result is None

    def test_find_package_found(self, tmp_path: Path) -> None:
        """Test finding existing package."""
        # Create mock UV cache structure with correct format
        # UV uses py3 for Python 3.x, not py312
        package_dir = tmp_path / "wheels-v6" / "pypi" / "requests" / "2.31.0-py3-none-any"
        package_dir.mkdir(parents=True)

        cache = UVCache(tmp_path)
        result = cache.find_package("requests", "2.31.0", "3.12")
        assert result == package_dir

    def test_find_all_packages_empty(self, tmp_path: Path) -> None:
        """Test finding all packages when cache is empty."""
        cache = UVCache(tmp_path)
        packages = cache.find_all_packages("3.12")
        assert packages == []

    def test_find_all_packages(self, tmp_path: Path) -> None:
        """Test finding all packages."""
        # Create mock UV cache structure with correct format
        (tmp_path / "wheels-v6" / "pypi" / "requests" / "2.31.0-py3-none-any").mkdir(parents=True)
        (tmp_path / "wheels-v6" / "pypi" / "numpy" / "1.24.0-py3-none-any").mkdir(parents=True)

        cache = UVCache(tmp_path)
        packages = cache.find_all_packages("3.12")
        assert len(packages) == 2

        names = [p[0] for p in packages]
        assert "requests" in names
        assert "numpy" in names

    def test_get_platform_tag(self) -> None:
        """Test platform tag generation."""
        cache = UVCache()
        tag = cache._get_platform_tag()
        assert isinstance(tag, str)
        assert len(tag) > 0
