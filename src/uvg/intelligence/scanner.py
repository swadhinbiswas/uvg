"""Project scanner for dependency intelligence.

Scans projects for dependency issues, storage analytics,
and runtime health.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from uvg.intelligence.analyzer import DependencyReport, ImportAnalyzer
from uvg.runtime.manifest import RuntimeManifest
from uvg.store.store import Store


@dataclass
class StorageStats:
    """Storage statistics for the UVG store."""

    total_objects: int = 0
    total_size_bytes: int = 0
    native_packages: int = 0
    pure_python_packages: int = 0
    python_versions: list[str] = field(default_factory=list)
    unique_packages: int = 0

    @property
    def total_size_mb(self) -> float:
        """Total size in megabytes.

        Returns:
            Size in MB rounded to 2 decimal places.
        """
        return round(self.total_size_bytes / (1024 * 1024), 2)


@dataclass
class RuntimeStats:
    """Runtime statistics for a project."""

    project_path: str = ""
    fingerprint: str = ""
    package_count: int = 0
    native_package_count: int = 0
    entry_point_count: int = 0
    python_version: str = ""
    is_valid: bool = False
    verification_errors: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    """Result of a project scan."""

    dependency_report: DependencyReport | None = None
    runtime_stats: RuntimeStats | None = None
    storage_stats: StorageStats | None = None
    scan_errors: list[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues.

        Returns:
            True if any issues found.
        """
        if self.dependency_report and self.dependency_report.has_issues:
            return True
        if self.runtime_stats and self.runtime_stats.verification_errors:
            return True
        return bool(self.scan_errors)


class ProjectScanner:
    """Scans projects for dependency and runtime issues.

    Combines import analysis, manifest verification, and
    storage analytics into a single scanning interface.
    """

    def __init__(
        self,
        store: Store | None = None,
        analyzer: ImportAnalyzer | None = None,
    ) -> None:
        """Initialize project scanner.

        Args:
            store: UVG store instance.
            analyzer: Import analyzer instance.
        """
        self.store = store
        self.analyzer = analyzer or ImportAnalyzer()

    def scan_project(
        self,
        project_path: Path,
        runtime_dir: Path | None = None,
        exclude_patterns: list[str] | None = None,
    ) -> ScanResult:
        """Scan a project for dependency issues.

        Args:
            project_path: Path to the project root.
            runtime_dir: Path to the runtime directory.
            exclude_patterns: Glob patterns to exclude.

        Returns:
            ScanResult with analysis results.
        """
        result = ScanResult()

        if runtime_dir is None:
            runtime_dir = project_path / ".uvg" / "runtime"

        manifest_path = runtime_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = RuntimeManifest.load(manifest_path)
                result.runtime_stats = self._compute_runtime_stats(manifest, runtime_dir)

                manifest_packages = set(manifest.packages.keys())
                result.dependency_report = self.analyzer.generate_report(
                    directory=project_path,
                    manifest_packages=manifest_packages,
                    exclude_patterns=exclude_patterns,
                )
            except Exception as e:
                result.scan_errors.append(f"Failed to load manifest: {e}")
        else:
            result.scan_errors.append("No runtime manifest found. Run 'uvg sync' first.")

        return result

    def _compute_runtime_stats(
        self,
        manifest: RuntimeManifest,
        runtime_dir: Path,
    ) -> RuntimeStats:
        """Compute runtime statistics from a manifest.

        Args:
            manifest: Runtime manifest.
            runtime_dir: Runtime directory path.

        Returns:
            RuntimeStats instance.
        """
        native_count = sum(1 for pkg in manifest.packages.values() if pkg.is_native)

        verification_errors: list[str] = []
        for pkg in manifest.packages.values():
            if not pkg.editable:
                store_path = Path(pkg.store_path)
                if not store_path.exists():
                    verification_errors.append(f"Store object missing: {pkg.name}")

        return RuntimeStats(
            project_path=str(runtime_dir.parent.parent),
            fingerprint=manifest.fingerprint,
            package_count=len(manifest.packages),
            native_package_count=native_count,
            entry_point_count=len(manifest.entry_points),
            python_version=manifest.python_version,
            is_valid=len(verification_errors) == 0,
            verification_errors=verification_errors,
        )

    def get_storage_stats(self) -> StorageStats:
        """Get storage statistics from the store.

        Returns:
            StorageStats instance.
        """
        if self.store is None:
            return StorageStats()

        info = self.store.get_info()
        objects = self.store.list_objects(limit=10000)

        python_versions: set[str] = set()
        unique_packages: set[str] = set()
        native_count = 0
        pure_count = 0

        for obj in objects:
            python_versions.add(obj["python_version"])
            unique_packages.add(f"{obj['package_name']}=={obj['package_version']}")
            if obj["is_native"]:
                native_count += 1
            else:
                pure_count += 1

        return StorageStats(
            total_objects=info["object_count"],
            total_size_bytes=info["total_size_bytes"],
            native_packages=native_count,
            pure_python_packages=pure_count,
            python_versions=sorted(python_versions),
            unique_packages=len(unique_packages),
        )
