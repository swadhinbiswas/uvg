"""Project scanner for dependency intelligence.

Scans projects for dependency issues and runtime health.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from uvg.intelligence.analyzer import DependencyReport, ImportAnalyzer
from uvg.runtime.manifest import RuntimeManifest


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
    """Result of scanning a project."""

    project_path: str = ""
    runtime_stats: RuntimeStats | None = None
    dependency_report: DependencyReport | None = None
    scan_errors: list[str] = field(default_factory=list)


class ProjectScanner:
    """Scans projects for dependency issues and runtime health."""

    def __init__(self) -> None:
        """Initialize project scanner."""
        pass

    def scan_project(
        self,
        project_path: Path,
        runtime_dir: Path | None = None,
    ) -> ScanResult:
        """Scan a project for dependency issues.

        Args:
            project_path: Path to the project.
            runtime_dir: Optional runtime directory.

        Returns:
            ScanResult with findings.
        """
        result = ScanResult(project_path=str(project_path))

        # Scan runtime if provided
        if runtime_dir and runtime_dir.exists():
            result.runtime_stats = self._scan_runtime(runtime_dir)

        # Analyze imports
        try:
            analyzer = ImportAnalyzer()
            manifest_packages = set()
            if result.runtime_stats and result.runtime_stats.package_count > 0 and runtime_dir:
                # Get packages from manifest
                manifest_path = runtime_dir / "manifest.json"
                if manifest_path.exists():
                    manifest = RuntimeManifest.load(manifest_path)
                    manifest_packages = set(manifest.packages.keys())

            result.dependency_report = analyzer.generate_report(project_path, manifest_packages)
        except Exception as e:
            result.scan_errors.append(f"Failed to analyze imports: {e}")

        return result

    def _scan_runtime(self, runtime_dir: Path) -> RuntimeStats:
        """Scan runtime directory for statistics.

        Args:
            runtime_dir: Path to runtime directory.

        Returns:
            RuntimeStats with findings.
        """
        stats = RuntimeStats(
            project_path=str(runtime_dir.parent.parent),
            is_valid=True,
        )

        # Load manifest
        manifest_path = runtime_dir / "manifest.json"
        if not manifest_path.exists():
            stats.is_valid = False
            stats.verification_errors.append("Manifest not found")
            return stats

        try:
            manifest = RuntimeManifest.load(manifest_path)
            stats.fingerprint = manifest.fingerprint
            stats.package_count = len(manifest.packages)
            stats.python_version = manifest.python_version
            stats.entry_point_count = len(manifest.entry_points)

            # Count native packages
            for pkg in manifest.packages.values():
                if pkg.is_native:
                    stats.native_package_count += 1

        except Exception as e:
            stats.is_valid = False
            stats.verification_errors.append(f"Failed to load manifest: {e}")

        return stats
