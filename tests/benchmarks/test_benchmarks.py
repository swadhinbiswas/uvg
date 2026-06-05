"""Benchmark tests for GVX performance."""

from __future__ import annotations

from pathlib import Path

import pytest

from gvx.runtime.builder import RuntimeBuilder
from gvx.uv.cache import UVCache


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    project_dir = tmp_path / "benchmark_project"
    project_dir.mkdir()
    return project_dir


@pytest.fixture
def uv_cache() -> UVCache:
    """Get UV cache instance."""
    return UVCache()


class TestRuntimeBuilderBenchmarks:
    """Benchmark tests for runtime builder."""

    def test_cache_lookup_performance(
        self,
        benchmark: pytest.Benchmark,
        uv_cache: UVCache,
    ) -> None:
        """Benchmark UV cache lookup performance."""

        def lookup_package() -> None:
            uv_cache.find_package("requests", "2.31.0", "3.12")

        benchmark(lookup_package)

    def test_runtime_builder_init_performance(
        self,
        benchmark: pytest.Benchmark,
        temp_project: Path,
    ) -> None:
        """Benchmark runtime builder initialization."""

        def init_builder() -> None:
            RuntimeBuilder(temp_project, "3.12")

        benchmark(init_builder)

    def test_empty_runtime_build_performance(
        self,
        benchmark: pytest.Benchmark,
        temp_project: Path,
    ) -> None:
        """Benchmark building an empty runtime."""
        builder = RuntimeBuilder(temp_project, "3.12")

        def build_empty_runtime() -> None:
            builder.build([])

        benchmark(build_empty_runtime)
