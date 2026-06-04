"""Exception hierarchy for UVG."""

from __future__ import annotations


class UVGError(Exception):
    """Base exception for all UVG errors."""


class StoreError(UVGError):
    """Base exception for store operations."""


class ObjectNotFoundError(StoreError):
    """Raised when a store object is not found."""

    def __init__(self, object_hash: str) -> None:
        super().__init__(f"Store object not found: {object_hash}")
        self.object_hash = object_hash


class ObjectExistsError(StoreError):
    """Raised when attempting to create a duplicate store object."""

    def __init__(self, object_hash: str) -> None:
        super().__init__(f"Store object already exists: {object_hash}")
        self.object_hash = object_hash


class HashMismatchError(StoreError):
    """Raised when a hash verification fails."""

    def __init__(self, expected: str, actual: str, context: str = "") -> None:
        message = f"Hash mismatch: expected {expected}, got {actual}"
        if context:
            message = f"{context}: {message}"
        super().__init__(message)
        self.expected = expected
        self.actual = actual


class StoreCorruptionError(StoreError):
    """Raised when store integrity is compromised."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Store corruption detected: {message}")


class RuntimeOperationError(UVGError):
    """Base exception for runtime operations."""


class RuntimeNotFoundError(RuntimeError):
    """Raised when a runtime is not found."""

    def __init__(self, project_path: str) -> None:
        super().__init__(f"Runtime not found for project: {project_path}")
        self.project_path = project_path


class FingerprintMismatchError(RuntimeError):
    """Raised when a runtime fingerprint does not match expected."""

    def __init__(self, expected: str, actual: str) -> None:
        super().__init__(f"Fingerprint mismatch: expected {expected}, got {actual}")
        self.expected = expected
        self.actual = actual


class DatabaseIndexError(UVGError):
    """Base exception for index/database operations."""


class IndexCorruptionError(DatabaseIndexError):
    """Raised when index integrity is compromised."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Index corruption detected: {message}")


class SecurityError(UVGError):
    """Base exception for security operations."""


class VerificationFailedError(SecurityError):
    """Raised when a security verification fails."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Verification failed: {message}")


class OfflineResolutionError(UVGError):
    """Raised when offline resolution fails."""

    def __init__(self, package_name: str, package_version: str) -> None:
        super().__init__(
            f"Package not available offline: {package_name}=={package_version}. "
            "Run in online mode first to download packages."
        )
        self.package_name = package_name
        self.package_version = package_version


class CredentialNotFoundError(SecurityError):
    """Raised when registry credentials are not found."""

    def __init__(self, registry: str) -> None:
        super().__init__(f"No credentials found for registry: {registry}")
        self.registry = registry


class CLIError(UVGError):
    """Base exception for CLI operations."""


class ConfigurationError(UVGError):
    """Raised when configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(f"Configuration error: {message}")
