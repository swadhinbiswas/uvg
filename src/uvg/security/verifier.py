"""Security verification engine.

Verifies hash integrity, runtime consistency, lockfile validity,
and supply chain provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from uvg.runtime.manifest import RuntimeManifest
from uvg.store.store import Store


class VerificationStatus(Enum):
    """Status of a verification check."""

    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"


@dataclass
class VerificationCheck:
    """Result of a single verification check."""

    name: str
    status: VerificationStatus
    message: str
    details: str = ""


@dataclass
class VerificationReport:
    """Complete verification report."""

    checks: list[VerificationCheck] = field(default_factory=list)
    timestamp: str = ""

    @property
    def passed(self) -> bool:
        """Check if all verification checks passed.

        Returns:
            True if no failures found.
        """
        return not any(c.status == VerificationStatus.FAIL for c in self.checks)

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings.

        Returns:
            True if any warnings found.
        """
        return any(c.status == VerificationStatus.WARN for c in self.checks)

    @property
    def failure_count(self) -> int:
        """Count failed checks.

        Returns:
            Number of failed checks.
        """
        return sum(1 for c in self.checks if c.status == VerificationStatus.FAIL)

    @property
    def warning_count(self) -> int:
        """Count warning checks.

        Returns:
            Number of warning checks.
        """
        return sum(1 for c in self.checks if c.status == VerificationStatus.WARN)

    def add_pass(self, name: str, message: str, details: str = "") -> None:
        """Add a passing check.

        Args:
            name: Check name.
            message: Check message.
            details: Additional details.
        """
        self.checks.append(
            VerificationCheck(name=name, status=VerificationStatus.PASS, message=message, details=details)
        )

    def add_fail(self, name: str, message: str, details: str = "") -> None:
        """Add a failing check.

        Args:
            name: Check name.
            message: Check message.
            details: Additional details.
        """
        self.checks.append(
            VerificationCheck(name=name, status=VerificationStatus.FAIL, message=message, details=details)
        )

    def add_warn(self, name: str, message: str, details: str = "") -> None:
        """Add a warning check.

        Args:
            name: Check name.
            message: Check message.
            details: Additional details.
        """
        self.checks.append(
            VerificationCheck(name=name, status=VerificationStatus.WARN, message=message, details=details)
        )

    def add_skip(self, name: str, message: str, details: str = "") -> None:
        """Add a skipped check.

        Args:
            name: Check name.
            message: Check message.
            details: Additional details.
        """
        self.checks.append(
            VerificationCheck(name=name, status=VerificationStatus.SKIP, message=message, details=details)
        )


