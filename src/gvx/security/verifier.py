"""Security verification engine.

Verifies runtime consistency and lockfile validity.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from gvx.runtime.manifest import RuntimeManifest
from gvx.uv.lockfile import GVXLockfile


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
    """Verifies security properties of GVX artifacts.

    Provides comprehensive verification of:
    - Runtime manifest consistency
    - Lockfile validity
    - Symlink integrity
    """

    def __init__(self) -> None:
        """Initialize security verifier."""
        pass

    def verify_runtime(self, runtime_dir: Path) -> VerificationReport:
        """Verify runtime integrity.

        Args:
            runtime_dir: Path to runtime directory.

        Returns:
            VerificationReport with runtime verification results.
        """
        report = VerificationReport()

        if not runtime_dir.exists():
            report.add_fail("runtime_exists", "Runtime directory does not exist")
            return report

        report.add_pass("runtime_exists", "Runtime directory exists")

        # Check manifest
        manifest_path = runtime_dir / "manifest.json"
        if not manifest_path.exists():
            report.add_fail("manifest_exists", "Manifest file does not exist")
            return report

        report.add_pass("manifest_exists", "Manifest file exists")

        try:
            manifest = RuntimeManifest.load(manifest_path)
            report.add_pass("manifest_valid", "Manifest is valid JSON")
        except Exception as e:
            report.add_fail("manifest_valid", f"Failed to parse manifest: {e}")
            return report

        # Check fingerprint
        if not manifest.fingerprint:
            report.add_warn("fingerprint_present", "No fingerprint in manifest")
        else:
            report.add_pass("fingerprint_present", f"Fingerprint: {manifest.fingerprint}")

        # Check symlinks
        site_packages = runtime_dir / "site-packages"
        if not site_packages.exists():
            report.add_fail("site_packages_exists", "site-packages directory does not exist")
        else:
            report.add_pass("site_packages_exists", "site-packages directory exists")

            # Verify symlinks
            broken_links = []
            for link in site_packages.iterdir():
                if link.is_symlink() and not link.exists():
                    broken_links.append(link.name)

            if broken_links:
                report.add_fail("symlinks_valid", f"Broken symlinks: {', '.join(broken_links)}")
            else:
                report.add_pass("symlinks_valid", "All symlinks are valid")

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
            lockfile = GVXLockfile.load(lockfile_path)
        except Exception as e:
            report.add_fail("lockfile_valid", f"Failed to parse lockfile: {e}")
            return report

        report.add_pass("lockfile_valid", "Lockfile is valid")

        missing_hashes = []
        for pkg in lockfile.packages:
            if not pkg.hash:
                missing_hashes.append(pkg.name)

        if missing_hashes:
            report.add_fail(
                "hashes_present",
                f"Missing hashes: {', '.join(missing_hashes)}",
            )
        else:
            report.add_pass("hashes_present", "All packages have hashes")

        if not lockfile.fingerprint:
            report.add_warn("lockfile_fingerprint", "No fingerprint in lockfile")
        else:
            report.add_pass("lockfile_fingerprint", f"Fingerprint: {lockfile.fingerprint}")

        return report

    def verify_all(
        self,
        runtime_dir: Path | None = None,
        lockfile_path: Path | None = None,
    ) -> VerificationReport:
        """Run all verification checks.

        Args:
            runtime_dir: Optional runtime directory.
            lockfile_path: Optional lockfile path.

        Returns:
            VerificationReport with all verification results.
        """
        report = VerificationReport()

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