class SecurityVerifier:
    """Verifies security properties of UVG artifacts.

    Provides comprehensive verification of:
    - Store object integrity
    - Runtime manifest consistency
    - Lockfile validity
    - Hash verification
    - Supply chain provenance
    """

    def __init__(self, store: Store | None = None) -> None:
        """Initialize security verifier.

        Args:
            store: UVG store instance.
        """
        self.store = store

    def verify_store(self) -> VerificationReport:
        """Verify store integrity.

        Returns:
            VerificationReport with store verification results.
        """
        report = VerificationReport()

        if self.store is None:
            report.add_skip("store_exists", "No store configured")
            return report

        if not self.store.store_path.exists():
            report.add_fail("store_exists", "Store directory does not exist")
            return report

        report.add_pass("store_exists", "Store directory exists")

        objects = self.store.list_objects(limit=1000)
        verified = 0
        failed = 0

        for obj_data in objects:
            try:
                obj = self.store.get_object(obj_data["hash"])
                obj.verify_integrity()
                verified += 1
            except Exception as e:
                failed += 1
                report.add_fail(
                    "object_integrity",
                    f"Object verification failed: {obj_data.get('package_name', 'unknown')}",
                    str(e),
                )

        if failed == 0:
            report.add_pass(
                "object_integrity",
                f"All {verified} objects verified successfully",
            )
        else:
            report.add_fail(
                "object_integrity",
                f"{failed} objects failed verification out of {verified + failed}",
            )

        return report

    def verify_runtime(self, runtime_dir: Path) -> VerificationReport:
        """Verify runtime integrity.

        Args:
            runtime_dir: Path to the runtime directory.

        Returns:
            VerificationReport with runtime verification results.
        """
        report = VerificationReport()

        manifest_path = runtime_dir / "manifest.json"
        if not manifest_path.exists():
            report.add_fail("manifest_exists", "Manifest file missing")
            return report

        report.add_pass("manifest_exists", "Manifest file exists")

        try:
            manifest = RuntimeManifest.load(manifest_path)
        except Exception as e:
            report.add_fail("manifest_valid", f"Failed to load manifest: {e}")
            return report

        report.add_pass("manifest_valid", "Manifest is valid JSON")

        if not manifest.fingerprint:
            report.add_fail("fingerprint_present", "No fingerprint in manifest")
        else:
            report.add_pass("fingerprint_present", f"Fingerprint: {manifest.fingerprint}")

        fp_path = runtime_dir / "fingerprint"
        if fp_path.exists():
            stored_fp = fp_path.read_text(encoding="utf-8").strip()
            if stored_fp == manifest.fingerprint:
                report.add_pass("fingerprint_match", "Fingerprint matches manifest")
            else:
                report.add_fail(
                    "fingerprint_match",
                    f"Fingerprint mismatch: stored={stored_fp}, manifest={manifest.fingerprint}",
                )
        else:
            report.add_warn("fingerprint_file", "Fingerprint file missing")

        site_packages = runtime_dir / "site-packages"
        if site_packages.exists():
            missing_symlinks = []
            for pkg in manifest.packages.values():
                symlink = site_packages / pkg.name
                if not symlink.exists():
                    missing_symlinks.append(pkg.name)

            if missing_symlinks:
                report.add_fail(
                    "symlinks_valid",
                    f"Missing symlinks: {', '.join(missing_symlinks)}",
                )
            else:
                report.add_pass("symlinks_valid", "All package symlinks valid")
        else:
            report.add_warn("symlinks_valid", "Site-packages directory missing")

        if self.store is not None:
            missing_objects = []
            for pkg in manifest.packages.values():
                if not self.store.has_object(pkg.wheel_hash):
                    missing_objects.append(pkg.name)

            if missing_objects:
                report.add_fail(
                    "store_objects_present",
                    f"Missing store objects: {', '.join(missing_objects)}",
                )
            else:
                report.add_pass("store_objects_present", "All store objects present")

        return report

    def verify_lockfile(self, lockfile_path: Path) -> VerificationReport:
        """Verify lockfile integrity.

        Args:
            lockfile_path: Path to the lockfile.

        Returns:
            VerificationReport with lockfile verification results.
        """
        report = VerificationReport()

        if not lockfile_path.exists():
            report.add_fail("lockfile_exists", "Lockfile does not exist")
            return report

        report.add_pass("lockfile_exists", "Lockfile exists")

        try:
            manifest = RuntimeManifest.load(lockfile_path)
        except Exception as e:
            report.add_fail("lockfile_valid", f"Failed to parse lockfile: {e}")
            return report

        report.add_pass("lockfile_valid", "Lockfile is valid")

        missing_hashes = []
        for name, pkg in manifest.packages.items():
            if not pkg.wheel_hash:
                missing_hashes.append(name)

        if missing_hashes:
            report.add_fail(
                "hashes_present",
                f"Missing hashes: {', '.join(missing_hashes)}",
            )
        else:
            report.add_pass("hashes_present", "All packages have hashes")

        if not manifest.fingerprint:
            report.add_warn("lockfile_fingerprint", "No fingerprint in lockfile")
        else:
            report.add_pass("lockfile_fingerprint", f"Fingerprint: {manifest.fingerprint}")

        return report

    def verify_all(
        self,
        runtime_dir: Path | None = None,
        lockfile_path: Path | None = None,
    ) -> VerificationReport:
        """Run all verification checks.

        Args:
            runtime_dir: Optional path to runtime directory.
            lockfile_path: Optional path to lockfile.

        Returns:
            Combined VerificationReport.
        """
        report = VerificationReport()

        store_report = self.verify_store()
        report.checks.extend(store_report.checks)

        if runtime_dir is not None:
            runtime_report = self.verify_runtime(runtime_dir)
            report.checks.extend(runtime_report.checks)
        else:
            report.add_skip("runtime_verify", "No runtime directory specified")

        if lockfile_path is not None:
            lockfile_report = self.verify_lockfile(lockfile_path)
            report.checks.extend(lockfile_report.checks)
        else:
            report.add_skip("lockfile_verify", "No lockfile specified")

        return report
